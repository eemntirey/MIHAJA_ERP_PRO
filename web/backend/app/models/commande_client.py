from app.models.base import BaseTenantModel
from app import db
from sqlalchemy import Enum, Numeric
import enum
import json

class StatutCommande(enum.Enum):
    EN_ATTENTE = 'en_attente'
    CONFIRMEE = 'confirmee'
    EXPEDIEE = 'expediee'
    LIVREE = 'livree'
    ANNULEE = 'annulee'

class CommandeClient(BaseTenantModel):
    __tablename__ = 'commandes_client'
    
    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    nom_client = db.Column(db.String(100), nullable=False)
    prenom_client = db.Column(db.String(100))
    email_client = db.Column(db.String(120), nullable=False)
    telephone_client = db.Column(db.String(20))
    
    adresse_livraison = db.Column(db.String(200))
    ville_livraison = db.Column(db.String(100))
    code_postal_livraison = db.Column(db.String(10))
    pays_livraison = db.Column(db.String(50), default='Madagascar')
    
    items = db.Column(db.Text, nullable=False)
    total_ht = db.Column(Numeric(10, 2), nullable=False, default=0)
    total_ttc = db.Column(Numeric(10, 2), nullable=False, default=0)
    
    statut = db.Column(Enum(StatutCommande), default=StatutCommande.EN_ATTENTE, nullable=False)
    
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), index=True)
    tenant = db.relationship('Tenant', backref='commandes_client')
    
    notes = db.Column(db.Text)
    
    @property
    def items_list(self):
        if self.items:
            try:
                return json.loads(self.items)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    @items_list.setter
    def items_list(self, value):
        self.items = json.dumps(value)
    
    def to_dict(self):
        data = super().to_dict()
        data['statut'] = (
            self.statut.value
            if hasattr(self.statut, 'value')
            else self.statut
        )
        data['total_ht'] = float(self.total_ht)
        data['total_ttc'] = float(self.total_ttc)
        enriched_items = []
        for item in self.items_list:
            produit = None
            try:
                from app.models.produit import Produit
                produit_query = Produit.query.filter_by(id=item.get('produit_id'))
                if self.tenant_id:
                    produit_query = produit_query.filter_by(tenant_id=self.tenant_id)
                produit = produit_query.first()
            except Exception:
                pass
            enriched_items.append({
                'produit_id': item.get('produit_id'),
                'quantite': item.get('quantite', 1),
                'produit_nom': produit.nom if produit else None,
                'prix_unitaire': float(produit.prix_vente_ht) if produit else 0,
                'total': float(produit.prix_vente_ht or 0) * item.get('quantite', 1) if produit else 0,
            })
        data['items'] = enriched_items
        return data
    
    def __repr__(self):
        return f'<CommandeClient {self.reference} - {self.nom_client}>'
