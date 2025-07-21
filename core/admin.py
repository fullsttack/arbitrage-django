from django.contrib import admin
from django.utils.html import format_html
from .models import Exchange, Currency, TradingPair

@admin.register(Exchange)
class ExchangeAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'is_active', 'websocket_status', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'display_name')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('General Information', {
            'fields': ('name', 'display_name', 'is_active')
        }),
        ('API Settings', {
            'fields': ('base_url', 'websocket_url')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    is_active_badge.short_description = 'Status'
    
    def websocket_status(self, obj):
        if obj.websocket_url:
            return format_html('<span style="color: green;">✓ Available</span>')
        return format_html('<span style="color: orange;">Not Available</span>')
    websocket_status.short_description = 'WebSocket'

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name', 'display_name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('symbol', 'name', 'display_name')
    list_editable = ('is_active',)
    readonly_fields = ('created_at',)
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    is_active_badge.short_description = 'Status'

@admin.register(TradingPair)
class TradingPairAdmin(admin.ModelAdmin):
    list_display = (
        'pair_name', 'exchange', 'symbol_format', 'pair_id', 
        'is_active', 'arbitrage_threshold', 'volume_range'
    )
    list_filter = ('exchange', 'is_active', 'base_currency', 'quote_currency')
    search_fields = ('symbol_format', 'pair_id', 'base_currency__symbol', 'quote_currency__symbol')
    list_editable = ('is_active', 'arbitrage_threshold')
    readonly_fields = ('created_at', 'updated_at', 'api_url_display')
    
    fieldsets = (
        ('General Information', {
            'fields': ('exchange', 'base_currency', 'quote_currency', 'is_active')
        }),
        ('Exchange Settings', {
            'fields': ('symbol_format', 'pair_id')
        }),
        ('Arbitrage Settings', {
            'fields': ('arbitrage_threshold', 'min_volume', 'max_volume')
        }),
        ('System Information', {
            'fields': ('api_url_display', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def pair_name(self, obj):
        return f"{obj.base_currency.symbol}/{obj.quote_currency.symbol}"
    pair_name.short_description = 'Pair'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    is_active_badge.short_description = 'Status'
    
    def volume_range(self, obj):
        return f"{obj.min_volume} - {obj.max_volume}"
    volume_range.short_description = 'Volume Range'
    
    def api_url_display(self, obj):
        url = obj.get_api_url()
        if url:
            return format_html('<a href="{}" target="_blank">{}</a>', url, url)
        return 'Not Defined'
    api_url_display.short_description = 'API URL'

# Customize admin site
admin.site.site_header = 'Digital Currency Arbitrage Admin'
admin.site.site_title = 'Arbitrage'
admin.site.index_title = 'Admin Panel'