import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)
class KeywordSuggestionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'keyword_suggestion'

    def ready(self):
        """
        Called once at server startup after all apps are loaded.

        We guard with a try/except so a missing model file doesn't
        crash the entire Django server during development (before
        train_model.py has been run).
        """
        # Avoid running during management commands like migrate, shell, etc.
        import sys
        if "runserver" not in sys.argv and "gunicorn" not in sys.argv[0]:
            return

        try:
            from ml_models.keyword_engine import preload_model
            preload_model()
        except FileNotFoundError as e:
            logger.warning(
                f"Keyword model not found at startup — "
                f"run ml_models/train_model.py first. ({e})"
            )
        except Exception as e:
            logger.error(f"Failed to preload keyword model: {e}")
