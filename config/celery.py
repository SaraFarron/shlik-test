"""
Celery configuration for Product Statistics Service.
"""
import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Celery Beat schedule
app.conf.beat_schedule = {
    'import-products-every-5-minutes': {
        'task': 'products.tasks.import_products_task',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
}
