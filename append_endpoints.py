"""Append new AI endpoints to ai.py"""
import os

AI_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'backend', 'app', 'api', 'v1', 'ai.py')

src = open(AI_FILE, encoding='utf-8-sig').read()

parts = []

parts.append('''
@ns.route('/analytics/finances')
@ns.doc(responses={200: 'Analyse finances', 403: 'Permission refusee'})
class AnalyticsFinancesResource(Resource):
    @permission_required('invoice.view')
    @tenant_required_readonly
    def get(self):
        try:
            result = analyze_finances()
            return result, 200
        except Exception as e:
            current_app.logger.exception('AI analytics finances error: %s', e)
            return {'message': 'Erreur lors de l analyse financiere'}, 500

''')

parts.append('''
@ns.route('/analytics/purchases')
@ns.doc(responses={200: 'Analyse achats', 403: 'Permission refusee'})
class AnalyticsPurchasesResource(Resource):
    @permission_required('purchase_order.view')
    @tenant_required_readonly
    def get(self):
        try:
            days = request.args.get('days', default=180, type=int)
            result = analyze_purchases(days=days)
            return result, 200
        except Exception as e:
            current_app.logger.exception('AI analytics purchases error: %s', e)
            return {'message': 'Erreur lors de l analyse des achats'}, 500

''')

src = src.rstrip() + ''.join(parts)

open(AI_FILE, 'w', encoding='utf-8-sig').write(src)
print('OK - finances + purchases added, size:', len(src))
