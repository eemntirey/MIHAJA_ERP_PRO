from flask_restx import Namespace, Resource
from app.security.tenant import tenant_required_readonly
from app.security.permissions import permission_required
from app.services.facturation_service import issue_invoice
from app import db

api = Namespace('factures', description='Gestion des factures')

@api.route('/')
class FactureList(Resource):
    @permission_required('invoice.view')
    @tenant_required_readonly
    def get(self):
        """Liste toutes les factures"""
        from app.models.facture import Facture
        from app.security.tenant import get_current_tenant_id
        tenant_id = get_current_tenant_id()
        query = Facture.query.filter_by(is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        factures = query.all()
        result = []
        for f in factures:
            d = f.to_dict()
            paiements = [p.to_dict() for p in f.paiements.filter_by(is_active=True).all()]
            d['paiements'] = paiements
            result.append(d)
        return {'factures': result}, 200

    @permission_required('invoice.create')
    @tenant_required_readonly
    def post(self):
        """Creation de facture"""
        from flask import request
        data = request.get_json()
        facture = issue_invoice(data)
        return facture.to_dict(), 201

@api.route('/<int:id>')
class FactureResource(Resource):
    @permission_required('invoice.view')
    @tenant_required_readonly
    def get(self, id):
        """Details d'une facture"""
        from app.models.facture import Facture
        from app.models.paiement import Paiement
        from app.security.tenant import tenant_filtered_get
        from app.security.tenant import get_current_tenant_id
        facture = tenant_filtered_get(Facture, id)
        if not facture:
            return {'message': 'Facture non trouvee'}, 404
        tenant_id = get_current_tenant_id()
        query = Paiement.query.filter_by(facture_id=id, is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        paiements = query.all()
        result = facture.to_dict()
        result['paiements'] = [p.to_dict() for p in paiements]
        return result, 200

    @permission_required('invoice.update')
    @tenant_required_readonly
    def put(self, id):
        """Met a jour une facture"""
        from app.models.facture import Facture
        from app.security.tenant import tenant_filtered_get
        from flask import request
        facture = tenant_filtered_get(Facture, id)
        if not facture:
            return {'message': 'Facture non trouvee'}, 404
        data = request.get_json()
        try:
            PROTECTED = {'id', 'created_at', 'updated_at', 'created_by', 'updated_by', 'tenant_id', 'is_active'}
            for key, value in data.items():
                if key in PROTECTED:
                    continue
                if hasattr(facture, key):
                    setattr(facture, key, value)
            db.session.commit()
            return facture.to_dict(), 200
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 400

    @permission_required('invoice.update')
    @tenant_required_readonly
    def delete(self, id):
        """Supprime une facture"""
        from app.models.facture import Facture
        from app.models.paiement import Paiement
        from app.security.tenant import tenant_filtered_get
        facture = tenant_filtered_get(Facture, id)
        if not facture:
            return {'message': 'Facture non trouvee'}, 404
        try:
            facture.is_active = False
            Paiement.query.filter_by(facture_id=id, is_active=True, tenant_id=facture.tenant_id).update({'is_active': False})
            db.session.commit()
            return {'message': 'Facture supprimee'}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 400

@api.route('/from-vente/<int:vente_id>')
class FactureFromVente(Resource):
    @permission_required('invoice.create')
    @tenant_required_readonly
    def post(self, vente_id):
        """Genere une facture depuis une vente"""
        from app.models.vente import Vente
        from app.models.facture import Facture
        from flask import request
        from app.security.tenant import tenant_filtered_get
        vente = tenant_filtered_get(Vente, vente_id)
        if not vente:
            return {'message': 'Vente non trouvee'}, 404
        data = request.get_json() or {}
        try:
            existing = Facture.query.filter_by(vente_id=vente.id, is_active=True, tenant_id=vente.tenant_id).first()
            if existing:
                return {'message': 'Une facture existe deja pour cette vente', 'facture': existing.to_dict()}, 409
            facture = Facture(
                vente_id=vente.id,
                client_id=vente.client_id,
                tenant_id=vente.tenant_id,
                reference=data.get('reference', f"FAC-{vente.reference}"),
                total_ht=vente.total_ht,
                total_ttc=vente.total_ttc,
                statut=data.get('statut', 'non_payee')
            )
            facture.save()
            return facture.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 400

