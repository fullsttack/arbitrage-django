# 🚀 Dynamic Configuration Manager
# Database-based configuration system

import json
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Dynamic configuration manager"""
    
    def __init__(self):
        self.cache_timeout = 300  # 5 minutes
        self.cache_prefix = 'config:'
    
    def get(self, category_name: str, key: str, default=None):
        """Get configuration value"""
        try:
            from django.core.cache import cache
            from .models import Configuration
            
            cache_key = f"{self.cache_prefix}{category_name}.{key}"
            
            # Try cache first
            value = cache.get(cache_key)
            if value is not None:
                return value
            
            config = Configuration.objects.select_related('category').get(
                category__name=category_name,
                key=key,
                is_active=True
            )
            value = config.value
            
            # Cache the value
            cache.set(cache_key, value, self.cache_timeout)
            return value
            
        except ImportError:
            # Django not ready yet
            return default
        except Exception as e:
            logger.warning(f"Configuration not found: {category_name}.{key} - {e}")
            return default
    
    def set(self, category_name: str, key: str, value, value_type=None):
        """Set configuration value"""
        try:
            from django.core.cache import cache
            from .models import Configuration, ConfigurationCategory
            
            category, _ = ConfigurationCategory.objects.get_or_create(
                name=category_name,
                defaults={'display_name': category_name.title()}
            )
            
            config, created = Configuration.objects.get_or_create(
                category=category,
                key=key,
                defaults={
                    'display_name': key.replace('_', ' ').title(),
                    'value_type': value_type or self._detect_type(value)
                }
            )
            
            config.set_value(value)
            config.save()
            
            # Clear cache
            cache_key = f"{self.cache_prefix}{category_name}.{key}"
            cache.delete(cache_key)
            
            return True
            
        except ImportError:
            # Django not ready yet
            return False
        except Exception as e:
            logger.error(f"Error setting config {category_name}.{key}: {e}")
            return False
    
    def get_category(self, category_name: str) -> dict:
        """Get all configs in a category"""
        try:
            from django.core.cache import cache
            from .models import Configuration, ConfigurationCategory
            
            cache_key = f"{self.cache_prefix}category:{category_name}"
            
            # Try cache first
            configs = cache.get(cache_key)
            if configs is not None:
                return configs
            
            category = ConfigurationCategory.objects.get(name=category_name, is_active=True)
            configs_qs = Configuration.objects.filter(
                category=category,
                is_active=True
            ).order_by('order', 'key')
            
            configs = {}
            for config in configs_qs:
                configs[config.key] = config.value
            
            # Cache the result
            cache.set(cache_key, configs, self.cache_timeout)
            return configs
            
        except ImportError:
            # Django not ready yet
            return {}
        except Exception as e:
            logger.warning(f"Configuration category not found: {category_name} - {e}")
            return {}
    
    def _detect_type(self, value):
        """Auto-detect value type"""
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, (dict, list)):
            return 'json'
        else:
            return 'string'
    
    def clear_cache(self, category_name: str = None, key: str = None):
        """Clear configuration cache"""
        try:
            from django.core.cache import cache
            
            if category_name and key:
                cache_key = f"{self.cache_prefix}{category_name}.{key}"
                cache.delete(cache_key)
            elif category_name:
                cache_key = f"{self.cache_prefix}category:{category_name}"
                cache.delete(cache_key)
            else:
                # Clear all config cache (not recommended in production)
                pass
        except ImportError:
            # Django not ready yet
            pass

# Global instance
config_manager = ConfigManager()

# Compatibility functions for legacy code
def get_redis_config(profile: str = 'default') -> dict:
    """Get Redis configuration"""
    return config_manager.get_category('redis') or {
        'heartbeat_ttl': 90,
        'offline_threshold': 120,
        'price_ttl': 1800,
        'cleanup_interval': 300,
        'old_price_threshold': 7200,
        'old_opportunity_threshold': 2592000,
        'max_opportunities': 10000,
        'batch_size': 1000,
        'pipeline_size': 100,
    }

def get_web_config(profile: str = 'default') -> dict:
    """Get Web configuration"""
    return config_manager.get_category('web') or {
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

def get_worker_config(profile: str = 'default') -> dict:
    """Get Worker configuration"""
    return config_manager.get_category('workers') or {
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

def get_arbitrage_config(profile: str = 'default') -> dict:
    """Get Arbitrage configuration"""
    return config_manager.get_category('arbitrage') or {
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

# WebSocket close codes
WS_CLOSE_CODES = {
    'AUTH_REQUIRED': 4001,
    'PERMISSION_DENIED': 4003,
    'RATE_LIMITED': 4029,
    'SERVER_ERROR': 4500
}

def get_ws_close_code(code_name: str) -> int:
    """🔌 Get WebSocket close code"""
    return WS_CLOSE_CODES.get(code_name, 4000)