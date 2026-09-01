from app import db
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import func

class BaseService:
    """Service de base avec fonctions CRUD génériques"""
    
    model = None
    
    @classmethod
    def _get_tenant_filter(cls, query):
        """Applique le filtre tenant à une requête"""
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        # Skip global tenant filter event listener to avoid duplicate filtering
        query = query.execution_options(_skip_tenant_filter=True)
        return query
    
    @classmethod
    def get_all(cls, page: int = 1, per_page: int = 20, 
                filters: Optional[Dict] = None, 
                order_by: Optional[str] = None) -> Tuple[List, int]:
        """Récupère toutes les entités avec pagination"""
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
        """Récupère une entité par son ID"""
        query = cls.model.query.filter_by(id=id, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()
    
    @classmethod
    def create(cls, data: Dict[str, Any]) -> Any:
        """Crée une nouvelle entité en bloquant le mass assignment des champs sensibles.

        Les champs protégés (tenant_id, is_active, role, statut, created_by,
        updated_by, etc.) ne peuvent jamais être fournis par l'appelant :
        le tenant_id est déterminé côté serveur (contexte authentifié).
        """
        protected_fields = getattr(cls, 'PROTECTED_FIELDS', None) or {
            'tenant_id', 'id', 'created_by', 'updated_by',
            'created_at', 'updated_at', 'is_active', 'role',
            'statut', 'password_hash',
            'custom_role_id', 'admin_statut',
            'device_id', 'is_principal_admin',
        }
        clean_data = {
            key: value for key, value in data.items()
            if key not in protected_fields
        }

        if hasattr(cls.model, 'tenant_id'):
            # La source de vérité du tenant est le contexte authentifié.
            tenant_id = get_current_tenant_id()
            if tenant_id is None:
                # Aucun contexte tenant (ex : super admin) : on accepte le
                # tenant fourni explicitement (provisioning plateforme).
                tenant_id = clean_data.get('tenant_id')
            if not tenant_id:
                raise ValueError("tenant_id est obligatoire pour cette ressource")
            clean_data['tenant_id'] = tenant_id

        instance = cls.model(**clean_data)
        instance.save()
        return instance
    
    @classmethod
    def update(cls, id: int, data: Dict[str, Any]) -> Optional[Any]:
        """Met à jour une entité"""
        instance = cls.get_by_id(id)
        if not instance:
            return None
        data = data or {}
        protected_fields = getattr(cls, 'PROTECTED_FIELDS', None) or {
            'tenant_id', 'id', 'created_by', 'updated_by',
            'created_at', 'updated_at', 'is_active', 'role',
            'statut', 'password_hash',
            'custom_role_id', 'admin_statut',
            'device_id', 'is_principal_admin',
        }
        for key, value in data.items():
            if key in protected_fields:
                continue
            if hasattr(instance, key):
                setattr(instance, key, value)
        instance.save()
        return instance
    
    @classmethod
    def delete(cls, id: int) -> bool:
        """Supprime une entité (soft delete)"""
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True
    
    @classmethod
    def hard_delete(cls, id: int) -> bool:
        """Supprime une entité (hard delete)"""
        query = cls.model.query.filter_by(id=id)
        query = cls._get_tenant_filter(query)
        instance = query.first()
        if not instance:
            return False
        instance.hard_delete()
        return True
    

    @classmethod
    def exists(cls, **kwargs) -> bool:
        """Vérifie si une entité existe avec les critères donnés"""
        query = cls.model.query.filter_by(**kwargs)
        query = cls._get_tenant_filter(query)
        return query.first() is not None