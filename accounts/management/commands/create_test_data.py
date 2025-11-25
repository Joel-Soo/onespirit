"""
Django management command to create test data for OneSpirit application.

Creates test data in the correct dependency order:
1. Django Users
2. TenantAccounts (without primary_contact)
3. Organizations
4. Contacts
5. Update TenantAccount.primary_contact
6. LoginUsers
7. MemberAccounts
8. Clubs
9. ClubStaff
10. ClubMembers
11. PaymentHistory (optional)

Usage:
    python manage.py create_test_data --scenario basic
    python manage.py create_test_data --scenario full --tenants 2 --members 10
    python manage.py create_test_data --clear-existing
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

# Import models
from accounts.models import (
    MemberAccount,
    PaymentHistory,
    PaymentMethod,
    PaymentStatus,
    PaymentType,
    TenantAccount,
)
from clubs.models import Club, ClubMember, ClubStaff
from people.models import Contact, LoginUser

# Import organizations if available
try:
    from organizations.models import Organization, OrganizationUser

    ORGANIZATIONS_AVAILABLE = True
except ImportError:
    ORGANIZATIONS_AVAILABLE = False
    Organization = None
    OrganizationUser = None


class Command(BaseCommand):
    help = "Creates test data for OneSpirit application in correct dependency order"

    def add_arguments(self, parser):
        parser.add_argument(
            "--scenario",
            type=str,
            default="basic",
            choices=["basic", "full", "minimal"],
            help="Test data scenario to create (default: basic)",
        )
        parser.add_argument(
            "--tenants",
            type=int,
            default=2,
            help="Number of tenant accounts to create (default: 2)",
        )
        parser.add_argument(
            "--members",
            type=int,
            default=5,
            help="Number of member accounts per tenant (default: 5)",
        )
        parser.add_argument(
            "--clubs",
            type=int,
            default=2,
            help="Number of clubs per tenant (default: 2)",
        )
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Clear existing test data before creating new data",
        )
        parser.add_argument(
            "--no-payments",
            action="store_true",
            help="Skip creating payment history data",
        )

    def handle(self, *args, **options):
        """Main command handler"""
        self.scenario = options["scenario"]
        self.num_tenants = options["tenants"]
        self.members_per_tenant = options["members"]
        self.clubs_per_tenant = options["clubs"]
        self.clear_existing = options["clear_existing"]
        self.create_payments = not options["no_payments"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Creating test data scenario: {self.scenario}\n"
                f"Tenants: {self.num_tenants}, Members per tenant: {self.members_per_tenant}, "
                f"Clubs per tenant: {self.clubs_per_tenant}\n"
            )
        )

        if not ORGANIZATIONS_AVAILABLE:
            self.stdout.write(
                self.style.WARNING(
                    "Warning: django-organizations not available. "
                    "Organizations will not be created.\n"
                )
            )

        try:
            with transaction.atomic():
                if self.clear_existing:
                    self._clear_existing_data()

                # Create test data in dependency order
                users = self._create_users()
                tenants = self._create_tenant_accounts()
                organizations = self._create_organizations()
                contacts = self._create_contacts(tenants, organizations)
                self._update_tenant_primary_contacts(tenants, contacts)
                login_users = self._create_login_users(users, contacts)
                member_accounts = self._create_member_accounts(tenants, contacts)
                clubs = self._create_clubs(tenants, organizations, contacts)
                club_staff = self._create_club_staff(clubs, contacts)
                club_members = self._create_club_members(clubs, member_accounts)

                if self.create_payments:
                    self._create_payment_history(tenants, member_accounts, users)

                self._print_summary(tenants, contacts, member_accounts, clubs)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating test data: {str(e)}"))
            raise CommandError(f"Failed to create test data: {str(e)}")

    def _clear_existing_data(self):
        """Clear existing test data"""
        self.stdout.write("Clearing existing test data...")

        # Delete in reverse dependency order
        PaymentHistory.objects.filter(description__icontains="[TEST DATA]").delete()
        ClubMember.objects.filter(club__name__icontains="Test").delete()
        ClubStaff.objects.filter(club__name__icontains="Test").delete()
        Club.objects.filter(name__icontains="Test").delete()
        MemberAccount.objects.filter(membership_number__startswith="TEST").delete()
        LoginUser.objects.filter(user__username__startswith="test").delete()
        Contact.objects.filter(last_name__icontains="Test").delete()
        if ORGANIZATIONS_AVAILABLE:
            Organization.objects.filter(name__icontains="Test").delete()
        TenantAccount.objects.filter(tenant_name__icontains="Test").delete()
        User.objects.filter(username__startswith="test").delete()

        self.stdout.write(self.style.SUCCESS("Existing test data cleared."))

    def _create_users(self):
        """Create Django Users"""
        self.stdout.write("Creating Django Users...")

        users = {}

        # Admin user
        admin_user, created = User.objects.get_or_create(
            username="testadmin",
            defaults={
                "email": "admin@test.com",
                "first_name": "Test",
                "last_name": "Admin",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin_user.set_password("testpass123")
            admin_user.save()
        users["admin"] = admin_user

        # Staff users
        for i in range(self.num_tenants):
            staff_user, created = User.objects.get_or_create(
                username=f"teststaff{i + 1}",
                defaults={
                    "email": f"staff{i + 1}@test.com",
                    "first_name": "Staff",
                    "last_name": f"User{i + 1}",
                    "is_staff": True,
                },
            )
            if created:
                staff_user.set_password("testpass123")
                staff_user.save()
            users[f"staff{i + 1}"] = staff_user

        #        # Regular users
        #        for i in range(self.members_per_tenant * self.num_tenants):
        #            member_user, created = User.objects.get_or_create(
        #                username=f'testmember{i+1}',
        #                defaults={
        #                    'email': f'member{i+1}@test.com',
        #                    'first_name': f'Member',
        #                    'last_name': f'User{i+1}'
        #                }
        #            )
        #            if created:
        #                member_user.set_password('testpass123')
        #                member_user.save()
        #            users[f'member{i+1}'] = member_user

        self.stdout.write(f"Created {len(users)} users.")
        return users

    def _create_tenant_accounts(self):
        """Create TenantAccounts without primary_contact"""
        self.stdout.write("Creating TenantAccounts...")

        tenants = []

        tenant_templates = [
            {
                "name": "Test Martial Arts Academy",
                "slug": "test-martial-arts",
                "subscription": "premium",
            },
            {
                "name": "Test Fitness Center",
                "slug": "test-fitness",
                "subscription": "basic",
            },
            {
                "name": "Test Combat Sports Club",
                "slug": "test-combat",
                "subscription": "enterprise",
            },
        ]

        for i in range(self.num_tenants):
            template = tenant_templates[i % len(tenant_templates)]

            tenant, created = TenantAccount.objects.get_or_create(
                tenant_slug=f"{template['slug']}-{i + 1}",
                defaults={
                    "tenant_name": f"{template['name']} {i + 1}",
                    "tenant_domain": f"test{i + 1}.onespirit.local",
                    "billing_email": f"billing@test{i + 1}.com",
                    "subscription_type": template["subscription"],
                    "subscription_start_date": timezone.now() - timedelta(days=30),
                    "monthly_fee": Decimal("99.99"),
                    "max_member_accounts": 50,
                    "max_clubs": 10,
                    "timezone": "UTC",
                    "locale": "en-US",
                },
            )
            tenants.append(tenant)

        self.stdout.write(f"Created {len(tenants)} tenant accounts.")
        return tenants

    def _create_organizations(self):
        """Create Organizations if django-organizations is available"""
        if not ORGANIZATIONS_AVAILABLE:
            return []

        self.stdout.write("Creating Organizations...")

        organizations = []

        org_templates = [
            "Test Karate Association",
            "Test Jiu-Jitsu Federation",
            "Test MMA Organization",
            "Test Fitness Network",
        ]

        for i in range(min(self.num_tenants, len(org_templates))):
            org, created = Organization.objects.get_or_create(
                name=f"{org_templates[i]} {i + 1}", defaults={"is_active": True}
            )
            organizations.append(org)

        self.stdout.write(f"Created {len(organizations)} organizations.")
        return organizations

    def _create_contacts(self, tenants, organizations):
        """Create Contacts"""
        self.stdout.write("Creating Contacts...")

        contacts = []

        # Contact templates
        contact_templates = [
            {"first": "John", "last": "TestDoe", "role": "owner"},
            {"first": "Jane", "last": "TestSmith", "role": "instructor"},
            {"first": "Mike", "last": "TestJohnson", "role": "member"},
            {"first": "Sarah", "last": "TestWilson", "role": "member"},
            {"first": "David", "last": "TestBrown", "role": "member"},
        ]

        contact_id = 1
        for tenant in tenants:
            # Create contacts for this tenant
            for i in range(self.members_per_tenant + 2):  # +2 for owner and staff
                template = contact_templates[i % len(contact_templates)]

                contact = Contact.objects.create(
                    first_name=template["first"],
                    last_name=f"{template['last']}{contact_id}",
                    date_of_birth=date(1990, 1, 1) + timedelta(days=contact_id * 30),
                    address=f"{contact_id} Test Street, Test City, TS {contact_id:05d}",
                    mobile_number=f"+1-555-{contact_id:04d}",
                    email=f"{template['first'].lower()}.{template['last'].lower()}{contact_id}@test.com",
                    tenant=tenant,
                    organization=organizations[tenants.index(tenant)]
                    if organizations
                    else None,
                    emergency_contact_name=f"Emergency Contact {contact_id}",
                    emergency_contact_phone=f"+1-555-{contact_id + 1000:04d}",
                    emergency_contact_relationship="Family",
                )
                contacts.append(contact)
                contact_id += 1

        self.stdout.write(f"Created {len(contacts)} contacts.")
        return contacts

    def _update_tenant_primary_contacts(self, tenants, contacts):
        """Update TenantAccount primary_contact to resolve circular dependency"""
        self.stdout.write("Setting TenantAccount primary contacts...")

        contacts_by_tenant = {}
        for contact in contacts:
            if contact.tenant not in contacts_by_tenant:
                contacts_by_tenant[contact.tenant] = []
            contacts_by_tenant[contact.tenant].append(contact)

        for tenant in tenants:
            if tenant in contacts_by_tenant and contacts_by_tenant[tenant]:
                # Set first contact as primary contact
                primary_contact = contacts_by_tenant[tenant][0]
                tenant.primary_contact = primary_contact
                tenant.save(update_fields=["primary_contact"])

        self.stdout.write("Updated tenant primary contacts.")

    def _create_login_users(self, users, contacts):
        """Create LoginUsers"""
        self.stdout.write("Creating LoginUsers...")

        login_users = []

        # Create login users for staff and some members
        user_keys = list(users.keys())
        for i, contact in enumerate(contacts[: len(user_keys)]):
            if i < len(user_keys):
                user_key = user_keys[i]
                user = users[user_key]

                # Determine permissions based on user type
                if "admin" in user_key:
                    permissions_level = "admin"
                    can_create_clubs = True
                    can_manage_members = True
                elif "staff" in user_key:
                    permissions_level = "staff"
                    can_create_clubs = True
                    can_manage_members = True
                else:
                    permissions_level = "member"
                    can_create_clubs = False
                    can_manage_members = False

                login_user = LoginUser.objects.create(
                    user=user,
                    contact=contact,
                    is_club_staff="staff" in user_key or "admin" in user_key,
                    permissions_level=permissions_level,
                    can_create_clubs=can_create_clubs,
                    can_manage_members=can_manage_members,
                )
                login_users.append(login_user)

        self.stdout.write(f"Created {len(login_users)} login users.")
        return login_users

    def _create_member_accounts(self, tenants, contacts):
        """Create MemberAccounts"""
        self.stdout.write("Creating MemberAccounts...")

        member_accounts = []

        contacts_by_tenant = {}
        for contact in contacts:
            if contact.tenant not in contacts_by_tenant:
                contacts_by_tenant[contact.tenant] = []
            contacts_by_tenant[contact.tenant].append(contact)

        membership_types = ["student", "instructor", "honorary", "lifetime"]
        membership_counter = 1

        for tenant in tenants:
            if tenant in contacts_by_tenant:
                tenant_contacts = contacts_by_tenant[tenant]

                for i, contact in enumerate(tenant_contacts[: self.members_per_tenant]):
                    membership_type = membership_types[i % len(membership_types)]

                    member_account = MemberAccount.objects.create(
                        tenant=tenant,
                        member_contact=contact,
                        primary_contact=contact,  # Same as member_contact
                        billing_email=contact.email,
                        membership_number=f"TEST{membership_counter:06d}",
                        membership_type=membership_type,
                        membership_start_date=date.today()
                        - timedelta(days=random.randint(1, 365)),
                        membership_end_date=date.today() + timedelta(days=365)
                        if membership_type != "lifetime"
                        else None,
                    )
                    member_accounts.append(member_account)
                    membership_counter += 1

        self.stdout.write(f"Created {len(member_accounts)} member accounts.")
        return member_accounts

    def _create_clubs(self, tenants, organizations, contacts):
        """Create Clubs"""
        self.stdout.write("Creating Clubs...")

        clubs = []

        club_templates = [
            {"name": "Test Karate Club", "style": "Karate", "level": "Beginner"},
            {
                "name": "Test Jiu-Jitsu Academy",
                "style": "Jiu-Jitsu",
                "level": "Advanced",
            },
            {
                "name": "Test MMA Gym",
                "style": "Mixed Martial Arts",
                "level": "All Levels",
            },
            {"name": "Test Boxing Club", "style": "Boxing", "level": "Intermediate"},
        ]

        contacts_by_tenant = {}
        for contact in contacts:
            if contact.tenant not in contacts_by_tenant:
                contacts_by_tenant[contact.tenant] = []
            contacts_by_tenant[contact.tenant].append(contact)

        club_id = 1
        for tenant in tenants:
            tenant_contacts = contacts_by_tenant.get(tenant, [])
            if not tenant_contacts:
                continue

            for i in range(self.clubs_per_tenant):
                template = club_templates[i % len(club_templates)]
                owner_contact = tenant_contacts[0]  # First contact as owner

                club = Club.objects.create(
                    name=f"{template['name']} {club_id}",
                    description=f"A {template['level']} {template['style']} club for testing purposes.",
                    tenant=tenant,
                    organization=organizations[tenants.index(tenant)]
                    if organizations
                    else None,
                    owner=owner_contact,
                    address=f"{club_id * 10} Test Dojo Street, Test City, TS {club_id:05d}",
                    phone_number=f"+1-555-{club_id + 2000:04d}",
                    email=f"club{club_id}@test.com",
                    website=f"https://testclub{club_id}.com",
                    established_date=date.today()
                    - timedelta(days=random.randint(365, 3650)),
                    max_members=50,
                    monthly_fee=Decimal("75.00") + Decimal(str(random.randint(0, 50))),
                    registration_fee=Decimal("25.00"),
                    is_accepting_members=True,
                )
                clubs.append(club)
                club_id += 1

        self.stdout.write(f"Created {len(clubs)} clubs.")
        return clubs

    def _create_club_staff(self, clubs, contacts):
        """Create ClubStaff"""
        self.stdout.write("Creating ClubStaff...")

        club_staff = []

        staff_roles = ["Instructor", "Assistant Instructor", "Manager", "Treasurer"]

        for club in clubs:
            # Get contacts from same tenant
            club_contacts = [c for c in contacts if c.tenant == club.tenant]

            # Create 1-2 staff per club
            num_staff = min(2, len(club_contacts) - 1)  # -1 to exclude owner
            for i in range(num_staff):
                if i + 1 < len(club_contacts):  # Skip owner (index 0)
                    contact = club_contacts[i + 1]
                    role = staff_roles[i % len(staff_roles)]

                    staff = ClubStaff.objects.create(
                        club=club,
                        contact=contact,
                        role=role,
                        hire_date=date.today() - timedelta(days=random.randint(1, 365)),
                        salary=Decimal("3000.00")
                        + Decimal(str(random.randint(0, 2000))),
                        is_active=True,
                    )
                    club_staff.append(staff)

        self.stdout.write(f"Created {len(club_staff)} club staff.")
        return club_staff

    def _create_club_members(self, clubs, member_accounts):
        """Create ClubMembers (many-to-many relationships)"""
        self.stdout.write("Creating ClubMembers...")

        club_members = []

        for club in clubs:
            # Get member accounts from same tenant
            club_member_accounts = [
                ma for ma in member_accounts if ma.tenant == club.tenant
            ]

            # Add 60-80% of member accounts to each club
            num_to_add = int(len(club_member_accounts) * random.uniform(0.6, 0.8))
            selected_members = random.sample(
                club_member_accounts, min(num_to_add, len(club_member_accounts))
            )

            for member_account in selected_members:
                club_member = ClubMember.objects.create(
                    club=club,
                    member_account=member_account,
                    join_date=date.today() - timedelta(days=random.randint(1, 365)),
                    membership_status="active",
                    belt_rank=random.choice(
                        ["White", "Yellow", "Orange", "Green", "Blue", "Brown", "Black"]
                    ),
                    monthly_fee_override=None,  # Use club default
                    notes="[TEST DATA] Member joined as part of test data generation.",
                )
                club_members.append(club_member)

        self.stdout.write(f"Created {len(club_members)} club memberships.")
        return club_members

    def _create_payment_history(self, tenants, member_accounts, users):
        """Create PaymentHistory records"""
        self.stdout.write("Creating PaymentHistory...")

        payments = []
        admin_user = users.get("admin")

        # Create payments for member accounts
        for member_account in member_accounts:
            # Create 1-3 payments per member
            num_payments = random.randint(1, 3)
            for i in range(num_payments):
                payment_date = timezone.now() - timedelta(days=random.randint(1, 365))

                payment = PaymentHistory.objects.create(
                    account=member_account,
                    amount=Decimal(str(random.randint(50, 150))),
                    currency="USD",
                    payment_date=payment_date,
                    due_date=payment_date.date()
                    - timedelta(days=random.randint(1, 30)),
                    payment_method=random.choice(PaymentMethod.choices)[0],
                    transaction_reference=f"TEST_TXN_{len(payments) + 1:06d}",
                    payment_status=random.choice(
                        [
                            PaymentStatus.COMPLETED,
                            PaymentStatus.COMPLETED,
                            PaymentStatus.PENDING,
                        ]
                    )[0],
                    payment_type=random.choice(
                        [
                            PaymentType.MEMBERSHIP_FEE,
                            PaymentType.GRADING_FEE,
                            PaymentType.EQUIPMENT,
                        ]
                    )[0],
                    description=f"[TEST DATA] Payment {i + 1} for member {member_account.membership_number}",
                    created_by=admin_user,
                )
                payments.append(payment)

        # Create tenant subscription payments
        for tenant in tenants:
            # Create monthly subscription payments
            for i in range(3):  # Last 3 months
                payment_date = timezone.now() - timedelta(days=30 * i)

                payment = PaymentHistory.objects.create(
                    account=tenant,
                    amount=tenant.monthly_fee,
                    currency="USD",
                    payment_date=payment_date,
                    due_date=payment_date.date(),
                    payment_method=PaymentMethod.STRIPE,
                    transaction_reference=f"SUB_TXN_{tenant.id}_{i + 1:02d}",
                    payment_status=PaymentStatus.COMPLETED,
                    payment_type=PaymentType.SUBSCRIPTION,
                    description=f"[TEST DATA] Monthly subscription for {tenant.tenant_name}",
                    created_by=admin_user,
                )
                payments.append(payment)

        self.stdout.write(f"Created {len(payments)} payment records.")
        return payments

    def _print_summary(self, tenants, contacts, member_accounts, clubs):
        """Print summary of created test data"""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("TEST DATA CREATION COMPLETE"))
        self.stdout.write("=" * 50)

        self.stdout.write(f"Scenario: {self.scenario}")
        self.stdout.write(f"Tenants: {len(tenants)}")
        self.stdout.write(f"Contacts: {len(contacts)}")
        self.stdout.write(f"Member Accounts: {len(member_accounts)}")
        self.stdout.write(f"Clubs: {len(clubs)}")

        self.stdout.write("\nTenant Details:")
        for tenant in tenants:
            member_count = MemberAccount.objects.filter(tenant=tenant).count()
            club_count = Club.objects.filter(tenant=tenant).count()
            self.stdout.write(
                f"  - {tenant.tenant_name}: {member_count} members, {club_count} clubs"
            )

        self.stdout.write("\nLogin Credentials (all passwords: testpass123):")
        self.stdout.write("  - testadmin (superuser)")
        for i in range(self.num_tenants):
            self.stdout.write(f"  - teststaff{i + 1} (staff)")

        self.stdout.write("\nNext Steps:")
        self.stdout.write("1. Login to Django admin with testadmin/testpass123")
        self.stdout.write("2. Explore the created tenants, contacts, and clubs")
        self.stdout.write("3. Test multi-tenant functionality")
        self.stdout.write(
            "4. Run: python manage.py create_test_data --clear-existing (to reset)"
        )
