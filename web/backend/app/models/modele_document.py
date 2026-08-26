from app.models.base import BaseTenantModel
from app import db

class ModeleDocument(BaseTenantModel):
    __tablename__ = 'modeles_documents'

    nom = db.Column(db.String(100), nullable=False)
    type_document = db.Column(db.String(50), nullable=False)
    contenu_modele = db.Column(db.Text, nullable=False)
    est_actif = db.Column(db.Boolean, default=True)
    est_defaut = db.Column(db.Boolean, default=False)
    logo_url = db.Column(db.String(500))
    mention_legales = db.Column(db.Text)
    conditions_generales = db.Column(db.Text)

    documents = db.relationship('DocumentGenere', back_populates='modele', lazy='dynamic')

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        return data

    def __repr__(self):
        return f'<ModeleDocument {self.nom} - {self.type_document}>'
