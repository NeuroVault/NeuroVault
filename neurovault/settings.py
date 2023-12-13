# Django settings for neurovault project.
import os
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

import matplotlib
from kombu import Exchange, Queue

matplotlib.use("Agg")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APPS_DIR = Path(BASE_DIR) / "neurovault" / "apps"

DEBUG = os.getenv("DEBUG", False)

DOMAIN_NAME = "https://neurovault.org"

TEMPLATE_DEBUG = DEBUG

ADMINS = [("Ross", "rosswilsonblair@gmail.com")]

MANAGERS = ADMINS

SITE_ID = 1

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST"),
        "PORT": os.getenv("POSTGRES_PORT"),
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

SECRET_KEY = os.getenv("SECRET_KEY")

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ["*"]

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = "Europe/Berlin"

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = "en-us"

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
if os.path.isabs(os.environ["NV_IMAGE_DATA"]):
    MEDIA_BASE = os.environ["NV_IMAGE_DATA"]
else:
    MEDIA_BASE = os.path.join(BASE_DIR, os.environ["NV_IMAGE_DATA"])
MEDIA_ROOT = os.path.join(MEDIA_BASE, "pub")
MEDIA_URL = "/public/media/"

PRIVATE_MEDIA_ROOT = MEDIA_BASE
PRIVATE_MEDIA_URL = "/media/images"


# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = "/var/www/static"

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = "/static/"

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    #    'django.contrib.staticfiles.finders.DefaultStorageFinder',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.common.BrokenLinkEmailsMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "neurovault.urls"

TEST_RUNNER = "django.test.runner.DiscoverRunner"

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = "neurovault.wsgi.application"

TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#dirs
        "DIRS": [str(APPS_DIR / "templates")],
        # https://docs.djangoproject.com/en/dev/ref/settings/#app-dirs
        "APP_DIRS": True,
        "OPTIONS": {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "neurovault.apps.main",
    "neurovault.apps.statmaps",
    "neurovault.apps.users",
    "django.contrib.sitemaps",
    "django.contrib.admin",
    "social_django",
    "rest_framework",
    "rest_framework.authtoken",
    "taggit",
    "crispy_forms",
    "crispy_bootstrap4",
    "polymorphic",
    "django_cleanup",
    "file_resubmit",
    "guardian",
    "django_celery_results",
]

AUTHENTICATION_BACKENDS = (
    "social_core.backends.facebook.FacebookOAuth2",
    "social_core.backends.google.GoogleOAuth2",
    "guardian.backends.ObjectPermissionBackend",
    "django.contrib.auth.backends.ModelBackend",
)

SOCIAL_AUTH_PIPELINE = (
    "social.pipeline.social_auth.social_details",
    "social.pipeline.social_auth.social_uid",
    "social.pipeline.social_auth.auth_allowed",
    "social.pipeline.social_auth.social_user",
    "social.pipeline.user.get_username",
    "social.pipeline.social_auth.associate_by_email",
    "social.pipeline.user.create_user",
    "social.pipeline.social_auth.associate_user",
    "social.pipeline.social_auth.load_extra_data",
    "social.pipeline.user.user_details",
)

SOCIAL_AUTH_FACEBOOK_SCOPE = ["email"]
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
FACEBOOK_API_SECRET = os.getenv("FACEBOOK_API_SECRET")
SOCIAL_AUTH_GOOGLE_PLUS_KEY = os.getenv("SOCIAL_AUTH_GOOGLE_PLUS_KEY")
SOCIAL_AUTH_GOOGLE_PLUS_SECRET = os.getenv("SOCIAL_AUTH_GOOGLE_PLUS_SECRET")
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET")

SESSION_SERIALIZER = "django.contrib.sessions.backends.signed_cookies"

REST_FRAMEWORK = {
    # Use hyperlinked styles by default.
    # Only used if the `serializer_class` attribute is not set on a view.
    "DEFAULT_MODEL_SERIALIZER_CLASS": "rest_framework.serializers.HyperlinkedModelSerializer",
    # LimitOffsetPagination will allow to set a ?limit= and ?offset=
    # variable in the URL.
    "DEFAULT_PAGINATION_CLASS": "neurovault.api.pagination.StandardResultPagination",
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly"
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "neurovault.api.utils.ExplicitUnicodeJSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "UNICODE_JSON": True,
}


LOGIN_REDIRECT_URL = "/my_collections/"
# LOGIN_URL          = '/login-form/'
# LOGIN_ERROR_URL    = '/login-error/'

CRISPY_TEMPLATE_PACK = "bootstrap4"

# For Apache, use 'sendfile.backends.xsendfile'
# For Nginx, use 'sendfile.backends.nginx'
# For Devserver, use 'sendfile.backends.development'
SENDFILE_BACKEND = "sendfile.backends.development"

PRIVATE_MEDIA_REDIRECT_HEADER = "X-Accel-Redirect"

PYCORTEX_DATASTORE = os.path.join(BASE_DIR, "pycortex_data")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
    "file_resubmit": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": "/tmp/file_resubmit/",
    },
}

DEFAULT_FROM_EMAIL = "noreply@neurovault.org"

if os.path.exists("/usr/local/share/pycortex/db/fsaverage"):
    STATICFILES_DIRS = (
        ("pycortex-ctmcache", "/usr/local/share/pycortex/db/fsaverage/cache"),
    )

# Celery config
BROKER_URL = "redis://redis:6379/0"

CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_DEFAULT_QUEUE = "default"
CELERY_QUEUES = (Queue("default", Exchange("default"), routing_key="default"),)
CELERY_IMPORTS = ("neurovault.apps.statmaps.tasks",)

""" Disabled for upgrade, do we still need this?
CELERYBEAT_SCHEDULE = {
    'anima_crawl_every day': {
        'task': 'crawl_anima',
        'schedule': timedelta(days=1)
    },
}
"""

CELERY_TIMEZONE = "Europe/Berlin"

ANONYMOUS_USER_ID = -1

# Bogus secret key.
try:
    from secrets import *
except ImportError:
    from bogus_secrets import *

try:
    from local_settings import *
except ImportError:
    pass

# freesurfer/pycortex environment
os.environ["XDG_CONFIG_HOME"] = PYCORTEX_DATASTORE
os.environ["FREESURFER_HOME"] = "/opt/freesurfer"
os.environ["SUBJECTS_DIR"] = os.path.join(os.environ["FREESURFER_HOME"], "subjects")
os.environ["FSLOUTPUTTYPE"] = "NIFTI_GZ"

# provToolbox path
os.environ["PATH"] += os.pathsep + "/path/to/lib/provToolbox/bin"

# CELERYBEAT_SCHEDULE = {
#    'run_make_correlation_df': {
#        'task': 'neurovault.apps.statmaps.tasks...',
#        'schedule': timedelta(minutes=30),
#    },
# }
# or manage periodic schedule in django admin
# CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'

if "test" in sys.argv or "benchmark" in sys.argv:
    test_media_root = os.path.join(tempfile.mkdtemp(prefix="neurovault_test_"))
    PRIVATE_MEDIA_ROOT = test_media_root
    CELERY_ALWAYS_EAGER = True
    CELERY_EAGER_PROPAGATES_EXCEPTIONS = True


TAGGIT_CASE_INSENSITIVE = True
GUARDIAN_GET_CONTENT_TYPE = (
    "polymorphic.contrib.guardian.get_polymorphic_base_content_type"
)

FIXTURE_DIRS = ("apps/statmaps/fixtures/",)


if os.getenv("EMAIL_HOST") is not None:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    MAIL_USE_TLS = True
    EMAIL_HOST = os.getenv("EMAIL_HOST")
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

if os.getenv("EMAIL_HOST") is not None:
    EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
    EMAIL_FILE_PATH = '/tmp/email-fallback' 
