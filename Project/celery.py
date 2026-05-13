import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Project.settings")

app = Celery("Project")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover tasks in all installed apps
app.autodiscover_tasks()