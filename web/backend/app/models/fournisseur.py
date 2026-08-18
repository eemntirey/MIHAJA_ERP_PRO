from app.models.base import BaseModel
from app import db
from sqlalchemy import Enum, Index, Numeric
import enum

class TypeFournisseur(enum.Enum):
    LOCAL = 'local'
    NATIONAL = 'national'
    INTERNATIONAL = 'international'
    GROSSISTE = 'grossiste'
    FABRICANT = 'fabricant'
    DISTRIBUTEUR = 'distributeur'

class Fournisseur(BaseModel):
    __tablename__ = 'fournisseurs'
    
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    raison_sociale = db.Column(db.String(200), nullable=False)
    nom_commercial = db.Column(db.String(200))
    
    # Identification légale
    siret = db.Column(db.String(20))
    numero_tva = db.Column(db.String(20))
    forme_juridique = db.Column(db.String(50))
    capital_social = db.Column(Numeric(10, 2))
    
    # Type
    type = db.Column(
        Enum(
            TypeFournisseur,
            values_callable=lambda enum_class: [e.value for e in enum_class]
        ),
        default=TypeFournisseur.LOCAL,
        nullable=False
    )
    # Contact
    email = db.Column(db.String(100))
    telephone = db.Column(db.String(20))
    mobile = db.Column(db.String(20))
    fax = db.Column(db.String(20))
    site_web = db.Column(db.String(200))
    
    # Contact principal
    contact_nom = db.Column(db.String(100))
    contact_prenom = db.Column(db.String(100))
    contact_fonction = db.Column(db.String(100))
    contact_email = db.Column(db.String(100))
    contact_telephone = db.Column(db.String(20))
    
    # Adresse
    adresse = db.Column(db.String(200))
    complement_adresse = db.Column(db.String(200))
    code_postal = db.Column(db.String(10))
    ville = db.Column(db.String(100))
    pays = db.Column(db.String(50), default='Madagascar')
    coordonnees_gps = db.Column(db.String(100))
    
    # Informations bancaires
    iban = db.Column(db.String(34))
    bic = db.Column(db.String(11))
    nom_banque = db.Column(db.String(100))
    
    # Informations commerciales
    conditions_paiement = db.Column(db.String(50), default='30 jours fin de mois')
    delai_livraison = db.Column(db.Integer, default=5)  # jours
    mode_livraison = db.Column(db.String(50), default='Standard')
    
    # Remises
    remise_standard = db.Column(Numeric(5, 2), default=0)
    remise_volume = db.Column(Numeric(5, 2), default=0)
    
    # Statut
    est_favori = db.Column(db.Boolean, default=False)
    est_actif = db.Column(db.Boolean, default=True)
    note = db.Column(db.Integer)  # 1-5
    
    # Relations
    produits = db.relationship('Produit', back_populates='fournisseur', lazy='dynamic')
    commandes = db.relationship('CommandeFournisseur', back_populates='fournisseur', lazy='dynamic')
    factures = db.relationship('FactureFournisseur', back_populates='fournisseur', lazy='dynamic')
    commandes_achat = db.relationship('CommandeAchat', back_populates='fournisseur', lazy='dynamic')
    paiements = db.relationship('Paiement', back_populates='fournisseur', lazy='dynamic')
    
    __table_args__ = (
        Index('idx_fournisseur_raison_sociale', 'raison_sociale'),
        Index('idx_fournisseur_type', 'type'),
    )
    
    @property
    def nom_complet(self):
        return self.nom_commercial or self.raison_sociale
    
    @property
    def nombre_produits(self):
        return self.produits.filter_by(is_active=True).count()
    
    @property
    def chiffre_affaires(self):
        """Chiffre d'affaires total avec ce fournisseur"""
        from app.models.commande_fournisseur import CommandeFournisseur
        tenant_id = getattr(self, 'tenant_id', None)
        query = db.session.query(
            db.func.sum(CommandeFournisseur.total_ht)
        ).filter(
            CommandeFournisseur.fournisseur_id == self.id,
            CommandeFournisseur.is_active == True
        )
        if tenant_id is not None:
            query = query.filter(CommandeFournisseur.tenant_id == tenant_id)
        total = query.scalar()
        return total or 0
    
    @property
    def dernieres_commandes(self):
        from app.models.commande_fournisseur import CommandeFournisseur
        return self.commandes.filter_by(is_active=True).order_by(
            CommandeFournisseur.created_at.desc()
        ).limit(5).all()
    
    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if 'type' in data and self.type:
            data['type'] = self.type.value
        data['nombre_produits'] = self.nombre_produits
        data['nom_complet'] = self.nom_complet
        data['chiffre_affaires'] = float(self.chiffre_affaires) if self.chiffre_affaires else 0
        return data
    
    def __repr__(self):
        return f'<Fournisseur {self.code} - {self.raison_sociale}>'