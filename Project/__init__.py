import os

# Only import Celery app when running as a Celery worker/beat process.
# This prevents Django runserver from probing the broker on startup.
if os.environ.get("RUN_CELERY", "false").lower() == "true":
    from .celery import app as celery_app
    __all__ = ("celery_app",)
else:
    __all__ = ()