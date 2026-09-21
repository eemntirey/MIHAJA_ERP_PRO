# web/backend/app/api/v1/sync_conflicts.py
from flask_restx import Namespace, Resource
from flask import request
from flask_jwt_extended import jwt_required
from app import db

ns = Namespace('sync/conflicts', description='Résolution de conflits de réplication')
from app.models.sync_replica import SyncConflict

ns = Namespace('sync/conflicts', description='Résolution de conflits de réplication')

@ns.route('')
class ConflictList(Resource):
    @jwt_required()
    def get(self):
        rows = SyncConflict.query.order_by(SyncConflict.created_at.desc()).all()
        return {'conflicts': [{
            'id': c.id,
            'entity': c.entity,
            'entity_pk': c.entity_pk,
            'local_payload': c.local_payload,
            'remote_payload': c.remote_payload,
            'resolved_as': c.resolved_as,
            'created_at': c.created_at.isoformat() if c.created_at else None,
        } for c in rows]}

@ns.route('/<int:conflict_id>/resolve')
class ConflictResolve(Resource):
    @jwt_required()
    def post(self, conflict_id):
        c = SyncConflict.query.get_or_404(conflict_id)
        resolution = (request.get_json() or {}).get('resolution')
        if resolution == 'local_wins':
            # Re-pousser avec priorité forcée (log audit uniquement pour V1)
            c.resolved_as = 'local_wins'
        elif resolution == 'remote_wins':
            # Applique le payload distant localement
            from app.services.replication.pull import _apply_remote_payload
            _apply_remote_payload(c)
            c.resolved_as = 'remote_wins'
        else:
            return {'message': 'resolution doit être local_wins ou remote_wins'}, 400
        db.session.commit()
        return {'id': c.id, 'resolved_as': c.resolved_as}
