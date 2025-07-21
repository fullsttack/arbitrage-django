from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Exchange(models.Model):
    name = models.CharField(max_length=50, unique=True)
    base_url = models.URLField()
    is_active = models.BooleanField(default=True)
    websocket_url = models.URLField(null=True, blank=True)
    has_websocket = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Currency(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.symbol} - {self.name}"

class TradingPair(models.Model):
    exchange = models.ForeignKey(Exchange, on_delete=models.CASCADE)
    base_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='base_pairs')
    quote_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='quote_pairs')
    symbol_format = models.CharField(max_length=20)
    pair_id = models.CharField(max_length=20, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    min_volume = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    max_volume = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    arbitrage_threshold = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.5,
        validators=[MinValueValidator(0.1), MaxValueValidator(10.0)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('exchange', 'base_currency', 'quote_currency')

    def __str__(self):
        return f"{self.exchange.name} - {self.base_currency.symbol}/{self.quote_currency.symbol}"