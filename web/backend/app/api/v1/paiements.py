from flask_restx import Namespace, Resource
from app.security.tenant import tenant_required_readonly
from app.security.permissions import permission_required
from app.services.paiement_service import process_payment
from app import db

ns = Namespace('paiements', description='Gestion des paiements')

@ns.route('/')
class PaiementList(Resource):
    @permission_required('payment.view')
    @tenant_required_readonly
    def get(self):
        """Liste tous les paiements"""
        from app.models.paiement import Paiement
        from app.security.tenant import get_current_tenant_id
        tenant_id = get_current_tenant_id()
        query = Paiement.query.filter_by(is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        paiements = query.all()
        return {'paiements': [p.to_dict() for p in paiements]}, 200

    @permission_required('payment.create')
    @tenant_required_readonly
    def post(self):
        """Creation de paiement"""
        from flask import request
        from flask_restx import abort
        data = request.get_json()
        if not data:
            return {'message': 'Donnees requises'}, 400
        
        montant = data.get('montant')
        if montant is None or float(montant) <= 0:
            return {'message': 'Le montant est requis et doit etre superieur a 0'}, 400
        
        facture_id = data.get('facture_id')
        if facture_id:
            from app.models.facture import Facture
            from app.security.tenant import get_current_tenant_id
            tenant_id = get_current_tenant_id()
            query = Facture.query.filter_by(id=facture_id, is_active=True)
            if tenant_id is not None:
                query = query.filter_by(tenant_id=tenant_id)
            facture = query.first()
            if not facture:
                return {'message': 'Facture non trouvee'}, 404
        
        paiement = process_payment(data)
        return paiement.to_dict(), 201

@ns.route('/<int:id>')
class PaiementResource(Resource):
    @permission_required('payment.view')
    @tenant_required_readonly
    def get(self, id):
        """Details d'un paiement"""
        from app.models.paiement import Paiement
        from app.security.tenant import tenant_filtered_get
        paiement = tenant_filtered_get(Paiement, id)
        if not paiement:
            return {'message': 'Paiement non trouve'}, 404
        return paiement.to_dict(), 200

    @permission_required('payment.create')
    @tenant_required_readonly
    def put(self, id):
        """Met a jour un paiement"""
        from app.models.paiement import Paiement
        from app.security.tenant import tenant_filtered_get
        from flask import request
        from app.services.paiement_service import update as update_payment

        paiement = tenant_filtered_get(Paiement, id)
        if not paiement:
            return {'message': 'Paiement non trouve'}, 404
        data = request.get_json()
        if not data:
            return {'message': 'Donnees requises'}, 400
        try:
            paiement = update_payment(id, data)
            return paiement.to_dict(), 200
        except ValueError as e:
            db.session.rollback()
            return {'message': str(e)}, 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Erreur mise a jour paiement')
            return {'message': 'Erreur lors de la mise a jour du paiement'}, 400

    @permission_required('payment.create')
    @tenant_required_readonly
    def delete(self, id):
        """Supprime un paiement"""
        from app.models.paiement import Paiement
        from app.security.tenant import tenant_filtered_get
        paiement = tenant_filtered_get(Paiement, id)
        if not paiement:
            return {'message': 'Paiement non trouve'}, 404
        try:
            paiement.is_active = False
            db.session.commit()
            # Recalcule le statut de la facture (et de la vente liee) :
            # supprimer le paiement peut retrograder facture/vente.
            if paiement.facture_id:
                from app.services.paiement_service import _recompute_facture_status
                _recompute_facture_status(paiement.facture_id)
            return {'message': 'Paiement supprime'}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 400

@ns.route('/facture/<int:facture_id>')
class PaiementFactureResource(Resource):
    @permission_required('payment.view')
    @tenant_required_readonly
    def get(self, facture_id):
        """Liste les paiements d'une facture"""
        from app.models.paiement import Paiement
        from app.security.tenant import get_current_tenant_id
        tenant_id = get_current_tenant_id()
        query = Paiement.query.filter_by(facture_id=facture_id, is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        paiements = query.all()
        return {'paiements': [p.to_dict() for p in paiements]}, 200

