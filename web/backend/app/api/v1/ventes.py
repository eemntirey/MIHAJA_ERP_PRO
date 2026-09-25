from flask_restx import Namespace, Resource, fields
from datetime import datetime, timedelta
from app.security.tenant import tenant_required_readonly
from app.security.permissions import permission_required
from app.services.vente_service import get_sales_summary, create_with_lignes, get_stats, update as update_vente
from flask import request, current_app
from app import db

ns = Namespace('ventes', description='Gestion des ventes')

ligne_vente_model = ns.model('LigneVente', {
    'produit_id': fields.Integer(required=True, description='ID produit'),
    'quantite': fields.Float(required=True, description='Quantité vendue'),
    'prix_unitaire': fields.Float(required=False, description='Prix unitaire HT (auto-sélectionné selon type de client si non fourni)'),
    'taux_tva': fields.Float(description='Taux TVA', default=20),
    'remise': fields.Float(description='Remise en pourcentage', default=0),
})

vente_model = ns.model('Vente', {
    'client_id': fields.Integer(required=True, description='ID client'),
    'type_vente': fields.String(description='Type de vente', default='detail', enum=['gros', 'detail']),
    'date': fields.String(description='Date de la vente'),
    'statut': fields.String(description='Statut de la vente', default='en_attente'),
    'mode_paiement': fields.String(description='Mode de paiement', default='especes'),
    'remarque': fields.String(description='Remarque'),
    'lignes': fields.List(fields.Nested(ligne_vente_model), required=True, description='Lignes de vente'),
})

@ns.route('/')
class VenteList(Resource):
    @permission_required('sale.view')
    @tenant_required_readonly
    def get(self):
        """Liste toutes les ventes"""
        # Filtres de date optionnels : strptime GARDE pour qu'une date
        # invalide (ou vide) donne un 400 francais, jamais un 500 (P0 #16).
        date_debut = request.args.get('date_debut')
        date_fin = request.args.get('date_fin')
        debut = fin = None
        if date_debut is not None:
            try:
                debut = datetime.strptime(date_debut, '%Y-%m-%d')
            except (TypeError, ValueError):
                return {'message': 'Format de date invalide (AAAA-MM-JJ).'}, 400
        if date_fin is not None:
            try:
                fin = datetime.strptime(date_fin, '%Y-%m-%d')
            except (TypeError, ValueError):
                return {'message': 'Format de date invalide (AAAA-MM-JJ).'}, 400
        try:
            borne_fin = fin + timedelta(days=1) if fin is not None else None
            limit_arg = request.args.get('limit')
            ventes = get_sales_summary(debut=debut, fin=borne_fin, limit=limit_arg)
            result = []
            for v in ventes:
                d = v.to_dict()
                if v.client:
                    d['client_nom'] = v.client.nom_complet or v.client.nom
                else:
                    d['client_nom'] = None
                if v.commercial:
                    d['commercial_nom'] = v.commercial.full_name
                else:
                    d['commercial_nom'] = None
                result.append(d)
            return {'ventes': result}, 200
        except Exception:
            current_app.logger.exception('Erreur lors de la liste des ventes')
            return {'ventes': []}, 500

    @ns.doc('create_vente')
    @permission_required('sale.create')
    @tenant_required_readonly
    @ns.expect(vente_model)
    def post(self):
        """Creation de vente"""
        from flask import request
        from app.services.facturation_service import FactureDejaExistante
        data = request.get_json()
        try:
            vente = create_with_lignes(data)
            # Notification temps réel "nouvelle vente" (best effort).
            try:
                from app.services.notification_service import notify_new_sale
                notify_new_sale(vente)
            except Exception:
                current_app.logger.exception('Erreur notification nouvelle vente')
            return vente.to_dict(), 201
        except FactureDejaExistante as e:
            # Conflit idempotent (facture_auto) : 409 avec la facture
            # existante, la vente n'a pas ete creee (transaction annulee).
            db.session.rollback()
            return {
                'message': str(e),
                'facture': e.facture.to_dict() if e.facture else None,
            }, 409
        except ValueError as e:
            db.session.rollback()
            return {'message': str(e)}, 400
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception('Erreur lors de la création de la vente')
            return {'message': f'Erreur lors de la création de la vente: {type(e).__name__}: {str(e)}'}, 400

@ns.route('/<int:id>')
class VenteResource(Resource):
    @permission_required('sale.view')
    @tenant_required_readonly
    def get(self, id):
        """Details d'une vente"""
        from app.models.vente import Vente
        from app.models.ligne_vente import LigneVente
        from app.security.tenant import tenant_filtered_get
        vente = tenant_filtered_get(Vente, id)
        if not vente:
            return {'message': 'Vente non trouvee'}, 404
        lignes = LigneVente.query.filter_by(vente_id=id, is_active=True, tenant_id=vente.tenant_id).all()
        result = vente.to_dict()
        result['lignes_vente'] = [l.to_dict() for l in lignes]
        if vente.client:
            result['client_nom'] = vente.client.nom_complet or vente.client.nom
        else:
            result['client_nom'] = None
        if vente.commercial:
            result['commercial_nom'] = vente.commercial.full_name
        else:
            result['commercial_nom'] = None
        return result, 200

    @permission_required('sale.update')
    @tenant_required_readonly
    def put(self, id):
        """Met a jour une vente"""
        from flask import request
        data = request.get_json() or {}
        try:
            vente = update_vente(id, data)
            if not vente:
                return {'message': 'Vente non trouvee'}, 404
            return vente.to_dict(), 200
        except ValueError as e:
            db.session.rollback()
            return {'message': str(e)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Erreur lors de la mise a jour de la vente')
            return {'message': 'Erreur lors de la mise a jour de la vente'}, 400

    @permission_required('sale.delete')
    @tenant_required_readonly
    def delete(self, id):
        """Supprime une vente (soft-delete en cascade)"""
        from app.models.vente import Vente
        from app.models.ligne_vente import LigneVente
        from app.models.facture import Facture
        from app.models.paiement import Paiement
        from app.security.tenant import tenant_filtered_get
        vente = tenant_filtered_get(Vente, id)
        if not vente:
            return {'message': 'Vente non trouvee'}, 404
        try:
            vente.is_active = False
            LigneVente.query.filter_by(vente_id=id, is_active=True, tenant_id=vente.tenant_id).update({'is_active': False}, synchronize_session=False)
            Facture.query.filter_by(vente_id=id, is_active=True, tenant_id=vente.tenant_id).update({'is_active': False}, synchronize_session=False)
            Paiement.query.filter_by(vente_id=id, is_active=True, tenant_id=vente.tenant_id).update({'is_active': False}, synchronize_session=False)
            from app import db
            db.session.commit()
            return {'message': 'Vente supprimee'}, 200
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Erreur lors de la suppression de la vente')
            return {'message': 'Erreur lors de la suppression de la vente'}, 400


@ns.route('/summary')
class VenteSummary(Resource):
    @permission_required('sale.view')
    @tenant_required_readonly
    def get(self):
        """Statistiques des ventes"""
        stats = get_stats()
        return stats, 200

