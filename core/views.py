import json
import asyncio
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from asgiref.sync import sync_to_async
from .redis_manager import redis_manager
from .models import Exchange, Currency, TradingPair

logger = logging.getLogger(__name__)

class DashboardView(TemplateView):
    """Main dashboard view for real-time arbitrage monitoring"""
    template_name = 'index.html'
    
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
    """API endpoint to get current prices"""
    try:
        await redis_manager.connect()
        prices = await redis_manager.get_all_current_prices()
        
        # Get symbol format mapping
        symbol_mapping = await get_symbol_format_mapping()
        
        # Format prices for frontend
        formatted_prices = []
        for key, price_data in prices.items():
            parts = key.split(':', 2)
            if len(parts) >= 3:
                exchange = parts[1]
                symbol = parts[2]
                
                price_data['exchange'] = exchange
                price_data['symbol'] = symbol
                
                # Get symbol_format for display
                symbol_key = f"{exchange}:{symbol}"
                if symbol_key in symbol_mapping:
                    price_data['display_symbol'] = symbol_mapping[symbol_key]
                else:
                    # Fallback to original symbol
                    price_data['display_symbol'] = symbol
                
                formatted_prices.append(price_data)
        
        return JsonResponse({
            'success': True,
            'data': formatted_prices,
            'count': len(formatted_prices)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt  
async def api_current_opportunities(request):
    """API endpoint to get current arbitrage opportunities"""
    try:
        await redis_manager.connect()
        opportunities = await redis_manager.get_latest_opportunities(100)
        
        # Get symbol format mapping  
        symbol_mapping = await get_symbol_format_mapping()
        
        # Add display symbols to opportunities
        for opp in opportunities:
            # Use symbol from opportunity data - format should be "XRP/USDT" or similar
            display_symbol = opp.get('symbol', f"{opp.get('base_currency', '')}/{opp.get('quote_currency', '')}")
            opp['display_symbol'] = display_symbol
        
        return JsonResponse({
            'success': True,
            'data': opportunities,
            'count': len(opportunities)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
async def api_system_stats(request):
    """API endpoint to get system statistics"""
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
def get_symbol_format_mapping():
    """Get mapping of exchange:symbol to symbol_format"""
    try:
        # Get trading pairs for symbol mapping
        trading_pairs = TradingPair.objects.filter(
            is_active=True,
            exchange__is_active=True
        ).select_related('exchange').values(
            'exchange__name',
            'symbol_format', 
            'pair_id'
        )
        
        # Create symbol to symbol_format mapping
        symbol_mapping = {}
        for pair in trading_pairs:
            exchange = pair['exchange__name']
            
            # For ramzinex, use pair_id as both key and display value
            if exchange == 'ramzinex' and pair['pair_id']:
                symbol_key = f"{exchange}:{pair['pair_id']}"
                symbol_mapping[symbol_key] = pair['pair_id']  # Display pair_id
            
            # For other exchanges, use symbol_format
            if pair['symbol_format']:
                symbol_key = f"{exchange}:{pair['symbol_format']}"
                symbol_mapping[symbol_key] = pair['symbol_format']  # Display symbol_format
        
        return symbol_mapping
    except Exception as e:
        logger.error(f"Error getting symbol format mapping: {e}")
        return {}

def extract_base_symbol(symbol_format):
    """Extract base currency symbol from trading pair format"""
    try:
        # Handle different formats: XRPUSDT, xrp_usdt, XRP/USDT
        symbol_upper = symbol_format.upper()
        
        # Skip numeric IDs (Ramzinex pair IDs)
        if symbol_upper.isdigit():
            return symbol_upper  # Return as-is for pair IDs
        
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