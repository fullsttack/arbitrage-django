from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from .models import Exchange, TradingPair, Currency

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
    
    context = {
        'exchanges': exchanges,
        'pairs': pairs,
    }
    return render(request, 'core/admin_panel.html', context)