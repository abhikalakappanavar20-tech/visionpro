import os
import sys
import tempfile

# Use /tmp for writable caches on Vercel
_tmp = os.environ.get('VERCEL', None) and tempfile.gettempdir() or tempfile.gettempdir()
os.environ.setdefault('HF_HOME', os.path.join(_tmp, 'hf_cache'))
os.environ.setdefault('TORCH_HOME', os.path.join(_tmp, 'torch_cache'))
os.environ.setdefault('MPLCONFIGDIR', os.path.join(_tmp, 'matplotlib'))
os.environ.setdefault('XDG_CACHE_HOME', os.path.join(_tmp, '.cache'))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VeriVision.settings')

import django
from django.core.management import call_command

django.setup()
call_command('migrate', '--noinput', verbosity=1)

# Ensure cache dirs exist (writable storage on Vercel)
for key in ('HF_HOME', 'TORCH_HOME', 'MPLCONFIGDIR'):
    os.makedirs(os.environ[key], exist_ok=True)

from VeriVision.wsgi import application

app = application
