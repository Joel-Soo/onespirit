from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

# Import existing Contact model from people app
from people.models import Contact

# Import tenant-aware managers
from .managers import MemberAccountManager

if TYPE_CHECKING:
    from typing import Literal


# Enums for PaymentHistory choices (best practice for type safety)
class PaymentMethod(models.TextChoices):
    """Payment method choices for PaymentHistory."""

    CASH = "cash", "Cash"
    CARD = "card", "Credit/Debit Card"
    BANK_TRANSFER = "bank_transfer", "Bank Transfer"
    CHECK = "check", "Check"
    PAYPAL = "paypal", "PayPal"
    STRIPE = "stripe", "Stripe"
    DIRECT_DEBIT = "direct_debit", "Direct Debit"


class PaymentStatus(models.TextChoices):
    """Payment status choices for PaymentHistory."""

    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"
    PARTIAL_REFUND = "partial_refund", "Partial Refund"
    CANCELLED = "cancelled", "Cancelled"


class PaymentType(models.TextChoices):
    """Payment type/category choices for PaymentHistory."""

    MEMBERSHIP_FEE = "membership_fee", "Membership Fee"
    GRADING_FEE = "grading_fee", "Grading Fee"
    EQUIPMENT = "equipment", "Equipment Purchase"
    EVENT_FEE = "event_fee", "Event Fee"
    SUBSCRIPTION = "subscription", "Tenant Subscription"
    LATE_FEE = "late_fee", "Late Payment Fee"
    REFUND = "refund", "Refund"
    ADJUSTMENT = "adjustment", "Account Adjustment"


class Account(models.Model):
    """
    Abstract base model for all account types in OneSpirit.
    Provides common functionality for billing, payment tracking, and contact relationships.
    """

    # Contact Relationships (per spec: "at least one contact", "primary contact")
    # NOTE: primary_contact is nullable at DB level to avoid circular dependency:
    # TenantAccount needs Contact for primary_contact, but Contact needs TenantAccount for tenant field.
    # Application-level validation ensures it's always set after creation.
    primary_contact = models.ForeignKey(
        Contact,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="%(class)s_primary_accounts",
        help_text="Primary contact for this account (required - set after creation to avoid circular dependency)",
    )

    # Billing Information
    billing_email = models.EmailField(
        help_text="Email address for billing notifications"
    )
    billing_contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_billing_accounts",
        help_text="Contact responsible for billing (optional, defaults to primary contact)",
    )

    # Account Status and Metadata
    account_status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("closed", "Closed"),
        ],
        default="active",
        help_text="Current status of the account",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(
        default=True, help_text="Soft delete flag - when False, account is deactivated"
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["account_status"], name="accounts_status_idx"),
            models.Index(fields=["is_active"], name="accounts_active_idx"),
            models.Index(fields=["created_at"], name="accounts_created_idx"),
        ]

    def clean(self) -> None:
        """Model-level validation"""
        super().clean()

        # Primary contact is required only after creation (to avoid admin/bulk load friction)
        # Allow missing primary_contact on initial create (when pk is None)
        if self.pk and not self.primary_contact:
            raise ValidationError({"primary_contact": "Primary contact is required"})

        # Primary contact must be active
        if self.primary_contact and not self.primary_contact.is_active:
            raise ValidationError({"primary_contact": "Primary contact must be active"})

        # Billing email validation
        if self.billing_email and not self.billing_email.strip():
            raise ValidationError({"billing_email": "Billing email cannot be empty"})

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override save with validation"""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        if self.primary_contact:
            return f"Account ({self.primary_contact.get_full_name()})"
        return "Account (No primary contact set)"


class TenantAccountContact(models.Model):
    """
    Through model for TenantAccount-Contact many-to-many relationship.
    Allows tracking additional metadata about the relationship.
    """

    account = models.ForeignKey("TenantAccount", on_delete=models.CASCADE)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=50,
        choices=[
            ("primary", "Primary Contact"),
            ("admin", "Tenant Admin"),
        ],
        default="admin",
    )
    added_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ["account", "contact"]
        indexes = [
            models.Index(
                fields=["account", "role"],
                name="acc_tenant_contact_rel_idx",
            ),
            models.Index(fields=["is_active"], name="acc_tenant_contact_act_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.contact.get_full_name()} - {self.account} ({self.role})"


class TenantAccount(Account):
    """
    Multi-tenant customer account that owns and manages subordinate entities.
    Represents the top-level customer in a multi-tenant deployment.
    """

    # Contact Relationships (many-to-many through TenantAccountContact)
    contacts = models.ManyToManyField(
        Contact,
        related_name="tenant_accounts",
        through="TenantAccountContact",
        help_text="All contacts associated with this tenant account",
    )

    # Tenant Identification
    tenant_name = models.CharField(
        max_length=100, help_text="Organization name for this tenant"
    )
    tenant_slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="URL-safe tenant identifier (unique across system)",
    )
    tenant_domain = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Custom domain for tenant (optional)",
    )

    # Billing and Subscription Management
    subscription_type = models.CharField(
        max_length=50,
        choices=[
            ("basic", "Basic"),
            ("premium", "Premium"),
            ("enterprise", "Enterprise"),
        ],
        default="basic",
        help_text="Subscription tier determining features and limits",
    )
    subscription_start_date = models.DateTimeField(
        help_text="When the subscription began"
    )
    subscription_end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the subscription expires (null for indefinite)",
    )
    monthly_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Monthly subscription fee amount",
    )

    # Limits and Quotas (per subscription type)
    # TODO add a boolean field to disable limits and quotas
    max_member_accounts = models.PositiveIntegerField(
        default=100, help_text="Maximum number of member accounts allowed"
    )
    max_clubs = models.PositiveIntegerField(
        default=5, help_text="Maximum number of clubs allowed"
    )
    max_associations = models.PositiveIntegerField(
        default=1, help_text="Maximum number of associations allowed"
    )

    # Configuration
    timezone = models.CharField(
        max_length=50, default="UTC", help_text="Default timezone for this tenant"
    )
    locale = models.CharField(
        max_length=10, default="en-US", help_text="Default locale for this tenant"
    )

    class Meta:
        db_table = "accounts_tenant_account"
        verbose_name = "Tenant Account"
        verbose_name_plural = "Tenant Accounts"
        indexes = [
            # Removed redundant Index on tenant_slug - unique=True already creates an index
            models.Index(fields=["subscription_type"], name="accounts_tenant_sub_idx"),
            models.Index(
                fields=["subscription_end_date"], name="accounts_tenant_exp_idx"
            ),
        ]
        # Removed constraints section - tenant_slug UniqueConstraint was redundant with unique=True

    def __str__(self) -> str:
        return f"{self.tenant_name} (Tenant)"

    def get_member_count(self) -> int:
        """Get current number of active member accounts"""
        return self.member_accounts.filter(is_active=True).count()

    def can_add_member(self) -> bool:
        """Check if tenant can add more member accounts"""
        return self.get_member_count() < self.max_member_accounts

    def get_subscription_status(self) -> Literal["active", "expired"]:
        """Check if subscription is active"""
        if not self.subscription_end_date:
            return "active"  # Indefinite subscription
        return "active" if self.subscription_end_date > timezone.now() else "expired"


class MemberAccount(Account):
    """
    Club member account with one-to-one Contact relationship and tenant association.
    Represents individual members within a martial arts club/organization.
    """

    # Enhanced managers for tenant-aware operations
    objects = MemberAccountManager()  # Default manager with tenant filtering
    all_objects = models.Manager()  # Bypass filtering when needed (use carefully)

    # Tenant Association (for multi-tenant isolation)
    tenant = models.ForeignKey(
        TenantAccount,
        on_delete=models.CASCADE,
        related_name="member_accounts",
        help_text="Tenant that owns this member account",
    )

    # Contact Relationship (one-to-one as per spec requirement)
    member_contact = models.OneToOneField(
        Contact,
        on_delete=models.CASCADE,
        related_name="member_account",
        help_text="Contact information for this member (one-to-one relationship)",
    )

    # Membership Information
    membership_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique membership identifier across entire system",
    )
    membership_type = models.CharField(
        max_length=50,
        choices=[
            ("student", "Student"),
            ("instructor", "Instructor"),
            ("honorary", "Honorary"),
            ("lifetime", "Lifetime Member"),
        ],
        default="student",
        help_text="Type of membership held by this member",
    )
    membership_start_date = models.DateField(help_text="Date when membership began")
    membership_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when membership expires (null for indefinite)",
    )

    # Club Associations (many-to-many through ClubMember model)
    clubs = models.ManyToManyField(
        "clubs.Club",
        through="clubs.ClubMember",
        related_name="account_members",
        blank=True,
        help_text="Clubs this member account is associated with",
    )

    class Meta:
        db_table = "accounts_member_account"
        verbose_name = "Member Account"
        verbose_name_plural = "Member Accounts"
        indexes = [
            models.Index(
                fields=["tenant", "membership_number"],
                name="accounts_member_tenant_num_idx",
            ),
            models.Index(fields=["membership_type"], name="accounts_member_type_idx"),
            models.Index(
                fields=["membership_start_date"], name="accounts_member_start_idx"
            ),
            models.Index(
                fields=["membership_end_date"], name="accounts_member_end_idx"
            ),
        ]
        # Removed constraints section:
        # - membership_number UniqueConstraint was redundant (field has unique=True)
        # - member_contact UniqueConstraint was redundant (OneToOneField is implicitly unique)

    def __str__(self) -> str:
        return (
            f"{self.member_contact.get_full_name()} (Member #{self.membership_number})"
        )

    def clean(self) -> None:
        """Additional validation for MemberAccount"""
        super().clean()

        # Ensure primary_contact is same as member_contact
        if self.member_contact and self.primary_contact != self.member_contact:
            raise ValidationError(
                {
                    "primary_contact": "Primary contact must be the same as member contact"
                }
            )

        # Validate membership dates
        if (
            self.membership_start_date
            and self.membership_end_date
            and self.membership_start_date >= self.membership_end_date
        ):
            raise ValidationError(
                {"membership_end_date": "End date must be after start date"}
            )

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override save to auto-set primary_contact"""
        if self.member_contact and not self.primary_contact:
            self.primary_contact = self.member_contact
        super().save(*args, **kwargs)

    def is_membership_active(self) -> bool:
        """Check if membership is currently active"""
        if not self.membership_end_date:
            return True  # Indefinite membership
        return self.membership_end_date >= timezone.now().date()

    def get_membership_status(self) -> Literal["inactive", "expired", "active"]:
        """Get readable membership status"""
        if not self.is_active:
            return "inactive"
        if not self.is_membership_active():
            return "expired"
        return "active"


class PaymentHistory(models.Model):
    """
    Payment history tracking for all account types using polymorphic relationships.
    Supports both TenantAccount (subscription billing) and MemberAccount (membership fees).
    """

    # Polymorphic Account Association (works with TenantAccount and MemberAccount)
    account_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text="Type of account (TenantAccount or MemberAccount)",
    )
    account_object_id = models.PositiveIntegerField(
        help_text="ID of the specific account instance"
    )
    account = GenericForeignKey("account_content_type", "account_object_id")

    # Payment Information
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Payment amount (positive for payments, negative for refunds)",
    )
    currency = models.CharField(
        max_length=3, default="USD", help_text="Currency code (ISO 4217)"
    )
    payment_date = models.DateTimeField(help_text="When the payment was made/processed")
    due_date = models.DateField(
        null=True, blank=True, help_text="When payment was/is due (for invoices)"
    )

    # Payment Method and Processing
    payment_method = models.CharField(
        max_length=50,
        choices=PaymentMethod.choices,
        help_text="Method used for payment",
    )
    transaction_reference = models.CharField(
        max_length=100, blank=True, help_text="External transaction ID or reference"
    )
    processor_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Fee charged by payment processor",
    )

    # Status and Classification
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        help_text="Current status of the payment",
    )
    payment_type = models.CharField(
        max_length=50,
        choices=PaymentType.choices,
        help_text="Category/purpose of the payment",
    )

    # References and Notes
    invoice_number = models.CharField(
        max_length=50, blank=True, help_text="Invoice number if applicable"
    )
    description = models.TextField(
        blank=True, help_text="Additional details about the payment"
    )
    notes = models.TextField(
        blank=True, help_text="Internal notes (not visible to customer)"
    )

    # Metadata and Audit Trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who created this payment record",
    )

    class Meta:
        db_table = "accounts_payment_history"
        verbose_name = "Payment History"
        verbose_name_plural = "Payment History"
        ordering = ["-payment_date"]
        indexes = [
            models.Index(
                fields=["account_content_type", "account_object_id"],
                name="accounts_payment_account_idx",
            ),
            models.Index(fields=["payment_date"], name="accounts_payment_date_idx"),
            models.Index(fields=["payment_status"], name="accounts_payment_status_idx"),
            models.Index(fields=["payment_type"], name="accounts_payment_type_idx"),
            models.Index(
                fields=["invoice_number"], name="accounts_payment_invoice_idx"
            ),
            models.Index(
                fields=["transaction_reference"], name="accounts_payment_ref_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.payment_type} - {self.amount} {self.currency} ({self.payment_status})"

    def get_account_display(self) -> str:
        """Get human-readable account information"""
        if hasattr(self.account, "tenant_name"):
            return f"Tenant: {self.account.tenant_name}"
        elif hasattr(self.account, "member_contact"):
            return f"Member: {self.account.member_contact.get_full_name()}"
        return str(self.account)

    def is_refund(self) -> bool:
        """Check if this is a refund transaction"""
        return self.amount < 0 or "refund" in self.payment_status

    def clean(self) -> None:
        """Model-level validation for PaymentHistory."""
        super().clean()

        # Validate amount is positive for non-refund payments
        if (
            self.payment_status
            not in [
                PaymentStatus.REFUNDED,
                PaymentStatus.PARTIAL_REFUND,
            ]
            and self.amount < 0
        ):
            raise ValidationError(
                {
                    "amount": "Amount must be positive for non-refund payments. "
                    f"Current status: {self.get_payment_status_display()}"
                }
            )

        # Validate processor fee is not negative
        if self.processor_fee < 0:
            raise ValidationError({"processor_fee": "Processor fee cannot be negative"})

        # Validate that refund payments have negative amounts or refund status
        if self.amount < 0 and self.payment_status not in [
            PaymentStatus.REFUNDED,
            PaymentStatus.PARTIAL_REFUND,
        ]:
            raise ValidationError(
                {
                    "payment_status": f"Negative amounts require refund status. "
                    f"Current status: {self.get_payment_status_display()}"
                }
            )

        # Validate payment_date is not in the future (unless pending)
        if self.payment_date and self.payment_date > timezone.now():
            if self.payment_status not in [PaymentStatus.PENDING]:
                raise ValidationError(
                    {
                        "payment_date": "Payment date cannot be in the future for completed payments"
                    }
                )

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override save to enforce validation."""
        self.full_clean()
        super().save(*args, **kwargs)
