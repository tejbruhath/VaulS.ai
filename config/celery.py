"""Celery configuration."""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('rag_api')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Optional: Define periodic tasks
app.conf.beat_schedule = {
    'rebuild-bm25-index': {
        'task': 'rag_api.ingestion.tasks.rebuild_bm25_index',
        'schedule': crontab(minute=0, hour=0),  # Daily at midnight
    },
}
