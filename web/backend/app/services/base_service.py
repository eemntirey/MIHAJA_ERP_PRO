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
        """Crée une nouvelle entité"""
        if hasattr(cls.model, 'tenant_id'):
            tenant_id = data.get('tenant_id') or get_current_tenant_id()
            if not tenant_id:
                raise ValueError("tenant_id est obligatoire pour cette ressource")
            data['tenant_id'] = tenant_id
        instance = cls.model(**data)
        instance.save()
        return instance
    
    @classmethod
    def update(cls, id: int, data: Dict[str, Any]) -> Optional[Any]:
        """Met à jour une entité"""
        instance = cls.get_by_id(id)
        if not instance:
            return None
        
        for key, value in data.items():
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