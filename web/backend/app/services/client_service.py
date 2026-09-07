from app.models.client import Client
from app.services.base_service import BaseService
from app.security.tenant import get_current_tenant_id
from app import db
from sqlalchemy import or_, func
from typing import Optional, Dict, Any, List, Tuple

class ClientService(BaseService):
    model = Client
    
    @classmethod
    def _get_tenant_filter(cls, query):
        """Applique le filtre tenant à une requête"""
        from app.security.tenant import set_tenant_filter
        query = set_tenant_filter(query, cls.model)
        # Skip global tenant filter event listener to avoid duplicate filtering
        query = query.execution_options(_skip_tenant_filter=True)
        return query
    
    @classmethod
    def get_all(cls, page: int = 1, per_page: int = 20,
                filters: Optional[Dict] = None,
                order_by: Optional[str] = None) -> Tuple[List[Client], int]:
        """Récupère tous les clients avec filtres"""
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        # Skip global tenant filter event listener to avoid duplicate filtering
        query = query.execution_options(_skip_tenant_filter=True)
        
        if filters:
            if filters.get('type'):
                query = query.filter_by(type=filters['type'])
            if filters.get('secteur'):
                query = query.filter_by(secteur=filters['secteur'])
            if filters.get('commercial_id'):
                query = query.filter_by(commercial_id=filters['commercial_id'])
            if filters.get('est_actif') is not None:
                query = query.filter_by(est_actif=filters['est_actif'])
            if filters.get('est_bloque') is not None:
                query = query.filter_by(est_bloque=filters['est_bloque'])
            if filters.get('search'):
                search = f"%{filters['search']}%"
                query = query.filter(
                    or_(
                        Client.raison_sociale.ilike(search),
                        Client.code.ilike(search),
                        Client.nom.ilike(search),
                        Client.prenom.ilike(search),
                        Client.email.ilike(search),
                        Client.ville_facturation.ilike(search)
                    )
                )
        
        if order_by:
            query = query.order_by(order_by)
        else:
            query = query.order_by(Client.nom.asc(), Client.prenom.asc())
        
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total
    
    @classmethod
    def create(cls, data: Dict[str, Any]) -> Client:
        """Crée un nouveau client"""
        if 'code' not in data or not data['code']:
            raise ValueError("Le code client est requis")
        
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("Aucun tenant associe a ce compte")
        
        q = cls.model.query.filter_by(code=data['code'], tenant_id=tenant_id)
        q = q.execution_options(_skip_tenant_filter=True)
        if q.first():
            raise ValueError(f"Le code {data['code']} existe déjà")
        
        if data.get('email'):
            q = cls.model.query.filter_by(email=data['email'], tenant_id=tenant_id)
            q = q.execution_options(_skip_tenant_filter=True)
            if q.first():
                raise ValueError(f"L'email {data['email']} existe déjà")
        
        data['tenant_id'] = tenant_id
        return super().create(data)
    
    @classmethod
    def get_by_email(cls, email: str) -> Optional[Client]:
        """Récupère un client par son email"""
        query = cls.model.query.filter_by(email=email, is_active=True)
        query = cls._get_tenant_filter(query)
        query = query.execution_options(_skip_tenant_filter=True)
        return query.first()
    
    @classmethod
    def get_clients_actifs(cls) -> List[Client]:
        """Récupère les clients actifs"""
        query = cls.model.query.filter_by(is_active=True, est_actif=True)
        query = cls._get_tenant_filter(query)
        query = query.execution_options(_skip_tenant_filter=True)
        return query.all()
    
    @classmethod
    def get_top_clients(cls, limit: int = 10) -> List[Dict]:
        """Récupère les meilleurs clients (CA)"""
        from app.models.vente import Vente
        from app.security.tenant import get_current_tenant_id
        
        tenant_id = get_current_tenant_id()
        query = db.session.query(
            Client.id,
            Client.nom,
            Client.prenom,
            Client.raison_sociale,
            func.sum(Vente.total_ttc).label('ca_total')
        ).join(
            Vente,
            Client.id == Vente.client_id
        ).filter(
            Client.is_active == True,
            Vente.is_active == True,
            Vente.statut == 'payee'
        )
        
        if tenant_id:
            query = query.filter(Client.tenant_id == tenant_id)
        
        # Skip global tenant filter event listener to avoid duplicate filtering
        query = query.execution_options(_skip_tenant_filter=True)
        
        results = query.group_by(
            Client.id
        ).order_by(
            func.sum(Vente.total_ttc).desc()
        ).limit(limit).all()
        
        return [{
            'id': r[0],
            'nom': r[1],
            'prenom': r[2],
            'raison_sociale': r[3],
            'ca_total': float(r[4] or 0)
        } for r in results]
    
    @classmethod
    def get_client_stats(cls, client_id: int) -> Dict:
        """Récupère les statistiques d'un client"""
        client = cls.get_by_id(client_id)
        if not client:
            return {}
        
        from app.models.vente import Vente
        from app.models.facture import Facture
        from app.models.paiement import Paiement
        
        # Dernières commandes
        dernieres_commandes = client.ventes.filter_by(
            is_active=True
        ).order_by(
            Vente.created_at.desc()
        ).limit(5).execution_options(_skip_tenant_filter=True).all()
        
        # Factures
        factures = client.factures.filter_by(
            is_active=True
        ).execution_options(_skip_tenant_filter=True).all()
        
        # Paiements récents
        paiements_recents = client.paiements.filter_by(
            is_active=True
        ).order_by(
            Paiement.created_at.desc()
        ).limit(10).execution_options(_skip_tenant_filter=True).all()
        
        return {
            'client': client.to_dict(),
            'total_achats': float(client.total_achats),
            'nombre_commandes': client.total_commandes,
            'dernier_achat': client.dernier_achat.isoformat() if client.dernier_achat else None,
            'dernieres_commandes': [v.to_dict() for v in dernieres_commandes],
            'factures': [f.to_dict() for f in factures],
            'paiements_recents': [p.to_dict() for p in paiements_recents],
            'solde': float(client.solde)
        }