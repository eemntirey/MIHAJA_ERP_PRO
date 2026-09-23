# web/backend/app/api/v1/sync_conflicts.py
# Résolution locale des conflits de réplication (backend embarqué).
#
# - GET  /sync/conflicts              : conflits à trancher
# - POST /sync/conflicts/<id>/resolve : {'resolution': 'local_wins' |
#                                       'remote_wins'}
#
# 'local_wins'  : la version locale est re-poussée avec X-Force-Win (le
#                 central l'applique sans arbitrage LWW).
# 'remote_wins' : la version centrale est écrite localement.
from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource

from app import db
from app.models.sync_replica import SyncConflict

ns = Namespace('sync/conflicts', description='Résolution des conflits locaux')


@ns.route('')
class ConflictList(Resource):
    @jwt_required()
    def get(self):
        """Conflits enregistrés, du plus récent au plus ancien."""
        rows = SyncConflict.query.order_by(
            SyncConflict.created_at.desc()
        ).all()
        return {
            'conflicts': [
                {
                    'id': c.id,
                    'entity': c.entity,
                    'entity_pk': c.entity_pk,
                    'local_payload': c.local_payload,
                    'remote_payload': c.remote_payload,
                    'resolved_as': c.resolved_as,
                    'created_at': (
                        c.created_at.isoformat() if c.created_at else None
                    ),
                } for c in rows
            ]
        }


@ns.route('/<int:conflict_id>/resolve')
class ConflictResolve(Resource):
    @jwt_required()
    def post(self, conflict_id):
        """Tranche un conflit : version locale ou version centrale."""
        conflict = SyncConflict.query.filter_by(id=conflict_id).first()
        if conflict is None:
            return {'message': 'Conflit introuvable.'}, 404

        resolution = (request.get_json(silent=True) or {}).get('resolution')
        if resolution not in ('local_wins', 'remote_wins'):
            return {
                'message': 'resolution doit être local_wins ou remote_wins'
            }, 400

        if resolution == 'local_wins':
            from app.services.replication.push import force_push_conflict
            ok, message = force_push_conflict(conflict)
            if not ok:
                return {
                    'message': f'Résolution locale impossible : {message}'
                }, 409
        else:
            from app.services.replication.pull import apply_remote_locally
            ok, message = apply_remote_locally(
                conflict.entity, conflict.remote_payload, conflict.entity_pk,
            )
            if not ok:
                return {'message': message}, 409

        conflict.resolved_as = resolution
        db.session.commit()
        return {'id': conflict.id, 'resolved_as': conflict.resolved_as}
