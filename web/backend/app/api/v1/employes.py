from flask import request, Response
from flask_restx import Namespace, Resource
from datetime import date
from app import db
from app.security.tenant import tenant_required_readonly
from app.security.plan_limits import check_plan_limits, check_admin_limit, require_module
from app.services.rh_service import EmployeService
from app.utils.audit import log_audit
from app.models.audit_log import TypeActionAudit

ns_employes = Namespace('employes', description='Gestion des employes')

_MODULE_RH = 'rh'


@ns_employes.route('/')
class EmployeList(Resource):
    @tenant_required_readonly
    @require_module(_MODULE_RH)
    def get(self):
        employes, total = EmployeService.get_all()
        return {'employes': [e.to_dict() for e in employes], 'total': total}, 200

    @tenant_required_readonly
    @require_module(_MODULE_RH)
    @check_plan_limits('employes')
    def post(self):
        data = request.get_json() or {}
        employe = EmployeService.create(data)
        try:
            log_audit(
                TypeActionAudit.CREATION_EMPLOYE,
                f"Création de l'employé {employe.nom_complet} (matricule={employe.matricule})",
                tenant_id=employe.tenant_id,
                utilisateur_id=getattr(request, 'current_user_id', None),
                metadata={'employe_id': employe.id, 'matricule': employe.matricule},
            )
        except Exception:
            pass
        return employe.to_dict(), 201


@ns_employes.route('/<int:id>')
class EmployeResource(Resource):
    @tenant_required_readonly
    @require_module(_MODULE_RH)
    def get(self, id):
        employe = EmployeService.get_by_id(id)
        if not employe:
            return {'message': 'Employe non trouve'}, 404
        return employe.to_dict(), 200

    @tenant_required_readonly
    @require_module(_MODULE_RH)
    def put(self, id):
        data = request.get_json() or {}
        employe = EmployeService.update(id, data)
        if not employe:
            return {'message': 'Employe non trouve'}, 404
        return employe.to_dict(), 200

    @tenant_required_readonly
    @require_module(_MODULE_RH)
    def delete(self, id):
        success = EmployeService.delete(id)
        if not success:
            return {'message': 'Employe non trouve'}, 404
        return {'message': 'Employe supprime'}, 200
