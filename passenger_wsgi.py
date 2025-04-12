import os
import sys

sys.path.insert(0, '/home/wielandtech/git_repo/w_tech/wielandtech')
os.environ['DJANGO_SETTINGS_MODULE'] = 'wielandtech.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()