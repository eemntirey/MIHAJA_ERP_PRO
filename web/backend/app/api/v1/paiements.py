from flask_restx import Namespace, Resource
from app.security.tenant import tenant_required
from app.services.paiement_service import process_payment
from app import db

ns = Namespace('paiements', description='Gestion des paiements')

@ns.route('/')
class PaiementList(Resource):
    @tenant_required
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

    @tenant_required
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
    @tenant_required
    def get(self, id):
        """Details d'un paiement"""
        from app.models.paiement import Paiement
        from app.security.tenant import tenant_filtered_get
        paiement = tenant_filtered_get(Paiement, id)
        if not paiement:
            return {'message': 'Paiement non trouve'}, 404
        return paiement.to_dict(), 200

    @tenant_required
    def put(self, id):
        """Met a jour un paiement"""
        from app.models.paiement import Paiement
        from app.security.tenant import tenant_filtered_get
        from app.services.paiement_service import _normalize_payment_data
        from flask import request
        paiement = tenant_filtered_get(Paiement, id)
        if not paiement:
            return {'message': 'Paiement non trouve'}, 404
        data = request.get_json()
        if not data:
            return {'message': 'Donnees requises'}, 400
        try:
            normalized = _normalize_payment_data(data)
            for key, value in normalized.items():
                if key not in ['id', 'created_at', 'updated_at', 'created_by', 'updated_by', 'tenant_id']:
                    setattr(paiement, key, value)
            db.session.commit()
            return paiement.to_dict(), 200
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 400

    @tenant_required
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
            return {'message': 'Paiement supprime'}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 400

@ns.route('/facture/<int:facture_id>')
class PaiementFactureResource(Resource):
    @tenant_required
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

