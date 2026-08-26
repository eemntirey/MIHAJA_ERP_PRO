from decimal import Decimal

from app.models.base import BaseModel
from app import db
from sqlalchemy import Numeric, Index, CheckConstraint


class Produit(BaseModel):
    __tablename__ = 'produits'
    
    # Identifiants
    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    code_barre = db.Column(db.String(50), unique=True)
    code_interne = db.Column(db.String(50), unique=True)
    
    # Informations générales
    nom = db.Column(db.String(200), nullable=False)
    description_courte = db.Column(db.String(500))
    description_longue = db.Column(db.Text)
    
    # Catégorisation
    categorie = db.Column(db.String(100), index=True)
    sous_categorie = db.Column(db.String(100))
    famille = db.Column(db.String(100))
    marque = db.Column(db.String(100))
    modele = db.Column(db.String(100))
    unite = db.Column(db.String(50), default='piece')
    
    # Prix
    prix_achat_ht = db.Column(Numeric(10, 2), nullable=False, default=0)
    prix_achat_ttc = db.Column(Numeric(10, 2))
    prix_vente_ht = db.Column(Numeric(10, 2), nullable=False, default=0)
    prix_vente_ttc = db.Column(Numeric(10, 2))
    taux_tva = db.Column(Numeric(5, 2), default=10.00)
    marge_standard = db.Column(Numeric(5, 2))
    
    # Stock
    quantite_stock = db.Column(Numeric(10, 2), default=0)
    seuil_alerte = db.Column(Numeric(10, 2), default=10)
    seuil_critique = db.Column(Numeric(10, 2), default=5)
    emplacement = db.Column(db.String(100))
    rayon = db.Column(db.String(50))
    etagere = db.Column(db.String(50))
    
    # Dimensions et poids
    poids = db.Column(Numeric(10, 2))
    longueur = db.Column(Numeric(10, 2))
    largeur = db.Column(Numeric(10, 2))
    hauteur = db.Column(Numeric(10, 2))
    volume = db.Column(Numeric(10, 2))
    
    # Fournisseur
    fournisseur_id = db.Column(db.Integer, db.ForeignKey('fournisseurs.id'), index=True)
    reference_fournisseur = db.Column(db.String(50))
    
    # Images et codes
    image_url = db.Column(db.String(500))
    qr_code_data = db.Column(db.String(500))
    
    # Prix multi-niveaux
    prix_grossiste = db.Column(Numeric(10, 2))
    prix_revendeur = db.Column(Numeric(10, 2))
    prix_demi_gros = db.Column(Numeric(10, 2))
    
    # Tags et recherche
    tags = db.Column(db.String(500))  # comma-separated tags
    
    # Statut
    statut = db.Column(db.String(20), default='actif')  # actif, en_rupture, abandonne
    est_service = db.Column(db.Boolean, default=False)
    est_dechirable = db.Column(db.Boolean, default=False)
    est_dangereux = db.Column(db.Boolean, default=False)
    
    # Relations
    fournisseur = db.relationship('Fournisseur', back_populates='produits')
    mouvements_stock = db.relationship('MouvementStock', back_populates='produit', lazy='dynamic')
    lignes_vente = db.relationship('LigneVente', back_populates='produit', lazy='dynamic')
    lignes_achat = db.relationship('LigneAchat', back_populates='produit', lazy='dynamic')
    
    __table_args__ = (
        Index('idx_produit_nom_categorie', 'nom', 'categorie'),
        Index('idx_produit_fournisseur', 'fournisseur_id', 'categorie'),
        Index('idx_produit_marque_modele', 'marque', 'modele'),
        CheckConstraint('prix_achat_ht >= 0', name='ck_prix_achat_ht_positive'),
        CheckConstraint('prix_vente_ht >= 0', name='ck_prix_vente_ht_positive'),
        CheckConstraint('quantite_stock >= 0', name='ck_quantite_stock_positive'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._calculer_prix_ttc()
        self._calculer_volume()
    
    def _calculer_prix_ttc(self):
        """Calcule les prix TTC"""
        if self.prix_achat_ht is not None and self.taux_tva is not None:
            self.prix_achat_ttc = self.prix_achat_ht * (1 + self.taux_tva / 100)
        if self.prix_vente_ht is not None and self.taux_tva is not None:
            self.prix_vente_ttc = self.prix_vente_ht * (1 + self.taux_tva / 100)
    
    def _calculer_volume(self):
        """Calcule le volume en m³"""
        if self.longueur is not None and self.largeur is not None and self.hauteur is not None:
            self.volume = (self.longueur * self.largeur * self.hauteur) / 1000000  # en m³
    
    @property
    def valeur_stock(self):
        """Valeur totale du stock"""
        return self.quantite_stock * self.prix_achat_ht
    
    @property
    def marge_unitaire(self):
        """Marge unitaire"""
        return self.prix_vente_ht - self.prix_achat_ht
    
    @property
    def taux_marge(self):
        """Taux de marge en pourcentage"""
        if self.prix_achat_ht and self.prix_achat_ht > 0:
            return ((self.prix_vente_ht - self.prix_achat_ht) / self.prix_achat_ht) * 100
        return 0
    
    @property
    def taux_marque(self):
        """Taux de marque en pourcentage"""
        if self.prix_vente_ht and self.prix_vente_ht > 0:
            return ((self.prix_vente_ht - self.prix_achat_ht) / self.prix_vente_ht) * 100
        return 0
    
    @property
    def est_en_rupture(self):
        """Vérifie si le produit est en rupture"""
        return self.quantite_stock <= 0
    
    @property
    def est_alerte_stock(self):
        """Vérifie si le stock est sous le seuil d'alerte"""
        return self.quantite_stock <= self.seuil_alerte
    
    @property
    def est_stock_critique(self):
        """Vérifie si le stock est critique"""
        return self.quantite_stock <= self.seuil_critique
    
    def ajouter_stock(self, quantite, raison='', utilisateur_id=None):
        """Ajoute du stock"""
        quantite = Decimal(str(quantite))
        if quantite <= 0:
            raise ValueError("La quantité doit être positive")
        
        self.quantite_stock += quantite
        self.save()
        
        # Créer un mouvement de stock
        from app.models.stock import MouvementStock
        mouvement = MouvementStock(
            produit_id=self.id,
            type_mouvement='entree',
            quantite=quantite,
            raison=raison,
            created_by=utilisateur_id,
            tenant_id=self.tenant_id
        )
        mouvement.save()
        return mouvement
    
    def retirer_stock(self, quantite, raison='', utilisateur_id=None):
        """Retire du stock"""
        quantite = Decimal(str(quantite))
        if quantite <= 0:
            raise ValueError("La quantité doit être positive")
        
        if self.quantite_stock < quantite:
            raise ValueError(f"Stock insuffisant. Disponible: {self.quantite_stock}")
        
        self.quantite_stock -= quantite
        self.save()
        
        # Créer un mouvement de stock
        from app.models.stock import MouvementStock
        mouvement = MouvementStock(
            produit_id=self.id,
            type_mouvement='sortie',
            quantite=quantite,
            raison=raison,
            created_by=utilisateur_id,
            tenant_id=self.tenant_id
        )
        mouvement.save()
        return mouvement
    
    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        # Ajouter les propriétés calculées
        data['valeur_stock'] = float(self.valeur_stock)
        data['marge_unitaire'] = float(self.marge_unitaire)
        data['taux_marge'] = float(self.taux_marge)
        data['taux_marque'] = float(self.taux_marque)
        data['est_en_rupture'] = self.est_en_rupture
        data['est_alerte_stock'] = self.est_alerte_stock
        return data
    
    def __repr__(self):
        return f'<Produit {self.reference} - {self.nom}>'
