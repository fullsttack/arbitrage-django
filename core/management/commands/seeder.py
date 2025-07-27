from django.core.management.base import BaseCommand
from core.models import Exchange, Currency, TradingPair

class Command(BaseCommand):
    help = 'Seed database with initial exchanges, currencies and trading pairs'

    def handle(self, *args, **options):
        self.stdout.write('🌱 Seeding database with initial data...')
        
        # Create Exchanges
        exchanges_data = [
            {
                'name': 'wallex',
                'display_name': 'wallex',
                'base_url': 'https://api.wallex.ir/v1/',
                'websocket_url': 'wss://api.wallex.ir/v1/ws',
                'is_active': True
            },
            {
                'name': 'lbank',
                'display_name': 'lbank',
                'base_url': 'https://api.lbkex.com/v2/',
                'websocket_url': 'wss://www.lbkex.net/ws/V2/',
                'is_active': True
            },
            {
                'name': 'ramzinex',
                'display_name': 'ramzinex',
                'base_url': 'https://publicapi.ramzinex.com/exchange/api/v1.0/',
                'websocket_url': 'wss://websocket.ramzinex.com/websocket',
                'is_active': True
            }
        ]
        
        for exchange_data in exchanges_data:
            exchange, created = Exchange.objects.get_or_create(
                name=exchange_data['name'],
                defaults=exchange_data
            )
            if created:
                self.stdout.write(f'✅ Created exchange: {exchange.display_name}')
            else:
                self.stdout.write(f'⚡ Exchange exists: {exchange.display_name}')
        
        # Create Currencies
        currencies_data = [
            {'symbol': 'XRP', 'name': 'Ripple', 'display_name': 'ریپل'},
            {'symbol': 'DOGE', 'name': 'DOGE', 'display_name': 'دوج'},
            {'symbol': 'NOT', 'name': 'Not', 'display_name': 'نات'},
            {'symbol': 'USDT', 'name': 'Tether', 'display_name': 'تتر'},
        ]
        
        for currency_data in currencies_data:
            currency, created = Currency.objects.get_or_create(
                symbol=currency_data['symbol'],
                defaults=currency_data
            )
            if created:
                self.stdout.write(f'✅ Created currency: {currency.symbol}')
            else:
                self.stdout.write(f'⚡ Currency exists: {currency.symbol}')
        
        # Create Trading Pairs
        trading_pairs_data = []
        exchanges = ['wallex', 'lbank', 'ramzinex']
        base_currencies = ['XRP', 'DOGE', 'NOT']
        quote_currency = 'USDT'
        symbol_formats = {
            'wallex': lambda base: f'{base}USDT',
            'lbank': lambda base: f'{base.lower()}_usdt',
            'ramzinex': lambda base: f'{base}/USDT',
        }
        pair_ids = { 
            'ramzinex': {'XRP': '643', 'DOGE': '432', 'NOT': '509'}
        }
        for exchange in exchanges:
            for base in base_currencies:
                trading_pairs_data.append({
                    'exchange': exchange,
                    'base_currency': base,
                    'quote_currency': quote_currency,
                    'symbol_format': symbol_formats[exchange](base),
                    'pair_id': pair_ids.get(exchange, {}).get(base, None),
                    'arbitrage_threshold': 0.3,
                    'min_volume': 100,
                    'max_volume': 1000000000
                })

        for pair_data in trading_pairs_data:
            try:
                exchange = Exchange.objects.get(name=pair_data['exchange'])
                base_currency = Currency.objects.get(symbol=pair_data['base_currency'])
                quote_currency = Currency.objects.get(symbol=pair_data['quote_currency'])
                
                pair, created = TradingPair.objects.get_or_create(
                    exchange=exchange,
                    base_currency=base_currency,
                    quote_currency=quote_currency,
                    defaults={
                        'symbol_format': pair_data['symbol_format'],
                        'pair_id': pair_data['pair_id'],
                        'arbitrage_threshold': pair_data['arbitrage_threshold'],
                        'min_volume': pair_data['min_volume'],
                        'max_volume': pair_data['max_volume']
                    }
                )
                
                if created:
                    self.stdout.write(f'✅ Created trading pair: {pair}')
                else:
                    self.stdout.write(f'⚡ Trading pair exists: {pair}')
                    
            except Exception as e:
                self.stdout.write(f'❌ Error creating trading pair: {e}')
        
        self.stdout.write(self.style.SUCCESS('🎉 Database seeded successfully!'))
        self.stdout.write('')
        self.stdout.write('📊 Summary:')
        self.stdout.write(f'   Exchanges: {Exchange.objects.count()}')
        self.stdout.write(f'   Currencies: {Currency.objects.count()}')
        self.stdout.write(f'   Trading Pairs: {TradingPair.objects.count()}')
        self.stdout.write('')
        self.stdout.write('🚀 Run "python manage.py runserver" and "python manage.py start_workers" to start the system')