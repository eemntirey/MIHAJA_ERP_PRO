from app.models.base import BaseTenantModel
from app import db

class DocumentGenere(BaseTenantModel):
    __tablename__ = 'documents_generes'

    modele_id = db.Column(db.Integer, db.ForeignKey('modeles_documents.id'), nullable=False, index=True)
    type_document = db.Column(db.String(50), nullable=False)
    reference = db.Column(db.String(100), nullable=False, index=True)
    entite_type = db.Column(db.String(50))  # vente/facture/commande/abonnement
    entite_id = db.Column(db.Integer, index=True)
    contenu_html = db.Column(db.Text)
    contenu_pdf_path = db.Column(db.String(500))
    date_generation = db.Column(db.DateTime, default=db.func.now())
    genere_par_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'))

    modele = db.relationship('ModeleDocument', back_populates='documents')

    def to_dict(self, exclude=None):
        data = super().to_dict(exclude)
        if self.modele:
            data['modele_nom'] = self.modele.nom
        return data

    def __repr__(self):
        return f'<DocumentGenere {self.reference}>'
