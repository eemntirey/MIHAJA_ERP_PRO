from flask_restx import Namespace, Resource
from app.services.fournisseur_service import FournisseurService
from app.security.tenant import tenant_required_readonly

ns = Namespace('fournisseurs', description='Gestion des fournisseurs')

@ns.route('/')
class FournisseurListResource(Resource):
    @ns.doc('list_fournisseurs')
    @tenant_required_readonly
    def get(self):
        """Liste tous les fournisseurs"""
        fournisseurs, total = FournisseurService.get_all()
        return {'fournisseurs': [f.to_dict() for f in fournisseurs], 'total': total}, 200

    @ns.doc('create_fournisseur')
    @tenant_required_readonly
    def post(self):
        """Cree un nouveau fournisseur"""
        from flask import request
        data = request.get_json()
        fournisseur = FournisseurService.create(data)
        return fournisseur.to_dict(), 201

@ns.route('/<int:fournisseur_id>')
class FournisseurResource(Resource):
    @ns.doc('get_fournisseur')
    @tenant_required_readonly
    def get(self, fournisseur_id):
        """Recupere un fournisseur par son ID"""
        fournisseur = FournisseurService.get_by_id(fournisseur_id)
        if not fournisseur:
            return {'message': 'Fournisseur non trouve'}, 404
        return fournisseur.to_dict(), 200

    @ns.doc('update_fournisseur')
    @tenant_required_readonly
    def put(self, fournisseur_id):
        """Met a jour un fournisseur"""
        from flask import request
        data = request.get_json()
        fournisseur = FournisseurService.update(fournisseur_id, data)
        if not fournisseur:
            return {'message': 'Fournisseur non trouve'}, 404
        return fournisseur.to_dict(), 200

    @ns.doc('delete_fournisseur')
    @tenant_required_readonly
    def delete(self, fournisseur_id):
        """Supprime un fournisseur"""
        success = FournisseurService.delete(fournisseur_id)
        if not success:
            return {'message': 'Fournisseur non trouve'}, 404
        return {'message': 'Fournisseur supprime'}, 200

@ns.route('/commandes')
class CommandeFournisseurListResource(Resource):
    @ns.doc('list_commandes_fournisseurs')
    @tenant_required_readonly
    def get(self):
        """Liste des commandes fournisseurs"""
        from app.models.commande_fournisseur import CommandeFournisseur
        from app.security.tenant import get_current_tenant_id
        tenant_id = get_current_tenant_id()
        query = CommandeFournisseur.query.filter_by(is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        commandes = query.all()
        return {'commandes': [c.to_dict() for c in commandes]}, 200

    @ns.doc('create_commande_fournisseur')
    @tenant_required_readonly
    def post(self):
        """Cree une commande fournisseur"""
        from flask import request
        from app.models.commande_fournisseur import CommandeFournisseur
        from app.security.tenant import get_current_tenant_id
        data = request.get_json()
        try:
            tenant_id = get_current_tenant_id()
            commande = CommandeFournisseur(
                fournisseur_id=data['fournisseur_id'],
                reference=data.get('reference', ''),
                total_ht=data.get('total_ht', 0),
                total_ttc=data.get('total_ttc', 0),
                statut=data.get('statut', 'en_attente'),
                tenant_id=tenant_id
            )
            commande.save()
            return commande.to_dict(), 201
        except Exception as e:
            return {'message': str(e)}, 400

@ns.route('/commandes/<int:id>')
class CommandeFournisseurResource(Resource):
    @ns.doc('get_commande_fournisseur')
    @tenant_required_readonly
    def get(self, id):
        """Recupere une commande fournisseur par ID"""
        from app.models.commande_fournisseur import CommandeFournisseur
        from app.security.tenant import tenant_filtered_get
        commande = tenant_filtered_get(CommandeFournisseur, id)
        if not commande:
            return {'message': 'Commande fournisseur non trouvee'}, 404
        return commande.to_dict(), 200

    @ns.doc('update_commande_fournisseur')
    @tenant_required_readonly
    def put(self, id):
        """Met a jour une commande fournisseur"""
        from app.models.commande_fournisseur import CommandeFournisseur
        from app.security.tenant import tenant_filtered_get
        from flask import request
        commande = tenant_filtered_get(CommandeFournisseur, id)
        if not commande:
            return {'message': 'Commande fournisseur non trouvee'}, 404
        data = request.get_json() or {}
        PROTECTED = {'id', 'tenant_id', 'created_at', 'updated_at', 'created_by', 'updated_by', 'is_active'}
        for key, value in data.items():
            if key in PROTECTED:
                continue
            if hasattr(commande, key):
                setattr(commande, key, value)
        commande.save()
        return commande.to_dict(), 200

    @ns.doc('delete_commande_fournisseur')
    @tenant_required_readonly
    def delete(self, id):
        """Supprime une commande fournisseur"""
        from app.models.commande_fournisseur import CommandeFournisseur
        from app.security.tenant import tenant_filtered_get
        commande = tenant_filtered_get(CommandeFournisseur, id)
        if not commande:
            return {'message': 'Commande fournisseur non trouvee'}, 404
        commande.delete()
        return {'message': 'Commande fournisseur supprimee'}, 200

@ns.route('/factures')
class FactureFournisseurListResource(Resource):
    @ns.doc('list_factures_fournisseurs')
    @tenant_required_readonly
    def get(self):
        """Liste des factures fournisseurs"""
        from app.models.facture_fournisseur import FactureFournisseur
        from app.security.tenant import get_current_tenant_id
        tenant_id = get_current_tenant_id()
        query = FactureFournisseur.query.filter_by(is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        factures = query.all()
        return {'factures': [f.to_dict() for f in factures]}, 200

    @ns.doc('create_facture_fournisseur')
    @tenant_required_readonly
    def post(self):
        """Cree une facture fournisseur"""
        from flask import request
        from app.models.facture_fournisseur import FactureFournisseur
        from app.security.tenant import get_current_tenant_id
        data = request.get_json()
        try:
            tenant_id = get_current_tenant_id()
            facture = FactureFournisseur(
                fournisseur_id=data['fournisseur_id'],
                reference=data.get('reference', ''),
                total_ht=data.get('total_ht', 0),
                total_ttc=data.get('total_ttc', 0),
                statut=data.get('statut', 'non_payee'),
                tenant_id=tenant_id
            )
            facture.save()
            return facture.to_dict(), 201
        except Exception as e:
            return {'message': str(e)}, 400

@ns.route('/factures/<int:id>')
class FactureFournisseurResource(Resource):
    @ns.doc('get_facture_fournisseur')
    @tenant_required_readonly
    def get(self, id):
        """Recupere une facture fournisseur par ID"""
        from app.models.facture_fournisseur import FactureFournisseur
        from app.security.tenant import tenant_filtered_get
        facture = tenant_filtered_get(FactureFournisseur, id)
        if not facture:
            return {'message': 'Facture fournisseur non trouvee'}, 404
        return facture.to_dict(), 200

    @ns.doc('update_facture_fournisseur')
    @tenant_required_readonly
    def put(self, id):
        """Met a jour une facture fournisseur"""
        from app.models.facture_fournisseur import FactureFournisseur
        from app.security.tenant import tenant_filtered_get
        from flask import request
        facture = tenant_filtered_get(FactureFournisseur, id)
        if not facture:
            return {'message': 'Facture fournisseur non trouvee'}, 404
        data = request.get_json() or {}
        PROTECTED = {'id', 'tenant_id', 'created_at', 'updated_at', 'created_by', 'updated_by', 'is_active'}
        for key, value in data.items():
            if key in PROTECTED:
                continue
            if hasattr(facture, key):
                setattr(facture, key, value)
        facture.save()
        return facture.to_dict(), 200

    @ns.doc('delete_facture_fournisseur')
    @tenant_required_readonly
    def delete(self, id):
        """Supprime une facture fournisseur"""
        from app.models.facture_fournisseur import FactureFournisseur
        from app.security.tenant import tenant_filtered_get
        facture = tenant_filtered_get(FactureFournisseur, id)
        if not facture:
            return {'message': 'Facture fournisseur non trouvee'}, 404
        facture.delete()
        return {'message': 'Facture fournisseur supprimee'}, 200
