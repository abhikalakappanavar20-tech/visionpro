import os
import sys

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VeriVision.settings')

# Initialize Django
import django
django.setup()

# Import the WSGI application
from VeriVision.wsgi import application

# Vercel handler
def handler(request, response):
    return application(request, response)