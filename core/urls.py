from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Main pages
    path('', views.dashboard, name='dashboard'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    
    # AJAX endpoints
    path('toggle-exchange/<int:exchange_id>/', views.toggle_exchange, name='toggle_exchange'),
    path('toggle-pair/<int:pair_id>/', views.toggle_pair, name='toggle_pair'),
    
    # API endpoints
    path('api/system/health/', views.api_system_health, name='api_system_health'),
    path('api/redis/stats/', views.api_redis_stats, name='api_redis_stats'),
    path('api/market-prices/', views.api_market_prices, name='api_market_prices'),
]