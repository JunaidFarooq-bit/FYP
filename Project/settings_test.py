"""
Django settings for testing environment.
"""

from .settings import *

# Test Database Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # In-memory database for speed
        'TEST': {
            'NAME': ':memory:',
        },
    }
}

# Alternative: Use PostgreSQL for tests (uncomment if needed)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'weblift_test',
#         'USER': 'postgres',
#         'PASSWORD': 'postgres',
#         'HOST': 'localhost',
#         'PORT': '5432',
#         'TEST': {
#             'NAME': 'weblift_test',
#         },
#     }
# }

# pgvector configuration for tests
if DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
    INSTALLED_APPS = list(INSTALLED_APPS) + ['pgvector']

# Celery Configuration for Tests
CELERY_TASK_ALWAYS_EAGER = True  # Run tasks synchronously in tests
CELERY_TASK_EAGER_PROPAGATES = True  # Propagate exceptions
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache'
CELERY_CACHE_BACKEND = 'memory'

# Cache Configuration for Tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache',
    }
}

# Media and Static Files for Tests
MEDIA_ROOT = BASE_DIR / 'test_media'
STATIC_ROOT = BASE_DIR / 'test_static'

# Email Backend for Tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Logging Configuration for Tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'ERROR',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['null'],
            'propagate': False,
        },
        'SEOAnalyzer': {
            'handlers': ['console'],
            'level': 'ERROR',
        },
        'keyword_ai': {
            'handlers': ['console'],
            'level': 'ERROR',
        },
        'comparative_analysis': {
            'handlers': ['console'],
            'level': 'ERROR',
        },
        'subscriptions': {
            'handlers': ['console'],
            'level': 'ERROR',
        },
    },
}

# Security Settings for Tests
DEBUG = False
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# API Keys for Testing (dummy values)
GROQ_API_KEY = 'test-groq-api-key'
OPENROUTER_API_KEY = 'test-openrouter-api-key'
OPENAI_API_KEY = 'test-openai-api-key'
MOZ_ACCESS_ID = 'test-moz-id'
MOZ_SECRET_KEY = 'test-moz-secret'
PINECONE_API_KEY = 'test-pinecone-key'
PINECONE_ENVIRONMENT = 'test'
USE_PINECONE = False  # Disable Pinecone in tests, use pgvector fallback

# Password Hashing for Tests (speed up tests)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Template Debug
TEMPLATE_DEBUG = False

# Disable Migrations for Tests (optional - speeds up tests)
# class DisableMigrations:
#     def __contains__(self, item):
#         return True
#     def __getitem__(self, item):
#         return None
# 
# MIGRATION_MODULES = DisableMigrations()

# Test Fixtures
FIXTURE_DIRS = [
    BASE_DIR / 'fixtures',
]

# Site URL for tests
SITE_URL = 'http://localhost:8000'

# Bank Details for Tests (dummy)
BANK_NAME = 'Test Bank'
BANK_ACCOUNT_NAME = 'WebLift Test'
BANK_ACCOUNT_NUMBER = 'TEST-1234-5678'
BANK_IBAN = 'TEST1234567890'
BANK_SWIFT = 'TESTSWIFT'
BANK_BRANCH = 'Test Branch'
BANK_COUNTRY = 'Test Country'
