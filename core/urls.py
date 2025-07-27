from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Main dashboard
    path('', views.SimpleDashboardView.as_view(), name='dashboard'),
    
    # API endpoints for real-time data
    path('api/prices/', views.api_current_prices, name='api_prices'),
    path('api/opportunities/', views.api_current_opportunities, name='api_opportunities'),
    path('api/stats/', views.api_system_stats, name='api_stats'),
    
    # Backup sync view
    path('dashboard/', views.dashboard_view, name='dashboard_sync'),
]