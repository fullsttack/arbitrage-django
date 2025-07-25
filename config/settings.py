import os
from pathlib import Path
from dotenv import load_dotenv
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

# Load environment variables
load_dotenv()

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Security
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-@9t@4rn2xrlbuh95k9nv16$vhoy%s7eallm3s2&q%6=1p+v^7n')
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0,pardak.ir,www.pardak.ir').split(',')

# Applications
INSTALLED_APPS = [
    'unfold',
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
    'core.middleware.CSRFMiddleware',
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

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database Configuration
DB_ENGINE = os.getenv('DB_ENGINE', 'django.db.backends.postgresql')
DB_NAME = os.getenv('DB_NAME', 'new')
DB_USER = os.getenv('DB_USER', 'mohsen')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

DATABASES = {
    'default': {
        'ENGINE': DB_ENGINE,
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
        'OPTIONS': {}
    }
}

# Redis Configuration (for prices and opportunities only)
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')

# Channels Configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(REDIS_HOST, REDIS_PORT)],
            'capacity': 5000,  # افزایش از 100 به 5000
            'expiry': 60,      # پیام‌ها 60 ثانیه expire می‌شوند
            'group_expiry': 86400,  # گروه‌ها 24 ساعت
            'symmetric_encryption_keys': None,
        },
    },
}

# Cache Configuration (Redis)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PASSWORD': REDIS_PASSWORD,
        }
    }
}

# Session Configuration
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

CSRF_TRUSTED_ORIGINS = ['https://pardak.ir','http://arbit.yaranejan.com','https://arbit.yaranejan.com','wss://arbit.yaranejan.com']
CSRF_COOKIE_SECURE = True  # If using HTTPS
SESSION_COOKIE_SECURE = True  # If using HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Performance Settings
WORKER_COUNT = int(os.getenv('WORKER_COUNT', 8))
ASGI_WORKERS = int(os.getenv('ASGI_WORKERS', 4))
MAX_CONNECTIONS = int(os.getenv('MAX_CONNECTIONS', 1000))

# Exchange API Configuration
WALLEX_API_KEY = os.getenv('WALLEX_API_KEY', '')
LBANK_API_KEY = os.getenv('LBANK_API_KEY', '')
RAMZINEX_API_KEY = os.getenv('RAMZINEX_API_KEY', '')

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
        'file_performance': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'performance.log',
            'maxBytes': parse_size(LOG_MAX_SIZE),
            'backupCount': LOG_BACKUP_COUNT,
            'formatter': 'performance',
            'level': 'INFO',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file_info'],
            'level': LOG_LEVEL,
            'propagate': True,
        },
        'core': {
            'handlers': ['console', 'file_debug', 'file_error'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'performance': {
            'handlers': ['console', 'file_performance'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file_info', 'file_error'],
        'level': LOG_LEVEL,
    },
}

# Default ID
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication settings
LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/admin/login/'

# Django Unfold Configuration
UNFOLD = {
    'SITE_TITLE': 'Digital Currency Arbitrage',
    'SITE_HEADER': 'Arbitrage Admin',
    'SITE_SYMBOL': '💰',
    'SHOW_HISTORY': True,
    'SHOW_VIEW_ON_SITE': True,
    'COLORS': {
        'primary': {
            '50': '250 245 255',
            '100': '243 232 255',
            '200': '233 213 255',
            '300': '216 180 254',
            '400': '196 181 253',
            '500': '168 85 247',
            '600': '147 51 234',
            '700': '126 34 206',
            '800': '107 33 168',
            '900': '88 28 135',
            '950': '59 7 100',
        },
    },
    'SIDEBAR': {
        'show_search': True,
        'show_all_applications': True,
        'navigation': [
            {
                'title': _('Trading'),
                'icon': 'currency_exchange',
                'items': [
                    {
                        'title': _('Exchanges'),
                        'icon': 'store',
                        'link': reverse_lazy('admin:core_exchange_changelist'),
                    },
                    {
                        'title': _('Currencies'),
                        'icon': 'payments',
                        'link': reverse_lazy('admin:core_currency_changelist'),
                    },
                    {
                        'title': _('Trading Pairs'),
                        'icon': 'swap_horiz',
                        'link': reverse_lazy('admin:core_tradingpair_changelist'),
                    },
                ],
            },
        ],
    },
}
