from flask import request, Response, g
from flask_restx import Namespace, Resource
from datetime import date
from app import db
from app.security.tenant import tenant_required
from app.security.plan_limits import check_plan_limits, require_module
from app.services.rh_service import EmployeService, PresenceService, SalaireService, PrimeService
from app.services.stagiaire_service import StagiaireService
from app.utils.audit import log_audit
from app.models.audit_log import TypeActionAudit

ns_employes = Namespace('employes', description='Gestion des employes')
ns_presences = Namespace('presences', description='Gestion des presences')
ns_salaires = Namespace('salaires', description='Gestion des salaires')
ns_primes = Namespace('primes', description='Gestion des primes')
ns_stagiaires = Namespace('stagiaires', description='Gestion des stagiaires')

_MODULE_RH = 'rh'


@ns_employes.route('/')
class EmployeList(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self):
        employes, total = EmployeService.get_all()
        return {'employes': [e.to_dict() for e in employes], 'total': total}, 200

    @tenant_required
    @require_module(_MODULE_RH)
    @check_plan_limits('employes')
    def post(self):
        data = request.get_json() or {}
        employe = EmployeService.create(data)
        try:
            log_audit(
                TypeActionAudit.CREATION_EMPLOYE,
                f"Création de l'employé {employe.nom_complet} (matricule={employe.matricule})",
                tenant_id=getattr(g, 'current_tenant_id', None),
                utilisateur_id=getattr(g, 'current_user', None) and g.current_user.id,
                metadata={'employe_id': employe.id, 'matricule': employe.matricule},
            )
        except Exception:
            pass
        return employe.to_dict(), 201


@ns_employes.route('/<int:id>')
class EmployeResource(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self, id):
        employe = EmployeService.get_by_id(id)
        if not employe:
            return {'message': 'Employe non trouve'}, 404
        return employe.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def put(self, id):
        data = request.get_json() or {}
        employe = EmployeService.update(id, data)
        if not employe:
            return {'message': 'Employe non trouve'}, 404
        try:
            log_audit(
                TypeActionAudit.MODIFICATION_EMPLOYE,
                f"Modification de l'employe {employe.nom_complet} (matricule={employe.matricule})",
                tenant_id=getattr(g, 'current_tenant_id', None),
                utilisateur_id=getattr(g, 'current_user', None) and g.current_user.id,
                metadata={'employe_id': employe.id, 'matricule': employe.matricule},
            )
        except Exception:
            pass
        return employe.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def delete(self, id):
        success = EmployeService.delete(id)
        if not success:
            return {'message': 'Employe non trouve'}, 404
        try:
            log_audit(
                TypeActionAudit.SUPPRESSION_EMPLOYE,
                f"Suppression de l'employe id={id}",
                tenant_id=getattr(g, 'current_tenant_id', None),
                utilisateur_id=getattr(g, 'current_user', None) and g.current_user.id,
                metadata={'employe_id': id},
            )
        except Exception:
            pass
        return {'message': 'Employe supprime'}, 200


@ns_presences.route('/')
class PresenceList(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self):
        presences, total = PresenceService.get_all()
        return {'presences': [p.to_dict() for p in presences], 'total': total}, 200

    @tenant_required
    @require_module(_MODULE_RH)
    def post(self):
        data = request.get_json() or {}
        presence = PresenceService.create(data)
        return presence.to_dict(), 201


@ns_presences.route('/registre')
class PresenceRegistre(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self):
        mois = request.args.get('mois')
        annee = request.args.get('annee')
        mois = int(mois) if mois else None
        annee = int(annee) if annee else None
        presences = PresenceService.get_registre(mois, annee)
        return {'presences': presences, 'count': len(presences)}, 200


@ns_presences.route('/registre/export')
class PresenceRegistreExport(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self):
        mois = request.args.get('mois')
        annee = request.args.get('annee')
        mois = int(mois) if mois else None
        annee = int(annee) if annee else None
        csv = PresenceService.get_registre_export(mois, annee)
        return Response(
            csv, mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=registre_presences.csv'}
        )


@ns_presences.route('/<int:id>')
class PresenceResource(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self, id):
        presence = PresenceService.get_by_id(id)
        if not presence:
            return {'message': 'Presence non trouvee'}, 404
        return presence.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def put(self, id):
        data = request.get_json() or {}
        presence = PresenceService.update(id, data)
        if not presence:
            return {'message': 'Presence non trouvee'}, 404
        return presence.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def delete(self, id):
        success = PresenceService.delete(id)
        if not success:
            return {'message': 'Presence non trouvee'}, 404
        return {'message': 'Presence supprimee'}, 200


@ns_salaires.route('/')
class SalaireList(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self):
        salaires, total = SalaireService.get_all()
        return {'salaires': [s.to_dict() for s in salaires], 'total': total}, 200

    @tenant_required
    @require_module(_MODULE_RH)
    def post(self):
        data = request.get_json() or {}
        salaire = SalaireService.create(data)
        return salaire.to_dict(), 201


@ns_salaires.route('/generer')
class SalaireGenerer(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def post(self):
        data = request.get_json() or {}
        mois = data.get('mois')
        annee = data.get('annee')
        if not mois or not annee:
            today = date.today()
            mois = mois or today.month
            annee = annee or today.year
        mois = int(mois)
        annee = int(annee)
        salaires = SalaireService.generate_salaries(mois, annee)
        return {
            'message': f"{len(salaires)} bulletins de salaire générés pour {mois}/{annee}",
            'generated': len(salaires),
            'salaires': [s.to_dict() for s in salaires],
        }, 200


@ns_salaires.route('/<int:id>/payer')
class SalairePayer(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def post(self, id):
        data = request.get_json() or {}
        salaire = SalaireService.marquer_paye(
            id,
            statut_paiement=data.get('statut_paiement'),
            mode_paiement=data.get('mode_paiement'),
            reference_paiement=data.get('reference_paiement'),
            date_paiement=data.get('date_paiement'),
        )
        if not salaire:
            return {'message': 'Salaire non trouve'}, 404
        return salaire.to_dict(), 200


@ns_salaires.route('/export')
class SalaireExport(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self):
        salaires, _ = SalaireService.get_all()
        headers = ['id', 'employe_id', 'employe_nom', 'mois', 'annee',
                   'salaire_base', 'primes', 'indemnites', 'deductions', 'avances',
                   'salaire_brut', 'salaire_net', 'statut_paiement', 'date_paiement', 'mode_paiement']
        records = []
        for s in salaires:
            d = s.to_dict()
            records.append({
                'id': d.get('id'),
                'employe_id': d.get('employe_id'),
                'employe_nom': d.get('employe_nom'),
                'mois': d.get('mois'),
                'annee': d.get('annee'),
                'salaire_base': d.get('salaire_base'),
                'primes': d.get('primes'),
                'indemnites': d.get('indemnites'),
                'deductions': d.get('deductions'),
                'avances': d.get('avances'),
                'salaire_brut': d.get('salaire_brut'),
                'salaire_net': d.get('salaire_net'),
                'statut_paiement': d.get('statut_paiement'),
                'date_paiement': d.get('date_paiement'),
                'mode_paiement': d.get('mode_paiement'),
            })
        import csv as _csv
        import io
        buf = io.StringIO()
        writer = _csv.writer(buf)
        writer.writerow(headers)
        for r in records:
            writer.writerow([r.get(h, '') for h in headers])
        return Response(buf.getvalue(), mimetype='text/csv',
                        headers={'Content-Disposition': 'attachment; filename=salaires.csv'})


@ns_salaires.route('/<int:id>')
class SalaireResource(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self, id):
        salaire = SalaireService.get_by_id(id)
        if not salaire:
            return {'message': 'Salaire non trouve'}, 404
        return salaire.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def put(self, id):
        data = request.get_json() or {}
        salaire = SalaireService.update(id, data)
        if not salaire:
            return {'message': 'Salaire non trouve'}, 404
        return salaire.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def delete(self, id):
        success = SalaireService.delete(id)
        if not success:
            return {'message': 'Salaire non trouve'}, 404
        return {'message': 'Salaire supprime'}, 200


@ns_primes.route('/')
class PrimeList(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self):
        primes, total = PrimeService.get_all()
        return {'primes': [p.to_dict() for p in primes], 'total': total}, 200

    @tenant_required
    @require_module(_MODULE_RH)
    def post(self):
        data = request.get_json() or {}
        prime = PrimeService.create(data)
        return prime.to_dict(), 201


@ns_primes.route('/<int:id>')
class PrimeResource(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self, id):
        prime = PrimeService.get_by_id(id)
        if not prime:
            return {'message': 'Prime non trouvee'}, 404
        return prime.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def put(self, id):
        data = request.get_json() or {}
        prime = PrimeService.update(id, data)
        if not prime:
            return {'message': 'Prime non trouvee'}, 404
        return prime.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def delete(self, id):
        success = PrimeService.delete(id)
        if not success:
            return {'message': 'Prime non trouvee'}, 404
        return {'message': 'Prime supprimee'}, 200


@ns_stagiaires.route('/')
class StagiaireList(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self):
        stagiaires, total = StagiaireService.get_all()
        return {'stagiaires': [s.to_dict() for s in stagiaires], 'total': total}, 200

    @tenant_required
    @require_module(_MODULE_RH)
    @check_plan_limits('stagiaires')
    def post(self):
        data = request.get_json() or {}
        try:
            stagiaire = StagiaireService.create(data)
        except ValueError as e:
            return {'message': str(e)}, 400
        try:
            log_audit(
                TypeActionAudit.CREATION_STAGIAIRE,
                f"Création du stagiaire {stagiaire.nom_complet} (matricule={stagiaire.matricule})",
                tenant_id=stagiaire.tenant_id,
                utilisateur_id=getattr(g, 'current_user', None) and g.current_user.id,
                metadata={'stagiaire_id': stagiaire.id, 'matricule': stagiaire.matricule},
            )
        except Exception:
            pass
        return stagiaire.to_dict(), 201


@ns_stagiaires.route('/<int:id>')
class StagiaireResource(Resource):
    @tenant_required
    @require_module(_MODULE_RH)
    def get(self, id):
        stagiaire = StagiaireService.get_by_id(id)
        if not stagiaire:
            return {'message': 'Stagiaire non trouve'}, 404
        return stagiaire.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def put(self, id):
        stagiaire = StagiaireService.get_by_id(id)
        if not stagiaire:
            return {'message': 'Stagiaire non trouve'}, 404
        data = request.get_json() or {}
        try:
            stagiaire = StagiaireService.update(id, data)
        except ValueError as e:
            return {'message': str(e)}, 400
        if not stagiaire:
            return {'message': 'Stagiaire non trouve'}, 404
        try:
            log_audit(
                TypeActionAudit.MODIFICATION_STAGIAIRE,
                f"Modification du stagiaire {stagiaire.nom_complet} (matricule={stagiaire.matricule})",
                tenant_id=getattr(g, 'current_tenant_id', None),
                utilisateur_id=getattr(g, 'current_user', None) and g.current_user.id,
                metadata={'stagiaire_id': stagiaire.id, 'matricule': stagiaire.matricule},
            )
        except Exception:
            pass
        return stagiaire.to_dict(), 200

    @tenant_required
    @require_module(_MODULE_RH)
    def delete(self, id):
        stagiaire = StagiaireService.get_by_id(id)
        if not stagiaire:
            return {'message': 'Stagiaire non trouve'}, 404
        stagiaire.delete()
        try:
            log_audit(
                TypeActionAudit.SUPPRESSION_STAGIAIRE,
                f"Suppression du stagiaire id={id}",
                tenant_id=getattr(g, 'current_tenant_id', None),
                utilisateur_id=getattr(g, 'current_user', None) and g.current_user.id,
                metadata={'stagiaire_id': id},
            )
        except Exception:
            pass
        return {'message': 'Stagiaire supprime'}, 200
