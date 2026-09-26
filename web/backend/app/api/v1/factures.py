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
        facture_ids = [f.id for f in factures]
        paiements_by_facture = {}
        if facture_ids:
            from app.models.paiement import Paiement
            payment_query = Paiement.query.filter(
                Paiement.facture_id.in_(facture_ids),
                Paiement.is_active.is_(True),
            )
            if tenant_id:
                payment_query = payment_query.filter(Paiement.tenant_id == tenant_id)
            for paiement in payment_query.all():
                paiements_by_facture.setdefault(paiement.facture_id, []).append(paiement.to_dict())

        result = []
        for f in factures:
            d = f.to_dict()
            d['paiements'] = paiements_by_facture.get(f.id, [])
            result.append(d)
        return {'factures': result}, 200

    @permission_required('invoice.create')
    @tenant_required_readonly
    def post(self):
        """Creation de facture"""
        from flask import request
        from app.services.facturation_service import (
            FactureDejaExistante,
            SuperAdminFactureInterdite,
            ensure_not_super_admin,
        )
        data = request.get_json() or {}
        try:
            # Un super administrateur ne facture jamais les produits
            # d'un tenant (supervision en lecture seule uniquement).
            ensure_not_super_admin()
            facture = issue_invoice(data)
        except SuperAdminFactureInterdite as exc:
            db.session.rollback()
            return {'message': str(exc)}, 403
        except FactureDejaExistante as exc:
            # Idempotence : la facture existante est renvoyee pour que
            # l'utilisateur recupere la bonne reference (jamais de doublon).
            db.session.rollback()
            return {'message': str(exc), 'facture': exc.facture.to_dict() if exc.facture else None}, 409
        except ValueError as e:
            db.session.rollback()
            return {'message': str(e)}, 400
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
            if 'statut' in data:
                # Mise a jour manuelle du statut : on re-synchronise la
                # vente liee (P0 #2) pour ne pas retomber dans l'etat
                # Facture=payee / Vente=en_attente.
                from app.services.facturation_service import _sync_vente_status
                _sync_vente_status(facture)
            db.session.commit()
            return facture.to_dict(), 200
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 400

    @permission_required('invoice.delete')
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
        from flask import request
        from app.security.tenant import tenant_filtered_get
        from app.services.facturation_service import (
            FactureDejaExistante,
            SuperAdminFactureInterdite,
            ensure_not_super_admin,
            issue_invoice,
        )
        try:
            # Un super administrateur ne facture jamais les ventes
            # (produits) d'un tenant, meme en acces global de lecture.
            ensure_not_super_admin()
        except SuperAdminFactureInterdite as exc:
            return {'message': str(exc)}, 403
        vente = tenant_filtered_get(Vente, vente_id)
        if not vente:
            return {'message': 'Vente non trouvee'}, 404
        data = request.get_json() or {}
        data['vente_id'] = vente.id
        try:
            facture = issue_invoice(data)
        except FactureDejaExistante as exc:
            db.session.rollback()
            return {
                'message': str(exc),
                'facture': exc.facture.to_dict() if exc.facture else None,
            }, 409
        except ValueError as e:
            db.session.rollback()
            return {'message': str(e)}, 400
        return facture.to_dict(), 201

