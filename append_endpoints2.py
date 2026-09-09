"""Append more AI endpoints to ai.py"""
import os

AI_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'backend', 'app', 'api', 'v1', 'ai.py')

src = open(AI_FILE, encoding='utf-8-sig').read()

parts = []

parts.append('''
@ns.route('/analytics/clients')
@ns.doc(responses={200: 'Analyse clients', 403: 'Permission refusee'})
class AnalyticsClientsResource(Resource):
    @permission_required('client.view')
    @tenant_required_readonly
    def get(self):
        try:
            days = request.args.get('days', default=90, type=int)
            result = analyze_clients(days=days)
            return result, 200
        except Exception as e:
            current_app.logger.exception('AI analytics clients error: %s', e)
            return {'message': 'Erreur lors de l analyse des clients'}, 500

@ns.route('/predictions/demand')
@ns.doc(responses={200: 'Prevision de demande', 403: 'Permission refusee'})
class PredictionsDemandResource(Resource):
    @permission_required('report.view')
    @tenant_required_readonly
    def get(self):
        try:
            product_id = request.args.get('product_id', default=None, type=int)
            periods = request.args.get('periods', default=30, type=int)
            result = predict_demand(product_id=product_id, periods=periods)
            return result, 200
        except Exception as e:
            current_app.logger.exception('AI predictions demand error: %s', e)
            return {'message': 'Erreur lors de la prevision de demande'}, 500

''')

src = src.rstrip() + ''.join(parts)

open(AI_FILE, 'w', encoding='utf-8-sig').write(src)
print('OK - clients + predictions added, size:', len(src))
