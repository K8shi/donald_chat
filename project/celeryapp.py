from __future__ import absolute_import, unicode_literals
from celery import Celery
import os

from django.conf import settings


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

celery_app = Celery("project")

celery_app.config_from_object("django.conf:settings", namespace="CELERY")

# celery_app.autodiscover_tasks(["project", "app"])
celery_app.autodiscover_tasks()
