from flask_restx import Namespace, Resource
from flask import request, Response
from app.security.tenant import tenant_required
from app.security.permissions import permission_required
from app.services.comptabilite_service import CompteComptableService, EcritureComptableService, TresorerieService, ComptaImportService
from datetime import date
from sqlalchemy import func
import io

ns_comptes = Namespace('comptes', description='Gestion des comptes comptables')
ns_ecritures = Namespace('ecritures', description='Gestion des ecritures comptables')
ns_tresorerie = Namespace('tresorerie', description='Gestion de la tresorerie')

@ns_comptes.route('/')
class CompteList(Resource):
    @tenant_required
    @permission_required('compte.view')
    def get(self):
        comptes, total = CompteComptableService.get_all()
        return {'comptes': [c.to_dict() for c in comptes], 'total': total}, 200

    @tenant_required
    @permission_required('compte.create')
    def post(self):
        from flask import request
        data = request.get_json()
        compte = CompteComptableService.create(data)
        return compte.to_dict(), 201


@ns_comptes.route('/<int:id>')
class CompteResource(Resource):
    @tenant_required
    @permission_required('compte.view')
    def get(self, id):
        compte = CompteComptableService.get_by_id(id)
        if not compte:
            return {'message': 'Compte non trouve'}, 404
        return compte.to_dict(), 200

    @tenant_required
    @permission_required('compte.update')
    def put(self, id):
        from flask import request
        data = request.get_json()
        compte = CompteComptableService.update(id, data)
        if not compte:
            return {'message': 'Compte non trouve'}, 404
        return compte.to_dict(), 200

    @tenant_required
    @permission_required('compte.delete')
    def delete(self, id):
        success = CompteComptableService.delete(id)
        if not success:
            return {'message': 'Compte non trouve'}, 404
        return {'message': 'Compte supprime'}, 200


@ns_comptes.route('/export')
class CompteExport(Resource):
    @tenant_required
    @permission_required('compte.view')
    def get(self):
        csv = ComptaImportService.export_comptes()
        return Response(
            csv, mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=comptes.csv'}
        )


@ns_ecritures.route('/')
class EcritureList(Resource):
    @tenant_required
    @permission_required('ecriture.view')
    def get(self):
        ecritures, total = EcritureComptableService.get_all()
        return {'ecritures': [e.to_dict() for e in ecritures], 'total': total}, 200

    @tenant_required
    @permission_required('ecriture.create')
    def post(self):
        from flask import request
        data = request.get_json() or {}
        if 'date' in data and isinstance(data['date'], str):
            try:
                data['date'] = date.fromisoformat(data['date'])
            except (ValueError, TypeError):
                pass
        ecriture = EcritureComptableService.create(data)
        return ecriture.to_dict(), 201


@ns_ecritures.route('/<int:id>')
class EcritureResource(Resource):
    @tenant_required
    @permission_required('ecriture.view')
    def get(self, id):
        ecriture = EcritureComptableService.get_by_id(id)
        if not ecriture:
            return {'message': 'Ecriture non trouvee'}, 404
        return ecriture.to_dict(), 200

    @tenant_required
    @permission_required('ecriture.update')
    def put(self, id):
        from flask import request
        data = request.get_json()
        ecriture = EcritureComptableService.update(id, data)
        if not ecriture:
            return {'message': 'Ecriture non trouvee'}, 404
        return ecriture.to_dict(), 200

    @tenant_required
    @permission_required('ecriture.delete')
    def delete(self, id):
        success = EcritureComptableService.delete(id)
        if not success:
            return {'message': 'Ecriture non trouvee'}, 404
        return {'message': 'Ecriture supprimee'}, 200


@ns_ecritures.route('/<int:id>/valider')
class EcritureValider(Resource):
    @tenant_required
    @permission_required('ecriture.update')
    def post(self, id):
        ecriture = EcritureComptableService.valider_ecriture(id)
        if not ecriture:
            return {'message': 'Ecriture non trouvee'}, 404
        return ecriture.to_dict(), 200


@ns_ecritures.route('/<int:id>/annuler')
class EcritureAnnuler(Resource):
    @tenant_required
    @permission_required('ecriture.update')
    def post(self, id):
        ecriture = EcritureComptableService.annuler_ecriture(id)
        if not ecriture:
            return {'message': 'Ecriture non trouvee'}, 404
        return ecriture.to_dict(), 201


@ns_ecritures.route('/journal')
class EcritureJournal(Resource):
    @tenant_required
    @permission_required('ecriture.view')
    def get(self):
        from flask import request
        date_debut = request.args.get('date_debut')
        date_fin = request.args.get('date_fin')
        compte_id = request.args.get('compte_id')
        debut = date.fromisoformat(date_debut) if date_debut else None
        fin = date.fromisoformat(date_fin) if date_fin else None
        if date_debut and debut is None:
            return {'message': 'Format de date_debut invalide (YYYY-MM-DD)'}, 400
        if date_fin and fin is None:
            return {'message': 'Format de date_fin invalide (YYYY-MM-DD)'}, 400
        try:
            compte_id_int = int(compte_id) if compte_id else None
        except (TypeError, ValueError):
            compte_id_int = None
        journal = EcritureComptableService.get_journal(debut, fin, compte_id_int)
        return journal, 200


@ns_ecritures.route('/export')
class EcritureExport(Resource):
    @tenant_required
    @permission_required('ecriture.view')
    def get(self):
        csv = ComptaImportService.export_ecritures()
        return Response(
            csv, mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=ecritures.csv'}
        )


@ns_tresorerie.route('/')
class TresorerieList(Resource):
    @tenant_required
    @permission_required('tresorerie.view')
    def get(self):
        tresoreries, total = TresorerieService.get_all()
        return {'tresoreries': [t.to_dict() for t in tresoreries], 'total': total}, 200

    @tenant_required
    @permission_required('tresorerie.create')
    def post(self):
        from flask import request
        data = request.get_json()
        entree = TresorerieService.create(data)
        return entree.to_dict(), 201


@ns_tresorerie.route('/<int:id>')
class TresorerieResource(Resource):
    @tenant_required
    @permission_required('tresorerie.view')
    def get(self, id):
        entree = TresorerieService.get_by_id(id)
        if not entree:
            return {'message': 'Entree de tresorerie non trouvee'}, 404
        return entree.to_dict(), 200

    @tenant_required
    @permission_required('tresorerie.update')
    def put(self, id):
        from flask import request
        data = request.get_json()
        entree = TresorerieService.update(id, data)
        if not entree:
            return {'message': 'Entree de tresorerie non trouvee'}, 404
        return entree.to_dict(), 200

    @tenant_required
    @permission_required('tresorerie.delete')
    def delete(self, id):
        success = TresorerieService.delete(id)
        if not success:
            return {'message': 'Entree de tresorerie non trouvee'}, 404
        return {'message': 'Entree de tresorerie supprimee'}, 200


@ns_tresorerie.route('/solde')
class TresorerieSolde(Resource):
    @tenant_required
    @permission_required('tresorerie.view')
    def get(self):
        from flask import request
        date_debut = request.args.get('date_debut')
        date_fin = request.args.get('date_fin')
        debut = date.fromisoformat(date_debut) if date_debut else None
        fin = date.fromisoformat(date_fin) if date_fin else None
        if date_debut and debut is None:
            return {'message': 'Format de date_debut invalide (YYYY-MM-DD)'}, 400
        if date_fin and fin is None:
            return {'message': 'Format de date_fin invalide (YYYY-MM-DD)'}, 400
        solde = TresorerieService.get_solde(debut, fin)
        return {'solde': solde, 'date_debut': date_debut, 'date_fin': date_fin}, 200


@ns_tresorerie.route('/mouvements')
class TresorerieMouvements(Resource):
    @tenant_required
    @permission_required('tresorerie.view')
    def get(self):
        from flask import request
        date_debut = request.args.get('date_debut')
        date_fin = request.args.get('date_fin')
        debut = date.fromisoformat(date_debut) if date_debut else None
        fin = date.fromisoformat(date_fin) if date_fin else None
        if date_debut and debut is None:
            return {'message': 'Format de date_debut invalide (YYYY-MM-DD)'}, 400
        if date_fin and fin is None:
            return {'message': 'Format de date_fin invalide (YYYY-MM-DD)'}, 400
        mouvements = TresorerieService.get_mouvements(debut, fin)
        return {'mouvements': mouvements, 'count': len(mouvements)}, 200


@ns_tresorerie.route('/export')
class TresorerieExport(Resource):
    @tenant_required
    @permission_required('tresorerie.view')
    def get(self):
        csv = ComptaImportService.export_tresorerie()
        return Response(
            csv, mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=tresorerie.csv'}
        )


@ns_comptes.route('/import')
class CompteImport(Resource):
    @tenant_required
    @permission_required('compte.create')
    def post(self):
        if 'file' not in request.files:
            return {'message': 'Fichier requis'}, 400
        file = request.files['file']
        if not file or file.filename == '':
            return {'message': 'Fichier vide'}, 400
        try:
            result = ComptaImportService.import_comptes(file)
            return {
                'message': f"Import terminé: {result['imported']} comptes importés",
                'imported': result['imported'],
                'errors': result['errors'],
                'details': result['details'],
            }, 200
        except ValueError as e:
            return {'message': str(e)}, 400
        except Exception:
            current_app.logger.exception('Erreur serveur lors de l import de comptes')
            return {'message': 'Erreur serveur lors de l import de comptes'}, 500


@ns_ecritures.route('/import')
class EcritureImport(Resource):
    @tenant_required
    @permission_required('ecriture.create')
    def post(self):
        if 'file' not in request.files:
            return {'message': 'Fichier requis'}, 400
        file = request.files['file']
        if not file or file.filename == '':
            return {'message': 'Fichier vide'}, 400
        try:
            result = ComptaImportService.import_ecritures(file)
            return {
                'message': f"Import terminé: {result['imported']} écritures importées",
                'imported': result['imported'],
                'errors': result['errors'],
                'details': result['details'],
            }, 200
        except ValueError as e:
            return {'message': str(e)}, 400
        except Exception:
            current_app.logger.exception('Erreur serveur lors de l import d ecritures')
            return {'message': 'Erreur serveur lors de l import d ecritures'}, 500


@ns_tresorerie.route('/import')
class TresorerieImport(Resource):
    @tenant_required
    @permission_required('tresorerie.create')
    def post(self):
        if 'file' not in request.files:
            return {'message': 'Fichier requis'}, 400
        file = request.files['file']
        if not file or file.filename == '':
            return {'message': 'Fichier vide'}, 400
        try:
            result = ComptaImportService.import_tresorerie(file)
            return {
                'message': f"Import terminé: {result['imported']} entrées trésorerie importées",
                'imported': result['imported'],
                'errors': result['errors'],
                'details': result['details'],
            }, 200
        except ValueError as e:
            return {'message': str(e)}, 400
        except Exception:
            current_app.logger.exception('Erreur serveur lors de l import de tresorerie')
            return {'message': 'Erreur serveur lors de l import de tresorerie'}, 500
