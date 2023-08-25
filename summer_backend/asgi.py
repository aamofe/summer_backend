import os
import django
from channels.routing import get_default_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'summer_backend.settings')

django.setup()

application = get_default_application()