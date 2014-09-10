import os
import sys	
sys.path.append('/var/www/NeuroVault')
sys.path.append('/var/www/neurosynth')
os.environ['DJANGO_SETTINGS_MODULE'] = 'neurovault.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
