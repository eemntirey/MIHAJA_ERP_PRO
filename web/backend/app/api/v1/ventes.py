from flask_restx import Namespace, Resource, fields
from app.security.tenant import tenant_required
from app.services.vente_service import get_sales_summary, create_with_lignes, get_stats
from flask import request
from app import db

ns = Namespace('ventes', description='Gestion des ventes')

ligne_vente_model = ns.model('LigneVente', {
    'produit_id': fields.Integer(required=True, description='ID produit'),
    'quantite': fields.Float(required=True, description='Quantité vendue'),
    'prix_unitaire': fields.Float(required=True, description='Prix unitaire HT'),
    'taux_tva': fields.Float(description='Taux TVA', default=20),
})

vente_model = ns.model('Vente', {
    'client_id': fields.Integer(required=True, description='ID client'),
    'date': fields.String(description='Date de la vente'),
    'statut': fields.String(description='Statut de la vente', default='en_attente'),
    'mode_paiement': fields.String(description='Mode de paiement', default='espece'),
    'remarque': fields.String(description='Remarque'),
    'lignes': fields.List(fields.Nested(ligne_vente_model), required=True, description='Lignes de vente'),
})

@ns.route('/')
class VenteList(Resource):
    @tenant_required
    def get(self):
        """Liste toutes les ventes"""
        try:
            ventes = get_sales_summary()
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
        except Exception as e:
            return {'ventes': [], 'message': str(e)}, 500

    @ns.doc('create_vente')
    @tenant_required
    @ns.expect(vente_model)
    def post(self):
        """Creation de vente"""
        from flask import request
        data = request.get_json()
        try:
            vente = create_with_lignes(data)
            return vente.to_dict(), 201
        except ValueError as e:
            db.session.rollback()
            return {'message': str(e)}, 400
        except Exception as e:
            db.session.rollback()
            return {'message': f"Erreur lors de la création de la vente: {str(e)}"}, 400

@ns.route('/<int:id>')
class VenteResource(Resource):
    @tenant_required
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

    @tenant_required
    def put(self, id):
        """Met a jour une vente"""
        from app.models.vente import Vente
        from app.security.tenant import tenant_filtered_get
        from flask import request
        vente = tenant_filtered_get(Vente, id)
        if not vente:
            return {'message': 'Vente non trouvee'}, 404
        data = request.get_json()
        try:
            for key, value in data.items():
                if key not in ['id', 'created_at', 'updated_at', 'created_by', 'updated_by', 'tenant_id']:
                    setattr(vente, key, value)
            from app import db
            db.session.commit()
            return vente.to_dict(), 200
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 400

    @tenant_required
    def delete(self, id):
        """Supprime une vente"""
        from app.models.vente import Vente
        from app.models.ligne_vente import LigneVente
        from app.security.tenant import tenant_filtered_get
        vente = tenant_filtered_get(Vente, id)
        if not vente:
            return {'message': 'Vente non trouvee'}, 404
        try:
            vente.is_active = False
            LigneVente.query.filter_by(vente_id=id, is_active=True, tenant_id=vente.tenant_id).update({'is_active': False})
            from app import db
            db.session.commit()
            return {'message': 'Vente supprimee'}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 400


@ns.route('/summary')
class VenteSummary(Resource):
    @tenant_required
    def get(self):
        """Statistiques des ventes"""
        stats = get_stats()
        return stats, 200

