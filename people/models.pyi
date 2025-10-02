"""
Type stubs for people.models

This file provides type hints for the people app models for better
IDE support and type checking.
"""

from __future__ import annotations
from typing import Any, List, Optional, Union, TYPE_CHECKING
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone

from accounts.managers import OrganizationAwareManager, TenantAwareManager

if TYPE_CHECKING:
    from typing import Dict
    from django.db.models import QuerySet
    from accounts.models import TenantAccount, MemberAccount, PaymentHistory
    from organizations.models import Organization

class Contact(models.Model):
    """Contact model for personal information relating to a person"""

    # === ORIGINAL MODEL FIELDS ===
    # Personal Information Fields (per specification)
    first_name: models.CharField
    last_name: models.CharField
    date_of_birth: models.DateField
    address: models.TextField
    mobile_number: models.CharField
    email: models.EmailField

    # Tenant relationship for multi-tenant isolation
    tenant: models.ForeignKey[TenantAccount]

    # Organization relationship for direct organization membership
    organization: models.ForeignKey[Organization]

    # Metadata Fields for auditing and soft delete
    created_at: models.DateTimeField
    updated_at: models.DateTimeField
    is_active: models.BooleanField

    # Organization and tenant-aware managers
    objects: OrganizationAwareManager[Contact]
    all_objects: models.Manager[Contact]
    tenant_objects: TenantAwareManager[Contact]

    # === ORIGINAL MODEL METHODS ===
    def __str__(self) -> str: ...
    def get_full_name(self) -> str: ...
    def get_age(self) -> Optional[int]: ...
    def get_absolute_url(self) -> str: ...
    def clean(self) -> None: ...
    def get_organization(self) -> Optional[Organization]: ...
    def can_access_organization(self, organization: Organization) -> bool: ...
    def get_all_organizations(self) -> List[Organization]: ...



class LoginUser(models.Model):
    """LoginUser model for contacts that can login and manage club membership"""

    # === ORIGINAL MODEL FIELDS ===
    # Relationship Fields
    user: models.OneToOneField[User]
    contact: models.OneToOneField[Contact]

    # Permission Fields for club management
    is_club_owner: models.BooleanField
    is_club_staff: models.BooleanField

    PERMISSION_CHOICES: List[tuple[str, str]]
    permissions_level: models.CharField

    # Additional Fields for club management
    can_create_clubs: models.BooleanField
    can_manage_members: models.BooleanField

    # Metadata
    created_at: models.DateTimeField
    updated_at: models.DateTimeField
    last_login_attempt: models.DateTimeField

    # === ORIGINAL MODEL METHODS ===
    def __str__(self) -> str: ...
    def has_club_permissions(self) -> bool: ...
    def can_manage_club(self, club: Any = None) -> bool: ...
    def get_managed_clubs(self) -> None: ...
    def can_access_organization(self, organization: Organization) -> bool: ...
    def is_organization_admin(self, organization: Organization) -> bool: ...
    def is_organization_owner(self, organization: Organization) -> bool: ...
    def get_organizations(self) -> List[Organization]: ...
    def get_organization_permission_level(self, organization: Organization) -> Optional[str]: ...
    def can_access_tenant(self, tenant: TenantAccount) -> bool: ...
    def get_tenant_account(self) -> Optional[TenantAccount]: ...
    def clean(self) -> None: ...



# === SIGNAL HANDLERS ===
def create_login_user_profile(sender: type[User], instance: User, created: bool, **kwargs: Any) -> None:
    """Create LoginUser profile when User is created (optional)"""
    ...

def sync_user_permissions(sender: type[LoginUser], instance: LoginUser, **kwargs: Any) -> None:
    """Sync Django User permissions with LoginUser permissions"""
    ...