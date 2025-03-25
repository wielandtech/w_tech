import os
import sys

sys.path.insert(0, '/home/wieland2/git_repo/w_blog/wielandtech')
os.environ['DJANGO_SETTINGS_MODULE'] = 'wielandtech.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()