# web/backend/app/api/v1/local_sync.py
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required

ns = Namespace('sync', description='Etat de synchronisation locale')

@ns.route('/local-status')
class LocalSyncStatus(Resource):
    @jwt_required()
    def get(self):
        from app.models.sync_replica import SyncState
        s = SyncState.get_or_create()
        return {
            'online': s.online,
            'pending_count': s.pending_count,
            'last_push_at': s.last_push_at.isoformat() if s.last_push_at else None,
            'last_pull_at': s.last_pull_at.isoformat() if s.last_pull_at else None,
            'last_error': s.last_error,
        }
