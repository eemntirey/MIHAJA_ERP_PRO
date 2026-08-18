from app.models.fournisseur import Fournisseur
from app.services.base_service import BaseService
from app.security.tenant import get_current_tenant_id
from app import db
from sqlalchemy import or_, func
from typing import Optional, Dict, Any, List, Tuple

class FournisseurService(BaseService):
    model = Fournisseur
    
    @classmethod
    def _get_tenant_filter(cls, query):
        """Applique le filtre tenant à une requête"""
        from app.security.tenant import set_tenant_filter
        return set_tenant_filter(query, cls.model)
    
    @classmethod
    def get_all(cls, page: int = 1, per_page: int = 20,
                filters: Optional[Dict] = None,
                order_by: Optional[str] = None) -> Tuple[List[Fournisseur], int]:
        """Récupère tous les fournisseurs avec filtres"""
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        
        if filters:
            if filters.get('type'):
                query = query.filter_by(type=filters['type'])
            if filters.get('pays'):
                query = query.filter_by(pays=filters['pays'])
            if filters.get('est_actif') is not None:
                query = query.filter_by(est_actif=filters['est_actif'])
            if filters.get('est_favori') is not None:
                query = query.filter_by(est_favori=filters['est_favori'])
            if filters.get('search'):
                search = f"%{filters['search']}%"
                query = query.filter(
                    or_(
                        Fournisseur.raison_sociale.ilike(search),
                        Fournisseur.code.ilike(search),
                        Fournisseur.siret.ilike(search),
                        Fournisseur.email.ilike(search),
                        Fournisseur.ville.ilike(search)
                    )
                )
        
        if order_by:
            query = query.order_by(order_by)
        else:
            query = query.order_by(Fournisseur.raison_sociale.asc())
        
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total
    
    @classmethod
    def create(cls, data: Dict[str, Any]) -> Fournisseur:
        """Crée un nouveau fournisseur"""
        tenant_id = get_current_tenant_id()
        
        # Vérifier le code unique dans le tenant
        q = cls.model.query.filter_by(code=data['code'])
        if tenant_id:
            q = q.filter_by(tenant_id=tenant_id)
        if q.first():
            raise ValueError(f"Le code {data['code']} existe déjà")
        
        # Vérifier le SIRET unique dans le tenant
        if data.get('siret'):
            q = cls.model.query.filter_by(siret=data['siret'])
            if tenant_id:
                q = q.filter_by(tenant_id=tenant_id)
            if q.first():
                raise ValueError(f"Le SIRET {data['siret']} existe déjà")
        
        if tenant_id:
            data['tenant_id'] = tenant_id
        fournisseur = cls.model(**data)
        fournisseur.save()
        return fournisseur
    
    @classmethod
    def get_by_siret(cls, siret: str) -> Optional[Fournisseur]:
        """Récupère un fournisseur par son SIRET"""
        query = cls.model.query.filter_by(siret=siret, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()
    
    @classmethod
    def get_top_fournisseurs(cls, limit: int = 10) -> List[Dict]:
        """Récupère les meilleurs fournisseurs (chiffre d'affaires)"""
        from app.models.commande_fournisseur import CommandeFournisseur
        from app.security.tenant import get_current_tenant_id
        
        tenant_id = get_current_tenant_id()
        query = db.session.query(
            Fournisseur.id,
            Fournisseur.raison_sociale,
            Fournisseur.code,
            func.sum(CommandeFournisseur.total_ht).label('ca_total')
        ).join(
            CommandeFournisseur,
            Fournisseur.id == CommandeFournisseur.fournisseur_id
        ).filter(
            Fournisseur.is_active == True,
            CommandeFournisseur.is_active == True
        )
        
        if tenant_id:
            query = query.filter(Fournisseur.tenant_id == tenant_id)
        
        results = query.group_by(
            Fournisseur.id
        ).order_by(
            func.sum(CommandeFournisseur.total_ht).desc()
        ).limit(limit).all()
        
        return [{
            'id': r[0],
            'raison_sociale': r[1],
            'code': r[2],
            'ca_total': float(r[3] or 0)
        } for r in results]