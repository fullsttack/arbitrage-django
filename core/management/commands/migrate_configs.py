# 🚀 Migration Command for Configuration Settings
# Migrate hardcoded configs to database

from django.core.management.base import BaseCommand
from core.models import ConfigurationCategory, Configuration
# Fallback web config for migration
WEB_CONFIGS = {
    'default': {
        'redis_stats_interval': 10,
        'connection_health_interval': 15,
        'alert_monitor_interval': 20,
        'api_timeout': 30,
        'cache_timeout': 60,
        'require_superuser': False,
        'require_staff': False,
        'session_timeout': 3600,
        'batch_size': 50,
        'max_concurrent': 10,
        'prices_limit': 500,
        'opportunities_limit': -1,
        'max_opportunities': -1,
    }
}

# Inline import of configs with fallbacks
import json

class Command(BaseCommand):
    help = 'Migrate hardcoded configuration to database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force overwrite existing configurations',
        )
        parser.add_argument(
            '--profile',
            type=str,
            default='default',
            help='Configuration profile to migrate (default: default)',
        )
    
    def handle(self, *args, **options):
        force = options['force']
        profile = options['profile']
        
        self.stdout.write(
            self.style.SUCCESS(f'🚀 Starting configuration migration for profile: {profile}')
        )
        
        # Migrate configurations
        self.migrate_web_config(profile, force)
        self.migrate_redis_config(profile, force)
        self.migrate_worker_config(profile, force)
        self.migrate_arbitrage_config(profile, force)
        
        self.stdout.write(
            self.style.SUCCESS('✅ Configuration migration completed!')
        )
    
    def migrate_web_config(self, profile, force):
        """Migrate web configuration"""
        category, created = ConfigurationCategory.objects.get_or_create(
            name='web',
            defaults={
                'display_name': 'Web Interface Settings',
                'description': 'Configuration for web dashboard and API',
                'order': 1
            }
        )
        
        if created:
            self.stdout.write(f'📁 Created category: {category.display_name}')
        
        web_config = WEB_CONFIGS.get(profile, WEB_CONFIGS['default'])
        
        configs = [
            ('redis_stats_interval', 'Redis Stats Interval', 'integer', 'Interval for Redis statistics updates (seconds)'),
            ('connection_health_interval', 'Connection Health Interval', 'integer', 'Interval for connection health checks (seconds)'),
            ('alert_monitor_interval', 'Alert Monitor Interval', 'integer', 'Interval for alert monitoring (seconds)'),
            ('api_timeout', 'API Timeout', 'integer', 'API request timeout (seconds)'),
            ('cache_timeout', 'Cache Timeout', 'integer', 'Static data cache timeout (seconds)'),
            ('require_superuser', 'Require Superuser', 'boolean', 'Require superuser for WebSocket access'),
            ('require_staff', 'Require Staff', 'boolean', 'Require staff status for WebSocket access'),
            ('session_timeout', 'Session Timeout', 'integer', 'Session timeout (seconds)'),
            ('batch_size', 'Batch Size', 'integer', 'Database batch processing size'),
            ('max_concurrent', 'Max Concurrent', 'integer', 'Maximum concurrent operations'),
            ('prices_limit', 'Prices Limit', 'integer', 'Price updates limit'),
            ('opportunities_limit', 'Opportunities Limit', 'integer', 'Opportunities to show (-1 for all)'),
            ('max_opportunities', 'Max Opportunities', 'integer', 'Maximum opportunities to fetch (-1 for all)'),
        ]
        
        self._create_configs(category, configs, web_config, force)
    
    def migrate_redis_config(self, profile, force):
        """Migrate Redis configuration"""
        category, created = ConfigurationCategory.objects.get_or_create(
            name='redis',
            defaults={
                'display_name': 'Redis Settings',
                'description': 'Configuration for Redis storage and caching',
                'order': 2
            }
        )
        
        if created:
            self.stdout.write(f'📁 Created category: {category.display_name}')
        
        # Use fallback Redis config
        redis_config = {
            'heartbeat_ttl': 90,
            'offline_threshold': 120,
            'price_ttl': 1800,
            'cleanup_interval': 300,
            'old_price_threshold': 7200,
            'old_opportunity_threshold': 2592000,
            'max_opportunities': 100000,
            'batch_size': 1000,
            'pipeline_size': 100,
        }
        
        configs = [
            ('heartbeat_ttl', 'Heartbeat TTL', 'integer', 'Connection heartbeat TTL (seconds)'),
            ('offline_threshold', 'Offline Threshold', 'integer', 'Offline detection threshold (seconds)'),
            ('price_ttl', 'Price TTL', 'integer', 'Price validity duration (seconds)'),
            ('cleanup_interval', 'Cleanup Interval', 'integer', 'Cleanup interval (seconds)'),
            ('old_price_threshold', 'Old Price Threshold', 'integer', 'Remove prices older than (seconds)'),
            ('old_opportunity_threshold', 'Old Opportunity Threshold', 'integer', 'Remove opportunities older than (seconds)'),
            ('max_opportunities', 'Max Opportunities', 'integer', 'Maximum opportunities to keep'),
            ('batch_size', 'Batch Size', 'integer', 'Batch processing size'),
            ('pipeline_size', 'Pipeline Size', 'integer', 'Redis pipeline size'),
        ]
        
        self._create_configs(category, configs, redis_config, force)
    
    def migrate_worker_config(self, profile, force):
        """Migrate Worker configuration"""
        category, created = ConfigurationCategory.objects.get_or_create(
            name='workers',
            defaults={
                'display_name': 'Worker Settings',
                'description': 'Configuration for background workers and processors',
                'order': 3
            }
        )
        
        if created:
            self.stdout.write(f'📁 Created category: {category.display_name}')
        
        # Use fallback Worker config
        worker_config = {
            'connection_retry_interval': 2,
            'health_check_interval': 5,
            'max_connection_failures': 5,
            'system_monitor_interval': 60,
            'cleanup_interval': 300,
            'performance_log_interval': 120,
            'arbitrage_calculators': 3,
            'calculation_batch_size': 50,
            'redis_cleanup_interval': 600,
            'data_retention_hours': 24,
        }
        
        configs = [
            ('connection_retry_interval', 'Connection Retry Interval', 'integer', 'Seconds between connection retries'),
            ('health_check_interval', 'Health Check Interval', 'integer', 'Health check interval (seconds)'),
            ('max_connection_failures', 'Max Connection Failures', 'integer', 'Max failures before giving up'),
            ('system_monitor_interval', 'System Monitor Interval', 'integer', 'System monitoring interval (seconds)'),
            ('cleanup_interval', 'Cleanup Interval', 'integer', 'Cleanup interval (seconds)'),
            ('performance_log_interval', 'Performance Log Interval', 'integer', 'Performance logging interval (seconds)'),
            ('arbitrage_calculators', 'Arbitrage Calculators', 'integer', 'Number of arbitrage calculators'),
            ('calculation_batch_size', 'Calculation Batch Size', 'integer', 'Pairs processed per batch'),
            ('redis_cleanup_interval', 'Redis Cleanup Interval', 'integer', 'Redis cleanup interval (seconds)'),
            ('data_retention_hours', 'Data Retention Hours', 'integer', 'Data retention period (hours)'),
        ]
        
        self._create_configs(category, configs, worker_config, force)
    
    def migrate_arbitrage_config(self, profile, force):
        """Migrate Arbitrage configuration"""
        category, created = ConfigurationCategory.objects.get_or_create(
            name='arbitrage',
            defaults={
                'display_name': 'Arbitrage Settings',
                'description': 'Configuration for arbitrage calculation and detection',
                'order': 4
            }
        )
        
        if created:
            self.stdout.write(f'📁 Created category: {category.display_name}')
        
        # Fallback arbitrage config
        arbitrage_config = {
            'min_profit_percentage': 0.5,
            'max_volume_percentage': 10.0,
            'calculation_timeout': 30,
            'symbol_blacklist': [],
            'exchange_fees': {},
            'max_opportunities_per_calculation': 100,
            'calculation_interval': 0.15,
            'min_calculation_interval': 0.05,
            'cache_update_interval': 30,
            'profit_threshold': 0.01,
            'min_exchanges': 2,
            'batch_size': 100,
            'max_opportunities': 50,
            'log_interval': 100,
            'quality_check_interval': 10,
            'connection_timeout': 30,
        }
        
        configs = [
            ('min_profit_percentage', 'Min Profit Percentage', 'float', 'Minimum profit percentage for opportunities'),
            ('max_volume_percentage', 'Max Volume Percentage', 'float', 'Maximum volume percentage to use'),
            ('calculation_timeout', 'Calculation Timeout', 'integer', 'Calculation timeout (seconds)'),
            ('symbol_blacklist', 'Symbol Blacklist', 'json', 'List of symbols to ignore'),
            ('exchange_fees', 'Exchange Fees', 'json', 'Exchange-specific fee structures'),
            ('max_opportunities_per_calculation', 'Max Opportunities Per Calculation', 'integer', 'Maximum opportunities per calculation cycle'),
            ('calculation_interval', 'Calculation Interval', 'float', 'Main loop interval (seconds)'),
            ('min_calculation_interval', 'Min Calculation Interval', 'float', 'Minimum interval (seconds)'),
            ('cache_update_interval', 'Cache Update Interval', 'integer', 'Trading pairs cache update (seconds)'),
            ('profit_threshold', 'Profit Threshold', 'float', 'Minimum profit % for broadcasting'),
            ('min_exchanges', 'Min Exchanges', 'integer', 'Minimum exchanges for arbitrage'),
            ('batch_size', 'Batch Size', 'integer', 'Opportunities batch size'),
            ('max_opportunities', 'Max Opportunities', 'integer', 'Max opportunities to keep'),
            ('log_interval', 'Log Interval', 'integer', 'Log every N calculations'),
            ('quality_check_interval', 'Quality Check Interval', 'integer', 'Quality checks frequency'),
            ('connection_timeout', 'Connection Timeout', 'integer', 'Connection health timeout (seconds)'),
        ]
        
        self._create_configs(category, configs, arbitrage_config, force)
    
    def _create_configs(self, category, configs, source_data, force):
        """Helper to create configuration entries"""
        for key, display_name, value_type, description in configs:
            if key not in source_data:
                continue
                
            config, created = Configuration.objects.get_or_create(
                category=category,
                key=key,
                defaults={
                    'display_name': display_name,
                    'description': description,
                    'value_type': value_type,
                    'is_active': True,
                    'is_required': True,
                }
            )
            
            if created or force:
                config.set_value(source_data[key])
                config.save()
                
                if created:
                    self.stdout.write(f'  ✅ Created: {category.name}.{key} = {source_data[key]}')
                else:
                    self.stdout.write(f'  🔄 Updated: {category.name}.{key} = {source_data[key]}')
            else:
                self.stdout.write(f'  ⏭️  Skipped: {category.name}.{key} (already exists)')