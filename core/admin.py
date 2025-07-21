from django.contrib import admin
from .models import Exchange, Currency, TradingPair

@admin.register(Exchange)
class ExchangeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'has_websocket', 'created_at')
    list_filter = ('is_active', 'has_websocket')
    search_fields = ('name',)
    list_editable = ('is_active',)

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('symbol', 'name')
    list_editable = ('is_active',)

@admin.register(TradingPair)
class TradingPairAdmin(admin.ModelAdmin):
    list_display = ('exchange', 'base_currency', 'quote_currency', 'symbol_format', 'is_active', 'arbitrage_threshold')
    list_filter = ('exchange', 'is_active', 'base_currency', 'quote_currency')
    search_fields = ('symbol_format', 'pair_id')
    list_editable = ('is_active', 'arbitrage_threshold')
    readonly_fields = ('created_at',)