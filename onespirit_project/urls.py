"""
URL configuration for onespirit_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.conf import settings
from django.conf.urls.static import static


def health_view(_request):
    """
    Health check endpoint for Docker/Kubernetes liveness monitoring.
    Verifies critical runtime dependencies: database and cache.
    Returns 200 if healthy, 503 if any component fails.
    """
    health_status = {
        "status": "healthy",
        "checks": {}
    }
    is_healthy = True

    # Check database connectivity
    try:
        connection.ensure_connection()
        health_status["checks"]["database"] = "connected"
    except Exception as e:
        health_status["checks"]["database"] = f"failed: {str(e)}"
        is_healthy = False

    # Check cache (Redis) connectivity
    try:
        cache.set("health_check", "ok", timeout=10)
        if cache.get("health_check") == "ok":
            health_status["checks"]["cache"] = "connected"
        else:
            health_status["checks"]["cache"] = "failed: unable to read"
            is_healthy = False
    except Exception as e:
        health_status["checks"]["cache"] = f"failed: {str(e)}"
        is_healthy = False

    if not is_healthy:
        health_status["status"] = "unhealthy"
        return JsonResponse(health_status, status=503)
    
    return JsonResponse(health_status)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('people/', include('people.urls')),
    path('health/', health_view),
]

# Serve media files in development
# In production, nginx serves these directly from the volume mount
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
