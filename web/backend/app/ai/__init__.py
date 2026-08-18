from .previsions import predict_sales, predict_stock_rupture
from .anomalies import detect_stock_anomalies, detect_sales_anomalies, detect_payment_anomalies
from .recommendations import suggest_reorders, suggest_cross_sell, suggest_pricing_adjustments
from .assistant import ask_assistant
from .training import train_models
from .external_services import external_ai, web_search, context_manager

__all__ = [
    'predict_sales',
    'predict_stock_rupture',
    'detect_stock_anomalies',
    'detect_sales_anomalies',
    'detect_payment_anomalies',
    'suggest_reorders',
    'suggest_cross_sell',
    'suggest_pricing_adjustments',
    'ask_assistant',
    'train_models',
    'external_ai',
    'web_search',
    'context_manager',
]
