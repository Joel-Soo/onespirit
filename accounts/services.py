"""
Service functions mirroring monkey-patched methods from accounts.utils.

These provide explicit, importable APIs without modifying model classes at runtime.
They are behavior-equivalent to the current patched methods to support a gradual migration.

Usage:
    from accounts import services as acct_svc
    accounts = acct_svc.get_accounts_for_contact(contact)
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Optional, Union

from django.contrib.contenttypes.models import ContentType
from django.db.models import QuerySet, Sum

from people.models import Contact, UserProfile
from accounts.models import MemberAccount, PaymentHistory, TenantAccount, PaymentStatus


# ----- Contact-centric services -----

def get_accounts_for_contact(contact: Contact) -> List[Union[TenantAccount, MemberAccount]]:
    # Primary relationships
    tenant_primary = list(contact.tenantaccount_primary_accounts.all())
    member_primary = list(contact.memberaccount_primary_accounts.all())

    # Associated via M2M (TenantAccountContact)
    tenant_associated = list(contact.tenant_accounts.all())

    # One-to-one member account
    member_account = getattr(contact, "member_account", None)

    all_accounts: List[Union[TenantAccount, MemberAccount]] = (
        tenant_primary + member_primary + tenant_associated
    )
    if member_account:
        all_accounts.append(member_account)

    # Deduplicate by model label + pk
    seen = set()
    unique: List[Union[TenantAccount, MemberAccount]] = []
    for a in all_accounts:
        key = (a._meta.label, a.pk)
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique


def get_tenant_accounts_for_contact(contact: Contact) -> List[TenantAccount]:
    accounts = get_accounts_for_contact(contact)
    tenant_accounts: List[TenantAccount] = []
    for account in accounts:
        if isinstance(account, TenantAccount):
            tenant_accounts.append(account)
        elif isinstance(account, MemberAccount) and account.tenant:
            tenant_accounts.append(account.tenant)
    # Deduplicate by pk
    seen = set()
    unique: List[TenantAccount] = []
    for t in tenant_accounts:
        if t.pk not in seen:
            seen.add(t.pk)
            unique.append(t)
    return unique



def get_member_accounts_for_contact(contact: Contact) -> List[MemberAccount]:
    accounts = get_accounts_for_contact(contact)
    return [a for a in accounts if isinstance(a, MemberAccount)]


def contact_has_tenant_account(contact: Contact) -> bool:
    return len(get_tenant_accounts_for_contact(contact)) > 0


def contact_has_member_account(contact: Contact) -> bool:
    return hasattr(contact, "member_account") and contact.member_account is not None


def get_primary_tenant_for_contact(contact: Contact) -> Optional[TenantAccount]:
    tenants = get_tenant_accounts_for_contact(contact)
    return tenants[0] if tenants else None


def contact_can_be_deleted(contact: Contact) -> bool:
    if contact.tenantaccount_primary_accounts.exists() or contact.memberaccount_primary_accounts.exists():
        return False
    if hasattr(contact, "member_account") and contact.member_account and contact.member_account.is_active:
        return False
    return True


def get_payment_history_for_contact(contact: Contact) -> List[PaymentHistory]:
    accounts = get_accounts_for_contact(contact)
    history: List[PaymentHistory] = []

    # Batch per model to reduce ContentType calls and use IN filters
    by_model: Dict[type, List[int]] = {}
    for a in accounts:
        by_model.setdefault(a.__class__, []).append(a.pk)

    for model_cls, ids in by_model.items():
        ct = ContentType.objects.get_for_model(model_cls)
        qs = PaymentHistory.objects.filter(
            account_content_type=ct, account_object_id__in=ids
        )
        history.extend(qs)

    # Sort by payment_date desc
    return sorted(history, key=lambda p: p.payment_date, reverse=True)


def get_total_payments_for_contact(contact: Contact) -> Decimal:
    payments = get_payment_history_for_contact(contact)
    total: Decimal = sum(
        (p.amount for p in payments if p.payment_status == PaymentStatus.COMPLETED),
        start=Decimal("0.00"),
    )
    return total


def get_account_summary(contact: Contact) -> Dict[str, object]:
    accounts = get_accounts_for_contact(contact)
    tenant_accounts = get_tenant_accounts_for_contact(contact)
    member_accounts = get_member_accounts_for_contact(contact)
    payment_history = get_payment_history_for_contact(contact)
    total_payments = get_total_payments_for_contact(contact)

    return {
        "total_accounts": len(accounts),
        "tenant_accounts": len(tenant_accounts),
        "member_accounts": len(member_accounts),
        "has_member_account": contact_has_member_account(contact),
        "has_tenant_account": contact_has_tenant_account(contact),
        "primary_tenant": get_primary_tenant_for_contact(contact),
        "recent_payments": payment_history[:5],
        "total_payments": total_payments,
        "can_be_deleted": contact_can_be_deleted(contact),
    }


# ----- LoginUser-centric services -----

def get_tenant_account_for_userprofile(user_profile: UserProfile) -> Optional[TenantAccount]:
    # If their contact has a member account, use its tenant
    if hasattr(user_profile.contact, "member_account") and user_profile.contact.member_account:
        return user_profile.contact.member_account.tenant

    tenants = get_tenant_accounts_for_contact(user_profile.contact)
    return tenants[0] if tenants else None


def userprofile_can_access_account(
    user_profile: UserProfile,
    account: Union[TenantAccount, MemberAccount],
) -> bool:
    tenant = get_tenant_account_for_userprofile(user_profile)
    if not tenant:
        return False

    if user_profile.permissions_level in ["admin", "owner"] or user_profile.is_club_owner:
        if isinstance(account, TenantAccount):
            return account == tenant
        if isinstance(account, MemberAccount):
            return account.tenant == tenant

    if hasattr(user_profile.contact, "member_account"):
        return user_profile.contact.member_account == account

    return False


def get_accessible_member_accounts_for_userprofile(user_profile: UserProfile) -> QuerySet[MemberAccount]:
    tenant = get_tenant_account_for_userprofile(user_profile)
    if not tenant:
        return MemberAccount.objects.none()

    if user_profile.permissions_level in ["admin", "owner"] or user_profile.is_club_owner:
        return MemberAccount.objects.filter(tenant=tenant, is_active=True)

    if hasattr(user_profile.contact, "member_account"):
        return MemberAccount.objects.filter(
            id=user_profile.contact.member_account.id, is_active=True
        )

    return MemberAccount.objects.none()



def get_accessible_payment_history_for_userprofile(user_profile: UserProfile) -> List[PaymentHistory]:
    accessible_accounts: List[Union[TenantAccount, MemberAccount]] = list(
        get_accessible_member_accounts_for_userprofile(user_profile)
    )
    tenant = get_tenant_account_for_userprofile(user_profile)

    if tenant and (user_profile.permissions_level in ["admin", "owner"] or user_profile.is_club_owner):
        accessible_accounts.append(tenant)

    # Batch by model for efficiency
    by_model: Dict[type, List[int]] = {}
    for a in accessible_accounts:
        by_model.setdefault(a.__class__, []).append(a.pk)

    history: List[PaymentHistory] = []
    for model_cls, ids in by_model.items():
        ct = ContentType.objects.get_for_model(model_cls)
        qs = PaymentHistory.objects.filter(
            account_content_type=ct, account_object_id__in=ids
        )
        history.extend(qs)

    return sorted(history, key=lambda p: p.payment_date, reverse=True)


def loginuser_can_create_member_accounts(login_user: LoginUser) -> bool:
    tenant = get_tenant_account_for_loginuser(login_user)
    if not tenant:
        return False
    if login_user.permissions_level in ["admin", "owner"] or login_user.is_club_owner:
        return tenant.can_add_member()
    return False


def loginuser_can_manage_billing(login_user: LoginUser) -> bool:
    return (
        login_user.permissions_level in ["admin", "owner"]
        or login_user.is_club_owner
        or login_user.can_manage_members
    )


def get_tenant_statistics_for_loginuser(
    login_user: LoginUser,
) -> Optional[Dict[str, Union[int, float, Decimal, str]]]:
    tenant = get_tenant_account_for_loginuser(login_user)
    if not tenant or not (login_user.permissions_level in ["admin", "owner"] or login_user.is_club_owner):
        return None

    ct = ContentType.objects.get_for_model(tenant.__class__)
    payments = PaymentHistory.objects.filter(
        account_content_type=ct,
        account_object_id=tenant.pk,
        payment_status=PaymentStatus.COMPLETED,
    )

    total_revenue = payments.aggregate(Sum("amount"))["amount__sum"] or Decimal("0.00")
    payment_count = payments.count()

    member_count = tenant.get_member_count()
    max_members = tenant.max_member_accounts or 0
    utilization = (member_count / max_members * 100) if max_members > 0 else 0

    return {
        "member_count": member_count,
        "max_members": max_members,
        "member_utilization": utilization,
        "total_revenue": total_revenue,
        "payment_count": payment_count,
        "subscription_status": tenant.get_subscription_status(),
    }