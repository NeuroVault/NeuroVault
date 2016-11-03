# Django settings for neurovault project.
import os
import sys
import tempfile
from datetime import timedelta

import matplotlib
from kombu import Exchange, Queue

matplotlib.use('Agg')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEBUG = True

DOMAIN_NAME = "http://neurovault.org"

TEMPLATE_DEBUG = DEBUG

ADMINS = (
    (('Chris', 'krzysztof.gorgolewski@gmail.com'))
)

MANAGERS = ADMINS

SITE_ID = 1

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'postgres',
        # The following settings are not used with sqlite3:
        'USER': 'postgres',
        'HOST': 'db',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '5432',        # Set to empty string for default.
    }
}


# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ["*"]

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Berlin'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

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
MEDIA_ROOT = os.path.join(BASE_DIR,'media')
MEDIA_URL = '/public/media/'

PRIVATE_MEDIA_ROOT = '/var/www/image_data'
PRIVATE_MEDIA_URL = '/media/images'


# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = '/var/www/static'

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'neurovault.apps.statmaps.middleware.CollectionRedirectMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'neurovault.urls'

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'neurovault.wsgi.application'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': (),
        'OPTIONS': {'context_processors': ("django.contrib.auth.context_processors.auth",
                                            "django.core.context_processors.debug",
                                            "django.core.context_processors.i18n",
                                            "django.core.context_processors.media",
                                            "django.core.context_processors.static",
                                            "django.core.context_processors.tz",
                                            "django.contrib.messages.context_processors.messages",
                                            'django.core.context_processors.request'),
                    'loaders': ('hamlpy.template.loaders.HamlPyFilesystemLoader',
                                'hamlpy.template.loaders.HamlPyAppDirectoriesLoader',
                                'django.template.loaders.filesystem.Loader',
                                'django.template.loaders.app_directories.Loader',
                                )}
    }
]

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'neurovault.apps.main',
    'neurovault.apps.statmaps',
    'neurovault.apps.users',
    'django.contrib.sitemaps',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
     #'django.contrib.admindocs',
    'social.apps.django_app.default',
    'rest_framework',
    'taggit',
    'crispy_forms',
    'coffeescript',
    'taggit_templatetags',
    'polymorphic',
    'djcelery',
    'django_cleanup',
    'file_resubmit',
    'django_mailgun',
    'django_hstore',
    'guardian',
    'oauth2_provider',
    'fixture_media'
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
# LOGGING = {

#     'version': 1,
#     'disable_existing_loggers': False,
#     'filters': {
#         'require_debug_false': {
#             '()': 'django.utils.log.RequireDebugFalse'
#         }
#     },
#     'handlers': {
#         'mail_admins': {
#             'level': 'ERROR',
#             'filters': ['require_debug_false'],
#             'class': 'django.utils.log.AdminEmailHandler'
#         }
#     },
#     'loggers': {
#         'django.request': {
#             'handlers': ['mail_admins'],
#             'level': 'ERROR',
#             'propagate': True,
#         },
#     }
# }

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'social.backends.facebook.FacebookOAuth2',
    'social.backends.google.GoogleOAuth2',
    'guardian.backends.ObjectPermissionBackend',
)

SOCIAL_AUTH_PIPELINE = (
    'social.pipeline.social_auth.social_details',
    'social.pipeline.social_auth.social_uid',
    'social.pipeline.social_auth.auth_allowed',
    'social.pipeline.social_auth.social_user',
    'social.pipeline.user.get_username',
    'social.pipeline.social_auth.associate_by_email',  # <--- enable this one
    'social.pipeline.user.create_user',
    'social.pipeline.social_auth.associate_user',
    'social.pipeline.social_auth.load_extra_data',
    'social.pipeline.user.user_details'
)

SOCIAL_AUTH_FACEBOOK_SCOPE = ['email']

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'

REST_FRAMEWORK = {
    # Use hyperlinked styles by default.
    # Only used if the `serializer_class` attribute is not set on a view.
    'DEFAULT_MODEL_SERIALIZER_CLASS':
        'rest_framework.serializers.HyperlinkedModelSerializer',

    # LimitOffsetPagination will allow to set a ?limit= and ?offset=
    # variable in the URL.
    'DEFAULT_PAGINATION_CLASS':
        'neurovault.api.pagination.StandardResultPagination',

    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ],

    'DEFAULT_AUTHENTICATION_CLASSES': (
        'oauth2_provider.ext.rest_framework.OAuth2Authentication',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'neurovault.api.utils.ExplicitUnicodeJSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'UNICODE_JSON': True,
}

OAUTH2_PROVIDER = {
    'REQUEST_APPROVAL_PROMPT': 'auto'
}

LOGIN_REDIRECT_URL = '/my_collections/'
#LOGIN_URL          = '/login-form/'
#LOGIN_ERROR_URL    = '/login-error/'

CRISPY_TEMPLATE_PACK = 'bootstrap3'

DBBACKUP_STORAGE = 'dbbackup.storage.dropbox_storage'
DBBACKUP_TOKENS_FILEPATH = '/home/filo/dbtokens'
DBBACKUP_POSTGRES_BACKUP_COMMAND = 'export PGPASSWORD=neurovault\n pg_dump --username={adminuser} --host={host} --port={port} {databasename} >'

# For Apache, use 'sendfile.backends.xsendfile'
# For Nginx, use 'sendfile.backends.nginx'
# For Devserver, use 'sendfile.backends.development'
SENDFILE_BACKEND = 'sendfile.backends.development'

PRIVATE_MEDIA_REDIRECT_HEADER = 'X-Accel-Redirect'

PYCORTEX_DATASTORE = os.path.join(BASE_DIR,'pycortex_data')

CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            },
            "file_resubmit": {
                'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
                "LOCATION": '/tmp/file_resubmit/'
            }
          }

# Mandrill config
EMAIL_BACKEND = 'django_mailgun.MailgunBackend'
MAILGUN_ACCESS_KEY = 'key-3ax6xnjp29jd6fds4gc373sgvjxteol0' # replace with a real key in production
MAILGUN_SERVER_NAME = 'samples.mailgun.org'# replace with 'neurovault.org' in production
DEFAULT_FROM_EMAIL = "noreply@neurovault.org"

if os.path.exists('/usr/local/share/pycortex/db/fsaverage'):
    STATICFILES_DIRS = (
                        ('pycortex-resources', '/usr/local/lib/python2.7/site-packages/cortex/webgl/resources'),
                        ('pycortex-ctmcache', '/usr/local/share/pycortex/db/fsaverage/cache')
                        )

# Celery config
BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_DEFAULT_QUEUE = 'default'
CELERY_QUEUES = (
    Queue('default', Exchange('default'), routing_key='default'),
)
CELERY_IMPORTS = ('neurovault.apps.statmaps.tasks', )

CELERYBEAT_SCHEDULE = {
    'anima_crawl_every day': {
        'task': 'crawl_anima',
        'schedule': timedelta(days=1)
    },
}

CELERY_TIMEZONE = 'Europe/Berlin'

ANONYMOUS_USER_ID = -1

DEFAULT_OAUTH_APPLICATION_ID = -1
DEFAULT_OAUTH_APP_NAME = 'DefaultOAuthApp'
DEFAULT_OAUTH_APP_OWNER_ID = -2
DEFAULT_OAUTH_APP_OWNER_USERNAME = 'DefaultAppOwner'
OAUTH_PERSONAL_TOKEN_LENGTH = 40

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
os.environ["SUBJECTS_DIR"] = os.path.join(os.environ["FREESURFER_HOME"],"subjects")
os.environ["FSLOUTPUTTYPE"] = "NIFTI_GZ"

# provToolbox path
os.environ["PATH"] += os.pathsep + '/path/to/lib/provToolbox/bin'

#CELERYBEAT_SCHEDULE = {
#    'run_make_correlation_df': {
#        'task': 'neurovault.apps.statmaps.tasks...',
#        'schedule': timedelta(minutes=30),
#    },
#}
# or manage periodic schedule in django admin
#CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'

if "test" in sys.argv or "benchmark" in sys.argv:
    test_media_root = os.path.join(tempfile.mkdtemp(prefix="neurovault_test_"))
    PRIVATE_MEDIA_ROOT = test_media_root
    CELERY_ALWAYS_EAGER = True
    CELERY_EAGER_PROPAGATES_EXCEPTIONS = True


TAGGIT_CASE_INSENSITIVE=True

FIXTURE_DIRS = (
    'apps/statmaps/fixtures/',
)

MEDIA_ROOT = PRIVATE_MEDIA_ROOT
