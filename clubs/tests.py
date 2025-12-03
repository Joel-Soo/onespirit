from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from accounts.models import TenantAccount, MemberAccount
from people.models import Contact, UserProfile
from organizations.models import Organization
from .models import Club, ClubStaff, ClubMember, ClubAffiliation


class ClubModelTestCase(TestCase):
    def setUp(self):
        # Create test tenant
        self.tenant = TenantAccount.objects.create(
            tenant_name="Test Martial Arts",
            tenant_slug="test-martial-arts",
            billing_email="billing@test.com",
            subscription_start_date=timezone.now().date()
        )

        # Create test contact
        self.contact = Contact.objects.create(
            first_name="John",
            last_name="Sensei",
            email="john@test.com",
            date_of_birth="1980-01-01",
            address="123 Test St",
            mobile_number="123-456-7890",
            tenant=self.tenant
        )

        # Set contact as primary contact for tenant
        self.tenant.primary_contact = self.contact
        self.tenant.save()

    def test_club_creation_inherits_from_organization(self):
        """Test that Club properly inherits from Organization"""
        club = Club.objects.create(
            name="Test Dojo",
            slug="test-dojo",
            tenant=self.tenant,
            description="Test martial arts club"
        )

        # Test inheritance properties
        self.assertIsInstance(club, Organization)
        self.assertEqual(club.name, "Test Dojo")
        self.assertEqual(club.slug, "test-dojo")
        self.assertTrue(club.is_active)
        self.assertEqual(club.tenant, self.tenant)

    def test_club_quota_enforcement(self):
        """Test tenant club quota is enforced"""
        # Create max_clubs (5) clubs
        for i in range(5):
            Club.objects.create(
                name=f"Club {i}",
                slug=f"club-{i}",
                tenant=self.tenant
            )

        # Attempt to create 6th club should fail
        club6 = Club(
            name="Club 6",
            slug="club-6",
            tenant=self.tenant
        )

        with self.assertRaises(ValidationError):
            club6.full_clean()

    def test_club_member_relationship_via_contact(self):
        """Test that club members are tracked via Contact.organization relationship"""
        club = Club.objects.create(
            name="Test Club",
            slug="test-club",
            tenant=self.tenant
        )

        # Link contact to club organization
        self.contact.organization = club
        self.contact.save()

        # Test member count
        self.assertEqual(club.member_count, 1)

    def test_club_staff_permissions(self):
        """Test club staff role permissions"""
        user = User.objects.create_user("teststaff", "staff@test.com")
        login_user = UserProfile.objects.create(user=user, contact=self.contact)

        club = Club.objects.create(
            name="Test Club",
            slug="test-club",
            tenant=self.tenant
        )

        staff = ClubStaff.objects.create(
            club=club,
            user=login_user,
            role='owner'
        )

        # Owner role should auto-set permissions
        self.assertTrue(staff.can_manage_members)
        self.assertTrue(staff.can_manage_schedule)
        self.assertTrue(staff.can_view_finances)

    def test_club_member_account_integration(self):
        """Test ClubMember through model works with MemberAccount"""
        club = Club.objects.create(
            name="Test Club",
            slug="test-club",
            tenant=self.tenant
        )

        member_account = MemberAccount.objects.create(
            tenant=self.tenant,
            member_contact=self.contact,
            primary_contact=self.contact,
            billing_email="member@test.com",
            membership_number="TEST001",
            membership_start_date=timezone.now().date()
        )

        club_member = ClubMember.objects.create(
            club=club,
            member_account=member_account,
            status='active'
        )

        # Test relationship
        self.assertEqual(club_member.club, club)
        self.assertEqual(club_member.member_account, member_account)
        self.assertTrue(club_member.membership_number)  # Should be auto-generated

    def test_club_affiliation_prevents_self_reference(self):
        """Test that clubs cannot affiliate with themselves"""
        club = Club.objects.create(
            name="Test Club",
            slug="test-club",
            tenant=self.tenant
        )

        affiliation = ClubAffiliation(
            club_primary=club,
            club_secondary=club,
            affiliation_type='partner'
        )

        with self.assertRaises(ValidationError):
            affiliation.full_clean()

    def test_social_media_handle_validation(self):
        """Test that social media handles are validated correctly"""
        club = Club(
            name="Test Club",
            slug="test-club",
            tenant=self.tenant,
            instagram_handle="@invalid_handle",  # Should not start with @
            twitter_handle="@also_invalid"       # Should not start with @
        )

        with self.assertRaises(ValidationError):
            club.full_clean()


class ClubQueryTestCase(TestCase):
    def setUp(self):
        # Create two separate tenants
        self.tenant1 = TenantAccount.objects.create(
            tenant_name="Tenant 1",
            tenant_slug="tenant-1",
            billing_email="billing1@test.com",
            subscription_start_date=timezone.now().date()
        )

        self.tenant2 = TenantAccount.objects.create(
            tenant_name="Tenant 2",
            tenant_slug="tenant-2",
            billing_email="billing2@test.com",
            subscription_start_date=timezone.now().date()
        )

        # Create clubs for each tenant
        self.club1 = Club.objects.create(
            name="Club 1",
            slug="club-1",
            tenant=self.tenant1
        )

        self.club2 = Club.objects.create(
            name="Club 2",
            slug="club-2",
            tenant=self.tenant2
        )

    def test_club_string_representation(self):
        """Test Club __str__ method"""
        self.assertEqual(str(self.club1), "Club 1")
        self.assertEqual(str(self.club2), "Club 2")

    def test_club_properties(self):
        """Test Club property methods"""
        # Test member_count and staff_count properties
        self.assertEqual(self.club1.member_count, 0)
        self.assertEqual(self.club1.staff_count, 0)


class ClubTenantIsolationTestCase(TestCase):
    def setUp(self):
        # Create two separate tenants
        self.tenant1 = TenantAccount.objects.create(
            tenant_name="Tenant 1",
            tenant_slug="tenant-1",
            billing_email="billing1@test.com",
            subscription_start_date=timezone.now().date()
        )

        self.tenant2 = TenantAccount.objects.create(
            tenant_name="Tenant 2",
            tenant_slug="tenant-2",
            billing_email="billing2@test.com",
            subscription_start_date=timezone.now().date()
        )

        # Create contacts for each tenant
        self.contact1 = Contact.objects.create(
            first_name="John",
            last_name="Staff1",
            email="staff1@test.com",
            date_of_birth="1980-01-01",
            address="123 Test St",
            mobile_number="123-456-7890",
            tenant=self.tenant1
        )

        self.contact2 = Contact.objects.create(
            first_name="Jane",
            last_name="Staff2",
            email="staff2@test.com",
            date_of_birth="1981-01-01",
            address="456 Test Ave",
            mobile_number="987-654-3210",
            tenant=self.tenant2
        )

        # Create clubs for each tenant
        self.club1 = Club.objects.create(
            name="Club 1",
            slug="club-1",
            tenant=self.tenant1
        )

        self.club2 = Club.objects.create(
            name="Club 2",
            slug="club-2",
            tenant=self.tenant2
        )

        # Create users and staff assignments
        user1 = User.objects.create_user("staff1", "staff1@test.com")
        self.user_profile1 = UserProfile.objects.create(user=user1, contact=self.contact1)

        user2 = User.objects.create_user("staff2", "staff2@test.com")
        self.user_profile2 = UserProfile.objects.create(user=user2, contact=self.contact2)

        # Create staff assignments
        self.staff1 = ClubStaff.objects.create(
            club=self.club1,
            user=self.user_profile1,
            role='instructor'
        )

        self.staff2 = ClubStaff.objects.create(
            club=self.club2,
            user=self.user_profile2,
            role='admin'
        )

    def test_club_staff_tenant_isolation_without_context(self):
        """Test ClubStaff queries without tenant context (should see all)"""
        # Without tenant context, should see all staff
        all_staff = ClubStaff.objects.all()
        self.assertEqual(all_staff.count(), 2)

    def test_club_staff_tenant_isolation_with_context(self):
        """Test ClubStaff queries with tenant context (should be filtered)"""
        from accounts.managers import set_current_tenant

        # Set tenant 1 context
        set_current_tenant(self.tenant1)

        # Should only see staff from tenant 1
        tenant1_staff = ClubStaff.objects.all()
        self.assertEqual(tenant1_staff.count(), 1)
        self.assertEqual(tenant1_staff.first(), self.staff1)

        # Set tenant 2 context
        set_current_tenant(self.tenant2)

        # Should only see staff from tenant 2
        tenant2_staff = ClubStaff.objects.all()
        self.assertEqual(tenant2_staff.count(), 1)
        self.assertEqual(tenant2_staff.first(), self.staff2)

        # Clear context
        set_current_tenant(None)

    def test_club_affiliation_tenant_isolation(self):
        """Test ClubAffiliation tenant isolation"""
        from accounts.managers import set_current_tenant

        # Create same-tenant affiliation (cross-tenant affiliations are now disallowed)
        club2_tenant1 = Club.objects.create(
            name="Club 2 - T1",
            slug="club-2-t1",
            tenant=self.tenant1
        )
        affiliation = ClubAffiliation.objects.create(
            club_primary=self.club1,
            club_secondary=club2_tenant1,
            affiliation_type='partner'
        )

        # Set tenant 1 context - should see affiliation since club_primary is in tenant1
        set_current_tenant(self.tenant1)
        tenant1_affiliations = ClubAffiliation.objects.all()
        self.assertEqual(tenant1_affiliations.count(), 1)
        self.assertEqual(tenant1_affiliations.first(), affiliation)

        # Set tenant 2 context - should NOT see affiliation since club_primary is in tenant1
        set_current_tenant(self.tenant2)
        tenant2_affiliations = ClubAffiliation.objects.all()
        self.assertEqual(tenant2_affiliations.count(), 0)

        # Clear context
        set_current_tenant(None)


class ClubStaffFilteringTestCase(TestCase):
    def setUp(self):
        # Create two separate tenants
        self.tenant1 = TenantAccount.objects.create(
            tenant_name="Tenant 1",
            tenant_slug="tenant-1",
            billing_email="billing1@test.com",
            subscription_start_date=timezone.now().date()
        )

        self.tenant2 = TenantAccount.objects.create(
            tenant_name="Tenant 2",
            tenant_slug="tenant-2",
            billing_email="billing2@test.com",
            subscription_start_date=timezone.now().date()
        )

        # Create contacts for each tenant
        self.contact1 = Contact.objects.create(
            first_name="John",
            last_name="Staff1",
            email="staff1@test.com",
            date_of_birth="1980-01-01",
            address="123 Test St",
            mobile_number="123-456-7890",
            tenant=self.tenant1
        )

        self.contact2 = Contact.objects.create(
            first_name="Jane",
            last_name="Staff2",
            email="staff2@test.com",
            date_of_birth="1981-01-01",
            address="456 Test Ave",
            mobile_number="987-654-3210",
            tenant=self.tenant1
        )

        self.contact3 = Contact.objects.create(
            first_name="Bob",
            last_name="Admin",
            email="admin@test.com",
            date_of_birth="1975-01-01",
            address="789 Admin St",
            mobile_number="555-123-4567",
            tenant=self.tenant1
        )

        # Create clubs
        self.club1 = Club.objects.create(
            name="Club 1",
            slug="club-1",
            tenant=self.tenant1
        )

        self.club2 = Club.objects.create(
            name="Club 2",
            slug="club-2",
            tenant=self.tenant1
        )

        self.club3 = Club.objects.create(
            name="Club 3",
            slug="club-3",
            tenant=self.tenant2
        )

        # Create users and login users
        self.user1 = User.objects.create_user("staff1", "staff1@test.com")
        self.user_profile1 = UserProfile.objects.create(
            user=self.user1,
            contact=self.contact1,
        )

        self.user2 = User.objects.create_user("staff2", "staff2@test.com")
        self.user_profile2 = UserProfile.objects.create(
            user=self.user2,
            contact=self.contact2,
        )

        self.user3 = User.objects.create_user("admin", "admin@test.com")
        self.user_profile3 = UserProfile.objects.create(
            user=self.user3,
            contact=self.contact3,
        )
        self.user_profile3.is_system_admin = True
        self.user_profile3.can_create_clubs = True
        self.user_profile3.can_manage_members = True
        self.user_profile3.save(update_fields=['is_system_admin','can_create_clubs','can_manage_members'])

        # Create staff assignments
        self.staff1_club1 = ClubStaff.objects.create(
            club=self.club1,
            user=self.user_profile1,
            role='instructor'
        )

        self.staff2_club2 = ClubStaff.objects.create(
            club=self.club2,
            user=self.user_profile2,
            role='instructor'
        )

        # Create some club members
        from accounts.models import MemberAccount
        self.member_account1 = MemberAccount.objects.create(
            tenant=self.tenant1,
            member_contact=self.contact1,
            primary_contact=self.contact1,
            billing_email="member1@test.com",
            membership_number="MEM001",
            membership_start_date=timezone.now().date()
        )

        self.club_member1 = ClubMember.objects.create(
            club=self.club1,
            member_account=self.member_account1,
            status='active'
        )

        self.member_account2 = MemberAccount.objects.create(
            tenant=self.tenant1,
            member_contact=self.contact2,
            primary_contact=self.contact2,
            billing_email="member2@test.com",
            membership_number="MEM002",
            membership_start_date=timezone.now().date()
        )

        self.club_member2 = ClubMember.objects.create(
            club=self.club2,
            member_account=self.member_account2,
            status='active'
        )

    def test_club_staff_filtering_without_user_context(self):
        """Test that without user context, staff can see all club entities (within tenant)"""
        from clubs.models import set_current_user
        from accounts.managers import set_current_tenant

        # Set tenant context but no user context
        set_current_tenant(self.tenant1)
        set_current_user(None)

        # Should see all staff within tenant (no user-based filtering)
        all_staff = ClubStaff.objects.all()
        self.assertEqual(all_staff.count(), 2)

        # Should see all members within tenant (no user-based filtering)
        all_members = ClubMember.objects.all()
        self.assertEqual(all_members.count(), 2)

    def test_club_staff_filtering_with_regular_user_context(self):
        """Test that regular staff users only see entities from their assigned clubs"""
        from clubs.models import set_current_user
        from accounts.managers import set_current_tenant

        # Set tenant context and user1 context (staff for club1 only)
        set_current_tenant(self.tenant1)
        set_current_user(self.user1)

        # Should only see staff from club1 (where user1 is assigned)
        filtered_staff = ClubStaff.objects.all()
        self.assertEqual(filtered_staff.count(), 1)
        self.assertEqual(filtered_staff.first(), self.staff1_club1)

        # Should only see members from club1 (where user1 is assigned)
        filtered_members = ClubMember.objects.all()
        self.assertEqual(filtered_members.count(), 1)
        self.assertEqual(filtered_members.first(), self.club_member1)

        # Switch to user2 context (staff for club2 only)
        set_current_user(self.user2)

        # Should only see staff from club2 (where user2 is assigned)
        filtered_staff = ClubStaff.objects.all()
        self.assertEqual(filtered_staff.count(), 1)
        self.assertEqual(filtered_staff.first(), self.staff2_club2)

        # Should only see members from club2 (where user2 is assigned)
        filtered_members = ClubMember.objects.all()
        self.assertEqual(filtered_members.count(), 1)
        self.assertEqual(filtered_members.first(), self.club_member2)

    def test_club_staff_filtering_with_admin_user_context(self):
        """Test that admin users see all entities within tenant (no club restrictions)"""
        from clubs.models import set_current_user
        from accounts.managers import set_current_tenant

        # Set tenant context and admin user context
        set_current_tenant(self.tenant1)
        set_current_user(self.user3)

        # Admin should see all staff within tenant
        admin_staff = ClubStaff.objects.all()
        self.assertEqual(admin_staff.count(), 2)

        # Admin should see all members within tenant
        admin_members = ClubMember.objects.all()
        self.assertEqual(admin_members.count(), 2)

    def test_club_staff_filtering_with_superuser_context(self):
        """Test that superusers see all entities within tenant (no club restrictions)"""
        from clubs.models import set_current_user
        from accounts.managers import set_current_tenant

        # Make user1 a superuser
        self.user1.is_superuser = True
        self.user1.save()

        # Set tenant context and superuser context
        set_current_tenant(self.tenant1)
        set_current_user(self.user1)

        # Superuser should see all staff within tenant
        super_staff = ClubStaff.objects.all()
        self.assertEqual(super_staff.count(), 2)

        # Superuser should see all members within tenant
        super_members = ClubMember.objects.all()
        self.assertEqual(super_members.count(), 2)

    def test_club_staff_filtering_user_without_club_assignments(self):
        """Test that users without club assignments see no entities"""
        from clubs.models import set_current_user
        from accounts.managers import set_current_tenant

        # Create a user with no club assignments
        user_no_clubs = User.objects.create_user("noclub", "noclub@test.com")
        contact_no_clubs = Contact.objects.create(
            first_name="No",
            last_name="Clubs",
            email="noclub@test.com",
            date_of_birth="1990-01-01",
            address="999 No Club St",
            mobile_number="999-999-9999",
            tenant=self.tenant1
        )
        user_profile_no_clubs = UserProfile.objects.create(
            user=user_no_clubs,
            contact=contact_no_clubs,
        )

        # Set tenant context and no-clubs user context
        set_current_tenant(self.tenant1)
        set_current_user(user_no_clubs)

        # Should see no staff (user has no club assignments)
        no_staff = ClubStaff.objects.all()
        self.assertEqual(no_staff.count(), 0)

        # Should see no members (user has no club assignments)
        no_members = ClubMember.objects.all()
        self.assertEqual(no_members.count(), 0)

    def test_club_staff_filtering_user_without_login_profile(self):
        """Test that Django users without UserProfile profiles see no entities"""
        from clubs.models import set_current_user
        from accounts.managers import set_current_tenant

        # Create a Django user without UserProfile profile
        user_no_profile = User.objects.create_user("noprofile", "noprofile@test.com")

        # Set tenant context and no-profile user context
        set_current_tenant(self.tenant1)
        set_current_user(user_no_profile)

        # Should see no staff (user has no UserProfile profile)
        no_staff = ClubStaff.objects.all()
        self.assertEqual(no_staff.count(), 0)

        # Should see no members (user has no UserProfile profile)
        no_members = ClubMember.objects.all()
        self.assertEqual(no_members.count(), 0)

    def test_club_staff_filtering_all_objects_manager_bypass(self):
        """Test that all_objects manager bypasses user filtering"""
        from clubs.models import set_current_user
        from accounts.managers import set_current_tenant

        # Set tenant context and restricted user context
        set_current_tenant(self.tenant1)
        set_current_user(self.user1)  # Only has access to club1

        # Regular manager should be filtered
        filtered_staff = ClubStaff.objects.all()
        self.assertEqual(filtered_staff.count(), 1)

        # all_objects manager should bypass filtering
        all_staff = ClubStaff.all_objects.all()
        self.assertEqual(all_staff.count(), 2)  # All staff across all tenants

    def tearDown(self):
        """Clean up context after each test"""
        from clubs.models import set_current_user
        from accounts.managers import set_current_tenant

        set_current_tenant(None)
        set_current_user(None)


class ClubStaffOrganizationUserTestCase(TestCase):
    def setUp(self):
        # Create tenant
        self.tenant = TenantAccount.objects.create(
            tenant_name="Test Tenant",
            tenant_slug="test-tenant",
            billing_email="billing@test.com",
            subscription_start_date=timezone.now().date()
        )

        # Create contacts
        self.contact1 = Contact.objects.create(
            first_name="John",
            last_name="Owner",
            email="owner@test.com",
            date_of_birth="1980-01-01",
            address="123 Test St",
            mobile_number="123-456-7890",
            tenant=self.tenant
        )

        self.contact2 = Contact.objects.create(
            first_name="Jane",
            last_name="Admin",
            email="admin@test.com",
            date_of_birth="1981-01-01",
            address="456 Test Ave",
            mobile_number="987-654-3210",
            tenant=self.tenant
        )

        # Create club
        self.club = Club.objects.create(
            name="Test Club",
            slug="test-club",
            tenant=self.tenant
        )

        # Create Django users and UserProfiles
        self.django_user1 = User.objects.create_user("owner", "owner@test.com")
        self.user_profile1 = UserProfile.objects.create(
            user=self.django_user1,
            contact=self.contact1,
        )
        self.user_profile1.is_club_owner = True
        self.user_profile1.can_create_clubs = True
        self.user_profile1.can_manage_members = True
        self.user_profile1.save(update_fields=['is_club_owner','can_create_clubs','can_manage_members'])

        self.django_user2 = User.objects.create_user("admin", "admin@test.com")
        self.user_profile2 = UserProfile.objects.create(
            user=self.django_user2,
            contact=self.contact2,
        )
        self.user_profile2.is_system_admin = True
        self.user_profile2.can_create_clubs = True
        self.user_profile2.can_manage_members = True
        self.user_profile2.save(update_fields=['is_system_admin','can_create_clubs','can_manage_members'])

        # Create OrganizationUsers for the club (since Club inherits from Organization)
        from organizations.models import OrganizationUser
        self.org_user1 = OrganizationUser.objects.create(
            user=self.django_user1,
            organization=self.club,
            is_admin=False
        )

        self.org_user2 = OrganizationUser.objects.create(
            user=self.django_user2,
            organization=self.club,
            is_admin=True
        )

    def test_club_staff_creation_with_organization_user(self):
        """Test creating ClubStaff with valid OrganizationUser"""
        staff = ClubStaff.objects.create(
            club=self.club,
            user=self.user_profile1,
            organization_user=self.org_user1,
            role='instructor'
        )

        self.assertEqual(staff.organization_user, self.org_user1)
        self.assertEqual(staff.user.user, self.org_user1.user)
        self.assertEqual(staff.club, self.org_user1.organization)

    def test_club_staff_creation_without_organization_user(self):
        """Test creating ClubStaff without OrganizationUser (should be allowed)"""
        staff = ClubStaff.objects.create(
            club=self.club,
            user=self.user_profile1,
            role='instructor'
        )

        self.assertIsNone(staff.organization_user)
        self.assertEqual(staff.club, self.club)
        self.assertEqual(staff.user, self.user_profile1)

    def test_organization_user_validation_mismatched_django_user(self):
        """Test validation fails when Django Users don't match"""
        from organizations.models import OrganizationUser

        # Create another user for mismatch
        other_django_user = User.objects.create_user("other", "other@test.com")
        other_org_user = OrganizationUser.objects.create(
            user=other_django_user,
            organization=self.club,
            is_admin=False
        )

        staff = ClubStaff(
            club=self.club,
            user=self.user_profile1,  # Uses django_user1
            organization_user=other_org_user,  # Uses other_django_user
            role='instructor'
        )

        with self.assertRaises(ValidationError) as cm:
            staff.full_clean()

        self.assertIn("OrganizationUser must belong to the same Django User", str(cm.exception))

    def test_organization_user_validation_mismatched_organization(self):
        """Test validation fails when Organizations don't match"""
        from organizations.models import OrganizationUser

        # Create another club/organization
        other_club = Club.objects.create(
            name="Other Club",
            slug="other-club",
            tenant=self.tenant
        )

        other_org_user = OrganizationUser.objects.create(
            user=self.django_user1,
            organization=other_club,  # Different organization
            is_admin=False
        )

        staff = ClubStaff(
            club=self.club,  # Using self.club
            user=self.user_profile1,
            organization_user=other_org_user,  # Links to other_club
            role='instructor'
        )

        with self.assertRaises(ValidationError) as cm:
            staff.full_clean()

        self.assertIn("OrganizationUser must belong to the same Organization", str(cm.exception))

    def test_organization_admin_detection(self):
        """Test is_organization_admin method"""
        # Create additional user to avoid unique constraint violation
        no_org_user = User.objects.create_user("no_org_test", "no_org_test@test.com")
        no_org_contact = Contact.objects.create(
            first_name="NoOrg",
            last_name="Test",
            email="no_org_test@test.com",
            date_of_birth="1983-01-01",
            address="600 NoOrg St",
            mobile_number="600-600-6000",
            tenant=self.tenant
        )
        no_org_login = UserProfile.objects.create(
            user=no_org_user,
            contact=no_org_contact,
        )

        # Staff with organization admin
        staff_admin = ClubStaff.objects.create(
            club=self.club,
            user=self.user_profile2,
            organization_user=self.org_user2,  # is_admin=True
            role='instructor'
        )

        # Staff with regular organization member
        staff_member = ClubStaff.objects.create(
            club=self.club,
            user=self.user_profile1,
            organization_user=self.org_user1,  # is_admin=False
            role='instructor'
        )

        # Staff without organization user
        staff_no_org = ClubStaff.objects.create(
            club=self.club,
            user=no_org_login,
            role='assistant'
        )

        self.assertTrue(staff_admin.is_organization_admin())
        self.assertFalse(staff_member.is_organization_admin())
        self.assertFalse(staff_no_org.is_organization_admin())

    def test_permission_hierarchy_levels(self):
        """Test permission hierarchy level calculation"""
        # Create additional users for different roles to avoid unique constraint violations
        # Create superuser
        superuser = User.objects.create_user("super", "super@test.com", is_superuser=True)
        super_contact = Contact.objects.create(
            first_name="Super",
            last_name="User",
            email="super@test.com",
            date_of_birth="1975-01-01",
            address="789 Super St",
            mobile_number="555-123-4567",
            tenant=self.tenant
        )
        super_login = UserProfile.objects.create(
            user=superuser,
            contact=super_contact,
        )
        super_login.is_system_admin = True
        super_login.can_create_clubs = True
        super_login.can_manage_members = True
        super_login.save(update_fields=['is_system_admin','can_create_clubs','can_manage_members'])

        # Create additional users for different roles
        owner_user = User.objects.create_user("owner_test", "owner_test@test.com")
        owner_contact = Contact.objects.create(
            first_name="Owner",
            last_name="Test",
            email="owner_test@test.com",
            date_of_birth="1976-01-01",
            address="111 Owner St",
            mobile_number="111-111-1111",
            tenant=self.tenant
        )
        owner_login = UserProfile.objects.create(
            user=owner_user,
            contact=owner_contact,
        )
        owner_login.is_club_owner = True
        owner_login.can_create_clubs = True
        owner_login.can_manage_members = True
        owner_login.save(update_fields=['is_club_owner','can_create_clubs','can_manage_members'])

        admin_user = User.objects.create_user("admin_test", "admin_test@test.com")
        admin_contact = Contact.objects.create(
            first_name="Admin",
            last_name="Test",
            email="admin_test@test.com",
            date_of_birth="1977-01-01",
            address="222 Admin St",
            mobile_number="222-222-2222",
            tenant=self.tenant
        )
        admin_login = UserProfile.objects.create(
            user=admin_user,
            contact=admin_contact,
        )
        admin_login.is_system_admin = True
        admin_login.can_create_clubs = True
        admin_login.can_manage_members = True
        admin_login.save(update_fields=['is_system_admin','can_create_clubs','can_manage_members'])

        instructor_user = User.objects.create_user("instructor_test", "instructor_test@test.com")
        instructor_contact = Contact.objects.create(
            first_name="Instructor",
            last_name="Test",
            email="instructor_test@test.com",
            date_of_birth="1978-01-01",
            address="333 Instructor St",
            mobile_number="333-333-3333",
            tenant=self.tenant
        )
        instructor_login = UserProfile.objects.create(
            user=instructor_user,
            contact=instructor_contact,
        )

        assistant_user = User.objects.create_user("assistant_test", "assistant_test@test.com")
        assistant_contact = Contact.objects.create(
            first_name="Assistant",
            last_name="Test",
            email="assistant_test@test.com",
            date_of_birth="1979-01-01",
            address="444 Assistant St",
            mobile_number="444-444-4444",
            tenant=self.tenant
        )
        assistant_login = UserProfile.objects.create(
            user=assistant_user,
            contact=assistant_contact,
        )

        # Test different hierarchy levels
        staff_super = ClubStaff.objects.create(
            club=self.club,
            user=super_login,
            role='instructor'
        )

        staff_org_admin = ClubStaff.objects.create(
            club=self.club,
            user=self.user_profile2,
            organization_user=self.org_user2,  # is_admin=True
            role='instructor'
        )

        staff_club_owner = ClubStaff.objects.create(
            club=self.club,
            user=owner_login,
            role='owner'
        )

        staff_club_admin = ClubStaff.objects.create(
            club=self.club,
            user=admin_login,
            role='admin'
        )

        staff_instructor = ClubStaff.objects.create(
            club=self.club,
            user=instructor_login,
            role='instructor'
        )

        staff_assistant = ClubStaff.objects.create(
            club=self.club,
            user=assistant_login,
            role='assistant'
        )

        self.assertEqual(staff_super.get_permission_hierarchy_level(), 100)
        self.assertEqual(staff_org_admin.get_permission_hierarchy_level(), 90)
        self.assertEqual(staff_club_owner.get_permission_hierarchy_level(), 80)
        self.assertEqual(staff_club_admin.get_permission_hierarchy_level(), 70)
        self.assertEqual(staff_instructor.get_permission_hierarchy_level(), 50)
        self.assertEqual(staff_assistant.get_permission_hierarchy_level(), 30)

    def test_can_manage_staff_member(self):
        """Test staff management permissions based on hierarchy"""
        # Create additional users to avoid unique constraint violations
        owner_user = User.objects.create_user("owner_manage", "owner_manage@test.com")
        owner_contact = Contact.objects.create(
            first_name="Owner",
            last_name="Manage",
            email="owner_manage@test.com",
            date_of_birth="1980-02-01",
            address="100 Owner St",
            mobile_number="100-100-1000",
            tenant=self.tenant
        )
        owner_login = UserProfile.objects.create(
            user=owner_user,
            contact=owner_contact,
        )
        owner_login.is_club_owner = True
        owner_login.can_create_clubs = True
        owner_login.can_manage_members = True
        owner_login.save(update_fields=['is_club_owner','can_create_clubs','can_manage_members'])

        instructor_user = User.objects.create_user("instructor_manage", "instructor_manage@test.com")
        instructor_contact = Contact.objects.create(
            first_name="Instructor",
            last_name="Manage",
            email="instructor_manage@test.com",
            date_of_birth="1981-02-01",
            address="200 Instructor St",
            mobile_number="200-200-2000",
            tenant=self.tenant
        )
        instructor_login = UserProfile.objects.create(
            user=instructor_user,
            contact=instructor_contact,
        )

        assistant_user = User.objects.create_user("assistant_manage", "assistant_manage@test.com")
        assistant_contact = Contact.objects.create(
            first_name="Assistant",
            last_name="Manage",
            email="assistant_manage@test.com",
            date_of_birth="1982-02-01",
            address="300 Assistant St",
            mobile_number="300-300-3000",
            tenant=self.tenant
        )
        assistant_login = UserProfile.objects.create(
            user=assistant_user,
            contact=assistant_contact,
        )

        # Create staff with different levels
        owner = ClubStaff.objects.create(
            club=self.club,
            user=owner_login,
            role='owner'
        )

        org_admin = ClubStaff.objects.create(
            club=self.club,
            user=self.user_profile2,
            organization_user=self.org_user2,  # is_admin=True
            role='instructor'
        )

        instructor = ClubStaff.objects.create(
            club=self.club,
            user=instructor_login,
            role='instructor'
        )

        assistant = ClubStaff.objects.create(
            club=self.club,
            user=assistant_login,
            role='assistant'
        )

        # Test management permissions
        self.assertTrue(org_admin.can_manage_staff_member(owner))  # Org admin can manage club owner
        self.assertTrue(owner.can_manage_staff_member(instructor))  # Owner can manage instructor
        self.assertTrue(instructor.can_manage_staff_member(assistant))  # Instructor can manage assistant
        self.assertFalse(assistant.can_manage_staff_member(instructor))  # Assistant cannot manage instructor
        self.assertFalse(instructor.can_manage_staff_member(owner))  # Instructor cannot manage owner

    def test_sync_with_organization_permissions(self):
        """Test syncing permissions with organization-level permissions"""
        # Organization admin gets elevated permissions
        staff_org_admin = ClubStaff.objects.create(
            club=self.club,
            user=self.user_profile2,
            organization_user=self.org_user2,  # is_admin=True
            role='instructor',
            can_manage_members=False,
            can_manage_schedule=False,
            can_view_finances=False
        )

        # Sync with organization permissions
        staff_org_admin.sync_with_organization()

        self.assertTrue(staff_org_admin.can_manage_members)
        self.assertTrue(staff_org_admin.can_manage_schedule)
        # Finances permission only for owner/admin roles
        self.assertFalse(staff_org_admin.can_view_finances)

        # Test with owner role
        staff_org_admin.role = 'owner'
        staff_org_admin.sync_with_organization()
        self.assertTrue(staff_org_admin.can_view_finances)

    def test_onetoone_constraint_enforcement(self):
        """Test that OneToOne constraint is enforced"""
        # Create first staff assignment with organization user
        staff1 = ClubStaff.objects.create(
            club=self.club,
            user=self.user_profile1,
            organization_user=self.org_user1,
            role='instructor'
        )

        # Try to create second staff assignment with same organization user
        with self.assertRaises(Exception):  # Should raise IntegrityError
            ClubStaff.objects.create(
                club=self.club,
                user=self.user_profile2,
                organization_user=self.org_user1,  # Same org user
                role='assistant'
            )

    def test_get_organization_user_method(self):
        """Test get_organization_user helper method"""
        # Create additional user to avoid unique constraint violation
        test_user = User.objects.create_user("get_org_test", "get_org_test@test.com")
        test_contact = Contact.objects.create(
            first_name="Get",
            last_name="OrgTest",
            email="get_org_test@test.com",
            date_of_birth="1985-01-01",
            address="500 GetOrg St",
            mobile_number="500-500-5000",
            tenant=self.tenant
        )
        test_login = UserProfile.objects.create(
            user=test_user,
            contact=test_contact,
        )

        staff_with_org = ClubStaff.objects.create(
            club=self.club,
            user=self.user_profile1,
            organization_user=self.org_user1,
            role='instructor'
        )

        staff_without_org = ClubStaff.objects.create(
            club=self.club,
            user=test_login,
            role='assistant'
        )

        self.assertEqual(staff_with_org.get_organization_user(), self.org_user1)
        self.assertIsNone(staff_without_org.get_organization_user())