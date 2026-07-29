import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VeriVision.settings')

import django
from django.core.management import call_command

django.setup()
call_command('migrate', '--noinput', verbosity=1)

from VeriVision.wsgi import application

app = application
