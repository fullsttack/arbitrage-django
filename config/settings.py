"""
High-Performance Django settings for Arbitrage Monitor
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Create logs directory
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ASGI Configuration
ASGI_APPLICATION = 'config.asgi.application'

# High-Performance Channel Layers with Redis
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(
                os.getenv('REDIS_HOST', 'localhost'),
                int(os.getenv('REDIS_PORT', 6379))
            )],
            'capacity': 5000,  # Increased capacity
            'expiry': 60,      # Message expiry
        },
    },
}

# High-Performance PostgreSQL Database
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.getenv('DB_NAME', 'arbit'),
        'USER': os.getenv('DB_USER', 'mohsen'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'OPTIONS': {
            'MAX_CONNS': 100,
            'OPTIONS': {
                '-c default_transaction_isolation=serializable',
            }
        },
        'CONN_MAX_AGE': 600,  # Connection pooling
    }
}

# Redis Configuration for High Performance
REDIS_CONFIG = {
    'HOST': os.getenv('REDIS_HOST', 'localhost'),
    'PORT': int(os.getenv('REDIS_PORT', 6379)),
    'DB': int(os.getenv('REDIS_DB', 0)),
    'PASSWORD': os.getenv('REDIS_PASSWORD', None),
    'CONNECTION_POOL_KWARGS': {
        'max_connections': 100,
        'retry_on_timeout': True,
        'socket_keepalive': True,
        'socket_keepalive_options': {},
    }
}

# Performance Settings
WORKER_COUNT = int(os.getenv('WORKER_COUNT', 8))
ASGI_WORKERS = int(os.getenv('ASGI_WORKERS', 4))
MAX_CONNECTIONS = int(os.getenv('MAX_CONNECTIONS', 1000))

# Cache Configuration (Redis)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"redis://{REDIS_CONFIG['HOST']}:{REDIS_CONFIG['PORT']}/{REDIS_CONFIG['DB']}",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': REDIS_CONFIG['CONNECTION_POOL_KWARGS'],
        }
    }
}

# Session engine
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# High-Performance Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_MAX_SIZE = os.getenv('LOG_MAX_SIZE', '100MB')
LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 10))

def parse_size(size_str):
    """Parse size string like '100MB' to bytes"""
    size_str = size_str.upper()
    if size_str.endswith('MB'):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('GB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    else:
        return int(size_str)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
        'detailed': {
            'format': '[{asctime}] {levelname} {name} {module}.{funcName}:{lineno} - {message}',
            'style': '{',
        },
        'performance': {
            'format': '[{asctime}] PERF {module}.{funcName} - {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'level': 'INFO',
        },
        'file_debug': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'debug.log',
            'maxBytes': parse_size(LOG_MAX_SIZE),
            'backupCount': LOG_BACKUP_COUNT,
            'formatter': 'detailed',
            'level': 'DEBUG',
        },
        'file_info': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'info.log',
            'maxBytes': parse_size(LOG_MAX_SIZE),
            'backupCount': LOG_BACKUP_COUNT,
            'formatter': 'verbose',
            'level': 'INFO',
        },
        'file_error': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'error.log',
            'maxBytes': parse_size(LOG_MAX_SIZE),
            'backupCount': LOG_BACKUP_COUNT,
            'formatter': 'detailed',
            'level': 'ERROR',
        },
        'file_arbitrage': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'arbitrage.log',
            'maxBytes': parse_size(LOG_MAX_SIZE) * 2,  # Larger for arbitrage logs
            'backupCount': LOG_BACKUP_COUNT,
            'formatter': 'performance',
            'level': 'DEBUG',
        },
        'file_exchanges': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'exchanges.log',
            'maxBytes': parse_size(LOG_MAX_SIZE) * 2,
            'backupCount': LOG_BACKUP_COUNT,
            'formatter': 'detailed',
            'level': 'DEBUG',
        },
        'file_performance': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'performance.log',
            'maxBytes': parse_size(LOG_MAX_SIZE),
            'backupCount': 5,
            'formatter': 'performance',
            'level': 'DEBUG',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file_info', 'file_error'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'core': {
            'handlers': ['console', 'file_debug', 'file_error'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'core.arbitrage': {
            'handlers': ['console', 'file_arbitrage', 'file_performance', 'file_error'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'core.services': {
            'handlers': ['console', 'file_exchanges', 'file_performance', 'file_error'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'performance': {
            'handlers': ['file_performance'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file_info', 'file_error'],
        'level': LOG_LEVEL,
    },
}

# Security settings
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', 0))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Performance monitoring
ENABLE_METRICS = os.getenv('ENABLE_METRICS', 'True').lower() == 'true'