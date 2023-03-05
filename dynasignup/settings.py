"""
Django settings for dynasignup project.

Generated by 'django-admin startproject' using Django 3.2.4.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""
import zoneinfo
from datetime import timedelta
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
from decouple import config
from django.urls import reverse_lazy
from django.utils.dateparse import parse_datetime, parse_date
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY", default='django-insecure-hmv)rcew6libys3k1an7k-b#)jqsdlkqsdnzuauzeqsdiz*#7-')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = ["inscriptions.dynamobile.net", '127.0.0.1', 'inscriptions.acelpb.com']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "whitenoise",
    'crispy_forms',
    'crispy_bootstrap4',
    'magiclink',
    "accounts",
    "import_export",
    "django_tables2",
    "signup2022.apps.Signup2022Config",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'dynasignup.urls'

AUTHENTICATION_BACKENDS = [
    'magiclink.backends.MagicLinkBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Set Djangos login URL to the magiclink login page
LOGIN_URL = 'magiclink:login'
LOGOUT_REDIRECT_URL = "index"

# Optional:
# If this setting is set to False a user account will be created the first
# time a user requests a login link.
MAGICLINK_REQUIRE_SIGNUP = False
MAGICLINK_REQUIRE_SAME_BROWSER = False
MAGICLINK_REQUIRE_SAME_IP = False

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

WSGI_APPLICATION = 'dynasignup.wsgi.application'

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'data' / 'db.sqlite3',
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.2/topics/i18n/

TIME_ZONE = 'Europe/Brussels'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_ROOT = BASE_DIR / 'static'
STATIC_URL = '/static/'

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CRISPY_TEMPLATE_PACK = 'bootstrap4'
CRISPY_FAIL_SILENTLY = True

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_ROOT = BASE_DIR / "uploads"
MEDIA_URL = "/uploads/"

LOGIN_REDIRECT_URL = reverse_lazy("index")

LANGUAGE_CODE = 'fr'  # default language

LANGUAGES = (
    ('fr', _('French')),
    ('nl', _('Dutch')),
)

LOCALE_PATHS = [
    BASE_DIR / "locale"
]

SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'

brussels_tz = zoneinfo.ZoneInfo("Europe/Brussels")

DYNAMOBILE_START_SIGNUP = parse_datetime(
    config("DYNAMOBILE_START_SIGNUP", default="2022-05-02 20:00:00")
).replace(
    tzinfo=brussels_tz
)
DYNAMOBILE_START_PARTIAL_SIGNUP = parse_datetime("2022-05-20 17:00:00").replace(
    tzinfo=brussels_tz
)
DYNAMOBILE_END_SIGNUP = parse_datetime("2022-05-20 17:00:00").replace(
    tzinfo=brussels_tz
)
DYNAMOBILE_FIRST_DAY = parse_date("2022-07-18")
DYNAMOBILE_LAST_DAY = parse_date("2022-07-25")

DYNAMOBILE_DAYS = [
    (day, day.strftime("%Y-%m-%d"))
    for day in (
        DYNAMOBILE_FIRST_DAY + timedelta(days=i)
        for i in range((DYNAMOBILE_LAST_DAY - DYNAMOBILE_FIRST_DAY).days + 1)
    )
]

# We reserve the right to accept up to 150 people on a case by case basis
DYNAMOBILE_MAX_PARTICIPANTS = config('DYNAMOBILE_MAX_PARTICIPANTS', default=135, cast=int)
# We reserve the right to accept up to 25 people on a case by case basis
DYNAMOBILE_MAX_VAE_PARTICIPANTS = config('DYNAMOBILE_MAX_VAE_PARTICIPANTS', default=20, cast=int)

EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=25, cast=int)
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='inscriptions@dynamobile.net')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)

SERVER_EMAIL = EMAIL_HOST_USER
ADMINS = [("Augustin", EMAIL_HOST_USER), ]

DYNAMOBILE_PRICES = (
    (0, 6, 80, 10),
    (6, 12, 160, 20),
    (12, 18, 240, 30),
    (18, 999, 325, 40),
)


OVH_API_KEY = config("OVH_API_KEY", default="")
OVH_API_SECRET = config("OVH_API_SECRET", default="")
OVH_API_CONSUMER = config("OVH_API_CONSUMER", default="")
