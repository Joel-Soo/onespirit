# AI-Executable Refactoring Plan: LoginUser → UserProfile

**Date:** 2025-12-02
**Parent Strategy Document:** refactor-strategy-loginuser-to-userprofile-2025-12-02.md

## Overview

This document provides step-by-step executable instructions for an AI agent to refactor the `LoginUser` model to `UserProfile` and clean up the permissions system.

**IMPORTANT:** This plan assumes execution from `/home/jdev/code` working directory.

---

## PHASE 1: PREPARATION (No Database Changes)

### Step 1.1: Create audit report of LoginUser references

**Action:**
```bash
grep -r "LoginUser" --include="*.py" . | grep -v ".venv" | grep -v "__pycache__" | tee /tmp/loginuser_references.txt
```

**Expected Output:**
File paths containing "LoginUser" references (excluding virtual environments)

**Validation:**
- [ ] Command completes successfully (exit code 0)
- [ ] Output saved to `/tmp/loginuser_references.txt`
- [ ] File is not empty

**If Validation Fails:**
STOP - Report: "Cannot find LoginUser references in codebase"

---

### Step 1.2: Count total LoginUser references

**Action:**
```bash
wc -l /tmp/loginuser_references.txt
```

**Expected Output:**
A number greater than 0

**Validation:**
- [ ] Count is > 0
- [ ] Count is < 1000 (sanity check)

**If Validation Fails:**
STOP - Report: "Unexpected number of references: [count]"

---

### Step 1.3: List unique files with LoginUser references

**Action:**
```bash
cut -d: -f1 /tmp/loginuser_references.txt | sort -u | tee /tmp/loginuser_files.txt
```

**Expected Files (minimum set):**
- people/models.py
- people/admin.py
- clubs/models.py

**Validation:**
- [ ] people/models.py is in the list
- [ ] At least 3 files in the list

**If Validation Fails:**
STOP - Report: "Expected files not found in reference list"

---

### Step 1.4: Audit permissions_level references

**Action:**
```bash
grep -r "permissions_level" --include="*.py" . | grep -v ".venv" | grep -v "__pycache__" | tee /tmp/permissions_level_references.txt
```

**Expected Output:**
File paths containing "permissions_level" references

**Validation:**
- [ ] Command completes successfully
- [ ] people/models.py is in results

**If Validation Fails:**
STOP - Report: "Cannot find permissions_level references"

---

### Step 1.5: Create backup branch

**Action:**
```bash
git checkout -b refactor/loginuser-to-userprofile
```

**Expected Output:**
```
Switched to a new branch 'refactor/loginuser-to-userprofile'
```

**Validation:**
- [ ] Exit code is 0
- [ ] Output contains "Switched to a new branch"

**Action to verify:**
```bash
git branch --show-current
```

**Expected Output:**
```
refactor/loginuser-to-userprofile
```

**If Validation Fails:**
STOP - Report: "Failed to create backup branch"

---

### Step 1.6: Verify current tests pass

**Action:**
```bash
python manage.py test people clubs accounts --verbosity=2
```

**Expected Output:**
All tests pass (exit code 0)

**Validation:**
- [ ] Exit code is 0
- [ ] No "FAILED" in output
- [ ] "OK" or "Ran X tests" in output

**If Validation Fails:**
STOP - Report: "Tests failing before refactor started. Cannot proceed safely."

**Record baseline:**
Save the number of tests that passed for later comparison.

---

### Step 1.7: Check for pending migrations

**Action:**
```bash
python manage.py makemigrations --check --dry-run
```

**Expected Output:**
```
No changes detected
```

**Validation:**
- [ ] Exit code is 0
- [ ] Output contains "No changes detected"

**If Validation Fails:**
STOP - Report: "There are pending migrations. Run makemigrations first."

---

## PHASE 2: MODEL RENAMING

### Step 2.1: Read current LoginUser model

**Action:**
Read file: `/home/jdev/code/people/models.py` lines 180-240

**Validation:**
- [ ] File exists
- [ ] Line 180 (approximately) contains `class LoginUser(models.Model):`
- [ ] Model has fields: user, contact, permissions_level, is_club_staff, can_create_clubs, can_manage_members

**If Validation Fails:**
STOP - Report: "LoginUser model structure has changed from expected"

---

### Step 2.2: Update model class name

**Action:**
Edit `/home/jdev/code/people/models.py`

**old_string:**
```python
class LoginUser(models.Model):
    """LoginUser model for contacts that can login and manage club membership"""
```

**new_string:**
```python
class UserProfile(models.Model):
    """UserProfile model for contacts that can login and manage club membership"""
```

**Validation:**
Read file and verify:
- [ ] "class UserProfile(models.Model):" exists
- [ ] "class LoginUser" does NOT exist

**If Validation Fails:**
STOP - Report: "Model class name replacement failed"

---

### Step 2.3: Update related_name for user field

**Action:**
Edit `/home/jdev/code/people/models.py`

**old_string:**
```python
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="login_profile",
        help_text="Django User account for authentication",
    )
```

**new_string:**
```python
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        help_text="Django User account for authentication",
    )
```

**Validation:**
- [ ] Grep for `related_name="profile"` in people/models.py succeeds
- [ ] Grep for `related_name="login_profile"` in people/models.py returns nothing

**If Validation Fails:**
STOP - Report: "User related_name update failed"

---

### Step 2.4: Update related_name for contact field

**Action:**
Edit `/home/jdev/code/people/models.py`

**old_string:**
```python
    contact = models.OneToOneField(
        Contact,
        on_delete=models.CASCADE,
        related_name="login_user",
        help_text="Associated contact information",
    )
```

**new_string:**
```python
    contact = models.OneToOneField(
        Contact,
        on_delete=models.CASCADE,
        related_name="user_profile",
        help_text="Associated contact information",
    )
```

**Validation:**
- [ ] Grep for `related_name="user_profile"` in people/models.py succeeds
- [ ] Grep for `related_name="login_user"` in people/models.py returns nothing (in UserProfile model)

**If Validation Fails:**
STOP - Report: "Contact related_name update failed"

---

### Step 2.5: Update Meta class verbose names

**Action:**
Edit `/home/jdev/code/people/models.py`

**old_string:**
```python
    class Meta:
        verbose_name = "Login User"
        verbose_name_plural = "Login Users"
```

**new_string:**
```python
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
```

**Validation:**
- [ ] Grep for `verbose_name = "User Profile"` in people/models.py succeeds

**If Validation Fails:**
STOP - Report: "Meta verbose_name update failed"

---

### Step 2.6: Update __str__ method

**Action:**
Edit `/home/jdev/code/people/models.py`

**old_string:**
```python
    def __str__(self) -> str:
        return f"{self.contact.get_full_name()} (Login User)"
```

**new_string:**
```python
    def __str__(self) -> str:
        return f"{self.contact.get_full_name()} (User Profile)"
```

**Validation:**
- [ ] Grep for "(User Profile)" in people/models.py succeeds

**If Validation Fails:**
STOP - Report: "__str__ method update failed"

---

### Step 2.7: Update signal receiver decorator

**Action:**
Edit `/home/jdev/code/people/models.py`

**old_string:**
```python
@receiver(post_save, sender=LoginUser)
def sync_user_permissions(
    sender: type[LoginUser], instance: LoginUser, **kwargs: Any
) -> None:
```

**new_string:**
```python
@receiver(post_save, sender=UserProfile)
def sync_user_permissions(
    sender: type[UserProfile], instance: UserProfile, **kwargs: Any
) -> None:
```

**Validation:**
- [ ] Grep for `sender=UserProfile` in people/models.py succeeds
- [ ] Grep for `sender=LoginUser` in people/models.py returns nothing

**If Validation Fails:**
STOP - Report: "Signal receiver update failed"

---

### Step 2.8: Read people/admin.py

**Action:**
Read file: `/home/jdev/code/people/admin.py`

**Expected content:**
Should contain references to LoginUser

**Validation:**
- [ ] File exists
- [ ] Contains "LoginUser" reference

**If Validation Fails:**
STOP - Report: "admin.py structure unexpected"

---

### Step 2.9: Update admin.py imports and registration

**Action:**
Read entire `/home/jdev/code/people/admin.py` file first to see current structure.

Then update all references:
- `from .models import LoginUser` → `from .models import UserProfile`
- `@admin.register(LoginUser)` → `@admin.register(UserProfile)`
- Any `LoginUser` references in class → `UserProfile`

**Method:**
Use Edit tool with replace_all=True for each pattern in the file.

**Validation:**
- [ ] Grep for "LoginUser" in people/admin.py returns nothing
- [ ] Grep for "UserProfile" in people/admin.py succeeds
- [ ] File is syntactically valid Python

**If Validation Fails:**
STOP - Report: "admin.py update failed"

---

### Step 2.10: Find and update test files

**Action:**
```bash
find . -path "*/tests/*.py" -type f -exec grep -l "LoginUser" {} \; | grep -v ".venv"
```

**Expected Output:**
List of test files containing LoginUser

**For each file found:**

**Action:**
Read the file, then use Edit tool with replace_all=True:
- `LoginUser` → `UserProfile`
- `login_profile` → `profile`
- `login_user` → `user_profile`

**Validation per file:**
- [ ] No "LoginUser" references remain (except in comments if intentional)
- [ ] File is syntactically valid

**If Validation Fails:**
STOP - Report: "Test file update failed: [filename]"

---

### Step 2.11: Rename test file

**Action:**
```bash
if [ -f "people/tests/test_loginuser_functionality.py" ]; then
    git mv people/tests/test_loginuser_functionality.py people/tests/test_userprofile_functionality.py
fi
```

**Validation:**
- [ ] Command completes successfully OR file doesn't exist
- [ ] If file existed, new file exists at new path

**If Validation Fails:**
STOP - Report: "Test file rename failed"

---

### Step 2.12: Update references in clubs/models.py

**Action:**
Read `/home/jdev/code/clubs/models.py`

Find any references to LoginUser and update them to UserProfile.

**Expected locations:**
- Docstrings mentioning LoginUser
- Type hints
- Comments

**Method:**
Use Edit tool to replace each occurrence

**Validation:**
- [ ] Grep for "LoginUser" in clubs/models.py returns nothing (or only in historical comments)
- [ ] File is syntactically valid

**If Validation Fails:**
STOP - Report: "clubs/models.py update failed"

---

### Step 2.13: Search for any remaining LoginUser references

**Action:**
```bash
grep -r "LoginUser" --include="*.py" . | grep -v ".venv" | grep -v "__pycache__" | grep -v "migrations/"
```

**Expected Output:**
Empty or only comments/docstrings explaining the refactor

**Validation:**
- [ ] No active code references to LoginUser
- [ ] Only acceptable references are in migration files or historical comments

**If Validation Fails:**
Review each remaining reference and update as needed, or STOP and report.

---

### Step 2.14: Create Django migration for model rename

**Action:**
```bash
python manage.py makemigrations people --name rename_loginuser_to_userprofile
```

**Expected Output:**
```
Migrations for 'people':
  people/migrations/XXXX_rename_loginuser_to_userprofile.py
    - Rename model LoginUser to UserProfile
```

**Validation:**
- [ ] Exit code is 0
- [ ] Migration file created
- [ ] Migration contains RenameModel operation

**Action to verify migration:**
Read the created migration file and verify it contains:
```python
operations = [
    migrations.RenameModel(
        old_name='LoginUser',
        new_name='UserProfile',
    ),
    ...
]
```

**If Validation Fails:**
STOP - Report: "Migration creation failed or incorrect"

---

### Step 2.15: Review generated migration

**Action:**
Read the migration file created in step 2.14

**Check for:**
- [ ] Has RenameModel operation
- [ ] May have AlterField operations for related_name changes
- [ ] Dependencies look correct

**Expected structure:**
The migration should handle:
1. RenameModel from LoginUser to UserProfile
2. AlterField for user.related_name
3. AlterField for contact.related_name

**If migration doesn't include related_name changes:**
This is OK - Django may handle this automatically or we may need to create a follow-up migration.

**Validation:**
- [ ] Migration file is syntactically valid Python
- [ ] Contains necessary operations

**If Validation Fails:**
STOP - Report: "Migration structure is incorrect"

---

### Step 2.16: Run migration (dry run)

**Action:**
```bash
python manage.py migrate people --plan
```

**Expected Output:**
Shows the migration plan including the rename operation

**Validation:**
- [ ] Exit code is 0
- [ ] Shows the new migration in the plan
- [ ] No errors or warnings

**If Validation Fails:**
STOP - Report: "Migration plan shows errors"

---

### Step 2.17: Run tests before applying migration

**Action:**
```bash
python manage.py test people clubs accounts --verbosity=2
```

**Expected Output:**
Tests should fail because code expects UserProfile but DB still has LoginUser

**Validation:**
- [ ] Some tests fail (this is expected)
- [ ] Errors mention "UserProfile" or model lookup issues

**This is expected at this point - the code has been updated but database hasn't been migrated yet.**

---

### Step 2.18: Apply migration

**Action:**
```bash
python manage.py migrate people
```

**Expected Output:**
```
Running migrations:
  Applying people.XXXX_rename_loginuser_to_userprofile... OK
```

**Validation:**
- [ ] Exit code is 0
- [ ] Output shows "OK" for the migration
- [ ] No errors

**If Validation Fails:**
STOP - Report: "Migration application failed: [error]"

**Rollback if needed:**
```bash
python manage.py migrate people <previous_migration_number>
```

---

### Step 2.19: Verify migration was applied

**Action:**
```bash
python manage.py showmigrations people
```

**Expected Output:**
The rename migration should have an [X] indicating it's applied

**Validation:**
- [ ] New migration shows as applied
- [ ] All previous migrations still applied

**If Validation Fails:**
STOP - Report: "Migration not properly applied"

---

### Step 2.20: Run tests after migration

**Action:**
```bash
python manage.py test people clubs accounts --verbosity=2
```

**Expected Output:**
All tests pass (or same number as baseline from Step 1.6)

**Validation:**
- [ ] Exit code is 0
- [ ] Number of tests matches baseline
- [ ] No new failures

**If Validation Fails:**
STOP - Report: "Tests failing after model rename. Errors: [list errors]"

**Required action if validation fails:**
Rollback migration and code changes, investigate failures.

---

### Step 2.21: Commit Phase 2 changes

**Action:**
```bash
git add -A
git commit -m "refactor: rename LoginUser model to UserProfile

- Renamed LoginUser class to UserProfile
- Updated related_name: login_profile -> profile
- Updated related_name: login_user -> user_profile
- Updated admin, tests, and all references
- Created and applied migration

All tests passing."
```

**Validation:**
- [ ] Commit succeeds
- [ ] Git status is clean

**If Validation Fails:**
STOP - Report: "Failed to commit changes"

---

## PHASE 3: PERMISSION FIELD REFACTORING

### Step 3.1: Read current UserProfile permission fields

**Action:**
Read `/home/jdev/code/people/models.py` lines 198-221

**Expected fields:**
- permissions_level (CharField with choices)
- is_club_staff (BooleanField)
- can_create_clubs (BooleanField)
- can_manage_members (BooleanField)

**Validation:**
- [ ] All four fields exist
- [ ] permissions_level has PERMISSION_CHOICES

**If Validation Fails:**
STOP - Report: "Permission field structure unexpected"

---

### Step 3.2: Add is_system_admin field to model

**Action:**
Edit `/home/jdev/code/people/models.py`

Find the permission fields section and add the new field:

**old_string:**
```python
    # Permission Fields for club management
    is_club_staff = models.BooleanField(
        default=False, help_text="Can assist with club management"
    )

    PERMISSION_CHOICES = [
```

**new_string:**
```python
    # Permission Fields for club management
    is_system_admin = models.BooleanField(
        default=False,
        help_text="System administrator with full tenant-wide access"
    )
    is_club_staff = models.BooleanField(
        default=False, help_text="Can assist with club management"
    )

    PERMISSION_CHOICES = [
```

**Validation:**
- [ ] is_system_admin field added
- [ ] Positioned before is_club_staff
- [ ] File is syntactically valid

**If Validation Fails:**
STOP - Report: "Failed to add is_system_admin field"

---

### Step 3.3: Create migration to add is_system_admin

**Action:**
```bash
python manage.py makemigrations people --name add_system_admin_field
```

**Expected Output:**
Migration file created with AddField operation

**Validation:**
- [ ] Exit code is 0
- [ ] Migration file created
- [ ] Contains AddField for is_system_admin

**If Validation Fails:**
STOP - Report: "Migration creation failed"

---

### Step 3.4: Apply migration to add field

**Action:**
```bash
python manage.py migrate people
```

**Expected Output:**
Migration applies successfully

**Validation:**
- [ ] Exit code is 0
- [ ] Migration marked as applied

**If Validation Fails:**
STOP - Report: "Failed to apply migration"

---

### Step 3.5: Create data migration file

**Action:**
```bash
python manage.py makemigrations people --empty --name migrate_permissions_data
```

**Expected Output:**
Empty migration file created

**Validation:**
- [ ] Migration file created
- [ ] File is empty template

**If Validation Fails:**
STOP - Report: "Failed to create empty migration"

---

### Step 3.6: Populate data migration

**Action:**
Read the empty migration file and get its exact path.

Edit the migration file to add the data migration code:

**new_string (replace entire operations list):**
```python
def migrate_permissions_forward(apps, schema_editor):
    UserProfile = apps.get_model('people', 'UserProfile')

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
        # 'member' keeps defaults (all False)

        user_profile.save()


def migrate_permissions_reverse(apps, schema_editor):
    UserProfile = apps.get_model('people', 'UserProfile')

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
        ('people', 'XXXX_add_system_admin_field'),  # Update with actual migration number
    ]

    operations = [
        migrations.RunPython(
            migrate_permissions_forward,
            migrate_permissions_reverse
        ),
    ]
```

**Important:** Update the dependency to reference the actual previous migration.

**Validation:**
- [ ] Migration file contains both forward and reverse functions
- [ ] Dependency is correct
- [ ] File is syntactically valid

**If Validation Fails:**
STOP - Report: "Data migration file is invalid"

---

### Step 3.7: Test data migration (dry run)

**Action:**
```bash
python manage.py migrate people --plan
```

**Expected Output:**
Shows data migration in the plan

**Validation:**
- [ ] New migration appears in plan
- [ ] No errors

**If Validation Fails:**
STOP - Report: "Data migration plan shows errors"

---

### Step 3.8: Apply data migration

**Action:**
```bash
python manage.py migrate people
```

**Expected Output:**
Migration applies successfully

**Validation:**
- [ ] Exit code is 0
- [ ] No errors during migration

**If Validation Fails:**
STOP - Report: "Data migration failed: [error]"

**Rollback:**
```bash
python manage.py migrate people <previous_migration>
```

---

### Step 3.9: Verify data migration results

**Action:**
Check that permissions were migrated correctly using Django shell:

```bash
python manage.py shell -c "
from people.models import UserProfile
print('Admin users:', UserProfile.objects.filter(is_system_admin=True).count())
print('Can create clubs:', UserProfile.objects.filter(can_create_clubs=True).count())
print('Can manage members:', UserProfile.objects.filter(can_manage_members=True).count())
"
```

**Validation:**
- [ ] Counts make sense based on your data
- [ ] At least some users have permissions set

**If Validation Fails:**
STOP - Report: "Data migration didn't populate fields correctly"

---

### Step 3.10: Update has_club_permissions method

**Action:**
Edit `/home/jdev/code/people/models.py`

**old_string:**
```python
    def has_club_permissions(self) -> bool:
        """Check if user has any club management permissions"""
        return (
            self.is_club_owner()
            or self.is_club_staff
            or self.permissions_level in ["owner", "admin"]
        )
```

**new_string:**
```python
    def has_club_permissions(self) -> bool:
        """Check if user has any club management permissions"""
        return (
            self.is_club_owner()  # Has club-specific ownership via ClubStaff
            or self.is_system_admin  # System-wide admin access
            or self.can_manage_members  # Can manage members globally
        )
```

**Validation:**
- [ ] Method updated
- [ ] No references to permissions_level in this method
- [ ] No references to is_club_staff in this method

**If Validation Fails:**
STOP - Report: "Method update failed"

---

### Step 3.11: Update can_manage_club method

**Action:**
Edit `/home/jdev/code/people/models.py`

Find line around 289 with:
```python
if self.is_club_owner(club) or self.permissions_level == "admin":
```

**old_string:**
```python
        if self.is_club_owner(club) or self.permissions_level == "admin":
            return True
```

**new_string:**
```python
        if self.is_club_owner(club) or self.is_system_admin:
            return True
```

**Validation:**
- [ ] Line updated
- [ ] No permissions_level reference in this method

**If Validation Fails:**
STOP - Report: "can_manage_club update failed"

---

### Step 3.12: Update get_managed_clubs method

**Action:**
Edit `/home/jdev/code/people/models.py`

Find line around 313 with:
```python
if self.permissions_level == "admin":
```

**old_string:**
```python
        # System admins can manage all clubs in their tenant
        if self.permissions_level == "admin":
            return Club.objects.select_related('tenant', 'organization').filter(
                tenant=self.contact.tenant
            )
```

**new_string:**
```python
        # System admins can manage all clubs in their tenant
        if self.is_system_admin:
            return Club.objects.select_related('tenant', 'organization').filter(
                tenant=self.contact.tenant
            )
```

**Validation:**
- [ ] Method updated
- [ ] Uses is_system_admin instead of permissions_level

**If Validation Fails:**
STOP - Report: "get_managed_clubs update failed"

---

### Step 3.13: Update get_club_permissions_summary method

**Action:**
Edit `/home/jdev/code/people/models.py`

Find around line 524:

**old_string:**
```python
        return {
            'is_admin': self.permissions_level == 'admin',
```

**new_string:**
```python
        return {
            'is_admin': self.is_system_admin,
```

**Validation:**
- [ ] Method updated

**If Validation Fails:**
STOP - Report: "get_club_permissions_summary update failed"

---

### Step 3.14: Update clean method

**Action:**
Edit `/home/jdev/code/people/models.py`

**old_string:**
```python
        # Ensure permission consistency
        # Check if user is a club owner via ClubStaff assignments
        if self.is_club_owner() and self.permissions_level not in ["owner", "admin"]:
            raise ValidationError(
                "Club owners must have permissions_level of 'owner' or 'admin'"
            )

        if self.permissions_level == "admin":
            self.can_create_clubs = True
            self.can_manage_members = True
```

**new_string:**
```python
        # Ensure permission consistency
        # System admins automatically get all capabilities
        if self.is_system_admin:
            self.can_create_clubs = True
            self.can_manage_members = True
```

**Validation:**
- [ ] Simplified validation logic
- [ ] No permissions_level references

**If Validation Fails:**
STOP - Report: "clean method update failed"

---

### Step 3.15: Update sync_user_permissions signal

**Action:**
Edit `/home/jdev/code/people/models.py`

**old_string:**
```python
    # Set Django staff status for club owners/admins
    if instance.is_club_owner() or instance.permissions_level in ["admin"]:
        user.is_staff = True
```

**new_string:**
```python
    # Set Django staff status for club owners/admins
    if instance.is_club_owner() or instance.is_system_admin:
        user.is_staff = True
```

**Validation:**
- [ ] Signal handler updated

**If Validation Fails:**
STOP - Report: "Signal handler update failed"

---

### Step 3.16: Search for remaining permissions_level references

**Action:**
```bash
grep -n "permissions_level" people/models.py
```

**Expected Output:**
Should only show:
- Line defining the field
- Line in PERMISSION_CHOICES

**Validation:**
- [ ] Only field definition and PERMISSION_CHOICES remain
- [ ] No usage in methods

**If Validation Fails:**
Review and update each remaining reference, or STOP and report.

---

### Step 3.17: Search for remaining is_club_staff references

**Action:**
```bash
grep -n "is_club_staff" people/models.py
```

**Expected Output:**
Should only show the field definition

**Validation:**
- [ ] Only field definition remains
- [ ] No usage in methods (we removed it from has_club_permissions)

**If Validation Fails:**
Update remaining references or STOP and report.

---

### Step 3.18: Run tests after method updates

**Action:**
```bash
python manage.py test people clubs accounts --verbosity=2
```

**Expected Output:**
All tests pass

**Validation:**
- [ ] Exit code is 0
- [ ] Same number of tests as baseline

**If Validation Fails:**
STOP - Report: "Tests failing after method updates: [errors]"

---

### Step 3.19: Commit permission method updates

**Action:**
```bash
git add -A
git commit -m "refactor: update permission checking methods to use is_system_admin

- Replace permissions_level checks with is_system_admin
- Simplify has_club_permissions method
- Update can_manage_club to use is_system_admin
- Update get_managed_clubs to use is_system_admin
- Simplify clean() validation
- Update signal handler

All tests passing."
```

**Validation:**
- [ ] Commit succeeds

**If Validation Fails:**
STOP - Report: "Failed to commit"

---

### Step 3.20: Update admin.py list_display

**Action:**
Read `/home/jdev/code/people/admin.py`

Update admin class to show new permission fields:

**Expected changes:**
- Add 'is_system_admin' to list_display
- Add 'is_system_admin' to list_filter
- Remove 'permissions_level' from list_display if present
- Update fieldsets to show new structure

**Method:**
Read the full file, then use Edit tool to update the admin configuration.

**Validation:**
- [ ] Admin shows is_system_admin
- [ ] File is valid Python

**If Validation Fails:**
STOP - Report: "Admin update failed"

---

### Step 3.21: Remove deprecated fields from model

**Action:**
Edit `/home/jdev/code/people/models.py`

Remove these field definitions:
1. permissions_level field
2. PERMISSION_CHOICES
3. is_club_staff field

**Method:**
Read the file to find exact line ranges, then use Edit tool to remove each field.

**Validation:**
- [ ] Fields removed from model
- [ ] File is syntactically valid
- [ ] No references to removed fields in model methods

**If Validation Fails:**
STOP - Report: "Failed to remove deprecated fields"

---

### Step 3.22: Create migration to remove deprecated fields

**Action:**
```bash
python manage.py makemigrations people --name remove_deprecated_permission_fields
```

**Expected Output:**
Migration with RemoveField operations

**Validation:**
- [ ] Migration created
- [ ] Contains RemoveField for permissions_level
- [ ] Contains RemoveField for is_club_staff

**If Validation Fails:**
STOP - Report: "Migration creation failed"

---

### Step 3.23: Review removal migration

**Action:**
Read the migration file

**Validation:**
- [ ] Has RemoveField for permissions_level
- [ ] Has RemoveField for is_club_staff
- [ ] Dependencies are correct

**If Validation Fails:**
STOP - Report: "Migration structure incorrect"

---

### Step 3.24: Apply removal migration

**Action:**
```bash
python manage.py migrate people
```

**Expected Output:**
Migration applies successfully

**Validation:**
- [ ] Exit code is 0
- [ ] No errors

**If Validation Fails:**
STOP - Report: "Migration failed: [error]"

**Rollback:**
```bash
python manage.py migrate people <previous_migration>
```

---

### Step 3.25: Run full test suite

**Action:**
```bash
python manage.py test people clubs accounts --verbosity=2
```

**Expected Output:**
All tests pass

**Validation:**
- [ ] Exit code is 0
- [ ] All tests pass
- [ ] Count matches baseline

**If Validation Fails:**
STOP - Report: "Tests failing after field removal: [errors]"

---

### Step 3.26: Commit Phase 3 completion

**Action:**
```bash
git add -A
git commit -m "refactor: remove deprecated permission fields

- Removed permissions_level field (replaced by is_system_admin + capability flags)
- Removed is_club_staff field (redundant with ClubStaff model)
- Updated admin interface
- Created and applied migrations

All tests passing. Permission system now uses:
- is_system_admin for tenant-wide admin access
- can_create_clubs for club creation permission
- can_manage_members for member management permission
- ClubStaff model for club-specific roles"
```

**Validation:**
- [ ] Commit succeeds

**If Validation Fails:**
STOP - Report: "Failed to commit"

---

## PHASE 4: FINAL VALIDATION

### Step 4.1: Run full test suite with coverage

**Action:**
```bash
python manage.py test people clubs accounts --verbosity=2
```

**Validation:**
- [ ] Exit code is 0
- [ ] All tests pass
- [ ] No warnings about deprecated fields

**If Validation Fails:**
STOP - Report: "Final test suite has failures"

---

### Step 4.2: Check for any remaining references

**Action:**
```bash
grep -r "LoginUser" --include="*.py" . | grep -v ".venv" | grep -v "__pycache__" | grep -v "migrations/"
grep -r "login_profile" --include="*.py" . | grep -v ".venv" | grep -v "__pycache__"
grep -r "login_user" --include="*.py" . | grep -v ".venv" | grep -v "__pycache__"
grep -r "permissions_level" --include="*.py" . | grep -v ".venv" | grep -v "__pycache__" | grep -v "migrations/"
grep -r "is_club_staff" --include="*.py" . | grep -v ".venv" | grep -v "__pycache__" | grep -v "migrations/"
```

**Expected Output:**
Empty or only migration files

**Validation:**
- [ ] No active code references to old names
- [ ] Only migration files reference old field names

**If Validation Fails:**
Review and update remaining references.

---

### Step 4.3: Verify migrations are consistent

**Action:**
```bash
python manage.py makemigrations --check --dry-run
```

**Expected Output:**
```
No changes detected
```

**Validation:**
- [ ] No pending migrations

**If Validation Fails:**
STOP - Report: "Unexpected pending migrations detected"

---

### Step 4.4: Check migration history

**Action:**
```bash
python manage.py showmigrations people
```

**Expected Output:**
All migrations marked as applied, including the new ones

**Validation:**
- [ ] All migrations show [X]
- [ ] New migrations are in the list

**If Validation Fails:**
STOP - Report: "Migration history is inconsistent"

---

### Step 4.5: Generate summary report

**Action:**
Create a summary of changes:

```bash
cat > /tmp/refactor_summary.txt << 'EOF'
Refactoring Summary: LoginUser → UserProfile
=============================================

Changes Applied:
1. Renamed LoginUser model to UserProfile
2. Updated related_name: login_profile → profile
3. Updated related_name: login_user → user_profile
4. Added is_system_admin field
5. Migrated permissions_level data to new fields
6. Removed permissions_level field
7. Removed is_club_staff field
8. Updated all method implementations
9. Updated admin interface
10. Updated all tests

Migrations Created:
EOF

python manage.py showmigrations people --plan | tail -5 >> /tmp/refactor_summary.txt

echo "" >> /tmp/refactor_summary.txt
echo "Tests Status:" >> /tmp/refactor_summary.txt
python manage.py test people clubs accounts 2>&1 | tail -3 >> /tmp/refactor_summary.txt

cat /tmp/refactor_summary.txt
```

**Validation:**
- [ ] Summary created
- [ ] Shows all migrations
- [ ] Shows test results

---

### Step 4.6: Final commit and push preparation

**Action:**
```bash
git log --oneline | head -10
```

**Expected Output:**
Should show the commits from this refactor

**Validation:**
- [ ] Commits are present
- [ ] Commit messages are descriptive

---

## COMPLETION CHECKLIST

- [ ] Phase 1: Preparation completed
- [ ] Phase 2: Model renamed (LoginUser → UserProfile)
- [ ] Phase 3: Permission fields refactored
- [ ] Phase 4: Final validation passed
- [ ] All tests passing
- [ ] No pending migrations
- [ ] No references to old names in active code
- [ ] Git history is clean
- [ ] Ready for code review/merge

## SUCCESS CRITERIA MET

✅ All existing functionality preserved
✅ All tests passing
✅ No data loss
✅ Clearer permission semantics
✅ No permission escalation or security issues
✅ Admin interface working correctly
✅ Code is clean and maintainable

## NEXT STEPS

1. Review the changes
2. Test manually in development environment
3. Create pull request
4. Deploy to staging for validation
5. Deploy to production

---

## ROLLBACK PROCEDURE

If any step fails and cannot be resolved:

**Rollback all changes:**
```bash
# Return to main branch
git checkout joel-soo/main

# Delete refactor branch
git branch -D refactor/loginuser-to-userprofile

# Rollback database
python manage.py migrate people <migration_number_before_refactor>
```

**Verify rollback:**
```bash
python manage.py test people clubs accounts
```

All original functionality should be restored.
