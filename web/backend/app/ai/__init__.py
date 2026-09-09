from .previsions import predict_sales, predict_stock_rupture
from .anomalies import detect_stock_anomalies, detect_sales_anomalies, detect_payment_anomalies
from .recommendations import suggest_reorders, suggest_cross_sell, suggest_pricing_adjustments
from .assistant import ask_assistant
from .training import train_models
from .external_services import external_ai, web_search, context_manager
from .ai_permissions import (
    AIPermissionError,
    can_access_domain,
    require_domain_access,
    get_accessible_domains,
    get_ai_user_context,
)
from .ai_tools import (
    get_sales_summary,
    get_sales_evolution,
    get_top_products,
    get_product_sales_history,
    get_low_stock_products,
    get_stock_health,
    get_stock_turnover,
    get_customer_debts,
    get_pending_invoices,
    get_supplier_price_changes,
    get_pending_purchase_orders,
    get_clients_summary,
    get_suppliers_summary,
    get_products_dormant,
)
from .ai_analytics import (
    analyze_stock,
    analyze_sales,
    analyze_finances,
    analyze_purchases,
    analyze_clients,
)
from .ai_insights import generate_insights
from .ai_predictions import predict_stock_rupture as predict_rupture, predict_sales_trend, predict_demand
from .ai_prompts import build_system_prompt, build_context_block

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
    'AIPermissionError',
    'can_access_domain',
    'require_domain_access',
    'get_accessible_domains',
    'get_ai_user_context',
    'get_sales_summary',
    'get_sales_evolution',
    'get_top_products',
    'get_product_sales_history',
    'get_low_stock_products',
    'get_stock_health',
    'get_stock_turnover',
    'get_customer_debts',
    'get_pending_invoices',
    'get_supplier_price_changes',
    'get_pending_purchase_orders',
    'get_clients_summary',
    'get_suppliers_summary',
    'get_products_dormant',
    'analyze_stock',
    'analyze_sales',
    'analyze_finances',
    'analyze_purchases',
    'analyze_clients',
    'generate_insights',
    'predict_rupture',
    'predict_sales_trend',
    'predict_demand',
    'build_system_prompt',
    'build_context_block',
]
