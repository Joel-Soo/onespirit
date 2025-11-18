"""
Production settings for onespirit_project.

This file contains settings specific to production environment.
"""

from .base import *
from pathlib import Path
import os

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# ALLOWED_HOSTS must be set via environment variable in production
_raw_hosts = os.getenv('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(',') if h.strip()]

def _build_csrf_trusted(origins_hosts: list[str]) -> list[str]:
    origins: list[str] = []
    for h in origins_hosts:
        host = h.strip()
        if not host:
            continue
        if host.startswith('*.'):
            # Allow all subdomains
            origins.append(f"https://{host}")
        else:
            origins.append(f"https://{host}")
    return origins


def _read_secret_file(var_name: str) -> str | None:
    """Read a secret value from file pointed by env var (e.g., SECRET_KEY_FILE)."""
    path = os.getenv(var_name)
    if path and os.path.isfile(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception:
            return None
    return None


# Database
# Use environment variables for database configuration in production
_db_password = _read_secret_file('DB_PASSWORD_FILE') or os.getenv('DB_PASSWORD', '')

DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.getenv('DB_NAME', ''),
        'USER': os.getenv('DB_USER', ''),
        'PASSWORD': _db_password,
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}


# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Trust reverse proxy proto header (nginx-proxy)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Cookie SameSite defaults
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# CSRF trusted origins derived from ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS = _build_csrf_trusted(ALLOWED_HOSTS)

# Secret key (prefer docker secret file if provided)
SECRET_KEY = _read_secret_file('SECRET_KEY_FILE') or os.getenv('SECRET_KEY', SECRET_KEY)

# Email configuration (optional password via secret file)
EMAIL_HOST_PASSWORD = _read_secret_file('EMAIL_PASSWORD_FILE') or os.getenv('EMAIL_HOST_PASSWORD', '')


# Caching configuration - use Redis in production
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 10000,
        }
    }
}


# Logging configuration for production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'accounts.middleware': {
            'handlers': ['file', 'console'],
            'level': 'WARNING',
            'propagate': True,
        },
        'accounts.managers': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}


# Static files configuration (align with docker-compose.prod mount /app/static)
STATIC_ROOT = Path('/app/static')


# Tenant-specific settings
TENANT_SETTINGS = {
    # Disable tenant isolation debugging in production
    'DEBUG_TENANT_ISOLATION': False,

    # Cache timeout for tenant lookups (in seconds)
    'TENANT_CACHE_TIMEOUT': 600,  # 10 minutes in production

    # Maximum number of cached tenant entries
    'TENANT_CACHE_MAX_ENTRIES': 1000,

    # Enable tenant access control middleware
    'ENABLE_TENANT_ACCESS_CONTROL': True,
}
