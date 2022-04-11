from __future__ import absolute_import, unicode_literals
import os
import logging
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'printer_management.settings')

logger = logging.getLogger(__name__)
app = Celery('printer_management')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


app.conf.update({
    'broker_url': 'filesystem://',
    'broker_transport_options': {
        'data_folder_in': './broker/out',
        'data_folder_out': './broker/out',
        'data_folder_processed': './broker/processed'
    }})


# setup folder for message broking
for f in ['./broker/out', './broker/processed']:
    if not os.path.exists(f):
        os.makedirs(f)

# here is the beat schedule dictionary defined
app.conf.beat_schedule = {
    '5s up Brew! just testing!': {
        'task': 'printer_support.email.test',
        # 'schedule': crontab(hour=7, minute=30, day_of_week=4),
        'schedule': 5,
        'args': ('Its Thrusday! Brew is just testing!',)
    },
}
app.conf.timezone = 'UTC'


# celery -A printer_support beat -l INFO
# celery -A printer_support worker -l info
# celery -A printer_support beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler

# pip install gevent
# celery -A <module> worker -l info -P gevent
