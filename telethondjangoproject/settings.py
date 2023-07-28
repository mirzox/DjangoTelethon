"""
Django settings for telethondjangoproject project.

Generated by 'django-admin startproject' using Django 4.1.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

import os
from pathlib import Path
import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(os.path.join(BASE_DIR, '.env'))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", False) == 'True'
print(DEBUG)
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', ' ').split(' ')
print(ALLOWED_HOSTS)

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'account',
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

ROOT_URLCONF = 'telethondjangoproject.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
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

WSGI_APPLICATION = 'telethondjangoproject.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

DB_SQLITE = "sqlite"
DB_POSTGRESQL = "postgresql"

DATABASES_ALL = {
    DB_SQLITE: {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
    DB_POSTGRESQL: {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': os.environ.get('DB_HOST'),
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASS'),
        'PORT': os.environ.get('DB_PORT')
    }
}

DATABASES = {"default": DATABASES_ALL[os.environ.get("DJANGO_DB", DB_SQLITE)]}


CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_LOCATION"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PASSWORD": os.environ.get("REDIS_PASSWORD"),
        },
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

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


LOG_DIR = os.path.join(BASE_DIR, os.environ.get('LOGING_ROOT'))  # Create a 'logs' folder in your project root


# def dynamic_log_file_name(log_path, log_name):
#     log_p = os.path.join(log_path, log_name)
#     if not os.path.exists(os.path.join(log_p)):
#         os.makedirs(log_p, exist_ok=True)
#     return os.path.join(log_path, f'{log_name}/{log_name}.log')


def dynamic_log_file_name(log_name):
    log_date = datetime.now().strftime('%Y-%m-%d')
    return os.path.join(LOG_DIR, f'{log_name}_{log_date}.log')


class DynamicTimedRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, filename, **kwargs):
        filename = dynamic_log_file_name(filename)
        super().__init__(filename, **kwargs)


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers':
        {
        'file': {
            '()': DynamicTimedRotatingFileHandler,
            'filename':  'server/server',
            'formatter': 'standard',
            'when': 'midnight',
            'interval': 1,       # 1 day interval
            'backupCount': 30,
        },
        'file_module1': {
            "()": DynamicTimedRotatingFileHandler,
            "filename": "google_api/google_api",
            'formatter': 'standard',
            'when': 'midnight',
            'interval': 1,  # 1 day interval
            'backupCount': 30,
        },
        'file_module2': {
            "()": DynamicTimedRotatingFileHandler,
            "filename": "scheduler/scheduler",
            'formatter': 'standard',
            'when': 'midnight',
            'interval': 1,  # 1 day interval
            'backupCount': 30,
        },
        # 'file_module3': {
        #     "()": DynamicTimedRotatingFileHandler,
        #     "filename": "tguser/tguser",
        #     'formatter': 'standard',
        #     'when': 'midnight',
        #     'interval': 1,  # 1 day interval
        #     'backupCount': 30,
        # }
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'google_api': {
            'handlers': ['file_module1'],
            'level': 'INFO',
            'propagate': False,
        },
        'scheduler': {
            'handlers': ['file_module2'],
            'level': 'INFO',
            'propagate': False,
        },
        # 'tguser': {
        #     'handlers': ['file_module3'],
        #     'level': 'INFO',
        #     'propagate': False,
        # }
    }
}


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = 'ru'

TIME_ZONE = 'Asia/Tashkent'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/



# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_DIR = os.path.join(BASE_DIR, os.environ.get('SESSION_DIR'))
GOOGLE_API_CREDENTIALS = os.path.join(BASE_DIR, os.environ.get('GOOGLE_API_CREDENTIALS'))

HOUR_DIFFERENCE = int(os.environ.get('HOUR_DIFFERENCE', 5))
TYPING_DELAY = int(os.environ.get('TYPING_DELAY', 5))

# if DEBUG:
STATIC_URL = 'static/'
STATIC_ROOT = 'static'
