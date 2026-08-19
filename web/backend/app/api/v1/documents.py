from flask_restx import Namespace, Resource
from flask import send_file, abort
from app.security.tenant import tenant_required, get_current_tenant
from app.services.document_service import ModeleDocumentService, DocumentGenereService
from app.utils.pdf_generator import generate_document_pdf
from app.utils.qr_generator import generate_qr_code
from app import db
from datetime import datetime
import os

ns_modeles = Namespace('modeles-documents', description='Gestion des modeles de documents')
ns_documents = Namespace('documents', description='Gestion des documents generes')

@ns_modeles.route('/')
class ModeleList(Resource):
    @tenant_required
    def get(self):
        modeles, total = ModeleDocumentService.get_all()
        return {'modeles': [m.to_dict() for m in modeles], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        modele = ModeleDocumentService.create(data)
        return modele.to_dict(), 201

@ns_modeles.route('/<int:id>')
class ModeleResource(Resource):
    @tenant_required
    def get(self, id):
        modele = ModeleDocumentService.get_by_id(id)
        if not modele:
            return {'message': 'Modele non trouve'}, 404
        return modele.to_dict(), 200

    @tenant_required
    def put(self, id):
        from flask import request
        data = request.get_json()
        modele = ModeleDocumentService.update(id, data)
        if not modele:
            return {'message': 'Modele non trouve'}, 404
        return modele.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = ModeleDocumentService.delete(id)
        if not success:
            return {'message': 'Modele non trouve'}, 404
        return {'message': 'Modele supprime'}, 200

@ns_documents.route('/')
class DocumentList(Resource):
    @tenant_required
    def get(self):
        documents, total = DocumentGenereService.get_all()
        return {'documents': [d.to_dict() for d in documents], 'total': total}, 200

    @tenant_required
    def post(self):
        from flask import request
        data = request.get_json()
        document = DocumentGenereService.create(data)
        return document.to_dict(), 201

@ns_documents.route('/<int:id>')
class DocumentResource(Resource):
    @tenant_required
    def get(self, id):
        document = DocumentGenereService.get_by_id(id)
        if not document:
            return {'message': 'Document non trouve'}, 404
        return document.to_dict(), 200

    @tenant_required
    def delete(self, id):
        success = DocumentGenereService.delete(id)
        if not success:
            return {'message': 'Document non trouve'}, 404
        return {'message': 'Document supprime'}, 200

@ns_documents.route('/<int:id>/pdf')
class DocumentPdfResource(Resource):
    @tenant_required
    def get(self, id):
        document = DocumentGenereService.get_by_id(id)
        if not document or not document.contenu_pdf_path:
            return {'message': 'PDF non trouve'}, 404
        if not os.path.exists(document.contenu_pdf_path):
            return {'message': 'Fichier PDF introuvable sur le serveur'}, 404
        return send_file(
            document.contenu_pdf_path,
            mimetype='application/pdf',
            as_attachment=False,
            download_name=os.path.basename(document.contenu_pdf_path)
        )

@ns_documents.route('/generer')
class GenererDocument(Resource):
    @tenant_required
    def post(self):
        from flask import request
        from app.models.tenant import Tenant
        data = request.get_json()
        modele_id = data.get('modele_id')
        type_document = data.get('type_document')
        reference = data.get('reference')
        entite_type = data.get('entite_type')
        entite_id = data.get('entite_id')
        donnees = data.get('donnees', {}) or {}

        modele = ModeleDocumentService.get_by_id(modele_id)
        if not modele:
            modele = ModeleDocumentService.get_defaut_by_type(type_document)
        if not modele:
            return {'message': 'Modele non trouve'}, 404

        html_content = modele.contenu_modele
        for key, value in donnees.items():
            html_content = html_content.replace('{{' + key + '}}', str(value) if value is not None else '')

        tenant = None
        current_tenant = get_current_tenant()
        if current_tenant:
            tenant = current_tenant.to_dict()
        else:
            tenant_user = None
            from flask_jwt_extended import get_jwt
            claims = get_jwt() or {}
            tenant_id = claims.get('tenant_id')
            if tenant_id:
                tenant_obj = db.session.get(Tenant, tenant_id)
                if tenant_obj:
                    tenant = tenant_obj.to_dict()

        modele_dict = modele.to_dict()
        modele_dict.pop('tenant_id', None)

        filename = f"{type_document}_{reference}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        pdf_path = generate_document_pdf(
            filename=filename,
            type_document=type_document,
            reference=reference,
            donnees=donnees,
            tenant=tenant,
            modele=modele_dict,
        )

        document = DocumentGenereService.create({
            'modele_id': modele.id,
            'type_document': type_document,
            'reference': reference,
            'entite_type': entite_type,
            'entite_id': entite_id,
            'contenu_html': html_content,
            'contenu_pdf_path': pdf_path,
        })
        result = document.to_dict()
        result['pdf_url'] = f"/api/v1/documents/{document.id}/pdf"
        return result, 201
