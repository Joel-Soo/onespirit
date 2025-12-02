from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone

from accounts.managers import OrganizationAwareManager, TenantAwareManager

if TYPE_CHECKING:
    from typing import List

    from organizations.models import Organization

    from accounts.models import TenantAccount

# Import signals to register them


class Contact(models.Model):
    """Contact model for personal information relating to a person"""

    # Personal Information Fields (per specification)
    first_name = models.CharField(
        max_length=50, db_index=True, help_text="Person's first name"
    )
    last_name = models.CharField(
        max_length=50, db_index=True, help_text="Person's last name"
    )
    date_of_birth = models.DateField(
        help_text="Date of birth for age calculation and records"
    )
    address = models.TextField(help_text="Complete postal address")
    mobile_number = models.CharField(
        max_length=20, help_text="Primary mobile phone number"
    )
    email = models.EmailField(
        db_index=True, help_text="Email address (must be unique per tenant)"
    )

    # TODO move Emergency Contact Information and Medical Information to ClubMember model
    # Emergency Contact Information
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

    # Medical Information (for martial arts safety)
    medical_conditions = models.TextField(
        blank=True, help_text="Any medical conditions relevant to training"
    )
    medical_clearance_date = models.DateField(
        null=True, blank=True, help_text="Date of last medical clearance (if required)"
    )

    # Tenant relationship for multi-tenant isolation
    # TODO make tenant not nullable
    tenant = models.ForeignKey(
        "accounts.TenantAccount",
        on_delete=models.CASCADE,
        related_name="people_contacts",
        help_text="Tenant that owns this contact",
        null=True,  # Temporarily nullable for migration
        blank=True,
    )

    # Organization relationship for direct organization membership
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="people_contacts",
        help_text="Direct organization membership",
    )

    # Metadata Fields for auditing and soft delete
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, help_text="Soft delete flag")

    # Organization and tenant-aware managers
    objects = OrganizationAwareManager()  # Default manager with dual filtering
    all_objects = models.Manager()  # Bypass all filtering when needed
    tenant_objects = (
        TenantAwareManager()
    )  # Tenant-only filtering for legacy compatibility

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"
        indexes = [
            models.Index(
                fields=["last_name", "first_name"], name="people_contact_name_idx"
            ),
            models.Index(fields=["email"], name="people_contact_email_idx"),
            models.Index(fields=["tenant"], name="people_contact_tenant_idx"),
            models.Index(fields=["tenant", "email"], name="people_contact_t_email_idx"),
            models.Index(fields=["organization"], name="people_contact_org_idx"),
            models.Index(
                fields=["organization", "email"], name="people_contact_org_email_idx"
            ),
            models.Index(fields=["is_active"], name="people_contact_active_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "email"], name="people_contact_tenant_email_unique"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def get_full_name(self) -> str:
        """Return formatted full name"""
        return f"{self.first_name} {self.last_name}".strip()

    def get_age(self) -> Optional[int]:
        """Calculate current age from date of birth"""
        if not self.date_of_birth:
            return None
        today = timezone.now().date()
        age = today.year - self.date_of_birth.year
        if today.month < self.date_of_birth.month or (
            today.month == self.date_of_birth.month
            and today.day < self.date_of_birth.day
        ):
            age -= 1
        return age

    def get_absolute_url(self) -> str:
        """Return URL for contact detail view"""
        return reverse("people:contact_detail", kwargs={"pk": self.pk})

    def clean(self) -> None:
        """Custom validation"""

        # Validate date of birth is in the past
        if self.date_of_birth and self.date_of_birth >= timezone.now().date():
            raise ValidationError(
                {"date_of_birth": "Date of birth must be in the past"}
            )

        # Validate email format (additional to EmailField validation)
        if self.email and not self.email.strip():
            raise ValidationError({"email": "Email address cannot be empty"})

    def get_organization(self) -> Optional[Organization]:
        """Get primary organization for contact"""
        return self.organization

    def can_access_organization(self, organization: Organization) -> bool:
        """Check if contact can access organization"""
        return self.organization == organization

    def get_all_organizations(self) -> List[Organization]:
        """Get all organizations contact has access to"""
        orgs = []
        if self.organization:
            orgs.append(self.organization)
        return orgs


class UserProfile(models.Model):
    """UserProfile model for contacts that can login and manage club membership"""

    # Relationship Fields
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        help_text="Django User account for authentication",
    )
    contact = models.OneToOneField(
        Contact,
        on_delete=models.CASCADE,
        related_name="user_profile",
        help_text="Associated contact information",
    )

    # Permission Fields for club management
    is_system_admin = models.BooleanField(
        default=False,
        help_text="System administrator with full tenant-wide access"
    )
    is_club_owner = models.BooleanField(
        default=False, help_text="Can own and fully manage clubs"
    )
    is_club_staff = models.BooleanField(
        default=False, help_text="Can assist with club management"
    )

    PERMISSION_CHOICES = [
        ("member", "Member"),
        ("staff", "Staff"),
        ("owner", "Owner"),
        ("admin", "Administrator"),
    ]
    permissions_level = models.CharField(
        max_length=20,
        choices=PERMISSION_CHOICES,
        default="member",
        help_text="General permission level for club operations",
    )

    # Additional Fields for club management
    can_create_clubs = models.BooleanField(
        default=False, help_text="Permission to create new clubs"
    )
    can_manage_members = models.BooleanField(
        default=False, help_text="Permission to manage club member rosters"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_attempt = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        indexes = [
            models.Index(
                fields=["permissions_level"], name="people_loginuser_perm_idx"
            ),
            models.Index(fields=["is_club_owner"], name="people_loginuser_owner_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.contact.get_full_name()} (User Profile)"

    def has_club_permissions(self) -> bool:
        """Check if user has any club management permissions"""
        return (
            self.is_club_owner  # Has club-specific ownership via ClubStaff
            or self.is_system_admin  # System-wide admin access
            or self.can_manage_members  # Can manage members globally
        )

    def can_manage_club(self, club: Any = None) -> bool:
        """Check if user can manage a specific club (placeholder for future Club model)"""
        if not club:
            return self.has_club_permissions()

        # Check if club belongs to same tenant
        if hasattr(club, "tenant") and club.tenant != self.contact.tenant:
            return False

        # Check if user has organization-level permissions over club's organization
        if hasattr(club, "organization"):
            org_permission = self.get_organization_permission_level(club.organization)
            if org_permission in ["owner", "admin"]:
                return True

        if self.is_club_owner or self.is_system_admin:
            return True
        # Future implementation will check club-specific permissions
        return False

    def get_managed_clubs(self):
        """Return queryset of clubs this user can manage.

        System admins manage all clubs in their tenant; regular users manage clubs
        where they have active staff assignments.
        """
        from clubs.models import Club

        # System admins can manage all clubs in their tenant
        if self.is_system_admin:
            return (
                Club.objects.select_related("tenant", "organization").filter(
                    tenant=self.contact.tenant
                )
            )

        # Regular users: clubs where they have active staff assignments
        return (
            Club.objects.select_related("tenant", "organization")
            .filter(staff_assignments__user=self, staff_assignments__is_active=True)
            .distinct()
        )

    def get_club_permissions_summary(self) -> dict:
        """Return a summary of the user's club-related permissions."""
        return {
            "is_admin": self.is_system_admin,
            "can_create_clubs": self.can_create_clubs,
            "can_manage_members": self.can_manage_members,
            "is_club_owner": self.is_club_owner,
        }

    def can_access_organization(self, organization: Organization) -> bool:
        """Check if user can access organization"""
        user = self.user

        # Check django-organizations membership (any level)
        if organization.is_admin(user) or organization.is_owner(user):
            return True

        # Check for regular organization membership
        from organizations.models import OrganizationUser

        if OrganizationUser.objects.filter(
            user=user, organization=organization
        ).exists():
            return True

        # Check direct organization membership through Contact
        return self.contact.organization == organization

    def is_organization_admin(self, organization: Organization) -> bool:
        """Check if user is organization admin"""
        return organization.is_admin(self.user)

    def is_organization_owner(self, organization: Organization) -> bool:
        """Check if user is organization owner"""
        return organization.is_owner(self.user)

    def get_organizations(self) -> List[Organization]:
        """Get all organizations user belongs to"""
        from organizations.models import OrganizationUser

        user = self.user
        org_users = OrganizationUser.objects.filter(user=user)
        return [org_user.organization for org_user in org_users]

    def get_organization_permission_level(
        self, organization: Organization
    ) -> Optional[str]:
        """Get permission level within organization"""
        if organization.is_owner(self.user):
            return "owner"
        elif organization.is_admin(self.user):
            return "admin"
        elif self.contact.organization == organization:
            return "member"
        else:
            # Check for regular organization membership via OrganizationUser
            from organizations.models import OrganizationUser

            if OrganizationUser.objects.filter(
                user=self.user, organization=organization
            ).exists():
                return "member"
            return None

    def can_access_tenant(self, tenant: TenantAccount) -> bool:
        """Check if user can access specific tenant - required by middleware"""
        return self.contact.tenant == tenant

    def get_tenant_account(self) -> Optional[TenantAccount]:
        """Get user's tenant account - required by middleware"""
        return self.contact.tenant

    def clean(self) -> None:
        """Custom validation"""

        if not self.contact_id:
            raise ValidationError(
                {"contact": "UserProfile must be associated with a Contact"}
            )

        # Ensure permission consistency
        if self.is_club_owner and self.permissions_level not in ["owner", "admin"]:
            self.permissions_level = "owner"

        if self.permissions_level == "admin":
            self.is_club_owner = True
            self.can_create_clubs = True
            self.can_manage_members = True


# Signal handlers for UserProfile
@receiver(post_save, sender=User)
def create_login_user_profile(
    sender: type[User], instance: User, created: bool, **kwargs: Any
) -> None:
    """Create UserProfile profile when User is created (optional)"""
    # This will be called when creating User accounts
    # Implementation can be added later when user registration is implemented
    pass


@receiver(post_save, sender=UserProfile)
def sync_user_permissions(
    sender: type[UserProfile], instance: UserProfile, **kwargs: Any
) -> None:
    """Sync Django User permissions with UserProfile permissions"""
    user = instance.user

    # Set Django User active status based on Contact active status
    if hasattr(instance, "contact") and instance.contact:
        user.is_active = instance.contact.is_active

    # Set Django staff status for club owners/admins
    if instance.is_club_owner or instance.is_system_admin:
        user.is_staff = True

    user.save(update_fields=["is_active", "is_staff"])
