from app.models.base import BaseModel
from app import db
from sqlalchemy import Enum, ForeignKey
import enum
from datetime import datetime

from app.models.utilisateur import Utilisateur


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
    code_postal = db.Column(db.String(20))
    
    # Abonnement
    statut = db.Column(
        Enum(StatutTenant, values_callable=lambda x: [e.value for e in x]),
        default=StatutTenant.EN_ESSAI,
        nullable=False,
    )
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

    # Paiement / Vitrine : configuration du compte marchand Papi du tenant
    # Les clés sont stockées chiffrées (Fernet / ENCRYPTION_KEY) et ne sont
    # jamais renvoyées en clair au frontend.
    papi_api_key_encrypted = db.Column(db.Text, nullable=True)
    papi_webhook_secret_encrypted = db.Column(db.Text, nullable=True)
    papi_environment = db.Column(db.String(20), nullable=True)
    papi_configured_at = db.Column(db.DateTime, nullable=True)

    # Vitrine publique : activée uniquement si le tenant a configuré Papi
    # ET basculé explicitement ce toggle. Aucun produit n'est exposé sinon.
    vitrine_enabled = db.Column(db.Boolean, nullable=False, default=False)
    vitrine_enabled_at = db.Column(db.DateTime, nullable=True)

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

    # Admin principal : rattaché au TENANT (et non à un utilisateur),
    # conformément à l'architecture SUPER ADMIN =| TENANT == ADMIN.
    admin_principal_id = db.Column(
        db.Integer,
        db.ForeignKey('utilisateurs.id', use_alter=True, name='tenants_admin_principal_id_fkey'),
        nullable=True
    )

    # Traçabilité (surcharge des colonnes de BaseModel) : override nécessaire
    # pour casser le cycle de dépendances circulaires tenants <-> utilisateurs
    # côté DDL PostgreSQL (drop_all/create_all de la suite de tests).
    created_by = db.Column(
        db.Integer,
        db.ForeignKey('utilisateurs.id', use_alter=True, name='tenants_created_by_fkey'),
        nullable=True,
    )
    updated_by = db.Column(
        db.Integer,
        db.ForeignKey('utilisateurs.id', use_alter=True, name='tenants_updated_by_fkey'),
        nullable=True,
    )

    def has_papi_configured(self) -> bool:
        """Le tenant a-t-il saisi une clé API Papi marchand ?"""
        return bool(self.papi_api_key_encrypted)

    def is_vitrine_active(self) -> bool:
        """Le tenant est-il exposé sur la vitrine commune ?

        Trois conditions cumulatives :
        1. La vitrine est activée par le tenant (toggle).
        2. Le tenant a configuré son compte marchand Papi.
        3. Le tenant a un statut actif (cf. StatutTenant).
        """
        if not self.vitrine_enabled:
            return False
        if not self.has_papi_configured():
            return False
        statut = self.statut.value if hasattr(self.statut, 'value') else self.statut
        return statut in ('actif', 'en_essai')

    def to_papi_status_dict(self) -> dict:
        """Statut Papi / vitrine pour le frontend (jamais la clé en clair)."""
        return {
            'papi_configured': self.has_papi_configured(),
            'papi_configured_at': (
                self.papi_configured_at.isoformat() if self.papi_configured_at else None
            ),
            'papi_environment': self.papi_environment,
            'vitrine_enabled': bool(self.vitrine_enabled),
            'vitrine_enabled_at': (
                self.vitrine_enabled_at.isoformat() if self.vitrine_enabled_at else None
            ),
            'vitrine_active': self.is_vitrine_active(),
        }

    def to_dict(self, include_subscription=False):
        data = {
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

            'admin_principal_id': self.admin_principal_id,

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

        if include_subscription:
            from app.models.abonnement import Abonnement, StatutAbonnement
            from datetime import datetime
            now = datetime.utcnow()
            abonnement = Abonnement.query.filter(
                Abonnement.tenant_id == self.id,
                Abonnement.is_active == True
            ).order_by(Abonnement.created_at.desc()).first()
            if abonnement:
                data['abonnement'] = abonnement.to_dict()
                data['abonnement']['statut'] = (
                    abonnement.statut.value
                    if hasattr(abonnement.statut, 'value')
                    else abonnement.statut
                )
                data['abonnement']['date_debut'] = (
                    abonnement.date_debut.isoformat()
                    if abonnement.date_debut
                    else None
                )
                data['abonnement']['date_fin'] = (
                    abonnement.date_fin.isoformat()
                    if abonnement.date_fin
                    else None
                )
            else:
                data['abonnement'] = None

            if self.admin_principal_id:
                admin = db.session.get(Utilisateur, self.admin_principal_id)
                if admin:
                    data['admin_principal'] = {
                        'id': admin.id,
                        'username': admin.username,
                        'email': admin.email,
                        'nom': admin.nom,
                        'prenom': admin.prenom,
                        'role': admin.role.value if hasattr(admin.role, 'value') else admin.role,
                    }
                else:
                    data['admin_principal'] = None
            else:
                data['admin_principal'] = None

        return data

    def __repr__(self):
        return f'<Tenant {self.nom} ({self.slug})>'
