# web/backend/app/api/v1/local_sync.py
# État de réplication du POSTE (backend embarqué) — consommé par le badge
# `shared/components/SyncStatus/SyncStatus.jsx`.
from flask import current_app
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required

ns = Namespace('sync', description='État de synchronisation locale')


@ns.route('/local-status')
class LocalSyncStatus(Resource):
    @jwt_required()
    def get(self):
        from app.models.sync_replica import SyncState

        s = SyncState.get_or_create()

        # Risque n°2 : dérive d'horloge mesurée par le planificateur
        # (app/services/replication/maintenance.check_clock_drift). Exposée ici
        # plutôt que stockée en base : aucune migration de schéma n'est requise.
        drift = current_app.extensions.get('clock_drift_seconds')
        try:
            tolerance = int(current_app.config.get(
                'SYNC_CLOCK_DRIFT_TOLERANCE_S', 300
            ))
        except (TypeError, ValueError):
            tolerance = 300

        return {
            'online': s.online,
            'pending_count': s.pending_count,
            'last_push_at': s.last_push_at.isoformat() if s.last_push_at else None,
            'last_pull_at': s.last_pull_at.isoformat() if s.last_pull_at else None,
            'last_error': s.last_error,
            'device_id': current_app.config.get('REPLICATION_DEVICE_ID'),
            'clock_drift_seconds': drift,
            'clock_drift_warning': (
                drift is not None and abs(drift) > tolerance
            ),
        }




@ns.route('/local-run')
class LocalSyncRun(Resource):
    def post(self):
        """Déclenche immédiatement un cycle push/pull sur le poste local."""
        if not current_app.config.get('LOCAL_EMBEDDED'):
            return {'message': 'Route réservée au backend local embarqué.'}, 404

        from app.services.replication.push import push_pending
        from app.services.replication.pull import pull_changes

        push_result = push_pending(current_app._get_current_object())
        pull_result = pull_changes(current_app._get_current_object())
        return {
            'push': push_result,
            'pull': pull_result,
            'online': True,
        }, 200
