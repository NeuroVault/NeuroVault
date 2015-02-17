# Django settings for neurovault project.
import os
from datetime import timedelta
import matplotlib
matplotlib.use('Agg')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEBUG = True

TEMPLATE_DEBUG = DEBUG

ADMINS = (
    (('Chris', 'krzysztof.gorgolewski@gmail.com'),
     ('Gabriel', 'rivera@infocortex.com'))
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'neurovault',
        # The following settings are not used with sqlite3:
        'USER': 'neurovault',
        'PASSWORD': 'neurovault',
        'HOST': '127.0.0.1',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        #'PORT': '',        # Set to empty string for default.
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

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = os.path.join(BASE_DIR,'static')

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

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'hamlpy.template.loaders.HamlPyFilesystemLoader',
    'hamlpy.template.loaders.HamlPyAppDirectoriesLoader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'neurovault.apps.statmaps.middleware.CollectionRedirectMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'neurovault.urls'

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'neurovault.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

TEMPLATE_CONTEXT_PROCESSORS = ("django.contrib.auth.context_processors.auth",
"django.core.context_processors.debug",
"django.core.context_processors.i18n",
"django.core.context_processors.media",
"django.core.context_processors.static",
"django.core.context_processors.tz",
"django.contrib.messages.context_processors.messages",
'django.core.context_processors.request',
)

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
    #'south',
    'corsheaders',
    'dbbackup',
    'polymorphic',
    'djcelery',
    'parsley',
    'django_cleanup'
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

    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ],
}

# Allow cross-origin requests from approved sites
CORS_ORIGIN_REGEX_WHITELIST = (
    '.*neurosynth.org',
    'pilab.colorado.edu'
    '.*'
)

#LOGIN_URL          = '/login-form/'
#LOGIN_REDIRECT_URL = '/logged-in/'
#LOGIN_ERROR_URL    = '/login-error/'

CRISPY_TEMPLATE_PACK = 'bootstrap'

DBBACKUP_STORAGE = 'dbbackup.storage.dropbox_storage'
DBBACKUP_TOKENS_FILEPATH = '/home/filo/dbtokens'
DBBACKUP_POSTGRES_BACKUP_COMMAND = 'export PGPASSWORD=neurovault\n pg_dump --username={adminuser} --host={host} --port={port} {databasename} >'

# the the original image paths are retained to support old links.
# Nginx will serve the PRIVATE_MEDIA_URL with private/ prepended to the path
# e.g. for PRIVATE_MEDIA_URL 'media/images', configure internal location '/private/media/images'
PRIVATE_MEDIA_ROOT = os.path.join(BASE_DIR,'private_media')
PRIVATE_MEDIA_URL = '/media/images'

# For Apache, use 'sendfile.backends.xsendfile'
# For Nginx, use 'sendfile.backends.nginx'
# For Devserver, use 'sendfile.backends.development'
SENDFILE_BACKEND = 'sendfile.backends.development'

PRIVATE_MEDIA_REDIRECT_HEADER = 'X-Accel-Redirect'

PYCORTEX_DATASTORE = os.path.join(BASE_DIR,'pycortex_data')

# Pycortex static data is deployed by collectstatic at build time.
STATICFILES_DIRS = (
    ('pycortex-resources', '/path/to/pycortex/cortex/webgl/resources'),
    ('pycortex-ctmcache', os.path.join(PYCORTEX_DATASTORE,'db/fsaverage/cache')),
)


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

# Celery config
BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

#CELERYBEAT_SCHEDULE = {
#    'run_make_correlation_df': {
#        'task': 'neurovault.apps.statmaps.tasks...',
#        'schedule': timedelta(minutes=30),
#    },
#}
# or manage periodic schedule in django admin
#CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
