from app.models.base import BaseModel
from app import db
from sqlalchemy import Enum, ForeignKey
import enum
from datetime import datetime


class StatutTenant(enum.Enum):
    ACTIF = 'actif'
    INACTIF = 'inactif'
    BLOQUE = 'bloque'
    EN_ESSAI = 'en_essai'


class Tenant(BaseModel):
    __tablename__ = 'tenants'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    domaine = db.Column(db.String(200), unique=True, index=True)
    email_contact = db.Column(db.String(120))
    telephone = db.Column(db.String(20))
    adresse = db.Column(db.String(200))
    ville = db.Column(db.String(100))
    pays = db.Column(db.String(50), default='Madagascar')
    code_postal = db.Column(db.String(10))
    
    # Abonnement
    statut = db.Column(Enum(StatutTenant), default=StatutTenant.EN_ESSAI, nullable=False)
    plan = db.Column(db.String(50), default='gratuit')  # gratuit, starter, pro, enterprise
    date_debut_essai = db.Column(db.DateTime)
    date_fin_essai = db.Column(db.DateTime)
    date_abonnement = db.Column(db.DateTime)
    
    # Limites
    max_utilisateurs = db.Column(db.Integer, default=5)
    max_produits = db.Column(db.Integer, default=100)
    max_clients = db.Column(db.Integer, default=50)
    
    # Configuration
    logo = db.Column(db.String(200))
    devise = db.Column(db.String(10), default='MGA')
    langue = db.Column(db.String(5), default='mg')
    fuseau_horaire = db.Column(db.String(50), default='Indian/Antananarivo')
    
    # Relations
    utilisateurs = db.relationship(
        'Utilisateur',
        back_populates='tenant',
        lazy='dynamic',
        primaryjoin='and_(Tenant.id==Utilisateur.tenant_id, Utilisateur.is_active==True)'
    )
    abonnements = db.relationship(
        'Abonnement',
        back_populates='tenant',
        lazy='dynamic'
    )
    paiements = db.relationship(
        'Paiement',
        back_populates='tenant',
        lazy='dynamic'
    )
    employes = db.relationship(
        'Employe',
        back_populates='tenant',
        lazy='dynamic'
    )
    stagiaires = db.relationship(
        'Stagiaire',
        back_populates='tenant',
        lazy='dynamic'
    )
    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'slug': self.slug,
            'domaine': self.domaine,
            'email_contact': self.email_contact,
            'telephone': self.telephone,
            'adresse': self.adresse,
            'ville': self.ville,
            'pays': self.pays,
            'code_postal': self.code_postal,

            'statut': (
                self.statut.value
                if hasattr(self.statut, 'value')
                else self.statut
            ),

            'plan': self.plan,

            'date_debut_essai': (
                self.date_debut_essai.isoformat()
                if self.date_debut_essai
                else None
            ),

            'date_fin_essai': (
                self.date_fin_essai.isoformat()
                if self.date_fin_essai
                else None
            ),

            'date_abonnement': (
                self.date_abonnement.isoformat()
                if self.date_abonnement
                else None
            ),

            'max_utilisateurs': self.max_utilisateurs,
            'max_produits': self.max_produits,
            'max_clients': self.max_clients,

            'logo': self.logo,
            'devise': self.devise,
            'langue': self.langue,
            'fuseau_horaire': self.fuseau_horaire,

            'is_active': self.is_active,

            'created_at': (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),

            'updated_at': (
                self.updated_at.isoformat()
                if self.updated_at
                else None
            ),
        }
    def __repr__(self):
        return f'<Tenant {self.nom} ({self.slug})>'
