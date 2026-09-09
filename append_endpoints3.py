"""Append remaining AI endpoints to ai.py"""
import os

AI_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'backend', 'app', 'api', 'v1', 'ai.py')

src = open(AI_FILE, encoding='utf-8-sig').read()

markers = [
    "class AssistantContextResource(Resource):",
    "class AssistantContextResource(Resource):\n",
    "class AssistantContextResource(Resource):\n",
    "class AssistantContextResource(Resource)",
]

marker = None
for m in markers:
    if m in src:
        marker = m
        break

if marker is None:
    print("ERROR: could not find AssistantContextResource")
else:
    parts = """

@ns.route('/assistant/enhanced')
@ns.doc(responses={200: 'Reponse amelioree', 400: 'Requete invalide'})
class AssistantEnhancedResource(Resource):
    @permission_required('report.view')
    @tenant_required_readonly
    def post(self):
        \"\"\"Interroger l assistant IA ameliore (insights proactifs + memoire)\"\"\"
        try:
            body = request.get_json() or {}
            prompt = body.get('prompt', '')
            conversation = body.get('conversation', [])
            user_id = body.get('user_id', 'default')

            if not prompt or not isinstance(prompt, str) or len(prompt.strip()) < 3:
                return {'message': 'Veuillez fournir une question valide (minimum 3 caracteres)'}, 400

            from app.ai.assistant import ask_assistant_enhanced
            response_text = ask_assistant_enhanced(
                prompt=prompt,
                conversation=conversation,
                user_id=user_id
            )
            return {'prompt': prompt, 'response': response_text}, 200
        except Exception as e:
            current_app.logger.exception('AI assistant enhanced error: %s', e)
            return {'message': 'Erreur avec l assistant'}, 500


"""
    src = src.replace(marker, marker + parts)
    open(AI_FILE, 'w', encoding='utf-8-sig').write(src)
    print('OK - assistant/enhanced added, size:', len(src))
