import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
_env_file = os.path.join(BASE_DIR, '.env')
if not os.path.exists(_env_file):
    _env_file = os.path.join(BASE_DIR.parent, '.env')
if os.path.exists(_env_file):
    environ.Env.read_env(_env_file)

SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'channels',
    'drf_spectacular',
    'django_filters',
    'apps.crm',
    'apps.amocrm',
    'apps.analytics',
    'apps.ai_analyst',
    'apps.dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
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

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': env('REDIS_URL'),
    }
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [env('REDIS_URL')],
        },
    }
}

CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Tashkent'

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'sync-amocrm-every-15min': {
        'task': 'apps.amocrm.tasks.sync_all',
        'schedule': 900,
    },
    'sync-bitrix-every-15min': {
        'task': 'apps.crm.tasks.sync_bitrix_all',
        'schedule': 900,
    },
    # AI avto-hisobotlar (Asia/Tashkent)
    'ai-daily-report': {
        'task': 'apps.ai_analyst.tasks.generate_daily_report',
        'schedule': crontab(hour=8, minute=0),
    },
    'ai-weekly-report': {
        'task': 'apps.ai_analyst.tasks.generate_weekly_report',
        'schedule': crontab(hour=8, minute=0, day_of_week=1),  # dushanba
    },
    # Metrik alertlar — har soat
    'ai-metric-alerts': {
        'task': 'apps.ai_analyst.tasks.check_metric_alerts',
        'schedule': crontab(minute=0),
    },
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'AmoCRM AI Dashboard API',
    'DESCRIPTION': 'AmoCRM ma\'lumotlarini AI bilan tahlil qiluvchi dashboard API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

AMOCRM_DOMAIN = env('AMOCRM_DOMAIN')
AMOCRM_CLIENT_ID = env('AMOCRM_CLIENT_ID')
AMOCRM_CLIENT_SECRET = env('AMOCRM_CLIENT_SECRET')
AMOCRM_REDIRECT_URI = env('AMOCRM_REDIRECT_URI', default='http://localhost:8000/amocrm/callback/')

BITRIX_WEBHOOK_URL = env('BITRIX_WEBHOOK_URL', default='')

DEFAULT_CRM = env('DEFAULT_CRM', default='amocrm')

ANTHROPIC_API_KEY = env('ANTHROPIC_API_KEY')

LANGCHAIN_CLAUDE_MODEL = env('LANGCHAIN_CLAUDE_MODEL', default='claude-sonnet-4-6')

EMBEDDINGS_PROVIDER = env('EMBEDDINGS_PROVIDER', default='fastembed')

EMBEDDINGS_MODEL = env(
    'EMBEDDINGS_MODEL',
    default='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
)

OPENAI_API_KEY = env('OPENAI_API_KEY', default='')

FAISS_INDEX_DIR = MEDIA_ROOT / 'faiss_index'
RAG_UPLOAD_DIR = MEDIA_ROOT / 'rag_docs'

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'http://localhost:3000',
    'http://localhost:8000',
])

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
