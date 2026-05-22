"""
Django base settings for AmoCRM AI Dashboard.
"""
import os
from pathlib import Path

import environ

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Environment
env = environ.Env(
    DEBUG=(bool, False),
)
# .env faylni qidirish: avval loyiha root, keyin bir daraja yuqorida
_env_file = os.path.join(BASE_DIR, '.env')
if not os.path.exists(_env_file):
    _env_file = os.path.join(BASE_DIR.parent, '.env')
if os.path.exists(_env_file):
    environ.Env.read_env(_env_file)

SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])


# =============================================================================
# Application definition
# =============================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'channels',
    'drf_spectacular',
    'django_filters',
    # Local apps
    'apps.crm',           # Unified CRM adapter (AmoCRM + Bitrix24)
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


# =============================================================================
# Database
# =============================================================================

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


# =============================================================================
# Password validation
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# =============================================================================
# Internationalization
# =============================================================================

LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True


# =============================================================================
# Static & Media files
# =============================================================================

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# =============================================================================
# Redis / Cache
# =============================================================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': env('REDIS_URL'),
    }
}


# =============================================================================
# Channels (WebSocket)
# =============================================================================

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [env('REDIS_URL')],
        },
    }
}


# =============================================================================
# Celery
# =============================================================================

CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Tashkent'

CELERY_BEAT_SCHEDULE = {
    'sync-amocrm-every-15min': {
        'task': 'apps.amocrm.tasks.sync_all',
        'schedule': 900,  # 15 daqiqa
    },
    'sync-bitrix-every-15min': {
        'task': 'apps.crm.tasks.sync_bitrix_all',
        'schedule': 900,  # 15 daqiqa
    },
}


# =============================================================================
# Django REST Framework
# =============================================================================

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


# =============================================================================
# SimpleJWT
# =============================================================================

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}


# =============================================================================
# drf-spectacular (Swagger)
# =============================================================================

SPECTACULAR_SETTINGS = {
    'TITLE': 'AmoCRM AI Dashboard API',
    'DESCRIPTION': 'AmoCRM ma\'lumotlarini AI bilan tahlil qiluvchi dashboard API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}


# =============================================================================
# AmoCRM
# =============================================================================

AMOCRM_DOMAIN = env('AMOCRM_DOMAIN')
AMOCRM_CLIENT_ID = env('AMOCRM_CLIENT_ID')
AMOCRM_CLIENT_SECRET = env('AMOCRM_CLIENT_SECRET')
AMOCRM_REDIRECT_URI = env('AMOCRM_REDIRECT_URI', default='http://localhost:8000/amocrm/callback/')


# =============================================================================
# Bitrix24
# =============================================================================

BITRIX_WEBHOOK_URL = env('BITRIX_WEBHOOK_URL', default='')


# =============================================================================
# CRM sozlama — 'amocrm' yoki 'bitrix'
# =============================================================================

DEFAULT_CRM = env('DEFAULT_CRM', default='amocrm')


# =============================================================================
# Anthropic Claude AI
# =============================================================================

ANTHROPIC_API_KEY = env('ANTHROPIC_API_KEY')


# =============================================================================
# LangChain — RAG, Agent, Memory
# =============================================================================

# RAG va Agent uchun ishlatiladigan Claude modeli
LANGCHAIN_CLAUDE_MODEL = env('LANGCHAIN_CLAUDE_MODEL', default='claude-sonnet-4-6')

# Embedding provayderi: 'fastembed' (lokal, ONNX) | 'huggingface' | 'openai'
EMBEDDINGS_PROVIDER = env('EMBEDDINGS_PROVIDER', default='fastembed')

# Embedding modeli — fastembed/huggingface uchun. Ko'p tilli (uz/ru) model.
EMBEDDINGS_MODEL = env(
    'EMBEDDINGS_MODEL',
    default='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
)

# OpenAI embeddings ishlatilganda kerak bo'ladi
OPENAI_API_KEY = env('OPENAI_API_KEY', default='')

# FAISS lokal vektor ombori va RAG hujjatlari uchun papkalar
FAISS_INDEX_DIR = MEDIA_ROOT / 'faiss_index'
RAG_UPLOAD_DIR = MEDIA_ROOT / 'rag_docs'


# =============================================================================
# CORS
# =============================================================================

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'http://localhost:3000',
    'http://localhost:8000',
])


# =============================================================================
# Default primary key
# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
