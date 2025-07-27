from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeNumericListFilter
from .models import Exchange, Currency, TradingPair, ConfigurationCategory, Configuration

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
@admin.register(ConfigurationCategory)
class ConfigurationCategoryAdmin(ModelAdmin):
    list_display = ('name', 'display_name', 'is_active', 'order', 'config_count', 'action_links')
    list_filter = ('is_active',)
    search_fields = ('name', 'display_name')
    list_editable = ('is_active', 'order')
    ordering = ('order', 'name')
    
    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'display_name', 'description', 'is_active', 'order'),
            'classes': ('wide',),
        }),
    )
    
    def config_count(self, obj):
        count = obj.configuration_set.count()
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">{} configs</span>',
            count
        )
    config_count.short_description = 'Configurations'
    
    def action_links(self, obj):
        return format_html(
            '<div class="flex space-x-2">'
            '<a href="{}" class="text-blue-600 hover:text-blue-800">Edit</a>'
            '<a href="{}?category__id={}" class="text-green-600 hover:text-green-800">View Configs</a>'
            '</div>',
            reverse('admin:core_configurationcategory_change', args=[obj.pk]),
            reverse('admin:core_configuration_changelist'),
            obj.pk
        )
    action_links.short_description = 'Actions'


@admin.register(Configuration)
class ConfigurationAdmin(ModelAdmin):
    list_display = ('key_display', 'category', 'value_display', 'value_type', 'is_active', 'is_required', 'order', 'action_links')
    list_filter = ('category', 'value_type', 'is_active', 'is_required')
    search_fields = ('key', 'display_name', 'description')
    list_editable = ('is_active', 'order')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('category__order', 'order', 'key')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'key', 'display_name', 'description', 'value_type'),
            'classes': ('wide',),
        }),
        ('Value Settings', {
            'fields': ('string_value', 'integer_value', 'float_value', 'boolean_value', 'json_value'),
            'classes': ('wide',),
            'description': 'Set value based on the selected value type above',
        }),
        ('Configuration Options', {
            'fields': ('default_value', 'is_active', 'is_required', 'order'),
            'classes': ('wide',),
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def key_display(self, obj):
        return format_html(
            '<div class="font-medium text-gray-900">{}</div>'
            '<div class="text-sm text-gray-500">{}</div>',
            obj.key,
            obj.display_name
        )
    key_display.short_description = 'Configuration Key'
    
    def value_display(self, obj):
        value = obj.value
        if obj.value_type == 'json':
            import json
            try:
                formatted_value = json.dumps(value, indent=2)[:100]
                if len(str(value)) > 100:
                    formatted_value += '...'
                return format_html('<pre class="text-xs bg-gray-100 p-1 rounded">{}</pre>', formatted_value)
            except:
                return str(value)[:100]
        elif obj.value_type == 'boolean':
            if value:
                return format_html('<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">✓ True</span>')
            else:
                return format_html('<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">✗ False</span>')
        else:
            str_value = str(value)[:50]
            if len(str(value)) > 50:
                str_value += '...'
            return format_html('<code class="text-sm bg-gray-100 px-1 rounded">{}</code>', str_value)
    value_display.short_description = 'Current Value'
    
    def action_links(self, obj):
        return format_html(
            '<div class="flex space-x-2">'
            '<a href="{}" class="text-blue-600 hover:text-blue-800">Edit</a>'
            '<button onclick="copyToClipboard(\'{}.{}\')" class="text-purple-600 hover:text-purple-800">Copy Key</button>'
            '</div>',
            reverse('admin:core_configuration_change', args=[obj.pk]),
            obj.category.name,
            obj.key
        )
    action_links.short_description = 'Actions'
    
    class Media:
        js = ('admin/js/copy_config_key.js',)
    
    # Custom actions
    def activate_configs(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} configurations have been activated.')
    activate_configs.short_description = "Activate selected configurations"
    
    def deactivate_configs(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} configurations have been deactivated.')
    deactivate_configs.short_description = "Deactivate selected configurations"
    
    actions = ['activate_configs', 'deactivate_configs']


# Customize admin site
admin.site.site_header = 'Digital Currency Arbitrage Admin'
admin.site.site_title = 'Arbitrage'
admin.site.index_title = 'Admin Panel'