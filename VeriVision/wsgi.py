"""
WSGI config for VeriVision project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VeriVision.settings')

application = get_wsgi_application()
