"""
WSGI config for diners project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/wsgi/
"""

import os, sys

sys.path.append('/usr/local/lib/python3.9/site-packages')

from django.core.wsgi import get_wsgi_application

sys.path.append('/home/segundo/diners/src/diners')
sys.path.append('/home/segundo/diners/src/')
sys.path.append('/home/segundo/diners/')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'diners.settings.production')

application = get_wsgi_application()
