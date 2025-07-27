import json
import asyncio
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from asgiref.sync import sync_to_async
from .redis import redis_manager
from .models import Exchange, Currency, TradingPair
from .config_manager import get_web_config
from .services.config import get_ramzinex_pair_info, get_ramzinex_display_symbol, get_ramzinex_currency_name

logger = logging.getLogger(__name__)

# Initialize config - can be changed via environment or settings
WEB_CONFIG = get_web_config('default')

class SimpleDashboardView(LoginRequiredMixin, TemplateView):
    """🚀 Simple Dashboard View"""
    template_name = 'index.html'
    login_url = '/admin/login/'
    
    def dispatch(self, request, *args, **kwargs):
        """🔐 Simple authentication check"""
        if not request.user.is_authenticated:
            from django.shortcuts import redirect
            login_url = f"{self.login_url}?next={request.get_full_path()}"
            return redirect(login_url)
        
        # Check permissions based on config
        if WEB_CONFIG['require_superuser'] and not request.user.is_superuser:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Superuser access required")
        
        if WEB_CONFIG['require_staff'] and not request.user.is_staff:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Staff access required")
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """📊 Dashboard context data"""
        context = super().get_context_data(**kwargs)
        
        # Dynamic WebSocket URL
        request = self.request
        ws_scheme = 'wss' if request.is_secure() else 'ws'
        ws_url = f"{ws_scheme}://{request.get_host()}/ws/arbitrage/"
        
        context.update({
            'page_title': 'Dashboard',
            'websocket_url': ws_url,
            'opportunities_limit': WEB_CONFIG.get('opportunities_limit', -1),
            'max_opportunities': WEB_CONFIG.get('max_opportunities', -1),
            'update_intervals': {
                'redis_stats': WEB_CONFIG['redis_stats_interval'],
                'connection_health': WEB_CONFIG['connection_health_interval'],
                'alerts': WEB_CONFIG['alert_monitor_interval']
            }
        })
        
        return context

@csrf_exempt
async def api_current_prices(request):
    """💰 API: Get current prices"""
    if not await check_permissions(request):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        await redis_manager.connect()
        prices = await redis_manager.get_all_prices()
        
        # Format prices for frontend
        formatted_prices = []
        for key, price_data in prices.items():
            parts = key.split(':')
            if len(parts) >= 3:
                exchange = parts[1]
                original_symbol = parts[2]
                
                # Enhanced price data
                price_data['exchange'] = exchange
                price_data['symbol'] = original_symbol
                
                # Add Ramzinex mapping for display only
                if exchange == 'ramzinex':
                    # original_symbol is pair_id (like "13", "432", etc.)
                    pair_info = get_ramzinex_pair_info(original_symbol)
                    if pair_info:
                        price_data['display_symbol'] = get_ramzinex_display_symbol(original_symbol)
                        price_data['currency_name'] = get_ramzinex_currency_name(original_symbol)
                        price_data['base_currency'] = pair_info['base']
                        price_data['quote_currency'] = pair_info['quote']
                    else:
                        price_data['display_symbol'] = original_symbol
                        price_data['currency_name'] = original_symbol
                else:
                    price_data['display_symbol'] = original_symbol
                    price_data['currency_name'] = original_symbol.replace('USDT', '').replace('TMN', '').replace('_', '').replace('-', '')
                
                formatted_prices.append(price_data)
        
        # Limit results for performance
        if len(formatted_prices) > WEB_CONFIG['prices_limit']:
            formatted_prices = formatted_prices[:WEB_CONFIG['prices_limit']]
        
        return JsonResponse({
            'success': True,
            'data': formatted_prices,
            'count': len(formatted_prices),
            'limit': WEB_CONFIG['prices_limit']
        })
        
    except Exception as e:
        logger.error(f"❌ API prices error: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt  
async def api_current_opportunities(request):
    """🎯 API: Get current arbitrage opportunities"""
    if not await check_permissions(request):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        await redis_manager.connect()
        
        # Get opportunities with configured limit
        opportunities = await redis_manager.get_latest_opportunities(
            WEB_CONFIG.get('opportunities_limit', -1)
        )
        
        # Get best opportunity
        best_opportunity = await redis_manager.get_highest_profit_opportunity()
        
        # Get total count
        total_count = await redis_manager.get_opportunities_count()

        return JsonResponse({
            'success': True,
            'data': opportunities,
            'count': len(opportunities),
            'total_count': total_count,
            'best_opportunity': best_opportunity,
            'limit': WEB_CONFIG.get('opportunities_limit', -1)
        })
        
    except Exception as e:
        logger.error(f"❌ API opportunities error: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
async def api_system_stats(request):
    """📊 API: Get system statistics"""
    if not await check_permissions(request):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        await redis_manager.connect()
        
        # Get basic stats
        stats = await redis_manager.get_redis_stats()
        opportunities_count = await redis_manager.get_opportunities_count()
        prices_count = await redis_manager.get_active_prices_count()
        best_opportunity = await redis_manager.get_highest_profit_opportunity()
        
        # Calculate hit rate
        hits = stats.get('keyspace_hits', 0)
        misses = stats.get('keyspace_misses', 0)
        total = hits + misses
        hit_rate = f"{(hits/total)*100:.1f}%" if total > 0 else "N/A"
        
        return JsonResponse({
            'success': True,
            'data': {
                'opportunities_count': opportunities_count,
                'prices_count': prices_count,
                'redis_memory': stats.get('memory_used', 'N/A'),
                'redis_clients': stats.get('connected_clients', 0),
                'redis_ops_per_sec': stats.get('operations_per_sec', 0),
                'redis_uptime': stats.get('uptime_seconds', 0),
                'redis_hit_rate': hit_rate,
                'best_opportunity': best_opportunity,
                'config': {
                    'opportunities_limit': WEB_CONFIG.get('opportunities_limit', -1),
                    'prices_limit': WEB_CONFIG['prices_limit']
                }
            }
        })
        
    except Exception as e:
        logger.error(f"❌ API stats error: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@sync_to_async
def check_permissions(request):
    """🔐 Simple permission check - temporarily disabled for testing"""
    return True  # Temporarily bypass all checks
    
    # if not request.user.is_authenticated:
    #     return False
    # 
    # if WEB_CONFIG['require_superuser'] and not request.user.is_superuser:
    #     return False
    #     
    # if WEB_CONFIG['require_staff'] and not request.user.is_staff:
    #     return False
    # 
    # return True

# Legacy compatibility
def dashboard_view(request):
    """📊 Sync dashboard view for compatibility"""
    view = SimpleDashboardView()
    view.request = request
    return view.get(request)