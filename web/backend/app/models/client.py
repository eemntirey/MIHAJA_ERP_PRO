from app.models.base import BaseModel
from app import db
from sqlalchemy import Enum, Index, Numeric
import enum

class TypeClient(enum.Enum):
    BOUTIQUE = 'boutique'
    EPICERIE = 'epicerie'
    REVENDEUR = 'revendeur'
    SEMI_GROSSISTE = 'semi_grossiste'
    GROSSISTE = 'grossiste'
    SUPERMARCHE = 'supermarche'
    RESTAURANT = 'restaurant'
    HOTEL = 'hotel'
    ENTREPRISE = 'entreprise'
    INSTITUTION = 'institution'
    PARTICULIER = 'particulier'

class SecteurActivite(enum.Enum):
    AGRICULTURE = 'agriculture'
    INDUSTRIE = 'industrie'
    CONSTRUCTION = 'construction'
    COMMERCE = 'commerce'
    TRANSPORT = 'transport'
    SERVICES = 'services'
    AUTRE = 'autre'

class Client(BaseModel):
    __tablename__ = 'clients'
    
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    raison_sociale = db.Column(db.String(200))
    nom = db.Column(db.String(100))
    prenom = db.Column(db.String(100))
    type = db.Column(
        Enum(
            TypeClient,
            values_callable=lambda enum_class: [e.value for e in enum_class]
        ),
        default=TypeClient.PARTICULIER
    )
    secteur = db.Column(
        Enum(
            SecteurActivite,
            values_callable=lambda enum_class: [e.value for e in enum_class]
        ),
        default=SecteurActivite.AUTRE
    )
    
    # Identification
    siret = db.Column(db.String(20))
    numero_tva = db.Column(db.String(20))
    numero_rcs = db.Column(db.String(50))
    
    # Contact
    email = db.Column(db.String(100), unique=True, index=True)
    email_secondaire = db.Column(db.String(100))
    telephone = db.Column(db.String(20))
    telephone_secondaire = db.Column(db.String(20))
    mobile = db.Column(db.String(20))
    fax = db.Column(db.String(20))
    site_web = db.Column(db.String(200))
    
    # Adresse de facturation
    adresse_facturation = db.Column(db.String(200))
    complement_facturation = db.Column(db.String(200))
    code_postal_facturation = db.Column(db.String(10))
    ville_facturation = db.Column(db.String(100))
    pays_facturation = db.Column(db.String(50), default='Madagascar')
    
    # Adresse de livraison (si différente)
    adresse_livraison = db.Column(db.String(200))
    complement_livraison = db.Column(db.String(200))
    code_postal_livraison = db.Column(db.String(10))
    ville_livraison = db.Column(db.String(100))
    pays_livraison = db.Column(db.String(50), default='Madagascar')
    
    # Contact principal
    contact_nom = db.Column(db.String(100))
    contact_prenom = db.Column(db.String(100))
    contact_fonction = db.Column(db.String(100))
    contact_email = db.Column(db.String(100))
    contact_telephone = db.Column(db.String(20))
    
    # Informations commerciales
    conditions_paiement = db.Column(db.String(50), default='30 jours')
    remise_standard = db.Column(Numeric(5, 2), default=0)
    plafond_credit = db.Column(Numeric(10, 2))
    echeance_credit = db.Column(db.Integer, default=30)  # jours
    
    # Compte client
    solde = db.Column(Numeric(10, 2), default=0)
    points_fidelite = db.Column(db.Integer, default=0)
    
    # Commercial
    commercial_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), index=True)
    
    # Statut
    est_favori = db.Column(db.Boolean, default=False)
    est_actif = db.Column(db.Boolean, default=True)
    est_bloque = db.Column(db.Boolean, default=False)
    note = db.Column(db.Integer)  # 1-5
    
    # Relations
    commercial = db.relationship('Utilisateur', back_populates='clients', foreign_keys='Client.commercial_id')
    ventes = db.relationship('Vente', back_populates='client', lazy='dynamic')
    factures = db.relationship('Facture', back_populates='client', lazy='dynamic')
    paiements = db.relationship('Paiement', back_populates='client', lazy='dynamic')
    
    __table_args__ = (
        Index('idx_client_nom_prenom', 'nom', 'prenom'),
        Index('idx_client_type_secteur', 'type', 'secteur'),
        Index('idx_client_commercial', 'commercial_id'),
    )
    
    @property
    def nom_complet(self):
        if self.type == TypeClient.PARTICULIER:
            return f"{self.prenom} {self.nom}"
        return self.raison_sociale or f"{self.prenom} {self.nom}"
    
    @property
    def adresse_complete_facturation(self):
        return f"{self.adresse_facturation}, {self.code_postal_facturation} {self.ville_facturation}, {self.pays_facturation}"
    
    @property
    def total_achats(self):
        """Total des achats du client"""
        from app.models.vente import Vente
        return self.ventes.filter_by(is_active=True, statut='payee').with_entities(
            db.func.sum(Vente.total_ttc)
        ).scalar() or 0
    
    @property
    def total_commandes(self):
        """Nombre total de commandes"""
        return self.ventes.filter_by(is_active=True).count()
    
    @property
    def dernier_achat(self):
        """Date du dernier achat"""
        from app.models.vente import Vente
        derniere_vente = self.ventes.filter_by(is_active=True).order_by(
            Vente.created_at.desc()
        ).first()
        return derniere_vente.created_at if derniere_vente else None
    
    @property
    def est_a_credit(self):
        """Vérifie si le client est à crédit"""
        return self.solde < 0
    
    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if 'type' in data and self.type:
            data['type'] = self.type.value
        if 'secteur' in data and self.secteur:
            data['secteur'] = self.secteur.value
        data['nom_complet'] = self.nom_complet
        data['total_achats'] = float(self.total_achats)
        data['total_commandes'] = self.total_commandes
        return data
    
    def __repr__(self):
        return f'<Client {self.code} - {self.nom_complet}>'