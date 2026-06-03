import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Project.settings")

app = Celery("Project")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover tasks in all installed apps
app.autodiscover_tasks()

# Prevent Celery from connecting to the broker on Django startup/import.
# Connection happens only when a task is actually dispatched.
app.conf.update(
    broker_connection_retry_on_startup=False,
    task_always_eager=os.environ.get("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true",
)