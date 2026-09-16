from flask import request, current_app, g
from flask_restx import Namespace, Resource
from app.models.produit import Produit
from app.models.tenant import Tenant
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.commande_client import CommandeClient
from app.services.commande_service import CommandeService
from app.services.commande_papi_service import (
    CommandePapiError,
    create_commande_papi_payment,
    ELECTRONIC_METHODS,
)
from app import db
from app.security.rate_limit import rate_limit
from datetime import datetime

MAX_PUBLIC_ORDER_TOTAL = 500000

ns_public = Namespace('public', description='API publique (catalogue, commandes, notifications)')
ns = ns_public


def _resolve_public_commande(ref):
    """Résout une commande pour les endpoints vitrine (tracking, paiement,
    statut) en bornant strictement la portée.

    La recherche par référence dans CommandeService n'est filtrée par tenant
    QUAND un JWT portant un tenant_id est présent — un appelant anonyme
    retombait sur une portée globale (audit P2-4). On re-scope donc ici :
    autorisé si la commande appartient à un tenant éligible vitrine, OU si
    le JWT présent autorise explicitement son propriétaire (commande liée
    à un compte particulier).
    """
    commande = CommandeService.get_by_reference(ref)
    if not commande or not commande.tenant_id:
        return None
    try:
        if commande.tenant_id in _get_active_tenant_ids():
            return commande
    except Exception:
        return None
    if commande.utilisateur_id:
        try:
            from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
            verify_jwt_in_request(optional=True)
            ident = get_jwt_identity()
            if ident is not None and str(ident).isdigit() and int(ident) == commande.utilisateur_id:
                return commande
        except Exception:
            return None
    return None


def _resolve_public_tenant():
    """Résout un tenant côté public via les en-têtes X-Tenant-Slug / X-Tenant-Domaine.

    Sans tenant, l'accès au catalogue public reste possible (cas "landing"
    multi-tenant), mais la création de commande exige un tenant connu.

    Le tenant résolu est mis en cache dans ``g.public_tenant`` afin que
    les endpoints de catalogue (liste + détail) puissent l'utiliser pour
    filtrer strictement les produits exposés.
    """
    cached = getattr(g, 'public_tenant', None)
    if cached is not None:
        return cached

    tenant_slug = request.headers.get('X-Tenant-Slug')
    tenant_domaine = request.headers.get('X-Tenant-Domaine')
    if not tenant_slug and not tenant_domaine:
        g.public_tenant = None
        return None
    query = Tenant.query.filter_by(is_active=True)
    if tenant_slug:
        tenant = query.filter_by(slug=tenant_slug).first()
    else:
        tenant = query.filter_by(domaine=tenant_domaine).first()
    g.public_tenant = tenant
    return tenant


def _scope_query_to_tenant(query):
    """Filtre optionnellement une requête Produit par tenant public.

    Si l'appelant a fourni un identifiant de tenant (via les en-têtes
    ``X-Tenant-Slug`` / ``X-Tenant-Domaine``), le résultat est strictement
    limité aux produits de ce tenant — un visiteur d'un tenant ne doit
    jamais voir les produits d'un autre tenant.

    Sans en-tête, on conserve le comportement "landing" actuel (tous les
    tenants actifs).
    """
    tenant = _resolve_public_tenant()
    if tenant is not None:
        return query.filter(Produit.tenant_id == tenant.id)
    return query


def _get_active_tenant_ids():
    """Liste des tenants exposés sur la vitrine commune.
    Un tenant apparaît dans la vitrine publique si et seulement si :
    - il a un Abonnement actif non expiré ;
    - il a configuré son compte marchand Papi ;
    - il a explicitement activé le toggle vitrine (vitrine_enabled=True).

    Ces trois conditions cumulatives évitent d'exposer un tenant qui n'est
    pas prêt à recevoir des paiements en ligne pour ses commandes.
    """
    now = datetime.utcnow()
    eligible_ids = {
        row[0] for row in db.session.query(Abonnement.tenant_id)
        .filter(
            Abonnement.statut == StatutAbonnement.ACTIF,
            Abonnement.date_fin > now,
            Abonnement.is_active == True,
        )
        .distinct()
        .all()
    }
    if not eligible_ids:
        return set()

    tenants = Tenant.query.filter(Tenant.id.in_(eligible_ids)).all()
    return {t.id for t in tenants if t.is_vitrine_active()}


def _infer_tenant_from_items(items):
    """Déduit le tenant vendeur depuis le premier produit du panier.

    Utilisé uniquement quand aucun en-tête X-Tenant-* n'est fourni
    (Checkout sans contexte vendeur). Le service refuse ensuite tout
    panier mélangeant plusieurs tenants (ValueError -> 400), donc ce
    fallback ne peut jamais élargir l'accès : il lève 400/404 au pire.
    """
    try:
        if not isinstance(items, list) or not items:
            return None
        first = items[0] if isinstance(items[0], dict) else None
        if not first:
            return None
        produit_id = first.get('produit_id')
        if not produit_id:
            return None
        produit = db.session.get(Produit, int(produit_id))
        if not produit or not getattr(produit, 'tenant_id', None):
            return None
        return db.session.get(Tenant, produit.tenant_id)
    except Exception:
        return None


@ns_public.route('/produits')
class PublicProduitList(Resource):
    @rate_limit(30, 300)
    def get(self):
        active_tenant_ids = _get_active_tenant_ids()
        scoped_tenant = _resolve_public_tenant()
        if scoped_tenant is not None:
            if not active_tenant_ids or scoped_tenant.id not in active_tenant_ids:
                return {'produits': []}, 200
            allowed_tenant_ids = {scoped_tenant.id}
        else:
            allowed_tenant_ids = active_tenant_ids

        query = Produit.query.filter(
            Produit.is_active == True,
            Produit.published == True,
            Produit.quantite_stock > 0,
            Produit.quantite_stock > Produit.seuil_alerte,
        )
        if allowed_tenant_ids:
            query = query.filter(Produit.tenant_id.in_(allowed_tenant_ids))
        else:
            query = query.filter(Produit.tenant_id == -1)
        produits = query.all()
        tenant_map = {}
        if allowed_tenant_ids:
            tenants = Tenant.query.filter(Tenant.id.in_(allowed_tenant_ids)).all()
            tenant_map = {t.id: t.nom for t in tenants}
        result = []
        for p in produits:
            d = p.to_public_dict()
            d['tenant_nom'] = tenant_map.get(p.tenant_id, '')
            result.append(d)
        return {'produits': result}, 200


@ns_public.route('/produits/<int:produit_id>')
class PublicProduitDetail(Resource):
    @rate_limit(30, 300)
    def get(self, produit_id):
        active_tenant_ids = _get_active_tenant_ids()
        scoped_tenant = _resolve_public_tenant()
        if scoped_tenant is not None:
            if not active_tenant_ids or scoped_tenant.id not in active_tenant_ids:
                return {'message': 'Produit non trouve'}, 404
            allowed_tenant_ids = {scoped_tenant.id}
        else:
            allowed_tenant_ids = active_tenant_ids

        produit = Produit.query.filter(
            Produit.id == produit_id,
            Produit.is_active == True,
            Produit.published == True,
            Produit.quantite_stock > 0,
            Produit.quantite_stock > Produit.seuil_alerte,
        )
        if allowed_tenant_ids:
            produit = produit.filter(Produit.tenant_id.in_(allowed_tenant_ids))
        else:
            produit = produit.filter(Produit.tenant_id == -1)
        produit = produit.first()
        if not produit:
            return {'message': 'Produit non trouve'}, 404
        data = produit.to_public_dict()
        if produit.tenant_id and produit.tenant_id in (allowed_tenant_ids or set()):
            tenant = db.session.get(Tenant, produit.tenant_id)
            if tenant:
                data['tenant_nom'] = tenant.nom
        else:
            data['tenant_nom'] = ''
        return data, 200


@ns_public.route('/tenants/<int:tenant_id>')
class PublicTenantDetail(Resource):
    @rate_limit(30, 300)
    def get(self, tenant_id):
        # Un tenant n'est visible publiquement QUE s'il est éligible
        # vitrine (abonnement actif + Papi configuré + vitrine_enabled).
        # Sans ce gate, un attaquant itérait les IDs et lisait slug,
        # domaine, statut interne et plan de TOUS les tenants actifs,
        # y compris suspendus ou jamais exposés (audit P1-1).
        if tenant_id not in _get_active_tenant_ids():
            return {'message': 'Vendeur non trouve'}, 404
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            return {'message': 'Vendeur non trouve'}, 404
        data = {
            'id': tenant.id,
            'nom': tenant.nom,
            'slug': tenant.slug,
            'domaine': tenant.domaine,
            'ville': tenant.ville,
            'pays': tenant.pays,
        }
        return data, 200


@ns_public.route('/commandes')
class PublicCommandeCreate(Resource):
    # Cache d'idempotence en mémoire (clé -> reference de commande).
    # Évite les doublons sur double-clic / refresh pendant l'envoi.
    # TTL : 10 minutes. En multi-processus, chaque worker garde son cache :
    # la collision de référence reste impossible (référence unique en DB) et
    # le pire cas est une commande en double si deux workers reçoivent la
    # même clé simultanément — le frontend verrouille déjà le bouton.
    _idempotency_cache = {}
    _idempotency_ttl_s = 600

    @classmethod
    def _idempotency_get(cls, key):
        import time
        entry = cls._idempotency_cache.get(key)
        if not entry:
            return None
        ref, ts = entry
        if time.time() - ts > cls._idempotency_ttl_s:
            cls._idempotency_cache.pop(key, None)
            return None
        return ref

    @classmethod
    def _idempotency_put(cls, key, ref):
        import time
        # Borne anti-fuite mémoire : 2000 entrées max.
        if len(cls._idempotency_cache) > 2000:
            cls._idempotency_cache.clear()
        cls._idempotency_cache[key] = (ref, time.time())

    @rate_limit(30, 300)
    def post(self):
        # silent=True : un corps JSON invalide ne doit jamais produire un 500
        # (werkzeug BadRequest non interceptee par flask-restx) mais un 4xx
        # explicite et exploitable (audit #7 - jamais de 500 sur saisie invalide).
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not data:
            return {'message': "Corps de requete JSON invalide ou vide"}, 400

        data.pop('tenant_id', None)
        data.pop('is_active', None)

        # Idempotence : même clé = même réponse, jamais de 2e commande.
        idempotency_key = request.headers.get('Idempotency-Key')
        if idempotency_key:
            cached_ref = self._idempotency_get(idempotency_key)
            if cached_ref:
                commande = _resolve_public_commande(cached_ref)
                if commande:
                    return commande.to_public_dict(), 200

        # Lier la commande au compte connecté (si un JWT valide est présent).
        # Une commande invité (sans JWT) reste valide : utilisateur_id = None.
        utilisateur_id = None
        try:
            from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
            verify_jwt_in_request(optional=True)
            ident = get_jwt_identity()
            if ident is not None and str(ident).isdigit():
                utilisateur_id = int(ident)
        except Exception:
            utilisateur_id = None
        data['utilisateur_id'] = utilisateur_id

        # Résolution du tenant via les en-têtes publics (slug ou domaine).
        # Fallback : si aucun en-tête (panier multi-produits sans contexte),
        # on déduit le tenant depuis le premier produit du panier — le
        # service refuse ensuite tout panier multi-tenant (ValueError 400).
        tenant = _resolve_public_tenant()
        if not tenant:
            tenant = _infer_tenant_from_items(data.get('items', []))
        if not tenant:
            return {
                'message': 'Tenant requis (X-Tenant-Slug ou X-Tenant-Domaine)'
            }, 400

        # Vérifier que le tenant est actif sur la vitrine
        try:
            active_tenant_ids = _get_active_tenant_ids()
        except Exception:
            current_app.logger.exception('Vérification vitrine impossible')
            return {
                'message': 'Service de commande momentanément indisponible, réessayez.',
            }, 503
        if not active_tenant_ids or tenant.id not in active_tenant_ids:
            return {'message': 'Ce vendeur ne prend pas de commandes publiques actuellement'}, 403

        data['tenant_id'] = tenant.id

        client = data.get('client') or {}
        nom_client = data.get('nom_client') or client.get('nom')
        email_client = data.get('email_client') or client.get('email')
        items = data.get('items', [])

        missing = []
        if not nom_client:
            missing.append('nom_client')
        if not email_client:
            missing.append('email_client')
        if not items:
            missing.append('items')
        if missing:
            return {'message': f"Champs requis manquants: {', '.join(missing)}"}, 400

        if not isinstance(items, list) or len(items) == 0:
            return {'message': 'Le panier doit contenir au moins un article'}, 400

        try:
            commande = CommandeService.create_commande(data)
            if commande.total_ttc > MAX_PUBLIC_ORDER_TOTAL:
                db.session.delete(commande)
                db.session.commit()
                return {'message': 'Montant de commande trop eleve pour un achat public'}, 403
            if idempotency_key:
                self._idempotency_put(idempotency_key, commande.reference)
            return commande.to_public_dict(), 201
        except ValueError as e:
            return {'message': str(e)}, 400
        except Exception as exc:
            db.session.rollback()
            current_app.logger.exception('Erreur création commande publique: %s', exc)
            # Message générique : jamais renvoyer str(exc) à un anonyme
            # (audit P2-4 — fuite d'informations sur les internes/schema).
            return {
                'message': 'Erreur lors de la création de la commande. Vérifiez les coordonnées, le panier et le mode de paiement.',
            }, 500


@ns_public.route('/commandes/tracking/<string:ref>')
class PublicCommandeTracking(Resource):
    @rate_limit(30, 300)
    def get(self, ref):
        commande = _resolve_public_commande(ref)
        if not commande:
            return {'message': 'Commande non trouvee'}, 404
        statut_value = (
            commande.statut.value
            if hasattr(commande.statut, 'value')
            else commande.statut
        )
        return {
            'reference': commande.reference,
            'statut': statut_value,
            'updated_at': commande.updated_at.isoformat() if commande.updated_at else None,
        }, 200


@ns_public.route('/commandes/<string:ref>/papi-payment')
class PublicCommandePapiPayment(Resource):
    @rate_limit(5, 300)
    def post(self, ref):
        """Crée un lien de paiement Papi (compte marchand du tenant) pour
        une commande vitrine existante. Le client est ensuite redirigé
        vers le ``paymentLink`` retourné.
        """
        commande = _resolve_public_commande(ref)
        if not commande:
            return {'message': 'Commande introuvable'}, 404

        tenant = db.session.get(Tenant, commande.tenant_id) if commande.tenant_id else None
        if not tenant:
            return {'message': 'Vendeur introuvable'}, 404

        if not tenant.is_vitrine_active():
            return {
                'message': (
                    "Le paiement en ligne n'est pas disponible pour ce vendeur. "
                    "Veuillez choisir le paiement à la livraison."
                )
            }, 400

        data = request.get_json() or {}
        payment_method = (data.get('payment_method') or 'MVOLA').upper()
        if payment_method not in ELECTRONIC_METHODS:
            return {
                'message': (
                    f"Mode de paiement invalide. "
                    f"Choisissez parmi: {', '.join(ELECTRONIC_METHODS)}"
                )
            }, 400

        # Récupération des infos client pour pré-remplir le payload Papi
        client_info = data.get('client') or {}
        customer_name = (
            f"{commande.prenom_client or ''} {commande.nom_client or ''}".strip()
            or client_info.get('nom')
            or ''
        )
        customer_email = commande.email_client or client_info.get('email') or ''
        customer_phone = (
            commande.telephone_client
            or client_info.get('telephone')
            or ''
        )

        try:
            result = create_commande_papi_payment(
                commande_id=commande.id,
                payment_method=payment_method,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                is_test_mode=bool(data.get('is_test_mode', False)),
            )
        except CommandePapiError as exc:
            current_app.logger.warning(
                'Commande Papi payment error: ref=%s err=%s', ref, exc
            )
            return {'message': 'Erreur lors de la creation du paiement'}, 400
        except Exception:
            current_app.logger.exception(
                'Erreur inattendue paiement Papi commande: ref=%s', ref
            )
            return {'message': 'Erreur lors de la création du paiement'}, 500

        return result, 200


@ns_public.route('/commandes/<string:ref>/papi-status')
class PublicCommandePapiStatus(Resource):
    """Permet au frontend de savoir si la commande a été payée (statut minimal)."""

    @rate_limit(30, 300)
    def get(self, ref):
        commande = _resolve_public_commande(ref)
        if not commande:
            return {'message': 'Commande introuvable'}, 404

        from app.models.paiement import Paiement
        paiement = Paiement.query.filter_by(
            commande_client_id=commande.id,
            provider='papi',
            is_active=True,
        ).order_by(Paiement.created_at.desc()).first()

        data = {
            'reference': commande.reference,
            'statut': (
                commande.statut.value
                if hasattr(commande.statut, 'value')
                else commande.statut
            ),
            # Minimal : expose seulement l'état du paiement, jamais le détail complet
            'paiement_statut': (
                paiement.statut.value
                if paiement and hasattr(paiement.statut, 'value')
                else (paiement.statut if paiement else None)
            ),
            'paiement_updated_at': (
                paiement.updated_at.isoformat()
                if paiement and getattr(paiement, 'updated_at', None)
                else None
            ),
        }
        return data, 200


@ns_public.route('/mes-commandes')
class PublicMesCommandes(Resource):
    @rate_limit(30, 300)
    def get(self):
        """Liste les commandes du compte connecté (tous vendeurs confondus).

        Nécessite un JWT valide (utilisateur "particulier" connecté sur la
        vitrine). Le filtrage par utilisateur_id garantit l'isolation des
        données : le bypass du filtre tenant global est nécessaire car les
        commandes appartiennent aux tenants vendeurs, pas au client.
        """
        from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
        try:
            verify_jwt_in_request()
        except Exception:
            return {'message': 'Authentification requise'}, 401

        user_id = get_jwt_identity()
        if isinstance(user_id, str) and user_id.isdigit():
            user_id = int(user_id)
        if not user_id:
            return {'message': 'Authentification requise'}, 401

        commandes = (
            CommandeClient.query
            .filter_by(utilisateur_id=user_id, is_active=True)
            .order_by(CommandeClient.created_at.desc())
            .limit(50)
            .execution_options(_skip_tenant_filter=True)
            .all()
        )
        return {'commandes': [c.to_dict() for c in commandes]}, 200


@ns_public.route('/notifications')
class PublicNotifications(Resource):
    @rate_limit(30, 300)
    def get(self):
        ref = request.args.get('ref')
        if ref:
            commande = _resolve_public_commande(ref)
            if not commande:
                return {'message': 'Commande non trouvee'}, 404

            statut_value = (
                commande.statut.value
                if hasattr(commande.statut, 'value')
                else commande.statut
            )

            return {
                'commande_ref': commande.reference,
                'statut': statut_value,
                'notifications': [
                    {
                        'message': f"Commande {statut_value}",
                        'date': commande.updated_at.isoformat() if commande.updated_at else None,
                        'statut': statut_value
                    }
                ]
            }, 200

        return {'notifications': []}, 200
    
    def post(self):
        data = request.get_json() or {}
        return {
            'message': 'Notification non supportée pour l\'instant. Utilisez /api/v1/notifications pour créer des notifications.',
            'data': data
        }, 501
