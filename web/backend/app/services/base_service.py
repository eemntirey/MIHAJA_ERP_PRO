from app import db
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import func

class BaseService:
    """Service de base avec fonctions CRUD generiques"""

    model = None

    @classmethod
    def _get_tenant_filter(cls, query):
        """Applique le filtre tenant (fail-closed) puis desactive le listener global."""
        from app.security.tenant import set_tenant_filter
        query = set_tenant_filter(query, cls.model)
        query = query.execution_options(_skip_tenant_filter=True)
        return query

    @classmethod
    def get_all(cls, page: int = 1, per_page: int = 20,
                filters: Optional[Dict] = None,
                order_by: Optional[str] = None) -> Tuple[List, int]:
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)

        if filters:
            for key, value in filters.items():
                if value is not None:
                    if hasattr(cls.model, key):
                        query = query.filter_by(**{key: value})

        if order_by:
            query = query.order_by(order_by)

        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id: int) -> Optional[Any]:
        query = cls.model.query.filter_by(id=id, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data: Dict[str, Any]) -> Any:
        protected_fields = getattr(cls, 'PROTECTED_FIELDS', None) or {
            'tenant_id', 'id', 'created_by', 'updated_by',
            'created_at', 'updated_at', 'is_active', 'role',
            'statut', 'password_hash',
            'custom_role_id', 'admin_statut',
        }
        clean = {k: v for k, v in data.items() if k not in protected_fields and hasattr(cls.model, k)}
        tenant_id = get_current_tenant_id()
        if tenant_id is None and hasattr(cls.model, 'tenant_id'):
            raise ValueError('Aucun tenant associe a ce compte')
        if hasattr(cls.model, 'tenant_id'):
            clean['tenant_id'] = tenant_id
        instance = cls.model(**clean)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id: int, data: Dict[str, Any]) -> Optional[Any]:
        instance = cls.get_by_id(id)
        if not instance:
            return None
        protected_fields = getattr(cls, 'PROTECTED_FIELDS', None) or {
            'tenant_id', 'id', 'created_by', 'created_at', 'password_hash',
        }
        for key, value in data.items():
            if key in protected_fields:
                continue
            if hasattr(instance, key):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id: int) -> bool:
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.is_active = False
        db.session.commit()
        return True
