"""
Utility functions for account management operations.

This module provides utility functions for creating accounts and generating
account summaries. For account-related operations on Contact and LoginUser models,
use the service functions in accounts.services instead.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional, Union

from people.models import Contact, LoginUser

if TYPE_CHECKING:
    from typing import Dict, List, Tuple

    from django.contrib.auth.models import User
    from django.db.models import QuerySet

    from accounts.models import MemberAccount, PaymentHistory, TenantAccount


def create_tenant_account(
    contact: Contact, tenant_data: Dict[str, Any], user: Optional[User] = None
) -> Tuple[Optional[TenantAccount], Optional[str]]:
    """
    Utility function to create a tenant account with proper validation
    """
    from django.db import transaction
    from django.utils import timezone

    from accounts.models import TenantAccount, TenantAccountContact

    try:
        with transaction.atomic():
            # Set default subscription_start_date if not provided
            if "subscription_start_date" not in tenant_data:
                tenant_data["subscription_start_date"] = timezone.now()

            # Create tenant account
            tenant = TenantAccount.objects.create(
                primary_contact=contact,
                billing_contact=contact,  # Default billing contact to primary
                billing_email=contact.email,
                **tenant_data,
            )

            # Create primary contact relationship
            TenantAccountContact.objects.create(
                account=tenant,
                contact=contact,
                relationship_type="primary",
                is_active=True,
            )

            return tenant, None

    except Exception as e:
        return None, str(e)


def create_member_account(
    tenant: TenantAccount,
    contact: Contact,
    membership_data: Dict[str, Any],
    user: Optional[User] = None,
) -> Tuple[Optional[MemberAccount], Optional[str]]:
    """
    Utility function to create a member account with proper validation
    """
    from django.db import transaction

    from accounts.models import MemberAccount

    try:
        with transaction.atomic():
            # Check tenant limits
            if not tenant.can_add_member():
                return (
                    None,
                    f"Tenant has reached maximum member limit ({tenant.max_member_accounts})",
                )

            # Create member account
            member = MemberAccount.objects.create(
                tenant=tenant,
                member_contact=contact,
                primary_contact=contact,
                billing_contact=contact,  # Default billing contact to member
                billing_email=contact.email,
                **membership_data,
            )

            return member, None

    except Exception as e:
        return None, str(e)


def get_account_summary(
    contact: Contact,
) -> Dict[
    str, Union[int, bool, Optional[TenantAccount], List[PaymentHistory], Decimal]
]:
    """
    Get a comprehensive summary of all accounts for a contact
    """
    from . import services as acct_svc

    accounts = acct_svc.get_accounts_for_contact(contact)
    tenant_accounts = acct_svc.get_tenant_accounts_for_contact(contact)
    member_accounts = acct_svc.get_member_accounts_for_contact(contact)
    payment_history = acct_svc.get_payment_history_for_contact(contact)
    total_payments = acct_svc.get_total_payments_for_contact(contact)

    return {
        "total_accounts": len(accounts),
        "tenant_accounts": len(tenant_accounts),
        "member_accounts": len(member_accounts),
        "has_member_account": acct_svc.contact_has_member_account(contact),
        "has_tenant_account": acct_svc.contact_has_tenant_account(contact),
        "primary_tenant": acct_svc.get_primary_tenant_for_contact(contact),
        "recent_payments": payment_history[:5],  # Last 5 payments
        "total_payments": total_payments,
        "can_be_deleted": acct_svc.contact_can_be_deleted(contact),
    }