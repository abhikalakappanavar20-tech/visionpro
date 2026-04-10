"""
ASGI config for VeriVision project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VeriVision.settings')

application = get_asgi_application()
