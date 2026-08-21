from flask import request
from flask_restx import Namespace, Resource, fields
from app.models.notification import Notification
from app import db
from app.security.tenant import tenant_required, get_current_tenant_id_or_none
from datetime import datetime

ns = Namespace('notifications', description='Gestion des notifications')

notification_model = ns.model('Notification', {
    'id': fields.Integer(readonly=True),
    'title': fields.String(required=True),
    'message': fields.String(),
    'type': fields.String(required=True, default='info'),
    'read': fields.Boolean(default=False),
    'read_at': fields.String(),
    'user_id': fields.Integer(),
    'link': fields.String(),
    'tenant_id': fields.Integer(readonly=True),
    'created_at': fields.String(readonly=True),
    'updated_at': fields.String(readonly=True),
    'is_active': fields.Boolean(readonly=True),
})


@ns.route('/')
class NotificationList(Resource):
    @ns.doc('list_notifications')
    @ns.marshal_list_with(notification_model)
    @tenant_required
    def get(self):
        tenant_id = get_current_tenant_id_or_none()
        query = Notification.query.filter_by(is_active=True)
        if tenant_id is not None:
            query = query.filter_by(tenant_id=tenant_id)
        notifications = query.order_by(Notification.created_at.desc()).limit(50).all()
        return [n.to_dict() for n in notifications]

    @ns.doc('create_notification')
    @ns.expect(notification_model, validate=True)
    @ns.marshal_with(notification_model, code=201)
    @tenant_required
    def post(self):
        data = request.get_json() or {}
        title = data.get('title')
        message = data.get('message')
        notif_type = data.get('type', 'info')
        link = data.get('link')
        user_id = data.get('user_id')

        if not title:
            return {'message': 'Le titre est requis'}, 400

        tenant_id = get_current_tenant_id_or_none()

        notification = Notification(
            title=title,
            message=message,
            type=notif_type,
            link=link,
            user_id=user_id,
            tenant_id=tenant_id,
        )
        db.session.add(notification)
        db.session.commit()
        return notification.to_dict(), 201


@ns.route('/<int:notification_id>')
class NotificationDetail(Resource):
    @ns.doc('get_notification')
    @ns.marshal_with(notification_model)
    @tenant_required
    def get(self, notification_id):
        tenant_id = get_current_tenant_id_or_none()
        query = Notification.query.filter_by(id=notification_id, is_active=True)
        if tenant_id is not None:
            query = query.filter_by(tenant_id=tenant_id)
        notification = query.first()
        if not notification:
            return {'message': 'Notification non trouvee'}, 404
        return notification.to_dict(), 200

    @ns.doc('delete_notification')
    @tenant_required
    def delete(self, notification_id):
        tenant_id = get_current_tenant_id_or_none()
        query = Notification.query.filter_by(id=notification_id, is_active=True)
        if tenant_id is not None:
            query = query.filter_by(tenant_id=tenant_id)
        notification = query.first()
        if not notification:
            return {'message': 'Notification non trouvee'}, 404
        notification.is_active = False
        db.session.commit()
        return {'message': 'Notification supprimee'}, 200


@ns.route('/<int:notification_id>/read')
class NotificationRead(Resource):
    @ns.doc('mark_notification_as_read')
    @ns.marshal_with(notification_model)
    @tenant_required
    def patch(self, notification_id):
        tenant_id = get_current_tenant_id_or_none()
        query = Notification.query.filter_by(id=notification_id, is_active=True)
        if tenant_id is not None:
            query = query.filter_by(tenant_id=tenant_id)
        notification = query.first()
        if not notification:
            return {'message': 'Notification non trouvee'}, 404
        notification.read = True
        notification.read_at = datetime.utcnow()
        db.session.commit()
        return notification.to_dict(), 200


@ns.route('/read-all')
class NotificationReadAll(Resource):
    @ns.doc('mark_all_notifications_as_read')
    @tenant_required
    def patch(self):
        tenant_id = get_current_tenant_id_or_none()
        query = Notification.query.filter_by(is_active=True, read=False)
        if tenant_id is not None:
            query = query.filter_by(tenant_id=tenant_id)
        now = datetime.utcnow()
        for notification in query.all():
            notification.read = True
            notification.read_at = now
        db.session.commit()
        return {'message': 'Toutes les notifications ont ete marquees comme lues'}, 200
