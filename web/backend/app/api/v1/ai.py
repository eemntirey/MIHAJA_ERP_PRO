from flask import request, jsonify, current_app
from flask_restx import Namespace, Resource, fields
from app.security.tenant import tenant_required_readonly
from app.security.permissions import permission_required
from app.ai import (
    predict_sales,
    detect_stock_anomalies,
    suggest_reorders,
    ask_assistant,
    train_models,
    external_ai,
    web_search,
    context_manager,
)
from app.ai.anomalies import detect_sales_anomalies, detect_payment_anomalies
from app.ai.recommendations import suggest_pricing_adjustments, suggest_cross_sell
from app.ai.previsions import predict_stock_rupture
from app.ai.ai_insights import generate_insights
from app.ai.ai_analytics import analyze_stock, analyze_sales, analyze_finances, analyze_purchases, analyze_clients
from app.ai.ai_predictions import predict_stock_rupture as predict_rupture_new, predict_sales_trend, predict_demand
from app.ai.ai_tools import (
    get_stock_health, get_low_stock_products, get_customer_debts,
    get_pending_invoices, get_supplier_price_changes, get_top_products,
)


ns = Namespace('ai', description="Module d'Intelligence Artificielle et Prédictions")

# Modèles pour la documentation Swagger
prevision_model = ns.model('Prevision', {
    'tenant_id': fields.Integer(description='ID du tenant'),
    'periods': fields.Integer(description='Nombre de périodes pour la prédiction'),
    'forecast': fields.List(fields.Float, description='Liste des prévisions'),
    'total_predicted': fields.Float(description='Total des ventes prédites'),
    'trend': fields.String(description='Tendance des ventes'),
    'confidence_score': fields.Float(description='Score de confiance')
})

anomaly_model = ns.model('Anomaly', {
    'type': fields.String(description="Type d'anomalie"),
    'severity': fields.String(description='Niveau de sévérité'),
    'count': fields.Integer(description="Nombre d'anomalies")
})

recommendation_model = ns.model('Recommendation', {
    'produit_id': fields.Integer(description='ID du produit'),
    'nom': fields.String(description='Nom du produit'),
    'quantite_suggeree': fields.Integer(description='Quantité suggérée'),
    'priorite': fields.String(description='Niveau de priorité')
})


@ns.route('/previsions')
@ns.doc(responses={200: 'Prévisions récupérées avec succès', 400: 'Requête invalide'})
class PrevisionsResource(Resource):
    @permission_required('report.view')
    @tenant_required_readonly
    def get(self):
        """Obtenir les prévisions de ventes pour une période donnée"""
        try:
            periods = request.args.get('periods', default=30, type=int)
            product_id = request.args.get('product_id', default=None, type=int)

            if periods <= 0 or periods > 365:
                return {'message': 'La période doit être entre 1 et 365 jours'}, 400

            data = predict_sales(periods=periods, product_id=product_id)
            return data, 200
        except Exception as e:
            current_app.logger.exception('AI previsions error: %s', e)
            return {
                'message': 'Erreur lors de la prédiction',
                'error': 'Erreur lors de la prédiction',
            }, 500


@ns.route('/anomalies')
@ns.doc(responses={200: 'Anomalies détectées avec succès', 500: 'Erreur serveur'})
class AnomaliesResource(Resource):
    @permission_required('report.view')
    @tenant_required_readonly
    def get(self):
        """Détecter les anomalies de stock, de ventes et de paiements"""
        try:
            anomaly_type = request.args.get('type', default='all', type=str)

            stock_anomalies = detect_stock_anomalies()
            sales_anomalies = detect_sales_anomalies()
            payment_anomalies = detect_payment_anomalies()

            result = {
                'stock_anomalies': stock_anomalies,
                'sales_anomalies': sales_anomalies,
                'payment_anomalies': payment_anomalies,
                'total_anomalies': stock_anomalies['count'] + sales_anomalies['count'] + payment_anomalies['count']
            }

            if anomaly_type != 'all':
                if anomaly_type == 'stock':
                    return {'stock_anomalies': stock_anomalies}, 200
                elif anomaly_type == 'sales':
                    return {'sales_anomalies': sales_anomalies}, 200
                elif anomaly_type == 'payment':
                    return {'payment_anomalies': payment_anomalies}, 200

            return result, 200
        except Exception as e:
            current_app.logger.exception('AI anomalies error: %s', e)
            return {'message': 'Erreur lors de la détection des anomalies'}, 500


@ns.route('/recommendations')
@ns.doc(responses={200: 'Recommandations récupérées avec succès', 500: 'Erreur serveur'})
class RecommendationsResource(Resource):
    @permission_required('report.view')
    @tenant_required_readonly
    def get(self):
        """Obtenir les recommandations de réapprovisionnement, d'ajustement de prix et de vente croisée"""
        try:
            recom_type = request.args.get('type', default='all', type=str)
            client_id = request.args.get('client_id', default=None, type=int)

            reorders = suggest_reorders()
            pricing = suggest_pricing_adjustments()

            result = {
                'reorder_suggestions': reorders,
                'pricing_suggestions': pricing
            }

            if client_id:
                cross_sell = suggest_cross_sell(client_id=client_id)
                result['cross_sell_suggestions'] = cross_sell

            if recom_type != 'all':
                if recom_type == 'reorder':
                    return {'reorder_suggestions': reorders}, 200
                elif recom_type == 'pricing':
                    return {'pricing_suggestions': pricing}, 200
                elif recom_type == 'cross_sell' and client_id:
                    cross_sell = suggest_cross_sell(client_id=client_id)
                    return {'cross_sell_suggestions': cross_sell}, 200

            return result, 200
        except Exception as e:
            current_app.logger.exception('AI recommendations error: %s', e)
            return {'message': 'Erreur lors de la génération des recommandations'}, 500


@ns.route('/assistant')
@ns.doc(responses={200: 'Réponse de l\'assistant', 400: 'Requête invalide'})
class AssistantResource(Resource):
    @permission_required('report.view')
    @tenant_required_readonly
    def post(self):
        """Interroger l'assistant virtuel ERP avec une question en langage naturel"""
        try:
            body = request.get_json() or {}
            prompt = body.get('prompt', '')
            conversation = body.get('conversation', [])

            if not prompt or not isinstance(prompt, str) or len(prompt.strip()) < 3:
                return {'message': 'Veuillez fournir une question valide (minimum 3 caractères)'}, 400

            response_text = ask_assistant(prompt=prompt, conversation=conversation)
            return {'prompt': prompt, 'response': response_text}, 200
        except Exception as e:
            current_app.logger.exception('AI assistant error: %s', e)
            return {'message': 'Erreur avec l\'assistant'}, 500


@ns.route('/train')
@ns.doc(responses={200: 'Modèles entraînés avec succès', 400: 'Requête invalide', 500: 'Erreur lors de l\'entraînement'})
class TrainResource(Resource):
    @permission_required('report.view')
    @tenant_required_readonly
    def post(self):
        """Entraîner/Réactualiser les modèles IA avec les dernières données"""
        try:
            body = request.get_json() or {}
            force_retrain = body.get('force_retrain', False)
            model_type = body.get('model_type', 'all')

            res = train_models(force_retrain=force_retrain, model_type=model_type)
            return res, 200
        except Exception as e:
            current_app.logger.exception('AI train error: %s', e)
            return {'message': 'Erreur lors de l entrainement des modeles'}, 500


@ns.route('/stock-ruptures')
@ns.doc(responses={200: 'Prédictions de rupture de stock récupérées', 500: 'Erreur serveur'})
class StockRuptureResource(Resource):
    @permission_required('report.view')
    @tenant_required_readonly
    def get(self):
        """Prédire les ruptures de stock pour les produits"""
        try:
            data = predict_stock_rupture()
            return {
                'message': 'Prédictions de rupture de stock',
                'predictions': data.get('predictions', []),
                'count': data.get('count', 0)
            }, 200
        except Exception as e:
            current_app.logger.exception('AI stock rupture error: %s', e)
            return {'message': 'Erreur lors de la prediction des ruptures'}, 500


@ns.route('/health')
@ns.doc(responses={200: 'Statut du module IA'})
class AIHealthResource(Resource):
    @permission_required('report.view')
    @tenant_required_readonly
    def get(self):
        """Vérifier le statut du module IA"""
        try:
            return {
                'status': 'healthy',
                'message': 'Module IA operationnel',
                'external_ai': {
                    'provider': external_ai.provider,
                    'configured': external_ai.is_configured()
                },
                'web_search': {
                    'enabled': web_search.enabled,
                    'configured': bool(web_search.serpapi_key)
                },
                'endpoints': [
                    {'path': '/ai/previsions', 'method': 'GET', 'description': 'Prévisions de ventes'},
                    {'path': '/ai/anomalies', 'method': 'GET', 'description': 'Détection d\'anomalies'},
                    {'path': '/ai/recommendations', 'method': 'GET', 'description': 'Recommandations'},
                    {'path': '/ai/assistant', 'method': 'POST', 'description': 'Assistant IA'},
                    {'path': '/ai/train', 'method': 'POST', 'description': 'Entraînement des modèles'},
                    {'path': '/ai/stock-ruptures', 'method': 'GET', 'description': 'Prédiction des ruptures'},
                    {'path': '/ai/search', 'method': 'POST', 'description': 'Recherche web externe'},
                    {'path': '/ai/context', 'method': 'POST', 'description': 'Mise à jour du contexte conversationnel'}
                ]
            }, 200
        except Exception as e:
            current_app.logger.exception('AI health error: %s', e)
            return {'message': 'Erreur'}, 500


@ns.route('/search')
class AISearchResource(Resource):
    @permission_required('report.view')
    @tenant_required_readonly
    def post(self):
        """Recherche web externe pour enrichir une réponse IA"""
        try:
            body = request.get_json() or {}
            query = body.get('query', '')
            max_results = int(body.get('max_results', 5))

            if not query or not isinstance(query, str) or len(query.strip()) < 2:
                return {'message': 'Requête de recherche invalide'}, 400

            results = web_search.search(query, max_results=max_results)
            return {'query': query, 'results': results}, 200
        except Exception as e:
            current_app.logger.exception('AI search error: %s', e)
            return {'message': 'Erreur lors de la recherche web'}, 500


@ns.route('/context')
class AIContextResource(Resource):
    @permission_required('report.view')
    @tenant_required_readonly
    def post(self):
        """Met à jour le contexte conversationnel de l'assistant"""
        try:
            body = request.get_json() or {}
            conversation = body.get('conversation', [])
            current_prompt = body.get('prompt', '')

            if not isinstance(conversation, list):
                return {'message': 'conversation doit être une liste'}, 400

            messages = context_manager.build_messages(conversation, current_prompt)
            return {'messages': messages}, 200
        except Exception as e:
            current_app.logger.exception('AI context error: %s', e)
            return {'message': 'Erreur lors de la mise à jour du contexte'}, 500

# ============================================================
# NOUVEAUX ENDPOINTS : Insights, Analytics, Predictions
# ============================================================

@ns.route('/insights')
@ns.doc(responses={200: 'Insights generes', 500: 'Erreur serveur'})
class InsightsResource(Resource):
    @permission_required('report.view')
    @tenant_required_readonly
    def get(self):
        try:
            insights = generate_insights()
            return {'insights': insights, 'count': len(insights)}, 200
        except Exception as e:
            current_app.logger.exception('AI insights error: %s', e)
            return {'message': 'Erreur lors de la generation des insights'}, 500

# NOUVEAUX ENDPOINTS
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

@ns.route('/assistant/enhanced')
@ns.doc(responses={200: 'Reponse amelioree', 400: 'Requete invalide'})
class AssistantEnhancedResource(Resource):
    @permission_required('report.view')
    @tenant_required_readonly
    def post(self):
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


@ns.route('/quick/stock-health')
@ns.doc(responses={200: 'Sante du stock', 403: 'Permission refusee'})
class QuickStockHealthResource(Resource):
    @permission_required('stock.view')
    @tenant_required_readonly
    def get(self):
        try:
            result = get_stock_health()
            return result, 200
        except Exception as e:
            current_app.logger.exception('AI quick stock health error: %s', e)
            return {'message': 'Erreur'}, 500


@ns.route('/quick/low-stock')
@ns.doc(responses={200: 'Produits en rupture/alerte', 403: 'Permission refusee'})
class QuickLowStockResource(Resource):
    @permission_required('stock.view')
    @tenant_required_readonly
    def get(self):
        try:
            limit = request.args.get('limit', default=20, type=int)
            result = get_low_stock_products(limit=limit)
            return result, 200
        except Exception as e:
            current_app.logger.exception('AI quick low stock error: %s', e)
            return {'message': 'Erreur'}, 500


@ns.route('/quick/customer-debts')
@ns.doc(responses={200: 'Creances clients', 403: 'Permission refusee'})
class QuickCustomerDebtsResource(Resource):
    @permission_required('invoice.view')
    @tenant_required_readonly
    def get(self):
        try:
            result = get_customer_debts()
            return result, 200
        except Exception as e:
            current_app.logger.exception('AI quick customer debts error: %s', e)
            return {'message': 'Erreur'}, 500


@ns.route('/quick/top-products')
@ns.doc(responses={200: 'Top produits', 403: 'Permission refusee'})
class QuickTopProductsResource(Resource):
    @permission_required('sale.view')
    @tenant_required_readonly
    def get(self):
        try:
            days = request.args.get('days', default=30, type=int)
            limit = request.args.get('limit', default=10, type=int)
            result = get_top_products(days=days, limit=limit)
            return result, 200
        except Exception as e:
            current_app.logger.exception('AI quick top products error: %s', e)
            return {'message': 'Erreur'}, 500


@ns.route('/quick/supplier-price-changes')
@ns.doc(responses={200: 'Variations de prix fournisseurs', 403: 'Permission refusee'})
class QuickSupplierPriceChangesResource(Resource):
    @permission_required('purchase_order.view')
    @tenant_required_readonly
    def get(self):
        try:
            days = request.args.get('days', default=180, type=int)
            result = get_supplier_price_changes(days=days)
            return result, 200
        except Exception as e:
            current_app.logger.exception('AI quick supplier price error: %s', e)
            return {'message': 'Erreur'}, 500


@ns.route('/quick/pending-invoices')
@ns.doc(responses={200: 'Factures en attente', 403: 'Permission refusee'})
class QuickPendingInvoicesResource(Resource):
    @permission_required('invoice.view')
    @tenant_required_readonly
    def get(self):
        try:
            result = get_pending_invoices()
            return result, 200
        except Exception as e:
            current_app.logger.exception('AI quick pending invoices error: %s', e)
            return {'message': 'Erreur'}, 500

