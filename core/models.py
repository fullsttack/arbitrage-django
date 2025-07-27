from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Exchange(models.Model):
    """Cryptocurrency Exchange"""
    name = models.CharField(max_length=50, unique=True, verbose_name="Exchange Name")
    display_name = models.CharField(max_length=100, verbose_name="Display Name")
    base_url = models.URLField(verbose_name="API Base URL")
    websocket_url = models.URLField(null=True, blank=True, verbose_name="WebSocket URL")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Exchange"
        verbose_name_plural = "Exchanges"
        ordering = ['name']

    def __str__(self):
        return self.display_name

class Currency(models.Model):
    """Cryptocurrency"""
    symbol = models.CharField(max_length=10, unique=True, verbose_name="Symbol")
    name = models.CharField(max_length=100, verbose_name="Full Name")
    display_name = models.CharField(max_length=100, verbose_name="Display Name", blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Currency"
        verbose_name_plural = "Currencies"
        ordering = ['symbol']

    def __str__(self):
        return f"{self.symbol} - {self.display_name or self.name}"

class TradingPair(models.Model):
    """Trading pair in each exchange"""
    exchange = models.ForeignKey(Exchange, on_delete=models.CASCADE, verbose_name="Exchange")
    base_currency = models.ForeignKey(
        Currency, 
        on_delete=models.CASCADE, 
        related_name='base_pairs', 
        verbose_name="Base Currency"
    )
    quote_currency = models.ForeignKey(
        Currency, 
        on_delete=models.CASCADE, 
        related_name='quote_pairs', 
        verbose_name="Quote Currency"
    )
    
    # Exchange-specific settings
    symbol_format = models.CharField(
        max_length=50, 
        verbose_name="Symbol Format",
        help_text="Symbol format in the exchange API (e.g., XRPUSDT for Wallex)"
    )
    pair_id = models.CharField(
        max_length=20, 
        null=True, 
        blank=True, 
        verbose_name="Pair ID",
        help_text="Numeric ID for Ramzinex"
    )
    
    # Arbitrage settings
    is_active = models.BooleanField(default=True, verbose_name="Active")
    arbitrage_threshold = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.5,
        validators=[MinValueValidator(0.1), MaxValueValidator(10.0)],
        verbose_name="Arbitrage Threshold (%)",
        help_text="Minimum profit percentage to identify an opportunity"
    )
    min_volume = models.DecimalField(
        max_digits=20, 
        decimal_places=8, 
        default=100,
        verbose_name="Minimum Volume",
        help_text="Minimum allowed trade volume"
    )
    max_volume = models.DecimalField(
        max_digits=20, 
        decimal_places=8, 
        default=10000,
        verbose_name="Maximum Volume",
        help_text="Maximum allowed trade volume"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('exchange', 'base_currency', 'quote_currency')
        verbose_name = "Trading Pair"
        verbose_name_plural = "Trading Pairs"
        ordering = ['exchange__name', 'base_currency__symbol']

    def __str__(self):
        return f"{self.exchange.name} - {self.base_currency.symbol}/{self.quote_currency.symbol}"
    
    @property
    def api_symbol(self):
        """Symbol used in the API - for WebSocket subscription"""
        if self.exchange.name == 'ramzinex':
            return self.pair_id or '2'  # Default for XRP
        return self.symbol_format
    
    @property
    def arbitrage_symbol(self):
        """Symbol used for arbitrage calculation - consistent with Redis keys"""
        # For Ramzinex, use pair_id; for others, use symbol_format
        if self.exchange.name == 'ramzinex':
            return self.pair_id
        return self.symbol_format
    
    def get_api_url(self):
        """Full API URL for this pair"""
        if self.exchange.name == 'wallex':
            return f"https://api.wallex.ir/v1/depth?symbol={self.symbol_format}"
        elif self.exchange.name == 'lbank':
            return f"https://api.lbkex.com/v2/depth.do?symbol={self.symbol_format}&size=1"
        elif self.exchange.name == 'ramzinex':
            return f"https://publicapi.ramzinex.com/exchange/api/v1.0/exchange/orderbooks/{self.pair_id}/buys_sells"
        return None


class ConfigurationCategory(models.Model):
    """Configuration category for grouping settings"""
    name = models.CharField(max_length=50, unique=True, verbose_name="Category Name")
    display_name = models.CharField(max_length=100, verbose_name="Display Name")
    description = models.TextField(blank=True, verbose_name="Description")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    order = models.PositiveIntegerField(default=0, verbose_name="Display Order")
    
    class Meta:
        verbose_name = "Configuration Category"
        verbose_name_plural = "Configuration Categories"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.display_name


class Configuration(models.Model):
    """Dynamic configuration settings"""
    
    VALUE_TYPES = [
        ('string', 'String'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
    ]
    
    category = models.ForeignKey(
        ConfigurationCategory, 
        on_delete=models.CASCADE, 
        verbose_name="Category"
    )
    key = models.CharField(max_length=100, verbose_name="Configuration Key")
    display_name = models.CharField(max_length=150, verbose_name="Display Name")
    description = models.TextField(blank=True, verbose_name="Description")
    value_type = models.CharField(max_length=20, choices=VALUE_TYPES, verbose_name="Value Type")
    string_value = models.TextField(blank=True, verbose_name="String Value")
    integer_value = models.BigIntegerField(null=True, blank=True, verbose_name="Integer Value")
    float_value = models.FloatField(null=True, blank=True, verbose_name="Float Value")
    boolean_value = models.BooleanField(null=True, blank=True, verbose_name="Boolean Value")
    json_value = models.JSONField(null=True, blank=True, verbose_name="JSON Value")
    default_value = models.TextField(blank=True, verbose_name="Default Value")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    is_required = models.BooleanField(default=False, verbose_name="Required")
    order = models.PositiveIntegerField(default=0, verbose_name="Display Order")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuration"
        verbose_name_plural = "Configurations"
        ordering = ['category__order', 'order', 'key']
        unique_together = ['category', 'key']
    
    def __str__(self):
        return f"{self.category.name}.{self.key}"
    
    @property
    def value(self):
        """Get the actual value based on type"""
        if self.value_type == 'string':
            return self.string_value
        elif self.value_type == 'integer':
            return self.integer_value
        elif self.value_type == 'float':
            return self.float_value
        elif self.value_type == 'boolean':
            return self.boolean_value
        elif self.value_type == 'json':
            return self.json_value
        return None
    
    def set_value(self, value):
        """Set value based on type"""
        # Clear all values first
        self.string_value = ""
        self.integer_value = None
        self.float_value = None
        self.boolean_value = None
        self.json_value = None
        
        if self.value_type == 'string':
            self.string_value = str(value)
        elif self.value_type == 'integer':
            self.integer_value = int(value)
        elif self.value_type == 'float':
            self.float_value = float(value)
        elif self.value_type == 'boolean':
            self.boolean_value = bool(value)
        elif self.value_type == 'json':
            self.json_value = value