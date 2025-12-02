# Refactoring Strategy: LoginUser → UserProfile + Permissions Cleanup

**Date:** 2025-12-02

## Executive Summary

### Phased Approach (6 phases):

1. **Preparation** - Audit data, create tests (no DB changes)
2. **Model Rename** - `LoginUser` → `UserProfile` (preserves all behavior)
3. **Permission Refactoring** - Replace `permissions_level` with explicit booleans
4. **Admin Updates** - Update Django admin interface
5. **Testing & Validation** - Comprehensive testing
6. **Documentation** - Update all docs

### Critical Design Decisions:

**Permission Mapping:**
- `permissions_level='admin'` → `is_system_admin=True`
- `permissions_level='owner'` → `can_create_clubs=True, can_manage_members=True`
- `permissions_level='staff'` → `can_manage_members=True`
- `permissions_level='member'` → All flags `False`

**Fields to Remove:**
- `permissions_level` (replaced by explicit booleans)
- `is_club_staff` (redundant with `ClubStaff` model)

**Fields to Keep:**
- `can_create_clubs`
- `can_manage_members`

**Fields to Add:**
- `is_system_admin` (tenant-wide admin access)

### Safety Features:

1. **Reversible migrations** - Can rollback at any phase
2. **Add before remove** - New fields added before old ones removed
3. **Data preservation** - Migration includes forward/reverse data mapping
4. **Comprehensive testing** - Test suite updated before migrations run

### Estimated Timeline:

19-29 hours total work (can be split across multiple days/sprints)

---

## Overview

This document outlines the strategy for refactoring the `LoginUser` model to `UserProfile` and cleaning up the permissions system to eliminate ambiguity and overlap.

## Goals

1. Rename `LoginUser` to `UserProfile`
2. Simplify permissions by separating system-level from resource-level permissions
3. Maintain backward compatibility during transition
4. Preserve all existing data

## Current State Analysis

### Current Model Structure (people/models.py:180-587)

```python
class LoginUser(models.Model):
    user = OneToOneField(User, related_name="login_profile")
    contact = OneToOneField(Contact, related_name="login_user")

    # PROBLEMATIC: Overlapping permissions
    permissions_level = CharField(choices=[member, staff, owner, admin])
    is_club_staff = BooleanField()
    can_create_clubs = BooleanField()
    can_manage_members = BooleanField()
```

### Issues Identified

1. **Overlapping permission systems**
   - `permissions_level='owner'` vs `ClubStaff.role='owner'`
   - `is_club_staff` boolean vs `permissions_level='staff'`

2. **Global vs resource-specific confusion**
   - `permissions_level='admin'` grants global access
   - `is_club_owner(club)` checks specific club ownership

3. **Ambiguous semantics**
   - What does "member", "staff", "owner" mean at the LoginUser level?

## Target State

### New Model Structure

```python
class UserProfile(models.Model):
    """
    Extended user profile linking Django User authentication
    with Contact business data and system-level permissions.
    """
    user = OneToOneField(User, related_name="profile")
    contact = OneToOneField(Contact, related_name="user_profile")

    # System-level permissions (tenant-wide)
    is_system_admin = BooleanField(
        default=False,
        help_text="Can manage all resources within tenant"
    )

    # Specific capabilities (system-level)
    can_create_clubs = BooleanField(
        default=False,
        help_text="Can create new clubs in the system"
    )
    can_manage_members = BooleanField(
        default=False,
        help_text="Can manage member rosters globally"
    )

    # Metadata
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    last_login_attempt = DateTimeField(null=True, blank=True)

    # Resource-specific permissions handled by:
    # - ClubStaff (club-level roles: owner, admin, instructor, assistant)
    # - OrganizationUser/OrganizationOwner (organization-level roles)
```

### Permission Mapping Strategy

Map old `permissions_level` values to new structure:

| Old `permissions_level` | New `is_system_admin` | New `can_create_clubs` | New `can_manage_members` | Notes |
|------------------------|----------------------|------------------------|-------------------------|-------|
| `admin` | `True` | `True` | `True` | Full system access |
| `owner` | `False` | `True` | `True` | Can create/manage, but not system admin |
| `staff` | `False` | `False` | `True` | Can manage members only |
| `member` | `False` | `False` | `False` | No system-level permissions |

**Important:** Users with `permissions_level='owner'` or `'staff'` should also be checked for actual `ClubStaff` assignments to ensure data integrity.

## Implementation Strategy

### Phase 1: Preparation (No Database Changes)

**Goal:** Set up infrastructure for smooth migration

#### Step 1.1: Create migration plan document
- Document all files that reference `LoginUser`
- Document all files that reference `permissions_level`
- Create mapping of old permissions to new permissions

#### Step 1.2: Audit data
```python
# Create Django management command: audit_loginuser_permissions.py
# Check for:
# - Users with permissions_level='owner' without ClubStaff.role='owner'
# - Users with is_club_staff=True but no ClubStaff assignments
# - Inconsistent permission states
```

#### Step 1.3: Create comprehensive tests
```python
# tests/test_userprofile_migration.py
# Test that migration preserves:
# - All user records
# - All permission mappings
# - All relationships (user, contact)
# - All method behaviors
```

### Phase 2: Model Renaming (Database Migration)

**Goal:** Rename model without changing behavior

#### Step 2.1: Create migration for model rename

```python
# people/migrations/000X_rename_loginuser_to_userprofile.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('people', '000X_previous_migration'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='LoginUser',
            new_name='UserProfile',
        ),
    ]
```

#### Step 2.2: Update model class name

```python
# people/models.py
class UserProfile(models.Model):  # Changed from LoginUser
    # Keep all existing fields unchanged for now
    ...

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        db_table = 'people_loginuser'  # Keep old table name for now
```

#### Step 2.3: Update related_name references

**Critical:** Django's `RenameModel` doesn't update `related_name`, so we need to:

```python
# In User model extension:
user.login_profile  # OLD - will break
user.profile  # NEW - update related_name

# In Contact model:
contact.login_user  # OLD - will break
contact.user_profile  # NEW - update related_name
```

Update in migration:
```python
operations = [
    migrations.AlterField(
        model_name='userprofile',
        name='user',
        field=models.OneToOneField(
            User,
            on_delete=models.CASCADE,
            related_name='profile',  # Changed from 'login_profile'
            ...
        ),
    ),
    migrations.AlterField(
        model_name='userprofile',
        name='contact',
        field=models.OneToOneField(
            Contact,
            on_delete=models.CASCADE,
            related_name='user_profile',  # Changed from 'login_user'
            ...
        ),
    ),
]
```

#### Step 2.4: Update all code references

Find and replace across codebase:
- `LoginUser` → `UserProfile`
- `login_profile` → `profile`
- `login_user` → `user_profile`

Files to update (search with grep):
```bash
grep -r "LoginUser" --include="*.py" .
grep -r "login_profile" --include="*.py" .
grep -r "login_user" --include="*.py" .
```

Expected files:
- `people/models.py` - Model definition
- `people/admin.py` - Admin registration
- `people/tests/test_loginuser_functionality.py` - Tests (rename file too)
- `clubs/models.py` - References in ClubStaff
- `accounts/tests/test_services.py` - References in tests
- Any views, serializers, forms that use the model

#### Step 2.5: Run tests

```bash
python manage.py test people clubs accounts
```

### Phase 3: Permission Field Refactoring (Database Migration + Data Migration)

**Goal:** Replace `permissions_level` with explicit boolean flags

#### Step 3.1: Add new fields (without removing old ones)

```python
# people/migrations/000X_add_system_permissions.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('people', '000X_rename_loginuser_to_userprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='is_system_admin',
            field=models.BooleanField(default=False),
        ),
        # can_create_clubs already exists, no need to add
        # can_manage_members already exists, no need to add
    ]
```

#### Step 3.2: Data migration to populate new fields

```python
# people/migrations/000X_migrate_permissions_data.py
from django.db import migrations

def migrate_permissions_forward(apps, schema_editor):
    UserProfile = apps.get_model('people', 'UserProfile')

    # Map old permissions_level to new fields
    for user_profile in UserProfile.objects.all():
        level = user_profile.permissions_level

        if level == 'admin':
            user_profile.is_system_admin = True
            user_profile.can_create_clubs = True
            user_profile.can_manage_members = True
        elif level == 'owner':
            user_profile.is_system_admin = False
            user_profile.can_create_clubs = True
            user_profile.can_manage_members = True
        elif level == 'staff':
            user_profile.is_system_admin = False
            # Keep existing can_create_clubs value
            user_profile.can_manage_members = True
        # 'member' keeps all False (defaults)

        user_profile.save()

def migrate_permissions_reverse(apps, schema_editor):
    UserProfile = apps.get_model('people', 'UserProfile')

    # Reverse migration
    for user_profile in UserProfile.objects.all():
        if user_profile.is_system_admin:
            user_profile.permissions_level = 'admin'
        elif user_profile.can_create_clubs and user_profile.can_manage_members:
            user_profile.permissions_level = 'owner'
        elif user_profile.can_manage_members:
            user_profile.permissions_level = 'staff'
        else:
            user_profile.permissions_level = 'member'

        user_profile.save()

class Migration(migrations.Migration):
    dependencies = [
        ('people', '000X_add_system_permissions'),
    ]

    operations = [
        migrations.RunPython(
            migrate_permissions_forward,
            migrate_permissions_reverse
        ),
    ]
```

#### Step 3.3: Update all code using permissions_level

**Before:**
```python
if user_profile.permissions_level == 'admin':
    # Grant access
```

**After:**
```python
if user_profile.is_system_admin:
    # Grant access
```

Find all usages:
```bash
grep -r "permissions_level" --include="*.py" .
```

Update each reference based on context:
- `permissions_level == 'admin'` → `is_system_admin`
- `permissions_level in ['owner', 'admin']` → `is_system_admin or can_create_clubs`
- Etc.

Files to review:
- `people/models.py` - Methods like `has_club_permissions()`, `can_manage_club()`, `get_managed_clubs()`
- Any views/serializers checking permissions

#### Step 3.4: Update method implementations

**Example - people/models.py:266-272:**

Before:
```python
def has_club_permissions(self) -> bool:
    return (
        self.is_club_owner()
        or self.is_club_staff
        or self.permissions_level in ["owner", "admin"]
    )
```

After:
```python
def has_club_permissions(self) -> bool:
    """Check if user has any club management permissions"""
    return (
        self.is_club_owner()  # Has club-specific ownership via ClubStaff
        or self.is_system_admin  # System-wide admin access
        or self.can_manage_members  # Can manage members globally
    )
```

**Example - people/models.py:289:**

Before:
```python
if self.is_club_owner(club) or self.permissions_level == "admin":
    return True
```

After:
```python
if self.is_club_owner(club) or self.is_system_admin:
    return True
```

**Example - people/models.py:313:**

Before:
```python
if self.permissions_level == "admin":
    return Club.objects.filter(tenant=self.contact.tenant)
```

After:
```python
if self.is_system_admin:
    return Club.objects.filter(tenant=self.contact.tenant)
```

#### Step 3.5: Remove deprecated fields

After confirming all code is updated and tests pass:

```python
# people/migrations/000X_remove_deprecated_permissions.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('people', '000X_migrate_permissions_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='permissions_level',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='is_club_staff',  # Redundant, use ClubStaff model
        ),
    ]
```

#### Step 3.6: Update clean() validation

Before:
```python
def clean(self):
    if self.is_club_owner() and self.permissions_level not in ["owner", "admin"]:
        raise ValidationError(...)

    if self.permissions_level == "admin":
        self.can_create_clubs = True
        self.can_manage_members = True
```

After:
```python
def clean(self):
    # Ensure system admins have full capabilities
    if self.is_system_admin:
        self.can_create_clubs = True
        self.can_manage_members = True
```

#### Step 3.7: Update signal handlers

Before (people/models.py:571-586):
```python
@receiver(post_save, sender=LoginUser)
def sync_user_permissions(sender, instance, **kwargs):
    user = instance.user

    if instance.is_club_owner() or instance.permissions_level in ["admin"]:
        user.is_staff = True
```

After:
```python
@receiver(post_save, sender=UserProfile)
def sync_user_permissions(sender, instance, **kwargs):
    user = instance.user

    if instance.is_club_owner() or instance.is_system_admin:
        user.is_staff = True
```

### Phase 4: Admin Interface Updates

#### Step 4.1: Update people/admin.py

```python
from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'contact',
        'user',
        'is_system_admin',
        'can_create_clubs',
        'can_manage_members',
        'created_at',
    ]
    list_filter = [
        'is_system_admin',
        'can_create_clubs',
        'can_manage_members',
    ]
    search_fields = [
        'user__username',
        'contact__first_name',
        'contact__last_name',
        'contact__email',
    ]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Relationships', {
            'fields': ('user', 'contact')
        }),
        ('System Permissions', {
            'fields': (
                'is_system_admin',
                'can_create_clubs',
                'can_manage_members',
            )
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'last_login_attempt'),
            'classes': ('collapse',)
        }),
    )
```

### Phase 5: Testing & Validation

#### Step 5.1: Update test files

Rename and update:
- `people/tests/test_loginuser_functionality.py` → `people/tests/test_userprofile_functionality.py`

Update test methods to use new field names:
```python
def test_system_admin_permissions(self):
    """Test that system admins have full access"""
    profile = UserProfile.objects.create(
        user=self.user,
        contact=self.contact,
        is_system_admin=True
    )

    self.assertTrue(profile.can_create_clubs)
    self.assertTrue(profile.can_manage_members)
    self.assertTrue(profile.has_club_permissions())
```

#### Step 5.2: Create migration validation tests

```python
# people/tests/test_permission_migration.py
from django.test import TestCase
from people.models import UserProfile

class PermissionMigrationTestCase(TestCase):
    """Verify that permissions were migrated correctly"""

    def test_admin_migration(self):
        """Admin users should have is_system_admin=True"""
        # Test logic
        pass

    def test_owner_migration(self):
        """Owner users should have can_create_clubs=True"""
        # Test logic
        pass

    def test_staff_migration(self):
        """Staff users should have can_manage_members=True"""
        # Test logic
        pass

    def test_member_migration(self):
        """Members should have no special permissions"""
        # Test logic
        pass
```

#### Step 5.3: Run full test suite

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test people
python manage.py test clubs
python manage.py test accounts

# Check migrations
python manage.py makemigrations --check --dry-run
```

### Phase 6: Documentation Updates

#### Step 6.1: Update docstrings

Update model and method docstrings to reflect new naming and permission structure.

#### Step 6.2: Update README/documentation

- Update any architecture documentation
- Update API documentation if applicable
- Update deployment/setup guides

#### Step 6.3: Create migration notes

Document the changes for other developers:
- What changed
- Why it changed
- How to update existing code
- Common patterns for permission checking

## Rollback Plan

If issues are discovered after deployment:

### Immediate Rollback (Phase 2 - Model Rename)

```bash
# Revert migration
python manage.py migrate people <previous_migration_number>

# Revert code changes
git revert <commit_hash>
```

### Rollback After Data Migration (Phase 3)

The data migration includes a reverse function, so:

```bash
# Migrations are reversible
python manage.py migrate people <migration_before_permissions_refactor>
```

Data is preserved because we:
1. Add new fields before removing old ones
2. Copy data from old to new fields
3. Only remove old fields after validation

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing code references | High | Comprehensive grep search + tests |
| Data loss during migration | Critical | Reversible migrations + backups |
| Permission escalation bugs | High | Thorough testing of permission checks |
| Third-party integrations break | Medium | Document changes, test integrations |
| Production downtime | High | Deploy during maintenance window |

## Timeline Estimate

| Phase | Estimated Time | Can Run in Production? |
|-------|---------------|----------------------|
| Phase 1: Preparation | 2-4 hours | Yes (no changes) |
| Phase 2: Model Rename | 4-6 hours | Yes (after testing) |
| Phase 3: Permission Refactor | 6-8 hours | Yes (after testing) |
| Phase 4: Admin Updates | 1-2 hours | Yes |
| Phase 5: Testing | 4-6 hours | Staging only |
| Phase 6: Documentation | 2-3 hours | Yes |
| **Total** | **19-29 hours** | - |

## Deployment Checklist

- [ ] Phase 1: Complete data audit
- [ ] Phase 1: All tests passing on current code
- [ ] Phase 2: Model rename migration created
- [ ] Phase 2: All code references updated (LoginUser → UserProfile)
- [ ] Phase 2: Tests passing with new model name
- [ ] Phase 3: Permission fields added (migration)
- [ ] Phase 3: Data migration created and tested
- [ ] Phase 3: All permissions_level references updated
- [ ] Phase 3: Deprecated fields removed
- [ ] Phase 3: Tests passing with new permission structure
- [ ] Phase 4: Admin interface updated
- [ ] Phase 5: All tests passing (unit, integration, e2e)
- [ ] Phase 5: Manual testing completed
- [ ] Phase 6: Documentation updated
- [ ] Database backup taken
- [ ] Rollback plan tested
- [ ] Deploy to staging
- [ ] Staging validation complete
- [ ] Deploy to production
- [ ] Production smoke tests complete

## Success Criteria

1. ✅ All existing functionality preserved
2. ✅ All tests passing
3. ✅ No data loss
4. ✅ Clearer permission semantics
5. ✅ No permission escalation or security issues
6. ✅ Admin interface working correctly
7. ✅ Documentation updated

## Post-Deployment

### Monitoring

Monitor for:
- Permission-related errors in logs
- Failed authentication attempts
- User reports of access issues

### Cleanup

After successful deployment and validation:
- Remove any compatibility shims
- Clean up old documentation
- Archive migration planning documents
