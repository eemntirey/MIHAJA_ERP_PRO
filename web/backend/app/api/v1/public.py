from flask import request, current_app, g
from flask_restx import Namespace, Resource
from app.models.produit import Produit
from app.models.tenant import Tenant
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.commande_client import CommandeClient
from app.services.commande_service import CommandeService
from app import db
from app.security.rate_limit import rate_limit
from datetime import datetime

MAX_PUBLIC_ORDER_TOTAL = 500000

ns_public = Namespace('public', description='API publique (catalogue, commandes, notifications)')
ns = ns_public


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
    now = datetime.utcnow()
    active_ids = [
        row[0] for row in db.session.query(Abonnement.tenant_id)
        .filter(
            Abonnement.statut == StatutAbonnement.ACTIF,
            Abonnement.date_fin > now,
            Abonnement.is_active == True
        )
        .distinct()
        .all()
    ]
    return set(active_ids)


@ns_public.route('/produits')
class PublicProduitList(Resource):
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
    def get(self, tenant_id):
        tenant = Tenant.query.filter_by(id=tenant_id, is_active=True).first()
        if not tenant:
            return {'message': 'Vendeur non trouve'}, 404
        data = {
            'id': tenant.id,
            'nom': tenant.nom,
            'slug': tenant.slug,
            'ville': tenant.ville,
            'pays': tenant.pays,
            'statut': tenant.statut.value if hasattr(tenant.statut, 'value') else tenant.statut,
            'plan': tenant.plan,
        }
        return data, 200


@ns_public.route('/commandes')
class PublicCommandeCreate(Resource):
    @rate_limit(3, 300)
    def post(self):
        data = request.get_json() or {}

        data.pop('tenant_id', None)
        data.pop('is_active', None)

        # Résolution du tenant via les en-têtes publics (slug ou domaine)
        tenant = _resolve_public_tenant()
        if not tenant:
            return {
                'message': 'Tenant requis (X-Tenant-Slug ou X-Tenant-Domaine)'
            }, 400
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
            return commande.to_dict(), 201
        except ValueError as e:
            return {'message': str(e)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Erreur création commande publique')
            return {'message': 'Erreur lors de la création de la commande'}, 500


@ns_public.route('/commandes/tracking/<string:ref>')
class PublicCommandeTracking(Resource):
    def get(self, ref):
        commande = CommandeService.get_by_reference(ref)
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


@ns_public.route('/notifications')
class PublicNotifications(Resource):
    def get(self):
        ref = request.args.get('ref')
        if ref:
            commande = CommandeService.get_by_reference(ref)
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
