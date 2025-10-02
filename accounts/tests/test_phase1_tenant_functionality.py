"""
Test suite for Phase 1 Enhanced Manual Approach - Automatic Tenant Filtering.

This module tests the core functionality implemented in Phase 1:
- Custom managers with tenant filtering
- Tenant context middleware
- Basic tenant isolation
"""

from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta

from accounts.models import TenantAccount, MemberAccount
from accounts.managers import set_current_tenant, get_current_tenant, TenantCacheManager
from accounts.middleware import TenantContextMiddleware
from people.models import Contact


class TenantManagerTestCase(TestCase):
    """Test tenant-aware managers functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create test contacts
        self.contact1 = Contact.objects.create(
            first_name="Test",
            last_name="User1",
            email="test1@example.com",
            date_of_birth="1990-01-01",
            address="123 Test St",
            mobile_number="555-0001",
            emergency_contact_name="Emergency Contact 1",
            emergency_contact_phone="555-0011",
            emergency_contact_relationship="Parent"
        )

        self.contact2 = Contact.objects.create(
            first_name="Test",
            last_name="User2",
            email="test2@example.com",
            date_of_birth="1985-01-01",
            address="456 Test Ave",
            mobile_number="555-0002",
            emergency_contact_name="Emergency Contact 2",
            emergency_contact_phone="555-0022",
            emergency_contact_relationship="Spouse"
        )
        
        # Create test tenants
        self.tenant1 = TenantAccount.objects.create(
            tenant_name="Test Tenant 1",
            tenant_slug="tenant1",
            primary_contact=self.contact1,
            billing_email="billing1@example.com",
            subscription_start_date=timezone.now().date(),
            max_member_accounts=100,
            max_clubs=5
        )
        
        self.tenant2 = TenantAccount.objects.create(
            tenant_name="Test Tenant 2", 
            tenant_slug="tenant2",
            primary_contact=self.contact2,
            billing_email="billing2@example.com",
            subscription_start_date=timezone.now().date(),
            max_member_accounts=50,
            max_clubs=3
        )
        
        # Create test member accounts
        self.member1 = MemberAccount.objects.create(
            tenant=self.tenant1,
            member_contact=self.contact1,
            primary_contact=self.contact1,  # Set primary_contact explicitly
            membership_number="M001",
            membership_type="student",
            membership_start_date=timezone.now().date(),
            billing_email="member1@example.com"
        )

        self.member2 = MemberAccount.objects.create(
            tenant=self.tenant2,
            member_contact=self.contact2,
            primary_contact=self.contact2,  # Set primary_contact explicitly
            membership_number="M002",
            membership_type="instructor",
            membership_start_date=timezone.now().date(),
            billing_email="member2@example.com"
        )
    
    def test_tenant_context_isolation(self):
        """Test that tenant context isolation works correctly."""
        # Test setting and getting tenant context
        set_current_tenant(self.tenant1)
        self.assertEqual(get_current_tenant(), self.tenant1)
        
        # Test clearing tenant context
        set_current_tenant(None)
        self.assertIsNone(get_current_tenant())
    
    def test_member_account_manager_filtering(self):
        """Test automatic tenant filtering in MemberAccount manager."""
        # Without tenant context, all_objects should return all members
        all_members = MemberAccount.all_objects.all()
        self.assertEqual(len(all_members), 2)
        
        # Set tenant context
        set_current_tenant(self.tenant1)
        
        # objects manager should only return members for current tenant
        tenant_members = MemberAccount.objects.all()
        self.assertEqual(len(tenant_members), 1)
        self.assertEqual(tenant_members[0].tenant, self.tenant1)
        
        # Change tenant context
        set_current_tenant(self.tenant2)
        
        tenant_members = MemberAccount.objects.all()
        self.assertEqual(len(tenant_members), 1)
        self.assertEqual(tenant_members[0].tenant, self.tenant2)
    
    def test_member_account_manager_methods(self):
        """Test enhanced MemberAccount manager methods."""
        set_current_tenant(self.tenant1)
        
        # Test get_active
        active_members = MemberAccount.objects.get_active()
        self.assertEqual(len(active_members), 1)
        self.assertTrue(active_members[0].is_active)
        
        # Test get_by_membership_type
        student_members = MemberAccount.objects.get_by_membership_type('student')
        self.assertEqual(len(student_members), 1)
        self.assertEqual(student_members[0].membership_type, 'student')
        
        instructor_members = MemberAccount.objects.get_by_membership_type('instructor') 
        self.assertEqual(len(instructor_members), 0)  # No instructors in tenant1
    
    def test_member_account_expiring_soon(self):
        """Test get_expiring_soon manager method."""
        # Set expiry date within 30 days
        expiry_date = timezone.now().date() + timedelta(days=15)
        self.member1.membership_end_date = expiry_date
        self.member1.save()
        
        set_current_tenant(self.tenant1)
        
        expiring_members = MemberAccount.objects.get_expiring_soon(30)
        self.assertEqual(len(expiring_members), 1)
        self.assertEqual(expiring_members[0], self.member1)
        
        # Test with shorter window
        expiring_members = MemberAccount.objects.get_expiring_soon(10)
        self.assertEqual(len(expiring_members), 0)

    def test_get_by_status_inactive(self):
        """Test filtering for inactive member accounts."""
        # Create additional contacts for test members
        contact3 = Contact.objects.create(
            first_name="Inactive",
            last_name="Member",
            email="inactive@example.com",
            date_of_birth="1992-01-01",
            address="789 Test Blvd",
            mobile_number="555-0003",
            emergency_contact_name="Emergency Contact 3",
            emergency_contact_phone="555-0033",
            emergency_contact_relationship="Friend"
        )

        # Create inactive member
        inactive_member = MemberAccount.objects.create(
            tenant=self.tenant1,
            member_contact=contact3,
            primary_contact=contact3,
            membership_number="M003",
            membership_type="student",
            membership_start_date=timezone.now().date() - timedelta(days=60),
            membership_end_date=timezone.now().date() + timedelta(days=30),
            billing_email="inactive@example.com",
            is_active=False  # Explicitly set to inactive
        )

        set_current_tenant(self.tenant1)

        # Test get_by_status for inactive members
        inactive_members = MemberAccount.objects.get_by_status("inactive")
        self.assertEqual(len(inactive_members), 1)
        self.assertEqual(inactive_members[0], inactive_member)
        self.assertFalse(inactive_members[0].is_active)

    def test_get_by_status_expired(self):
        """Test filtering for expired member accounts."""
        # Create contact for expired member
        contact4 = Contact.objects.create(
            first_name="Expired",
            last_name="Member",
            email="expired@example.com",
            date_of_birth="1988-01-01",
            address="321 Test Ln",
            mobile_number="555-0004",
            emergency_contact_name="Emergency Contact 4",
            emergency_contact_phone="555-0044",
            emergency_contact_relationship="Sibling"
        )

        # Create member with past end date (expired)
        expired_member = MemberAccount.objects.create(
            tenant=self.tenant1,
            member_contact=contact4,
            primary_contact=contact4,
            membership_number="M004",
            membership_type="student",
            membership_start_date=timezone.now().date() - timedelta(days=90),
            membership_end_date=timezone.now().date() - timedelta(days=5),  # Expired 5 days ago
            billing_email="expired@example.com",
            is_active=True  # Account is active but membership is expired
        )

        set_current_tenant(self.tenant1)

        # Test get_by_status for expired members
        expired_members = MemberAccount.objects.get_by_status("expired")
        self.assertEqual(len(expired_members), 1)
        self.assertEqual(expired_members[0], expired_member)
        self.assertTrue(expired_members[0].is_active)
        self.assertLess(expired_members[0].membership_end_date, timezone.now().date())

    def test_get_by_status_active(self):
        """Test filtering for active member accounts."""
        # Create contacts for active members
        contact5 = Contact.objects.create(
            first_name="Active",
            last_name="MemberFuture",
            email="active1@example.com",
            date_of_birth="1995-01-01",
            address="111 Test Dr",
            mobile_number="555-0005",
            emergency_contact_name="Emergency Contact 5",
            emergency_contact_phone="555-0055",
            emergency_contact_relationship="Parent"
        )

        contact6 = Contact.objects.create(
            first_name="Active",
            last_name="MemberIndefinite",
            email="active2@example.com",
            date_of_birth="1993-01-01",
            address="222 Test Ct",
            mobile_number="555-0006",
            emergency_contact_name="Emergency Contact 6",
            emergency_contact_phone="555-0066",
            emergency_contact_relationship="Spouse"
        )

        # Create member with future end date (active)
        active_member_future = MemberAccount.objects.create(
            tenant=self.tenant1,
            member_contact=contact5,
            primary_contact=contact5,
            membership_number="M005",
            membership_type="student",
            membership_start_date=timezone.now().date(),
            membership_end_date=timezone.now().date() + timedelta(days=60),  # Valid for 60 more days
            billing_email="active1@example.com",
            is_active=True
        )

        # Create member with no end date (indefinite/lifetime membership)
        active_member_indefinite = MemberAccount.objects.create(
            tenant=self.tenant1,
            member_contact=contact6,
            primary_contact=contact6,
            membership_number="M006",
            membership_type="lifetime",
            membership_start_date=timezone.now().date(),
            membership_end_date=None,  # No end date - indefinite membership
            billing_email="active2@example.com",
            is_active=True
        )

        set_current_tenant(self.tenant1)

        # Test get_by_status for active members
        active_members = MemberAccount.objects.get_by_status("active")

        # Should include: original member1, active_member_future, and active_member_indefinite
        self.assertEqual(len(active_members), 3)
        self.assertIn(self.member1, active_members)
        self.assertIn(active_member_future, active_members)
        self.assertIn(active_member_indefinite, active_members)

        # Verify all are actually active
        for member in active_members:
            self.assertTrue(member.is_active)

    def test_get_by_status_edge_case_today(self):
        """Test member with end date exactly today - should be active."""
        # Create contact for edge case member
        contact7 = Contact.objects.create(
            first_name="EdgeCase",
            last_name="Member",
            email="edgecase@example.com",
            date_of_birth="1991-01-01",
            address="333 Test Way",
            mobile_number="555-0007",
            emergency_contact_name="Emergency Contact 7",
            emergency_contact_phone="555-0077",
            emergency_contact_relationship="Friend"
        )

        # Create member with end date exactly today
        today_member = MemberAccount.objects.create(
            tenant=self.tenant1,
            member_contact=contact7,
            primary_contact=contact7,
            membership_number="M007",
            membership_type="student",
            membership_start_date=timezone.now().date() - timedelta(days=30),
            membership_end_date=timezone.now().date(),  # Ends today
            billing_email="edgecase@example.com",
            is_active=True
        )

        set_current_tenant(self.tenant1)

        # Member ending today should be considered active (inclusive)
        active_members = MemberAccount.objects.get_by_status("active")
        self.assertIn(today_member, active_members)

        # Should NOT be in expired
        expired_members = MemberAccount.objects.get_by_status("expired")
        self.assertNotIn(today_member, expired_members)

    def test_get_by_status_invalid(self):
        """Test with invalid status value returns empty queryset."""
        set_current_tenant(self.tenant1)

        # Test with invalid status
        result = MemberAccount.objects.get_by_status("invalid_status")
        self.assertEqual(len(result), 0)
        self.assertEqual(result.count(), 0)

        # Test with other invalid values
        result = MemberAccount.objects.get_by_status("")
        self.assertEqual(len(result), 0)

        result = MemberAccount.objects.get_by_status("ACTIVE")  # Case sensitive
        self.assertEqual(len(result), 0)

    def test_get_by_status_respects_tenant_filtering(self):
        """Test that get_by_status respects tenant filtering."""
        # Create contacts for multi-tenant test
        contact8 = Contact.objects.create(
            first_name="Tenant1",
            last_name="Inactive",
            email="t1inactive@example.com",
            date_of_birth="1987-01-01",
            address="444 Test Ave",
            mobile_number="555-0008",
            emergency_contact_name="Emergency Contact 8",
            emergency_contact_phone="555-0088",
            emergency_contact_relationship="Parent"
        )

        contact9 = Contact.objects.create(
            first_name="Tenant2",
            last_name="Inactive",
            email="t2inactive@example.com",
            date_of_birth="1986-01-01",
            address="555 Test Blvd",
            mobile_number="555-0009",
            emergency_contact_name="Emergency Contact 9",
            emergency_contact_phone="555-0099",
            emergency_contact_relationship="Sibling"
        )

        # Create inactive member in tenant1
        MemberAccount.objects.create(
            tenant=self.tenant1,
            member_contact=contact8,
            primary_contact=contact8,
            membership_number="M008",
            membership_type="student",
            membership_start_date=timezone.now().date(),
            billing_email="t1inactive@example.com",
            is_active=False
        )

        # Create inactive member in tenant2
        MemberAccount.objects.create(
            tenant=self.tenant2,
            member_contact=contact9,
            primary_contact=contact9,
            membership_number="M009",
            membership_type="instructor",
            membership_start_date=timezone.now().date(),
            billing_email="t2inactive@example.com",
            is_active=False
        )

        # Test with tenant1 context
        set_current_tenant(self.tenant1)
        inactive_members = MemberAccount.objects.get_by_status("inactive")
        self.assertEqual(len(inactive_members), 1)
        self.assertEqual(inactive_members[0].tenant, self.tenant1)

        # Test with tenant2 context
        set_current_tenant(self.tenant2)
        inactive_members = MemberAccount.objects.get_by_status("inactive")
        self.assertEqual(len(inactive_members), 1)
        self.assertEqual(inactive_members[0].tenant, self.tenant2)

        # Test without tenant context - should see all via all_objects
        set_current_tenant(None)
        all_inactive = MemberAccount.all_objects.filter(is_active=False)
        self.assertEqual(len(all_inactive), 2)


class TenantCacheManagerTestCase(TestCase):
    """Test tenant caching functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.contact1 = Contact.objects.create(
            first_name="Cache",
            last_name="Test",
            email="cache@example.com",
            date_of_birth="1990-01-01",
            address="789 Cache St",
            mobile_number="555-0003"
        )
        
        self.tenant1 = TenantAccount.objects.create(
            tenant_name="Cache Test Tenant",
            tenant_slug="cache-test",
            primary_contact=self.contact1,
            billing_email="cache@example.com",
            subscription_start_date=timezone.now().date(),
            max_member_accounts=50,
            max_clubs=2
        )
    
    def test_get_tenant_by_slug_caching(self):
        """Test tenant lookup caching."""
        # First lookup should hit database
        tenant = TenantCacheManager.get_tenant_by_slug('cache-test')
        self.assertEqual(tenant, self.tenant1)
        
        # Second lookup should use cache
        tenant2 = TenantCacheManager.get_tenant_by_slug('cache-test')
        self.assertEqual(tenant2, self.tenant1)
    
    def test_get_tenant_by_slug_not_found(self):
        """Test tenant lookup for non-existent slug."""
        tenant = TenantCacheManager.get_tenant_by_slug('non-existent')
        self.assertIsNone(tenant)
    
    def test_invalidate_tenant_cache(self):
        """Test tenant cache invalidation."""
        # Populate cache
        TenantCacheManager.get_tenant_by_slug('cache-test')
        
        # Invalidate cache
        TenantCacheManager.invalidate_tenant_cache('cache-test')
        
        # Next lookup should hit database again
        tenant = TenantCacheManager.get_tenant_by_slug('cache-test')
        self.assertEqual(tenant, self.tenant1)


@override_settings(ALLOWED_HOSTS=['*'])
class TenantMiddlewareTestCase(TestCase):
    """Test tenant context middleware."""
    
    def setUp(self):
        """Set up test data and request factory."""
        self.factory = RequestFactory()
        self.middleware = TenantContextMiddleware(lambda r: None)
        
        self.contact1 = Contact.objects.create(
            first_name="Middleware",
            last_name="Test", 
            email="middleware@example.com",
            date_of_birth="1990-01-01",
            address="321 Middleware St",
            mobile_number="555-0004"
        )
        
        self.tenant1 = TenantAccount.objects.create(
            tenant_name="Middleware Test Tenant",
            tenant_slug="middleware-test",
            primary_contact=self.contact1,
            billing_email="middleware@example.com",
            subscription_start_date=timezone.now().date(),
            max_member_accounts=75,
            max_clubs=4
        )
    
    def test_get_tenant_from_subdomain(self):
        """Test tenant detection from subdomain."""
        request = self.factory.get('/', HTTP_HOST='middleware-test.onespirit.com')
        tenant = self.middleware._get_tenant_from_subdomain(request)
        self.assertEqual(tenant, self.tenant1)
        
        # Test invalid subdomain
        request = self.factory.get('/', HTTP_HOST='nonexistent.onespirit.com')
        tenant = self.middleware._get_tenant_from_subdomain(request)
        self.assertIsNone(tenant)
    
    def test_get_tenant_from_path(self):
        """Test tenant detection from URL path.""" 
        request = self.factory.get('/tenant/middleware-test/members/')
        tenant = self.middleware._get_tenant_from_path(request)
        self.assertEqual(tenant, self.tenant1)
        
        # Test invalid path
        request = self.factory.get('/tenant/nonexistent/members/')
        tenant = self.middleware._get_tenant_from_path(request)
        self.assertIsNone(tenant)
    
    def test_middleware_sets_tenant_context(self):
        """Test that middleware properly sets tenant context."""
        # Create a simple response function that checks tenant context
        def get_response(request):
            from django.http import HttpResponse
            current_tenant = get_current_tenant() 
            return HttpResponse(f"Tenant: {current_tenant.tenant_slug if current_tenant else 'None'}")
        
        middleware = TenantContextMiddleware(get_response)
        
        # Test with subdomain
        request = self.factory.get('/', HTTP_HOST='middleware-test.onespirit.com')
        response = middleware(request)
        
        self.assertIn(b'middleware-test', response.content)
        self.assertTrue(hasattr(request, 'tenant'))
        self.assertEqual(request.tenant, self.tenant1)


class TenantIsolationIntegrationTestCase(TestCase):
    """Integration tests for complete tenant isolation functionality."""
    
    def setUp(self):
        """Set up comprehensive test data."""
        # Create contacts
        self.contact1 = Contact.objects.create(
            first_name="Integration",
            last_name="Test1",
            email="integration1@example.com",
            date_of_birth="1990-01-01",
            address="111 Integration St",
            mobile_number="555-0005",
            emergency_contact_name="Emergency 1",
            emergency_contact_phone="555-1001",
            emergency_contact_relationship="Parent"
        )

        self.contact2 = Contact.objects.create(
            first_name="Integration",
            last_name="Test2",
            email="integration2@example.com",
            date_of_birth="1990-01-01",
            address="222 Integration Ave",
            mobile_number="555-0006",
            emergency_contact_name="Emergency 2",
            emergency_contact_phone="555-1002",
            emergency_contact_relationship="Self"
        )
        
        # Create tenants
        self.tenant1 = TenantAccount.objects.create(
            tenant_name="Integration Tenant 1",
            tenant_slug="integration1",
            primary_contact=self.contact1,
            billing_email="billing1@integration.com",
            subscription_start_date=timezone.now().date(),
            max_member_accounts=100,
            max_clubs=10
        )
        
        self.tenant2 = TenantAccount.objects.create(
            tenant_name="Integration Tenant 2",
            tenant_slug="integration2", 
            primary_contact=self.contact2,
            billing_email="billing2@integration.com",
            subscription_start_date=timezone.now().date(),
            max_member_accounts=200,
            max_clubs=20
        )
        
        # Create member accounts for both tenants
        self.member1_t1 = MemberAccount.objects.create(
            tenant=self.tenant1,
            member_contact=self.contact1,
            primary_contact=self.contact1,  # Set primary_contact explicitly
            membership_number="INT001",
            membership_type="student",
            membership_start_date=timezone.now().date(),
            billing_email="integration1@example.com"
        )

        self.member2_t2 = MemberAccount.objects.create(
            tenant=self.tenant2,
            member_contact=self.contact2,
            primary_contact=self.contact2,  # Set primary_contact explicitly
            membership_number="INT002",
            membership_type="instructor",
            membership_start_date=timezone.now().date(),
            billing_email="integration2@example.com"
        )
    
    def test_complete_tenant_isolation(self):
        """Test complete tenant isolation workflow."""
        # Verify all objects manager sees everything
        all_members = MemberAccount.all_objects.all()
        self.assertEqual(len(all_members), 2)
        
        # Set tenant 1 context
        set_current_tenant(self.tenant1)
        
        # Verify only tenant 1 members are visible
        tenant1_members = MemberAccount.objects.all()
        self.assertEqual(len(tenant1_members), 1)
        self.assertEqual(tenant1_members[0].tenant, self.tenant1)
        self.assertEqual(tenant1_members[0].membership_number, "INT001")
        
        # Switch to tenant 2 context
        set_current_tenant(self.tenant2)
        
        # Verify only tenant 2 members are visible
        tenant2_members = MemberAccount.objects.all()
        self.assertEqual(len(tenant2_members), 1)
        self.assertEqual(tenant2_members[0].tenant, self.tenant2)
        self.assertEqual(tenant2_members[0].membership_number, "INT002")
        
        # Clear tenant context
        set_current_tenant(None)
        
        # Verify no automatic filtering without context
        no_context_members = MemberAccount.objects.all()
        self.assertEqual(len(no_context_members), 2)  # Should see all without filtering
    
    def test_tenant_switching_isolation(self):
        """Test rapid tenant context switching maintains proper isolation."""
        # Rapid switching test
        for _ in range(5):
            set_current_tenant(self.tenant1)
            t1_members = MemberAccount.objects.all()
            self.assertEqual(len(t1_members), 1)
            self.assertEqual(t1_members[0].tenant, self.tenant1)
            
            set_current_tenant(self.tenant2)
            t2_members = MemberAccount.objects.all()
            self.assertEqual(len(t2_members), 1)
            self.assertEqual(t2_members[0].tenant, self.tenant2)
        
        # Final verification
        set_current_tenant(None)
        final_count = MemberAccount.all_objects.count()
        self.assertEqual(final_count, 2)