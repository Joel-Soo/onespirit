"""
Tenant context middleware for automatic tenant detection and isolation.

This middleware automatically detects the tenant from the request (subdomain or URL path)
and sets the tenant context for automatic filtering throughout the application.
"""

import logging

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied

from .managers import TenantCacheManager, set_current_tenant
from .models import TenantAccount

logger = logging.getLogger(__name__)


class TenantContextMiddleware:
    """
    Middleware to automatically set tenant context from subdomain or URL.

    This middleware integrates with the existing TenantAccount.tenant_slug field
    and provides automatic tenant resolution without breaking existing functionality.

    Tenant detection order:
    1. Subdomain (e.g., club1.onespirit.com -> tenant_slug='club1')
    2. URL path (e.g., /tenant/club1/... -> tenant_slug='club1')
    3. Session-based tenant selection (for admin interfaces)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Clear any previous tenant context
        set_current_tenant(None)

        # Detect and set tenant context
        tenant = self.get_tenant_from_request(request)
        if tenant:
            set_current_tenant(tenant)
            request.tenant = tenant
            logger.debug(f"Set tenant context: {tenant.tenant_slug}")
        else:
            request.tenant = None

        # Process the request
        response = self.get_response(request)
        return response

    def get_tenant_from_request(self, request):
        """
        Extract tenant from request using multiple detection strategies.

        Args:
            request: Django HttpRequest object

        Returns:
            TenantAccount instance or None if no tenant detected/valid
        """
        tenant = None

        # Strategy 1: Extract from subdomain (e.g., club1.onespirit.com)
        tenant = self._get_tenant_from_subdomain(request)
        if tenant:
            return tenant

        # Strategy 2: Extract from URL path (e.g., /tenant/club1/...)
        tenant = self._get_tenant_from_path(request)
        if tenant:
            return tenant

        # Strategy 3: Get from session (for admin tenant selection)
        tenant = self._get_tenant_from_session(request)
        if tenant:
            return tenant

        return None

    def _get_tenant_from_subdomain(self, request):
        """
        Extract tenant from subdomain.

        Examples:
        - club1.onespirit.com -> tenant_slug='club1'
        - www.onespirit.com -> None (main site)
        - onespirit.com -> None (main site)
        """
        host = request.get_host().lower()

        # Skip localhost and IP addresses for development
        if host.startswith(("localhost", "127.0.0.1", "0.0.0.0")):
            return None

        # Extract subdomain
        parts = host.split(".")
        if len(parts) >= 3:  # e.g., ['club1', 'onespirit', 'com']
            subdomain = parts[0]

            # Skip common subdomains that aren't tenants
            if subdomain in ["www", "api", "admin", "static", "media"]:
                return None

            # Look up tenant by slug using cache
            tenant = TenantCacheManager.get_tenant_by_slug(subdomain)
            if tenant:
                logger.info(f"Tenant detected from subdomain: {subdomain}")
                return tenant

        return None

    def _get_tenant_from_path(self, request):
        """
        Extract tenant from URL path.

        Examples:
        - /tenant/club1/members/ -> tenant_slug='club1'
        - /tenant/club1/admin/ -> tenant_slug='club1'
        - /admin/ -> None (global admin)
        """
        path_parts = request.path.strip("/").split("/")

        # Check for /tenant/{slug}/ pattern
        if len(path_parts) >= 2 and path_parts[0] == "tenant":
            tenant_slug = path_parts[1]

            # Look up tenant by slug using cache
            tenant = TenantCacheManager.get_tenant_by_slug(tenant_slug)
            if tenant:
                logger.info(f"Tenant detected from URL path: {tenant_slug}")
                return tenant
            else:
                # Invalid tenant slug in URL - this might be a 404
                logger.warning(f"Invalid tenant slug in URL: {tenant_slug}")

        return None

    def _get_tenant_from_session(self, request):
        """
        Get tenant from session (used for admin tenant selection).

        This allows admin users to select a specific tenant to work with
        when accessing the admin interface.
        """
        if not hasattr(request, "session"):
            return None

        tenant_id = request.session.get("selected_tenant_id")
        if tenant_id:
            try:
                tenant = TenantAccount.objects.get(id=tenant_id, is_active=True)
                logger.debug(f"Tenant from session: {tenant.tenant_slug}")
                return tenant
            except TenantAccount.DoesNotExist:
                # Clean up invalid session data
                request.session.pop("selected_tenant_id", None)
                logger.warning(f"Invalid tenant ID in session: {tenant_id}")

        return None


class AdminTenantContextMiddleware:
    """
    Enhanced middleware specifically for Django admin tenant context.

    This middleware handles tenant selection in the admin interface,
    allowing superusers to switch between tenants for management purposes.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only process admin requests
        if request.path.startswith("/admin/") and request.user.is_authenticated:
            self._handle_admin_tenant_selection(request)

        response = self.get_response(request)
        return response

    def _handle_admin_tenant_selection(self, request):
        """
        Handle tenant selection in admin interface.

        This allows admin users to select which tenant they want to manage,
        storing the selection in the session for persistence across requests.
        """
        # Handle tenant selection form submission
        if request.method == "POST" and "admin_tenant_selection" in request.POST:
            tenant_id = request.POST.get("selected_tenant")
            if tenant_id:
                try:
                    tenant = TenantAccount.objects.get(id=tenant_id, is_active=True)
                    request.session["selected_tenant_id"] = tenant.id
                    logger.info(f"Admin selected tenant: {tenant.tenant_slug}")
                except TenantAccount.DoesNotExist:
                    request.session.pop("selected_tenant_id", None)
            else:
                # Clear tenant selection (view all tenants)
                request.session.pop("selected_tenant_id", None)
                logger.info("Admin cleared tenant selection")

        # Set tenant context from session
        tenant_id = request.session.get("selected_tenant_id")
        if tenant_id:
            try:
                tenant = TenantAccount.objects.get(id=tenant_id, is_active=True)
                set_current_tenant(tenant)
                request.tenant = tenant
            except TenantAccount.DoesNotExist:
                request.session.pop("selected_tenant_id", None)


class TenantAccessControlMiddleware:
    """
    Middleware to enforce tenant-based access control.

    This middleware ensures that users can only access data for tenants
    they have permission to view, providing an additional security layer.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Apply access control if tenant is detected and user is authenticated
        if (
            hasattr(request, "tenant")
            and request.tenant
            and not isinstance(request.user, AnonymousUser)
        ):
            if not self._user_can_access_tenant(request.user, request.tenant):
                logger.warning(
                    f"Access denied: User {request.user.username} "
                    f"attempted to access tenant {request.tenant.tenant_slug}"
                )
                raise PermissionDenied(
                    "You don't have permission to access this tenant."
                )

        response = self.get_response(request)
        return response

    def _user_can_access_tenant(self, user, tenant):
        """
        Check if user has permission to access the specified tenant.

        Args:
            user: Django User instance
            tenant: TenantAccount instance

        Returns:
            bool: True if user can access tenant, False otherwise
        """
        # Superusers can access any tenant
        if user.is_superuser:
            return True

        # Check if user is associated with the tenant through Contact/UserProfile
        try:
            from people.models import UserProfile

            user_profile = UserProfile.objects.get(user=user)

            # Use the utility method if available
            if hasattr(user_profile, "can_access_tenant"):
                return user_profile.can_access_tenant(tenant)

            # Fallback: check if user has any account in this tenant
            from accounts import services as acct_svc

            user_tenant = acct_svc.get_tenant_account_for_userprofile(user_profile)
            return user_tenant == tenant

        except UserProfile.DoesNotExist:
            pass

        # Default: deny access
        return False
