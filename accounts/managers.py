"""
Custom managers for tenant-aware operations.

This module provides automatic tenant filtering capabilities while preserving
the existing manual multi-tenant implementation. It enhances the current system
without breaking any existing functionality.
"""

from __future__ import annotations
from typing import Any, Optional, TYPE_CHECKING
from contextvars import ContextVar
from datetime import timedelta

from django.db import models
from django.db.models import Q
from django.core.cache import cache
from django.utils import timezone

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from accounts.models import TenantAccount, MemberAccount
    from organizations.models import Organization


# Thread-safe context variable for current tenant
_current_tenant: ContextVar[Optional[TenantAccount]] = ContextVar('current_tenant', default=None)


def set_current_tenant(tenant: Optional[TenantAccount]) -> None:
    """
    Set the current tenant in context.

    Args:
        tenant: TenantAccount instance or None to clear context
    """
    _current_tenant.set(tenant)


def get_current_tenant() -> Optional[TenantAccount]:
    """
    Get the current tenant from context.

    Returns:
        TenantAccount instance or None if no tenant is set
    """
    return _current_tenant.get()


class TenantAwareManager(models.Manager):
    """
    Base manager that automatically filters by current tenant.
    
    This manager provides automatic tenant isolation while preserving
    the ability to bypass filtering when needed using all_objects.
    """
    
    def get_queryset(self) -> QuerySet[Any]:
        """Override to add automatic tenant filtering when context is set."""
        queryset = super().get_queryset()
        tenant = get_current_tenant()

        # Only apply tenant filtering if:
        # 1. We have a current tenant in context
        # 2. The model has a 'tenant' field
        if tenant and hasattr(self.model, 'tenant'):
            return queryset.filter(tenant=tenant)

        return queryset


class MemberAccountManager(TenantAwareManager):
    """
    Enhanced manager for MemberAccount with tenant-aware filtering.
    
    Provides convenient methods for common queries while maintaining
    automatic tenant isolation from TenantAwareManager.
    """
    
    def get_active(self) -> QuerySet[MemberAccount]:
        """Get active member accounts for the current tenant."""
        return self.get_queryset().filter(is_active=True)
    
    def get_by_membership_type(self, membership_type: str) -> QuerySet[MemberAccount]:
        """
        Get member accounts filtered by membership type.

        Args:
            membership_type: The membership type to filter by

        Returns:
            QuerySet of MemberAccount instances
        """
        return self.get_queryset().filter(membership_type=membership_type)
    
    def get_expiring_soon(self, days: int = 30) -> QuerySet[MemberAccount]:
        """
        Get member accounts expiring within specified days.

        Args:
            days: Number of days to look ahead (default: 30)

        Returns:
            QuerySet of MemberAccount instances expiring soon
        """
        from django.utils import timezone

        expiry_date = timezone.now().date() + timedelta(days=days)
        return self.get_queryset().filter(
            membership_end_date__lte=expiry_date,
            membership_end_date__gte=timezone.now().date(),
            is_active=True
        )
    
    def get_by_status(self, status: str) -> QuerySet[MemberAccount]:
        """
        Get member accounts by membership status.

        Status values:
        - 'inactive': Members with is_active=False
        - 'expired': Active members with membership_end_date in the past
        - 'active': Active members with valid membership (no end date or future end date)

        Args:
            status: The membership status to filter by

        Returns:
            QuerySet of MemberAccount instances matching the status
        """
        today = timezone.now().date()

        if status == "inactive":
            return self.get_queryset().filter(is_active=False)
        elif status == "expired":
            return self.get_queryset().filter(
                is_active=True,
                membership_end_date__isnull=False,
                membership_end_date__lt=today
            )
        elif status == "active":
            return self.get_queryset().filter(
                is_active=True
            ).filter(
                Q(membership_end_date__isnull=True) | Q(membership_end_date__gte=today)
            )
        else:
            # Invalid status - return empty queryset
            return self.get_queryset().none()


class TenantCacheManager:
    """
    Cache manager for tenant lookups to improve performance.
    
    Provides caching for frequently accessed tenant data to reduce
    database queries for tenant resolution.
    """
    
    CACHE_TIMEOUT = 300  # 5 minutes
    
    @classmethod
    def get_tenant_by_slug(cls, slug: str) -> Optional[TenantAccount]:
        """
        Get tenant by slug with caching.

        Args:
            slug: The tenant slug to look up

        Returns:
            TenantAccount instance or None if not found
        """
        cache_key = f'tenant_slug_{slug}'
        tenant = cache.get(cache_key)

        if not tenant:
            try:
                # Import here to avoid circular imports
                from .models import TenantAccount
                tenant = TenantAccount.objects.select_related('primary_contact').get(
                    tenant_slug=slug,
                    is_active=True
                )
                cache.set(cache_key, tenant, cls.CACHE_TIMEOUT)
            except TenantAccount.DoesNotExist:
                # Cache the None result to avoid repeated DB hits
                cache.set(cache_key, None, cls.CACHE_TIMEOUT)
                return None

        return tenant
    
    @classmethod
    def invalidate_tenant_cache(cls, slug: str) -> None:
        """
        Invalidate cached tenant data.

        Args:
            slug: The tenant slug to invalidate
        """
        cache_key = f'tenant_slug_{slug}'
        cache.delete(cache_key)
    
    @classmethod
    def get_tenant_stats(cls, tenant_id: int) -> Optional[dict[str, Any]]:
        """
        Get cached tenant statistics.

        Args:
            tenant_id: The tenant ID to get stats for

        Returns:
            Dict with tenant statistics or None
        """
        cache_key = f'tenant_stats_{tenant_id}'
        stats = cache.get(cache_key)

        if not stats:
            # Import here to avoid circular imports
            from .models import TenantAccount, MemberAccount

            try:
                tenant = TenantAccount.objects.get(id=tenant_id)
                member_count = MemberAccount.all_objects.filter(
                    tenant=tenant, is_active=True
                ).count()

                stats = {
                    'member_count': member_count,
                    'member_utilization': (member_count / tenant.max_member_accounts * 100)
                                        if tenant.max_member_accounts > 0 else 0,
                    'subscription_status': tenant.get_subscription_status(),
                }
                cache.set(cache_key, stats, cls.CACHE_TIMEOUT)
            except TenantAccount.DoesNotExist:
                return None

        return stats
    
    @classmethod
    def invalidate_tenant_stats(cls, tenant_id: int) -> None:
        """
        Invalidate cached tenant statistics.

        Args:
            tenant_id: The tenant ID to invalidate stats for
        """
        cache_key = f'tenant_stats_{tenant_id}'
        cache.delete(cache_key)


# Organization context variables for dual tenant+organization filtering
_current_organization: ContextVar[Optional[Organization]] = ContextVar('current_organization', default=None)


def set_current_organization(organization: Optional[Organization]) -> None:
    """
    Set the current organization in context.

    Args:
        organization: Organization instance or None to clear context
    """
    _current_organization.set(organization)


def get_current_organization() -> Optional[Organization]:
    """
    Get the current organization from context.

    Returns:
        Organization instance or None if no organization is set
    """
    return _current_organization.get()


class OrganizationAwareManager(TenantAwareManager):
    """
    Manager with both tenant and organization awareness.
    
    This manager extends TenantAwareManager to provide automatic filtering
    by both tenant and organization when contexts are set.
    """
    
    def get_queryset(self) -> QuerySet[Any]:
        """Override to add automatic dual filtering when contexts are set."""
        queryset = super().get_queryset()  # Gets tenant filtering from parent
        organization = get_current_organization()

        # Only apply organization filtering if:
        # 1. We have a current organization in context
        # 2. The model has an 'organization' field
        if organization and hasattr(self.model, 'organization'):
            return queryset.filter(organization=organization)

        return queryset
    
    def for_organization(self, organization: Organization) -> QuerySet[Any]:
        """
        Get records for specific organization.

        Args:
            organization: Organization instance to filter by

        Returns:
            QuerySet filtered by organization (still respects tenant filtering)
        """
        return self.get_queryset().filter(organization=organization)
    
    def organization_members(self, organization: Organization) -> QuerySet[Any]:
        """
        Get organization members (alias for for_organization).

        Args:
            organization: Organization instance

        Returns:
            QuerySet of organization members
        """
        return self.for_organization(organization)
    
    def cross_tenant_organization_lookup(self, organization: Organization) -> QuerySet[Any]:
        """
        Get organization members across tenants (bypasses tenant filtering).

        Args:
            organization: Organization instance

        Returns:
            QuerySet of all organization members regardless of tenant
        """
        # Use all_objects to bypass tenant filtering, then filter by organization
        return self.model.all_objects.filter(organization=organization)