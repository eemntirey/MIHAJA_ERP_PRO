from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.utilisateur import Utilisateur, Role, StatutAdmin
from app.models.admin_device import AdminDevice, StatutDevice
from app.models.audit_log import AuditLog, TypeActionAudit
from app.security.tenant import get_current_tenant_id
from datetime import datetime
import json


ns = Namespace('admin/devices', description='Gestion des appareils administrateur')


def _get_current_user():
    user_id = get_jwt_identity()
    return db.session.get(Utilisateur, user_id)


def _log_audit(action_type, description, tenant_id=None, metadata=None):
    try:
        user_id = get_jwt_identity()
        audit = AuditLog(
            tenant_id=tenant_id,
            utilisateur_id=user_id,
            type_action=action_type,
            description=description,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        db.session.add(audit)
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass


@ns.route('/register')
class RegisterDevice(Resource):
    @jwt_required()
    def post(self):
        user = _get_current_user()
        if not user:
            return {'message': 'Utilisateur non trouve'}, 404

        if user.role != Role.ADMIN:
            return {'message': 'Acces refuse: admin requis'}, 403

        if user.admin_statut is not None and user.admin_statut != StatutAdmin.ACTIVE:
            return {'message': 'Administrateur suspendu ou revoque'}, 403

        data = request.get_json() or {}
        device_id = data.get('device_id')
        device_name = data.get('device_name')

        if not device_id:
            return {'message': 'device_id requis'}, 400

        existing = AdminDevice.query.filter_by(
            user_id=user.id,
            device_id=device_id,
            statut=StatutDevice.ACTIVE
        ).first()
        if existing:
            return {'message': 'Appareil deja enregistre et actif'}, 400

        device = AdminDevice(
            user_id=user.id,
            device_id=device_id,
            device_name=device_name,
            statut=StatutDevice.ACTIVE,
            last_seen=datetime.utcnow()
        )
        db.session.add(device)

        user.device_id = device_id
        db.session.add(user)
        db.session.commit()

        _log_audit(
            TypeActionAudit.DEVICE_REGISTERED,
            f"Appareil enregistre pour {user.username}: {device_id}",
            tenant_id=user.tenant_id,
            metadata={'user_id': user.id, 'device_id': device_id, 'device_name': device_name}
        )

        return {
            'message': 'Appareil enregistre avec succes',
            'device': device.to_dict()
        }, 201


@ns.route('/')
class DeviceCollection(Resource):
    @jwt_required()
    def get(self):
        user = _get_current_user()
        if not user:
            return {'message': 'Utilisateur non trouve'}, 404

        if user.role != Role.ADMIN:
            return {'message': 'Acces refuse: admin requis'}, 403

        devices = AdminDevice.query.filter_by(user_id=user.id).order_by(AdminDevice.created_at.desc()).all()
        return {
            'devices': [d.to_dict() for d in devices]
        }, 200

    @jwt_required()
    def post(self):
        user = _get_current_user()
        if not user:
            return {'message': 'Utilisateur non trouve'}, 404

        if user.role != Role.ADMIN:
            return {'message': 'Acces refuse: admin requis'}, 403

        if user.admin_statut is not None and user.admin_statut != StatutAdmin.ACTIVE:
            return {'message': 'Administrateur suspendu ou revoque'}, 403

        data = request.get_json() or {}
        device_id = data.get('device_id')
        device_name = data.get('device_name')

        if not device_id:
            return {'message': 'device_id requis'}, 400

        existing = AdminDevice.query.filter_by(
            user_id=user.id,
            device_id=device_id
        ).first()
        if existing:
            if existing.statut == StatutDevice.ACTIVE:
                return {'message': 'Appareil deja enregistre'}, 400
            existing.statut = StatutDevice.ACTIVE
            existing.last_seen = datetime.utcnow()
            db.session.add(existing)
        else:
            device = AdminDevice(
                user_id=user.id,
                device_id=device_id,
                device_name=device_name,
                statut=StatutDevice.ACTIVE,
                last_seen=datetime.utcnow()
            )
            db.session.add(device)

        db.session.commit()

        _log_audit(
            TypeActionAudit.DEVICE_REGISTERED,
            f"Ajout d'un appareil pour {user.username}: {device_id}",
            tenant_id=user.tenant_id,
            metadata={'user_id': user.id, 'device_id': device_id}
        )

        return {
            'message': 'Appareil ajoute avec succes'
        }, 201


@ns.route('/<string:device_id>')
class DeviceResource(Resource):
    @jwt_required()
    def delete(self, device_id):
        user = _get_current_user()
        if not user:
            return {'message': 'Utilisateur non trouve'}, 404

        if user.role != Role.ADMIN:
            return {'message': 'Acces refuse: admin requis'}, 403

        if user.admin_statut is not None and user.admin_statut != StatutAdmin.ACTIVE:
            return {'message': 'Administrateur suspendu ou revoque'}, 403

        device = AdminDevice.query.filter_by(
            user_id=user.id,
            device_id=device_id
        ).first()
        if not device:
            return {'message': 'Appareil non trouve'}, 404

        device.statut = StatutDevice.REVOKED
        db.session.add(device)

        if user.device_id == device_id:
            user.device_id = None
            db.session.add(user)

        db.session.commit()

        _log_audit(
            TypeActionAudit.DEVICE_REVOKED,
            f"Appareil revoque pour {user.username}: {device_id}",
            tenant_id=user.tenant_id,
            metadata={'user_id': user.id, 'device_id': device_id}
        )

        return {
            'message': 'Appareil revoque avec succes'
        }, 200


@ns.route('/change')
class ChangeDevice(Resource):
    @jwt_required()
    def post(self):
        user = _get_current_user()
        if not user:
            return {'message': 'Utilisateur non trouve'}, 404

        if user.role != Role.ADMIN:
            return {'message': 'Acces refuse: admin requis'}, 403

        if user.admin_statut is not None and user.admin_statut != StatutAdmin.ACTIVE:
            return {'message': 'Administrateur suspendu ou revoque'}, 403

        data = request.get_json() or {}
        old_device_id = data.get('old_device_id')
        new_device_id = data.get('new_device_id')
        new_device_name = data.get('new_device_name')

        if not old_device_id or not new_device_id:
            return {'message': 'old_device_id et new_device_id requis'}, 400

        old_device = AdminDevice.query.filter_by(
            user_id=user.id,
            device_id=old_device_id,
            statut=StatutDevice.ACTIVE
        ).first()
        if not old_device:
            return {'message': 'Ancien appareil non trouve ou non autorise'}, 403

        old_device.statut = StatutDevice.REVOKED
        db.session.add(old_device)

        existing = AdminDevice.query.filter_by(
            user_id=user.id,
            device_id=new_device_id
        ).first()
        if existing:
            existing.statut = StatutDevice.ACTIVE
            existing.last_seen = datetime.utcnow()
            db.session.add(existing)
        else:
            new_device = AdminDevice(
                user_id=user.id,
                device_id=new_device_id,
                device_name=new_device_name,
                statut=StatutDevice.ACTIVE,
                last_seen=datetime.utcnow()
            )
            db.session.add(new_device)

        user.device_id = new_device_id
        db.session.add(user)
        db.session.commit()

        _log_audit(
            TypeActionAudit.DEVICE_CHANGE_REQUESTED,
            f"Changement d'appareil pour {user.username}: {old_device_id} -> {new_device_id}",
            tenant_id=user.tenant_id,
            metadata={'user_id': user.id, 'old_device_id': old_device_id, 'new_device_id': new_device_id}
        )

        return {
            'message': 'Appareil change avec succes'
        }, 200
