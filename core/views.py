from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Exchange, TradingPair, Currency
from .redis_manager import redis_manager
import asyncio

def dashboard(request):
    """Main dashboard view"""
    context = {
        'active_exchanges': Exchange.objects.filter(is_active=True).count(),
        'active_pairs': TradingPair.objects.filter(is_active=True).count(),
        'total_currencies': Currency.objects.filter(is_active=True).count(),
    }
    return render(request, 'core/dashboard.html', context)

@staff_member_required
def admin_panel(request):
    """Admin panel for managing exchanges and pairs"""
    exchanges = Exchange.objects.all().order_by('name')
    pairs = TradingPair.objects.select_related(
        'exchange', 'base_currency', 'quote_currency'
    ).order_by('exchange__name', 'base_currency__symbol')
    currencies = Currency.objects.filter(is_active=True).order_by('symbol')
    
    context = {
        'exchanges': exchanges,
        'pairs': pairs,
        'currencies': currencies,
    }
    return render(request, 'core/admin_panel.html', context)

@require_POST
@staff_member_required
def toggle_exchange(request, exchange_id):
    """Toggle exchange active status"""
    try:
        exchange = Exchange.objects.get(id=exchange_id)
        exchange.is_active = not exchange.is_active
        exchange.save()
        
        messages.success(request, f"صرافی {exchange.name} {'فعال' if exchange.is_active else 'غیرفعال'} شد.")
        
        return JsonResponse({
            'success': True,
            'is_active': exchange.is_active
        })
    except Exchange.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'صرافی یافت نشد'})

@require_POST
@staff_member_required
def toggle_pair(request, pair_id):
    """Toggle trading pair active status"""
    try:
        pair = TradingPair.objects.get(id=pair_id)
        pair.is_active = not pair.is_active
        pair.save()
        
        messages.success(request, f"جفت {pair} {'فعال' if pair.is_active else 'غیرفعال'} شد.")
        
        return JsonResponse({
            'success': True,
            'is_active': pair.is_active
        })
    except TradingPair.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'جفت معاملاتی یافت نشد'})

def api_system_health(request):
    """API endpoint for system health check"""
    try:
        # Get basic stats
        stats = {
            'status': 'healthy',
            'exchanges': {
                'total': Exchange.objects.count(),
                'active': Exchange.objects.filter(is_active=True).count()
            },
            'pairs': {
                'total': TradingPair.objects.count(),
                'active': TradingPair.objects.filter(is_active=True).count()
            },
            'currencies': {
                'total': Currency.objects.count(),
                'active': Currency.objects.filter(is_active=True).count()
            }
        }
        
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)

async def api_redis_stats(request):
    """API endpoint for Redis statistics"""
    try:
        await redis_manager.connect()
        
        redis_stats = await redis_manager.get_redis_stats()
        opportunities_count = await redis_manager.get_opportunities_count()
        prices_count = await redis_manager.get_active_prices_count()
        
        stats = {
            'redis': redis_stats,
            'opportunities_count': opportunities_count,
            'prices_count': prices_count
        }
        
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)

def api_market_prices(request):
    """API endpoint for current market prices"""
    async def get_prices():
        try:
            await redis_manager.connect()
            prices = await redis_manager.get_all_current_prices()
            
            # Format prices for API response
            formatted_prices = []
            for key, price_data in prices.items():
                parts = key.split(':')
                if len(parts) >= 3:
                    formatted_prices.append({
                        'exchange': parts[1],
                        'symbol': parts[2],
                        'bid_price': price_data['bid_price'],
                        'ask_price': price_data['ask_price'],
                        'bid_volume': price_data.get('bid_volume', 0),
                        'ask_volume': price_data.get('ask_volume', 0),
                        'timestamp': price_data['timestamp']
                    })
            
            return JsonResponse({
                'count': len(formatted_prices),
                'prices': formatted_prices
            })
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=500)
    
    # Run async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(get_prices())
    finally:
        loop.close()