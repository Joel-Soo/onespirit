from __future__ import annotations

import contextvars
from typing import TYPE_CHECKING

from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.core.validators import URLValidator
from django.db import models
from django.urls import reverse
from organizations.models import Organization

from accounts.managers import TenantAwareManager, get_current_tenant

# Context variable for current user (similar to tenant context)
_current_user: contextvars.ContextVar = contextvars.ContextVar(
    "current_user", default=None
)


def set_current_user(user):
    """Set the current user in context for filtering."""
    _current_user.set(user)


def get_current_user():
    """Get the current user from context."""
    return _current_user.get()


if TYPE_CHECKING:
    pass


class ClubRelatedManager(models.Manager):
    """
    Manager for models related to Club that need tenant isolation via club.tenant.

    This manager provides tenant filtering for through models (ClubStaff, ClubMember, etc.)
    that don't have direct tenant fields but need tenant isolation through their club relationship.

    Additionally, it provides user-based filtering so that club staff can only see entities
    related to clubs where they have staff assignments.
    """

    def get_queryset(self):
        """Filter by current tenant and user context via club relationships."""
        queryset = super().get_queryset()
        tenant = get_current_tenant()
        user = get_current_user()

        # Apply tenant filtering if we have a current tenant in context
        if tenant:
            queryset = queryset.filter(club__tenant=tenant)

        # Apply user-based club filtering if we have a current user AND tenant in context
        # Only applies to models that have a 'club' field (ClubStaff, ClubMember, etc.)
        # User filtering is only enabled when tenant context is set to avoid cross-tenant data leakage
        if (
            user
            and tenant  # Only apply user filtering when tenant context is set
            and hasattr(self.model, "_meta")
            and hasattr(self.model._meta, "get_field")
        ):
            try:
                # Check if this model has a 'club' field and ensure it's a ForeignKey
                # User-based filtering should only apply to models that have a 'club' field (like ClubStaff, ClubMember)
                # Skip user filtering for models that don't have a 'club' field
                club_field = self.model._meta.get_field("club")
                if not isinstance(club_field, models.ForeignKey):
                    # Skip user filtering if 'club' exists but isn't a ForeignKey relationship
                    return queryset

                # Get LoginUser instance from Django User
                try:
                    from people.models import LoginUser

                    login_user = LoginUser.objects.get(user=user)

                    # Check if user is superuser or has system-wide admin permissions
                    if user.is_superuser or login_user.permissions_level == "admin":
                        # Superusers and system admins see all (within tenant scope)
                        pass
                    else:
                        # Regular users: only see entities from clubs where they have staff assignments
                        # Use all_objects to avoid circular manager calls while staying DB-agnostic
                        user_club_ids = list(
                            ClubStaff.all_objects.filter(
                                contact__login_user=login_user, is_active=True
                            ).values_list("club_id", flat=True)
                        )

                        if user_club_ids:
                            queryset = queryset.filter(club_id__in=user_club_ids)
                        else:
                            # User has no club assignments: return empty queryset
                            queryset = queryset.none()

                except LoginUser.DoesNotExist:
                    # User has no LoginUser profile: return empty queryset
                    queryset = queryset.none()

            except FieldDoesNotExist:
                # Model doesn't have a 'club' field: skip user filtering
                pass

        # When no tenant context: return queryset (possibly user-filtered)
        # This allows admin operations and system maintenance tasks to operate across tenants
        return queryset


class ClubAffiliationManager(models.Manager):
    """
    Manager for ClubAffiliation that filters by tenant via club_primary.tenant.

    ClubAffiliation has two club fields (club_primary, club_secondary), so we filter
    by the primary club's tenant to ensure tenant isolation.
    """

    def get_queryset(self):
        """Filter by current tenant via club_primary.tenant relationship."""
        queryset = super().get_queryset()
        tenant = get_current_tenant()

        # Only apply tenant filtering if we have a current tenant in context
        if tenant:
            return queryset.filter(club_primary__tenant=tenant)

        return queryset


class Club(Organization):
    """
    Club model inheriting from Organization for martial arts club operations.

    As specified: "Club: a type of Organization"

    Relationships:
    - Inherits from Organization (django-organizations)
    - Foreign key to TenantAccount (multi-tenant isolation)
    - Members via Contact.organization relationship (people_contacts)
    - Staff via ClubStaff through model
    """

    # Tenant relationship for multi-tenant isolation
    tenant = models.ForeignKey(
        "accounts.TenantAccount",
        on_delete=models.CASCADE,
        related_name="clubs",
        help_text="Tenant for multi-tenant isolation",
    )

    # Club profile information
    description = models.TextField(blank=True)
    founded_date = models.DateField(null=True, blank=True)

    # Contact information
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    # Address fields
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default="United States")

    # Social media profiles
    facebook_url = models.URLField(blank=True, validators=[URLValidator()])
    instagram_handle = models.CharField(max_length=100, blank=True)
    twitter_handle = models.CharField(max_length=100, blank=True)
    youtube_url = models.URLField(blank=True, validators=[URLValidator()])
    linkedin_url = models.URLField(blank=True, validators=[URLValidator()])

    # Club settings
    is_public = models.BooleanField(default=True)
    max_members = models.PositiveIntegerField(null=True, blank=True)

    # Additional timestamps (Organization already has created/modified)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Managers
    objects = TenantAwareManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "clubs_club"
        indexes = [
            models.Index(fields=["tenant"]),
            models.Index(fields=["founded_date"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(max_members__gte=1) | models.Q(max_members__isnull=True),
                name="positive_max_members",
            ),
        ]
        verbose_name = "Club"
        verbose_name_plural = "Clubs"
        ordering = ["name"]

    def clean(self):
        """Model-level validation"""
        super().clean()

        # Validate unique club name per tenant (use unfiltered manager to avoid context interference)
        if (
            Club.all_objects.filter(name=self.name, tenant=self.tenant)
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError("Club name already exists in this tenant")

        # Social media handle validation (simple rule: should not start with '@')
        if self.instagram_handle and self.instagram_handle.startswith("@"):
            raise ValidationError({"instagram_handle": "Handle should not start with '@'"})
        if self.twitter_handle and self.twitter_handle.startswith("@"):
            raise ValidationError({"twitter_handle": "Handle should not start with '@'"})

        # Validate tenant quota (only if quota is set and positive)
        if not self.pk and getattr(self.tenant, "max_clubs", None):
            try:
                max_allowed = int(self.tenant.max_clubs)
            except (TypeError, ValueError):
                max_allowed = None
            if max_allowed and max_allowed > 0:
                current_count = Club.all_objects.filter(tenant=self.tenant).count()
                if current_count >= max_allowed:
                    raise ValidationError(
                        f"Club quota exceeded. Maximum {max_allowed} clubs allowed."
                    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def member_count(self):
        """Return count of members in this club (via Contact.organization relationship)"""
        return self.people_contacts.filter(is_active=True).count()

    @property
    def staff_count(self):
        """Return count of staff in this club"""
        return self.staff_assignments.filter(is_active=True).count()

    def get_absolute_url(self):
        return reverse("clubs:detail", kwargs={"slug": self.slug})


class ClubStaff(models.Model):
    """
    Through model for managing club staff with roles and permissions.
    Links LoginUser to Club with specific role assignments.
    """

    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("admin", "Administrator"),
        ("instructor", "Instructor"),
        ("assistant", "Assistant"),
    ]

    club = models.ForeignKey(
        Club, on_delete=models.CASCADE, related_name="staff_assignments"
    )

    contact = models.ForeignKey(
        "people.Contact", on_delete=models.CASCADE, related_name="club_assignments"
    )

    organization_user = models.OneToOneField(
        "organizations.OrganizationUser",
        on_delete=models.CASCADE,
        related_name="club_staff_assignment",
        null=True,
        blank=True,
        help_text="Link to Organization User for django-organizations integration",
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="instructor")

    # Staff details
    title = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    specialties = models.TextField(blank=True)

    # Status and permissions
    is_active = models.BooleanField(default=True)
    can_manage_members = models.BooleanField(default=False)
    can_manage_schedule = models.BooleanField(default=False)
    can_view_finances = models.BooleanField(default=False)

    # Timestamps
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Managers
    objects = ClubRelatedManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "clubs_clubstaff"
        indexes = [
            models.Index(fields=["club", "is_active"]),
            models.Index(fields=["contact", "is_active"]),
            models.Index(fields=["role"]),
            models.Index(fields=["organization_user"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["club", "contact"], name="unique_staff_assignment_per_club"
            ),
            # Note: organization_user already has unique constraint from OneToOneField
        ]
        verbose_name = "Club Staff"
        verbose_name_plural = "Club Staff"
        ordering = ["role", "assigned_at"]

    def __str__(self):
        return f"{self.contact.get_full_name()} - {self.get_role_display()} at {self.club}"

    def clean(self):
        """Validate staff assignment"""
        super().clean()

        # Ensure staff contact has login_user and can access club tenant
        if not hasattr(self.contact, "login_user") or not self.contact.login_user:
            raise ValidationError("Staff contact must have an associated login user")

        if hasattr(self.contact.login_user, "can_access_tenant") and not self.contact.login_user.can_access_tenant(
            self.club.tenant
        ):
            raise ValidationError("Staff user cannot access club tenant")

        # Validate OrganizationUser consistency if provided
        if self.organization_user:
            # Ensure Django User matches between LoginUser and OrganizationUser
            if self.contact.login_user.user != self.organization_user.user:
                raise ValidationError(
                    "OrganizationUser must belong to the same Django User as the LoginUser"
                )

            # Ensure Organization matches Club (since Club inherits from Organization)
            if self.organization_user.organization != self.club:
                raise ValidationError(
                    "OrganizationUser must belong to the same Organization as the Club"
                )

        # Validate role-based permissions
        if self.role == "owner":
            self.can_manage_members = True
            self.can_manage_schedule = True
            self.can_view_finances = True
        elif self.role == "admin":
            self.can_manage_members = True
            self.can_manage_schedule = True

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_organization_user(self):
        """Get the associated OrganizationUser if it exists."""
        return self.organization_user

    def sync_with_organization(self):
        """Sync permissions with organization-level permissions."""
        if self.organization_user and self.organization_user.is_admin:
            # Organization admins get elevated club permissions
            self.can_manage_members = True
            self.can_manage_schedule = True
            if self.role in ["owner", "admin"]:
                self.can_view_finances = True

    def is_organization_admin(self):
        """Check if the user is an organization admin."""
        return self.organization_user and self.organization_user.is_admin

    def get_permission_hierarchy_level(self):
        """Get the permission hierarchy level for this staff assignment."""
        if self.contact.login_user.user.is_superuser:
            return 100  # Superuser
        if self.is_organization_admin():
            return 90  # Organization admin
        if self.role == "owner":
            return 80  # Club owner
        if self.role == "admin":
            return 70  # Club admin
        if self.role == "instructor":
            return 50  # Instructor
        if self.role == "assistant":
            return 30  # Assistant
        return 10  # Basic staff

    def can_manage_staff_member(self, other_staff):
        """Check if this staff member can manage another staff member."""
        if not isinstance(other_staff, ClubStaff):
            return False
        if other_staff.club != self.club:
            return False  # Can only manage staff in same club

        # Higher hierarchy level can manage lower level
        return (
            self.get_permission_hierarchy_level()
            > other_staff.get_permission_hierarchy_level()
        )


class ClubAffiliation(models.Model):
    """
    Model for managing relationships between clubs (partnerships, branches, etc.)
    """

    AFFILIATION_TYPES = [
        ("branch", "Branch Location"),
        ("partner", "Partner Club"),
        ("association", "Association Member"),
    ]

    club_primary = models.ForeignKey(
        Club, on_delete=models.CASCADE, related_name="affiliations_as_primary"
    )

    club_secondary = models.ForeignKey(
        Club, on_delete=models.CASCADE, related_name="affiliations_as_secondary"
    )

    affiliation_type = models.CharField(
        max_length=20, choices=AFFILIATION_TYPES, default="partner"
    )

    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    # Timestamps
    established_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Managers
    objects = ClubAffiliationManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "clubs_clubaffiliation"
        indexes = [
            models.Index(fields=["club_primary", "is_active"]),
            models.Index(fields=["affiliation_type"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["club_primary", "club_secondary"],
                name="unique_club_affiliation",
            ),
            models.CheckConstraint(
                check=~models.Q(club_primary=models.F("club_secondary")),
                name="no_self_affiliation",
            ),
        ]
        verbose_name = "Club Affiliation"
        verbose_name_plural = "Club Affiliations"
        ordering = ["established_at"]

    def __str__(self):
        return f"{self.club_primary} - {self.get_affiliation_type_display()} - {self.club_secondary}"

    def clean(self):
        """Validate affiliation"""
        super().clean()

        # Prevent self-affiliation
        if self.club_primary == self.club_secondary:
            raise ValidationError("Club cannot affiliate with itself")

        # Check for reverse affiliation (prevent duplicates)
        if (
            ClubAffiliation.objects.filter(
                club_primary=self.club_secondary, club_secondary=self.club_primary
            )
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError("Reverse affiliation already exists")

        # Enforce same-tenant affiliation to prevent cross-tenant relationships
        if self.club_primary.tenant_id != self.club_secondary.tenant_id:
            raise ValidationError("Affiliated clubs must belong to the same tenant")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ClubMember(models.Model):
    """
    Through model linking MemberAccount to Club for billing/membership tracking.
    Complements Contact.organization relationship with account-level tracking.
    """

    MEMBERSHIP_STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("suspended", "Suspended"),
        ("pending", "Pending Approval"),
    ]

    club = models.ForeignKey(
        Club, on_delete=models.CASCADE, related_name="member_accounts"
    )

    member_account = models.ForeignKey(
        "accounts.MemberAccount",
        on_delete=models.CASCADE,
        related_name="club_memberships",
    )

    # Membership details
    membership_number = models.CharField(max_length=50, blank=True)
    status = models.CharField(
        max_length=20, choices=MEMBERSHIP_STATUS_CHOICES, default="active"
    )

    # Membership dates
    joined_date = models.DateField(auto_now_add=True)
    renewal_date = models.DateField(null=True, blank=True)
    last_payment_date = models.DateField(null=True, blank=True)

    # Emergency contact info (moved from Contact model per TODO - people/models.py Lines 46-58)
    emergency_contact_name = models.CharField(
        max_length=100, blank=True, help_text="Name of emergency contact"
    )
    emergency_contact_phone = models.CharField(
        max_length=20, blank=True, help_text="Phone number for emergency contact"
    )
    emergency_contact_relationship = models.CharField(
        max_length=50,
        blank=True,
        help_text="Relationship to member (parent, spouse, etc.)",
    )

    # Medical information (moved from Contact model per TODO - people/models.py Lines 60-67)
    medical_conditions = models.TextField(
        blank=True, help_text="Any medical conditions relevant to training"
    )
    medical_clearance_date = models.DateField(
        null=True, blank=True, help_text="Date of last medical clearance (if required)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Managers
    objects = ClubRelatedManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "clubs_clubmember"
        indexes = [
            models.Index(fields=["club", "status"]),
            models.Index(fields=["member_account"]),
            models.Index(fields=["membership_number"]),
            models.Index(fields=["joined_date"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["club", "member_account"], name="unique_member_per_club"
            ),
            models.UniqueConstraint(
                fields=["club", "membership_number"],
                name="unique_membership_number_per_club",
                condition=models.Q(
                    membership_number__isnull=False, membership_number__gt=""
                ),
            ),
        ]
        verbose_name = "Club Member"
        verbose_name_plural = "Club Members"
        ordering = ["joined_date"]

    def __str__(self):
        return f"{self.member_account.member_contact.get_full_name()} - {self.club}"

    def clean(self):
        """Validate club membership"""
        super().clean()

        # Ensure member account and club are in same tenant
        if self.member_account.tenant != self.club.tenant:
            raise ValidationError("Member account and club must be in same tenant")

        # Do not assign a placeholder membership number here; we'll set it post-save when pk exists
        # This avoids triggering the conditional unique constraint and double validation.

    def save(self, *args, **kwargs):
        creating = self.pk is None
        # Run validation once per save
        self.full_clean()
        super().save(*args, **kwargs)

        # After initial save, ensure membership_number is set if blank
        if creating and not self.membership_number:
            self.membership_number = f"{self.club.id}-{self.pk}"
            # Update only the membership_number without re-validating all fields
            super().save(update_fields=["membership_number"])
