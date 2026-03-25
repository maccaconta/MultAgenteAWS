from __future__ import annotations

import os
from pathlib import Path

from core.config import AppConfig

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-only-secret-key')
DEBUG = os.getenv('DJANGO_DEBUG', 'true').lower() == 'true'
ALLOWED_HOSTS = [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', '*').split(',') if h.strip()]

INSTALLED_APPS = [
    'daphne',
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.core',
    'apps.catalog',
    'apps.conversations',
    'apps.agents',
    'apps.evaluations',
    'apps.realtime',
    'apps.api',
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
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

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

DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('DB_NAME', BASE_DIR / 'db.sqlite3'),
        'USER': os.getenv('DB_USER', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', ''),
        'PORT': os.getenv('DB_PORT', ''),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'Europe/Berlin'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
DEFAULT_FROM_EMAIL = AppConfig.DEFAULT_FROM_EMAIL

CHANNEL_LAYER_BACKEND = os.getenv(
    'CHANNEL_LAYER_BACKEND',
    'channels.layers.InMemoryChannelLayer',
)

if CHANNEL_LAYER_BACKEND == 'channels.layers.InMemoryChannelLayer':
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': CHANNEL_LAYER_BACKEND,
        }
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': CHANNEL_LAYER_BACKEND,
            'CONFIG': {
                'hosts': [os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1')],
            },
        }
    }






BEDROCK_REGION = AppConfig.AWS_REGION
BEDROCK_KB_ID = AppConfig.BEDROCK_KB_ID
BEDROCK_TURN_MODEL_ID = AppConfig.BEDROCK_TURN_MODEL_ID
BEDROCK_EVALUATE_MODEL_ID = AppConfig.BEDROCK_EVALUATE_MODEL_ID
BEDROCK_SUMMARIZE_MODEL_ID = AppConfig.BEDROCK_SUMMARIZE_MODEL_ID
BEDROCK_SUPERVISOR_MODEL_ID = AppConfig.BEDROCK_SUPERVISOR_MODEL_ID
BEDROCK_AGENT_TEAM_MANIFEST = AppConfig.BEDROCK_AGENT_TEAM_MANIFEST
EMS_PROMPT_FORMAT = os.getenv('EMS_PROMPT_FORMAT', 'database_json')
EMS_SIMULATION_DEFAULT_BLUEPRINT = os.getenv('EMS_SIMULATION_DEFAULT_BLUEPRINT', 'turno_padrao_telemedicina')
