from app import db
from app.models.audit_log import AuditLog, TypeActionAudit


def log_audit(type_action, description, tenant_id=None, utilisateur_id=None, metadata=None):
    try:
        entry = AuditLog(
            tenant_id=tenant_id,
            utilisateur_id=utilisateur_id,
            type_action=type_action,
            description=description,
            metadata_json=str(metadata) if metadata else None,
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
