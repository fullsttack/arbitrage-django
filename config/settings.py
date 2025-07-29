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
CSRF_TRUSTED_ORIGINS = ['https://api.mohsen.pro','http://api.mohsen.pro','wss://api.mohsen.pro']
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

# Simplified Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
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
    'SITE_TITLE': 'Digital Dashboard',
    'SITE_HEADER': 'Digital Dashboard',
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
            {
                'title': _('Configuration'),
                'icon': 'settings',
                'items': [
                    {
                        'title': _('Configuration Categories'),
                        'icon': 'folder',
                        'link': reverse_lazy('admin:core_configurationcategory_changelist'),
                    },
                    {
                        'title': _('Configurations'),
                        'icon': 'tune',
                        'link': reverse_lazy('admin:core_configuration_changelist'),
                    },
                ],
            },
        ],
    },
}
