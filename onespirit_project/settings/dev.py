"""
Development settings for onespirit_project.

This file contains settings specific to development environment.
"""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    # Test hosts for middleware testing
    'middleware-test.onespirit.com',
    'integration1.onespirit.com',
    'integration2.onespirit.com',
    'cache-test.onespirit.com',
    # Wildcard for subdomains in testing
    '*.onespirit.com',
]


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Caching configuration for tenant management
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'onespirit-cache',
        'TIMEOUT': 300,  # 5 minutes default
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}


# Logging configuration for tenant debugging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'accounts.middleware': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'accounts.managers': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}


# Tenant-specific settings
TENANT_SETTINGS = {
    # Enable tenant isolation debugging in development
    'DEBUG_TENANT_ISOLATION': DEBUG,

    # Cache timeout for tenant lookups (in seconds)
    'TENANT_CACHE_TIMEOUT': 300,

    # Maximum number of cached tenant entries
    'TENANT_CACHE_MAX_ENTRIES': 100,

    # Enable tenant access control middleware
    'ENABLE_TENANT_ACCESS_CONTROL': True,
}
