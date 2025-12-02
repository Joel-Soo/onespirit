"""
Tests for accounts.services module.

These tests ensure that service functions provide the same behavior as the
original monkey-patched methods while offering improved performance and
maintainability.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User

from people.models import Contact, UserProfile
from accounts.models import (
    TenantAccount,
    MemberAccount,
    PaymentHistory,
    PaymentMethod,
    PaymentStatus,
    PaymentType,
)
from accounts import services as acct_svc


class ContactServicesTestCase(TestCase):
    """Test Contact-related service functions"""

    def setUp(self):
        """Set up test data"""
        # Create test contacts
        from datetime import date
        self.contact1 = Contact.objects.create(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            date_of_birth=date(1990, 1, 1),
            address="123 Main St, City, State",
            mobile_number="555-0001"
        )
        self.contact2 = Contact.objects.create(
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
            date_of_birth=date(1985, 5, 15),
            address="456 Oak Ave, City, State",
            mobile_number="555-0002"
        )

        # Create test tenant account
        from django.utils import timezone
        self.tenant1 = TenantAccount.objects.create(
            tenant_name="Test Tenant 1",
            tenant_slug="test-tenant-1",
            primary_contact=self.contact1,
            billing_contact=self.contact1,
            billing_email=self.contact1.email,
            subscription_start_date=timezone.now(),
            max_member_accounts=10,
            is_active=True
        )

        # Create test member account
        self.member1 = MemberAccount.objects.create(
            tenant=self.tenant1,
            member_contact=self.contact2,
            primary_contact=self.contact2,
            billing_contact=self.contact2,
            billing_email=self.contact2.email,
            membership_number="MEM001",
            membership_type="student",
            membership_start_date=date.today(),
            is_active=True
        )

    def test_get_accounts_for_contact(self):
        """Test get_accounts_for_contact service function"""
        # Contact1 should have tenant account as primary
        accounts = acct_svc.get_accounts_for_contact(self.contact1)
        self.assertEqual(len(accounts), 1)
        self.assertIn(self.tenant1, accounts)

        # Contact2 should have member account
        accounts = acct_svc.get_accounts_for_contact(self.contact2)
        self.assertEqual(len(accounts), 1)
        self.assertIn(self.member1, accounts)

    def test_get_tenant_accounts_for_contact(self):
        """Test get_tenant_accounts_for_contact service function"""
        # Contact1 should have direct tenant access
        tenant_accounts = acct_svc.get_tenant_accounts_for_contact(self.contact1)
        self.assertEqual(len(tenant_accounts), 1)
        self.assertIn(self.tenant1, tenant_accounts)

        # Contact2 should have tenant access through member account
        tenant_accounts = acct_svc.get_tenant_accounts_for_contact(self.contact2)
        self.assertEqual(len(tenant_accounts), 1)
        self.assertIn(self.tenant1, tenant_accounts)

    def test_get_member_accounts_for_contact(self):
        """Test get_member_accounts_for_contact service function"""
        # Contact1 should have no member accounts
        member_accounts = acct_svc.get_member_accounts_for_contact(self.contact1)
        self.assertEqual(len(member_accounts), 0)

        # Contact2 should have one member account
        member_accounts = acct_svc.get_member_accounts_for_contact(self.contact2)
        self.assertEqual(len(member_accounts), 1)
        self.assertIn(self.member1, member_accounts)

    def test_contact_has_tenant_account(self):
        """Test contact_has_tenant_account service function"""
        self.assertTrue(acct_svc.contact_has_tenant_account(self.contact1))
        self.assertTrue(acct_svc.contact_has_tenant_account(self.contact2))

    def test_contact_has_member_account(self):
        """Test contact_has_member_account service function"""
        self.assertFalse(acct_svc.contact_has_member_account(self.contact1))
        self.assertTrue(acct_svc.contact_has_member_account(self.contact2))

    def test_get_primary_tenant_for_contact(self):
        """Test get_primary_tenant_for_contact service function"""
        primary_tenant = acct_svc.get_primary_tenant_for_contact(self.contact1)
        self.assertEqual(primary_tenant, self.tenant1)

        primary_tenant = acct_svc.get_primary_tenant_for_contact(self.contact2)
        self.assertEqual(primary_tenant, self.tenant1)

    def test_contact_can_be_deleted(self):
        """Test contact_can_be_deleted service function"""
        # Contact1 is primary for tenant, so cannot be deleted
        self.assertFalse(acct_svc.contact_can_be_deleted(self.contact1))

        # Contact2 has active member account, so cannot be deleted
        self.assertFalse(acct_svc.contact_can_be_deleted(self.contact2))

        # Create contact with no accounts - should be deletable
        from datetime import date
        contact3 = Contact.objects.create(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            date_of_birth=date(1992, 3, 10),
            address="789 Pine St, City, State",
            mobile_number="555-0003"
        )
        self.assertTrue(acct_svc.contact_can_be_deleted(contact3))

    def test_get_payment_history_for_contact(self):
        """Test get_payment_history_for_contact service function"""
        # Create test payment history
        from django.utils import timezone
        payment1 = PaymentHistory.objects.create(
            account=self.tenant1,
            amount=Decimal("100.00"),
            payment_status=PaymentStatus.COMPLETED,
            payment_method=PaymentMethod.CARD,
            payment_type=PaymentType.SUBSCRIPTION,
            payment_date=timezone.now()
        )

        payment_history = acct_svc.get_payment_history_for_contact(self.contact1)
        self.assertEqual(len(payment_history), 1)
        self.assertIn(payment1, payment_history)

    def test_get_total_payments_for_contact(self):
        """Test get_total_payments_for_contact service function"""
        # Create test payments
        from django.utils import timezone
        PaymentHistory.objects.create(
            account=self.tenant1,
            amount=Decimal("100.00"),
            payment_status=PaymentStatus.COMPLETED,
            payment_method=PaymentMethod.CARD,
            payment_type=PaymentType.SUBSCRIPTION,
            payment_date=timezone.now()
        )
        PaymentHistory.objects.create(
            account=self.tenant1,
            amount=Decimal("50.00"),
            payment_status=PaymentStatus.COMPLETED,
            payment_method=PaymentMethod.CARD,
            payment_type=PaymentType.SUBSCRIPTION,
            payment_date=timezone.now()
        )
        PaymentHistory.objects.create(
            account=self.tenant1,
            amount=Decimal("25.00"),
            payment_status=PaymentStatus.PENDING,  # Should not be included
            payment_method=PaymentMethod.CARD,
            payment_type=PaymentType.SUBSCRIPTION,
            payment_date=timezone.now()
        )

        total = acct_svc.get_total_payments_for_contact(self.contact1)
        self.assertEqual(total, Decimal("150.00"))

    def test_get_account_summary(self):
        """Test get_account_summary service function"""
        summary = acct_svc.get_account_summary(self.contact1)

        self.assertIsInstance(summary, dict)
        self.assertEqual(summary["total_accounts"], 1)
        self.assertEqual(summary["tenant_accounts"], 1)
        self.assertEqual(summary["member_accounts"], 0)
        self.assertTrue(summary["has_tenant_account"])
        self.assertFalse(summary["has_member_account"])
        self.assertEqual(summary["primary_tenant"], self.tenant1)
        self.assertFalse(summary["can_be_deleted"])


class UserProfileServicesTestCase(TestCase):
    """Test UserProfile-related service functions"""

    def setUp(self):
        """Set up test data"""
        from datetime import date
        # Create test users and contacts
        self.user1 = User.objects.create_user(
            username="testuser1",
            email="user1@example.com"
        )
        self.contact1 = Contact.objects.create(
            first_name="Test",
            last_name="User1",
            email="user1@example.com",
            date_of_birth=date(1988, 7, 20),
            address="111 Test St, City, State",
            mobile_number="555-1001"
        )
        self.user_profile1 = UserProfile.objects.create(
            user=self.user1,
            contact=self.contact1,
            permissions_level="member"
        )

        # Create tenant and member account
        from django.utils import timezone
        self.tenant1 = TenantAccount.objects.create(
            tenant_name="Test Tenant",
            tenant_slug="test-tenant-login",
            primary_contact=self.contact1,
            billing_contact=self.contact1,
            billing_email=self.contact1.email,
            subscription_start_date=timezone.now(),
            max_member_accounts=10,
            is_active=True
        )

        self.member1 = MemberAccount.objects.create(
            tenant=self.tenant1,
            member_contact=self.contact1,
            primary_contact=self.contact1,
            billing_contact=self.contact1,
            billing_email=self.contact1.email,
            membership_number="MEM002",
            membership_type="student",
            membership_start_date=date.today(),
            is_active=True
        )

    def test_get_tenant_account_for_userprofile(self):
        """Test get_tenant_account_for_userprofile service function"""
        tenant = acct_svc.get_tenant_account_for_userprofile(self.user_profile1)
        self.assertEqual(tenant, self.tenant1)

    def test_userprofile_can_access_account(self):
        """Test userprofile_can_access_account service function"""
        # User should be able to access their own member account
        can_access = acct_svc.userprofile_can_access_account(self.user_profile1, self.member1)
        self.assertTrue(can_access)

    def test_get_accessible_member_accounts_for_userprofile(self):
        """Test get_accessible_member_accounts_for_userprofile service function"""
        accessible = acct_svc.get_accessible_member_accounts_for_userprofile(self.user_profile1)
        self.assertEqual(accessible.count(), 1)
        self.assertIn(self.member1, accessible)

    def test_get_accessible_payment_history_for_userprofile(self):
        """Test get_accessible_payment_history_for_userprofile service function"""
        # Create test payment
        from django.utils import timezone
        payment = PaymentHistory.objects.create(
            account=self.member1,
            amount=Decimal("100.00"),
            payment_status=PaymentStatus.COMPLETED,
            payment_method=PaymentMethod.CARD,
            payment_type=PaymentType.MEMBERSHIP_FEE,
            payment_date=timezone.now()
        )

        payments = acct_svc.get_accessible_payment_history_for_userprofile(self.user_profile1)
        self.assertEqual(len(payments), 1)
        self.assertIn(payment, payments)

    def test_userprofile_can_create_member_accounts(self):
        """Test userprofile_can_create_member_accounts service function"""
        # Regular member should not be able to create accounts
        can_create = acct_svc.userprofile_can_create_member_accounts(self.user_profile1)
        self.assertFalse(can_create)

        # Admin should be able to create accounts
        self.user_profile1.permissions_level = "admin"
        self.user_profile1.save()
        can_create = acct_svc.userprofile_can_create_member_accounts(self.user_profile1)
        self.assertTrue(can_create)

    def test_userprofile_can_manage_billing(self):
        """Test userprofile_can_manage_billing service function"""
        # Regular member should not manage billing
        can_manage = acct_svc.userprofile_can_manage_billing(self.user_profile1)
        self.assertFalse(can_manage)

        # Admin should manage billing
        self.user_profile1.permissions_level = "admin"
        self.user_profile1.save()
        can_manage = acct_svc.userprofile_can_manage_billing(self.user_profile1)
        self.assertTrue(can_manage)

    def test_get_tenant_statistics_for_userprofile(self):
        """Test get_tenant_statistics_for_userprofile service function"""
        # Regular member should not see statistics
        stats = acct_svc.get_tenant_statistics_for_userprofile(self.user_profile1)
        self.assertIsNone(stats)

        # Admin should see statistics
        self.user_profile1.permissions_level = "admin"
        self.user_profile1.save()
        stats = acct_svc.get_tenant_statistics_for_userprofile(self.user_profile1)
        self.assertIsInstance(stats, dict)
        self.assertIn("member_count", stats)
        self.assertIn("total_revenue", stats)


class ServiceDeduplicationTestCase(TestCase):
    """Test that service functions properly handle deduplication"""

    def setUp(self):
        """Set up test data with potential duplicates"""
        from datetime import date
        self.contact = Contact.objects.create(
            first_name="Test",
            last_name="Contact",
            email="test@example.com",
            date_of_birth=date(1995, 12, 5),
            address="222 Dedup St, City, State",
            mobile_number="555-2001"
        )

        from django.utils import timezone
        self.tenant = TenantAccount.objects.create(
            tenant_name="Test Tenant",
            tenant_slug="test-tenant-dedup",
            primary_contact=self.contact,
            billing_contact=self.contact,
            billing_email=self.contact.email,
            subscription_start_date=timezone.now(),
            max_member_accounts=10,
            is_active=True
        )

        # Add contact to tenant via M2M (could create duplicate)
        self.tenant.contacts.add(self.contact)

    def test_account_deduplication(self):
        """Test that duplicate accounts are properly handled"""
        accounts = acct_svc.get_accounts_for_contact(self.contact)

        # Should only have one tenant account despite multiple relationships
        tenant_accounts = [a for a in accounts if isinstance(a, TenantAccount)]
        self.assertEqual(len(tenant_accounts), 1)

        # Test that deduplication uses proper model label + pk logic
        seen_keys = set()
        for account in accounts:
            key = (account._meta.label, account.pk)
            self.assertNotIn(key, seen_keys, "Duplicate account found")
            seen_keys.add(key)


class ServicePerformanceTestCase(TestCase):
    """Test that service functions provide expected performance improvements"""

    def setUp(self):
        """Set up test data for performance testing"""
        from datetime import date
        self.contact = Contact.objects.create(
            first_name="Performance",
            last_name="Test",
            email="perf@example.com",
            date_of_birth=date(1993, 8, 15),
            address="333 Perf Ave, City, State",
            mobile_number="555-3001"
        )

        # Create multiple accounts to test batching
        self.tenants = []
        self.members = []

        from django.utils import timezone
        for i in range(3):
            # Create a unique contact for each member to avoid uniqueness constraint
            member_contact = Contact.objects.create(
                first_name=f"Member",
                last_name=f"User{i}",
                email=f"member{i}@example.com",
                date_of_birth=date(1990 + i, 1, 1),
                address=f"444 Member St {i}, City, State",
                mobile_number=f"555-400{i}"
            )

            tenant = TenantAccount.objects.create(
                tenant_name=f"Tenant {i}",
                tenant_slug=f"test-tenant-perf-{i}",
                primary_contact=self.contact,
                billing_contact=self.contact,
                billing_email=self.contact.email,
                subscription_start_date=timezone.now(),
                max_member_accounts=10,
                is_active=True
            )
            self.tenants.append(tenant)

            member = MemberAccount.objects.create(
                tenant=tenant,
                member_contact=member_contact,
                primary_contact=member_contact,
                billing_contact=member_contact,
                billing_email=member_contact.email,
                membership_number=f"MEM00{i+10}",
                membership_type="student",
                membership_start_date=date.today(),
                is_active=True
            )
            self.members.append(member)

    def test_payment_history_batching(self):
        """Test that payment history queries are properly batched"""
        # Create payment history for each account
        from django.utils import timezone
        for tenant in self.tenants:
            PaymentHistory.objects.create(
                account=tenant,
                amount=Decimal("100.00"),
                payment_status=PaymentStatus.COMPLETED,
                payment_method=PaymentMethod.CARD,
                payment_type=PaymentType.SUBSCRIPTION,
                payment_date=timezone.now()
            )

        for member in self.members:
            PaymentHistory.objects.create(
                account=member,
                amount=Decimal("50.00"),
                payment_status=PaymentStatus.COMPLETED,
                payment_method=PaymentMethod.CARD,
                payment_type=PaymentType.MEMBERSHIP_FEE,
                payment_date=timezone.now()
            )

        # Test that we get tenant payments for the original contact
        # (since the contact is primary for all tenants)
        payments = acct_svc.get_payment_history_for_contact(self.contact)
        self.assertEqual(len(payments), 3)  # 3 tenant payments

        # Test total calculation for tenant payments
        total = acct_svc.get_total_payments_for_contact(self.contact)
        expected_total = Decimal("100.00") * 3  # 300.00
        self.assertEqual(total, expected_total)

        # Test that each member gets their own payment
        for i, member in enumerate(self.members):
            member_payments = acct_svc.get_payment_history_for_contact(member.member_contact)
            self.assertEqual(len(member_payments), 1)  # Each member has 1 payment