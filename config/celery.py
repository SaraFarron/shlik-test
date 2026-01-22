import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

app.conf.beat_schedule = {
    'import-products-every-5-minutes': {
        'task': 'products.tasks.import_products_task',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
}
