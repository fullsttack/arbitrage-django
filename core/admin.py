from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeNumericListFilter
from .models import Exchange, Currency, TradingPair

@admin.register(Exchange)
class ExchangeAdmin(ModelAdmin):
    list_display = ('name', 'display_name', 'is_active', 'is_active_badge', 'websocket_status', 'created_at', 'action_links')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'display_name')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('General Information', {
            'fields': ('name', 'display_name', 'is_active'),
            'classes': ('wide',),
        }),
        ('API Settings', {
            'fields': ('base_url', 'websocket_url'),
            'classes': ('wide',),
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">✓ Active</span>')
        return format_html('<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">✗ Inactive</span>')
    is_active_badge.short_description = 'Status'
    
    def websocket_status(self, obj):
        if obj.websocket_url:
            return format_html('<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">✓ Available</span>')
        return format_html('<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">Not Available</span>')
    websocket_status.short_description = 'WebSocket'
    
    def action_links(self, obj):
        return format_html(
            '<div class="flex space-x-2">'
            '<a href="{}" class="text-blue-600 hover:text-blue-800">Edit</a>'
            '<a href="{}" class="text-green-600 hover:text-green-800">View</a>'
            '</div>',
            reverse('admin:core_exchange_change', args=[obj.pk]),
            reverse('admin:core_exchange_change', args=[obj.pk])
        )
    action_links.short_description = 'Actions'

@admin.register(Currency)
class CurrencyAdmin(ModelAdmin):
    list_display = ('symbol', 'name', 'display_name', 'is_active', 'is_active_badge', 'created_at', 'action_links')
    list_filter = ('is_active', 'created_at')
    search_fields = ('symbol', 'name', 'display_name')
    list_editable = ('is_active',)
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Currency Information', {
            'fields': ('symbol', 'name', 'display_name', 'is_active'),
            'classes': ('wide',),
        }),
        ('System Information', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">✓ Active</span>')
        return format_html('<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">✗ Inactive</span>')
    is_active_badge.short_description = 'Status'
    
    def action_links(self, obj):
        return format_html(
            '<div class="flex space-x-2">'
            '<a href="{}" class="text-blue-600 hover:text-blue-800">Edit</a>'
            '<a href="{}" class="text-green-600 hover:text-green-800">View</a>'
            '</div>',
            reverse('admin:core_currency_change', args=[obj.pk]),
            reverse('admin:core_currency_change', args=[obj.pk])
        )
    action_links.short_description = 'Actions'

@admin.register(TradingPair)
class TradingPairAdmin(ModelAdmin):
    list_display = (
        'pair_name', 'exchange', 'symbol_format', 'pair_id', 
        'is_active', 'is_active_badge', 'arbitrage_threshold', 'volume_range', 'action_links'
    )
    list_filter = (
        'exchange', 
        'is_active', 
        'base_currency', 
        'quote_currency',
    )
    search_fields = ('symbol_format', 'pair_id', 'base_currency__symbol', 'quote_currency__symbol')
    list_editable = ('is_active', 'arbitrage_threshold')
    readonly_fields = ('created_at', 'updated_at', 'api_url_display')
    
    fieldsets = (
        ('General Information', {
            'fields': ('exchange', 'base_currency', 'quote_currency', 'is_active'),
            'classes': ('wide',),
        }),
        ('Exchange Settings', {
            'fields': ('symbol_format', 'pair_id'),
            'classes': ('wide',),
        }),
        ('Arbitrage Settings', {
            'fields': ('arbitrage_threshold', 'min_volume', 'max_volume'),
            'classes': ('wide',),
            'description': 'Configure arbitrage parameters for this trading pair',
        }),
        ('System Information', {
            'fields': ('api_url_display', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def pair_name(self, obj):
        return format_html(
            '<div class="font-medium">{}/{}</div>',
            obj.base_currency.symbol,
            obj.quote_currency.symbol
        )
    pair_name.short_description = 'Pair'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">✓ Active</span>')
        return format_html('<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">✗ Inactive</span>')
    is_active_badge.short_description = 'Status'
    
    def volume_range(self, obj):
        return format_html(
            '<div class="text-sm text-gray-600">{} - {}</div>',
            obj.min_volume,
            obj.max_volume
        )
    volume_range.short_description = 'Volume Range'
    
    def api_url_display(self, obj):
        url = obj.get_api_url()
        if url:
            return format_html(
                '<a href="{}" target="_blank" class="text-blue-600 hover:text-blue-800 break-all">{}</a>',
                url, url
            )
        return format_html('<span class="text-gray-500">Not Defined</span>')
    api_url_display.short_description = 'API URL'
    
    def action_links(self, obj):
        return format_html(
            '<div class="flex space-x-2">'
            '<a href="{}" class="text-blue-600 hover:text-blue-800">Edit</a>'
            '<a href="{}" class="text-green-600 hover:text-green-800">View</a>'
            '</div>',
            reverse('admin:core_tradingpair_change', args=[obj.pk]),
            reverse('admin:core_tradingpair_change', args=[obj.pk])
        )
    action_links.short_description = 'Actions'
    
    # Custom admin actions
    def activate_pairs(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} trading pairs have been activated.')
    activate_pairs.short_description = "Activate selected trading pairs"
    
    def deactivate_pairs(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} trading pairs have been deactivated.')
    deactivate_pairs.short_description = "Deactivate selected trading pairs"
    
    def reset_thresholds(self, request, queryset):
        updated = queryset.update(arbitrage_threshold=0.5)
        self.message_user(request, f'{updated} trading pairs have had their thresholds reset to 0.5%.')
    reset_thresholds.short_description = "Reset arbitrage thresholds to default"

# Customize admin site
admin.site.site_header = 'Digital Currency Arbitrage Admin'
admin.site.site_title = 'Arbitrage'
admin.site.index_title = 'Admin Panel'