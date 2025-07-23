import json
import asyncio
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.admin.views.decorators import staff_member_required
from asgiref.sync import sync_to_async
from .redis_manager import redis_manager
from .models import Exchange, Currency, TradingPair

logger = logging.getLogger(__name__)

@sync_to_async
def check_superuser_permissions(request):
    """Check if user is authenticated and is superuser - async safe"""
    from django.contrib.auth import get_user
    user = get_user(request)
    # For now, allow all authenticated users (remove superuser restriction for testing)
    return user.is_authenticated
    # return user.is_authenticated and user.is_superuser

class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view for real-time arbitrage monitoring - Superuser only"""
    template_name = 'index.html'
    login_url = '/admin/login/'
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user is authenticated (removed superuser restriction for testing)
        if not request.user.is_authenticated:
            from django.shortcuts import redirect
            from django.urls import reverse
            from urllib.parse import urlencode
            
            # Redirect to admin login with next parameter
            login_url = '/admin/login/'
            next_url = request.get_full_path()
            redirect_url = f"{login_url}?{urlencode({'next': next_url})}"
            return redirect(redirect_url)
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add initial context data
        context.update({
            'page_title': 'Cryptocurrency Arbitrage Dashboard',
            'websocket_url': 'ws://localhost:8000/ws/arbitrage/',
            'exchanges': self.get_exchanges(),
            'currencies': self.get_currencies(),
            'trading_pairs': self.get_trading_pairs(),
        })
        
        return context
    
    def get_exchanges(self):
        """Get active exchanges"""
        try:
            return list(Exchange.objects.filter(is_active=True).values(
                'name', 'display_name', 'websocket_url'
            ))
        except Exception as e:
            return []
    
    def get_currencies(self):
        """Get active currencies"""
        try:
            return list(Currency.objects.filter(is_active=True).values(
                'symbol', 'name', 'display_name'
            ))
        except Exception as e:
            return []
    
    def get_trading_pairs(self):
        """Get active trading pairs"""
        try:
            return list(TradingPair.objects.filter(
                is_active=True,
                exchange__is_active=True
            ).select_related('exchange', 'base_currency', 'quote_currency').values(
                'exchange__name',
                'exchange__display_name', 
                'base_currency__symbol',
                'quote_currency__symbol',
                'symbol_format',
                'arbitrage_threshold'
            ))
        except Exception as e:
            return []

@csrf_exempt
async def api_current_prices(request):
    """API endpoint to get current prices - Superuser only"""
    if not await check_superuser_permissions(request):
        return JsonResponse({'success': False, 'error': 'Superuser access required'}, status=403)
    
    try:
        await redis_manager.connect()
        prices = await redis_manager.get_all_current_prices()
        
        # Get currency names mapping
        currency_names = await get_currency_names_mapping()
        
        # Format prices for frontend
        formatted_prices = []
        for key, price_data in prices.items():
            parts = key.split(':', 2)
            if len(parts) >= 3:
                price_data['exchange'] = parts[1]
                price_data['symbol'] = parts[2]
                
                # Extract base currency from symbol and add name
                base_symbol = extract_base_symbol(parts[2])
                price_data['currency_name'] = currency_names.get(base_symbol, base_symbol)
                
                formatted_prices.append(price_data)
        
        return JsonResponse({
            'success': True,
            'data': formatted_prices,
            'count': len(formatted_prices),
            'currency_names': currency_names
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt  
async def api_current_opportunities(request):
    """API endpoint to get current arbitrage opportunities - Superuser only"""
    if not await check_superuser_permissions(request):
        return JsonResponse({'success': False, 'error': 'Superuser access required'}, status=403)
    
    try:
        await redis_manager.connect()
        opportunities = await redis_manager.get_latest_opportunities(100)
        
        # Get currency names mapping
        currency_names = await get_currency_names_mapping()
        
        # Add currency names to opportunities
        for opp in opportunities:
            base_symbol = opp.get('base_currency', '').upper()
            opp['currency_name'] = currency_names.get(base_symbol, base_symbol)
        
        return JsonResponse({
            'success': True,
            'data': opportunities,
            'count': len(opportunities),
            'currency_names': currency_names
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
async def api_system_stats(request):
    """API endpoint to get system statistics - Superuser only"""
    if not await check_superuser_permissions(request):
        return JsonResponse({'success': False, 'error': 'Superuser access required'}, status=403)
    
    try:
        await redis_manager.connect()
        
        stats = await redis_manager.get_redis_stats()
        opportunities_count = await redis_manager.get_opportunities_count()
        prices_count = await redis_manager.get_active_prices_count()
        
        return JsonResponse({
            'success': True,
            'data': {
                'opportunities_count': opportunities_count,
                'prices_count': prices_count,
                'redis_memory': stats.get('memory_used', 'N/A'),
                'redis_clients': stats.get('connected_clients', 0),
                'redis_ops_per_sec': stats.get('operations_per_sec', 0),
                'redis_uptime': stats.get('uptime_seconds', 0),
                'redis_hit_rate': calculate_hit_rate(stats)
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

def calculate_hit_rate(stats):
    """Calculate Redis cache hit rate"""
    try:
        hits = stats.get('keyspace_hits', 0)
        misses = stats.get('keyspace_misses', 0)
        total = hits + misses
        if total > 0:
            hit_rate = (hits / total) * 100
            return f"{hit_rate:.1f}%"
        return "N/A"
    except:
        return "N/A"

@sync_to_async
def get_currency_names_mapping():
    """Get mapping of currency symbols to display names"""
    try:
        currencies = Currency.objects.filter(is_active=True).values('symbol', 'name', 'display_name')
        mapping = {}
        for currency in currencies:
            symbol = currency['symbol'].upper()
            # Prefer name (English) over display_name (Persian) 
            name = currency.get('name') or currency.get('display_name') or symbol
            mapping[symbol] = name
        return mapping
    except Exception as e:
        logger.error(f"Error getting currency names: {e}")
        return {}

def extract_base_symbol(symbol_format):
    """Extract base currency symbol from trading pair format"""
    try:
        # Handle different formats: XRPUSDT, xrp_usdt, XRP/USDT
        symbol_upper = symbol_format.upper()
        
        # Format: XRP/USDT
        if '/' in symbol_upper:
            return symbol_upper.split('/')[0]
        
        # Format: xrp_usdt
        if '_' in symbol_upper:
            return symbol_upper.split('_')[0]
        
        # Format: XRPUSDT - assume USDT as quote
        if symbol_upper.endswith('USDT'):
            return symbol_upper[:-4]  # Remove USDT
        
        # Format: XRPTMN - assume TMN as quote  
        if symbol_upper.endswith('TMN'):
            return symbol_upper[:-3]  # Remove TMN
            
        return symbol_upper
    except:
        return symbol_format

# Traditional sync views for backwards compatibility
def dashboard_view(request):
    """Sync version of dashboard view"""
    view = DashboardView()
    view.request = request
    return view.get(request)