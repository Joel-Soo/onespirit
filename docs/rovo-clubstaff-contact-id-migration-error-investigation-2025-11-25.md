# ClubStaff contact_id Migration Error Investigation

**Date:** 2025-11-25
**Issue:** `sqlite3.OperationalError: no such column: clubs_clubstaff.contact_id`

## Problem Statement

Test `test_get_accessible_member_accounts_for_loginuser` in `accounts.tests.test_services.LoginUserServicesTestCase` was failing with:

```
sqlite3.OperationalError: no such column: clubs_clubstaff.contact_id
```

## Investigation Summary

The test is failing with `sqlite3.OperationalError: no such column: clubs_clubstaff.contact_id` because there's a schema mismatch between the database and the model definition.

**Root Cause:**
1. The `clubs_clubstaff` table was created with a `user_id` field (pointing to `people_loginuser`) in the initial migration
2. The `ClubStaff` model was later changed to use a `contact` field (pointing to `people_contact`) 
3. There's a pending migration (`clubs/migrations/0004_...`) that needs to be applied to convert the schema
4. The error occurs in the `LoginUser.is_club_owner()` method when it tries to query `clubs_clubstaff.contact_id`, but the database still has `user_id`

**Specific Error Flow:**
1. Test creates a `LoginUser` instance
2. Django's `post_save` signal calls `sync_user_permissions()` 
3. `sync_user_permissions()` calls `instance.is_club_owner()`
4. `is_club_owner()` queries `self.contact.club_assignments.filter(role="owner")`
5. This generates SQL looking for `clubs_clubstaff.contact_id` 
6. Database fails because it only has `clubs_clubstaff.user_id`

## Technical Details

### Current Database Schema
The database table `clubs_clubstaff` currently has:
- `user_id` field (from initial migration)

### Expected Model Schema  
The `ClubStaff` model now expects:
- `contact` field (pointing to `people_contact`)

### Migrations Status
Django detected pending migrations when running `makemigrations --dry-run`:

```
clubs/migrations/0004_remove_clubstaff_unique_staff_assignment_per_club_and_more.py
  - Remove field user from clubstaff  
  + Add field contact to clubstaff
```

## Solution

The pending migration needs to be applied. The error occurs because the model definition and database schema are out of sync.

**Next Steps:**
You need to either:
1. Apply the pending migration: `python manage.py migrate clubs 0004`
2. Or if you want to avoid making changes, temporarily modify the test to skip the problematic code path

## Files Examined

- `accounts/tests/test_services.py` - Contains the failing test
- `clubs/models.py` - Contains current ClubStaff model with `contact` field
- `clubs/migrations/0001_initial.py` - Original migration that created `user` field
- `clubs/migrations/0002_add_organization_user_to_clubstaff.py` - Added organization_user field
- `clubs/migrations/0003_add_club_name_uniqueness_constraint.py` - Added uniqueness constraint
- `people/models.py` - Contains LoginUser.is_club_owner() method that triggers the error
- `accounts/services.py` - Contains the service function being tested

## Key Code References

### LoginUser.is_club_owner() method (people/models.py:258)
```python
def is_club_owner(self) -> bool:
    return self.contact.club_assignments.filter(role="owner").exists()
```

### ClubStaff model (clubs/models.py)
```python
class ClubStaff(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='club_assignments')
    # ... other fields
```

The mismatch between expecting `contact` field but having `user_id` in the database is the root cause of this error.


---


      • command: "echo \"1\" | python manage.py makemigrations clubs --name convert_clubstaff_user_to_contact"
  └── Calling open_files:
      • file_paths: "['clubs/migrations/0004_convert_clubstaff_user_to_contact.py']"


   It is impossible to add a non-nullable field 'contact' to clubstaff without specifying a default. This is
   because...
   Please select a fix:
    1) Provide a one-off default now (will be set on all existing rows with a null value for this column)
    2) Quit and manually define a default value in models.py.
   Select an option: Please enter the default value as valid Python.
   The datetime and django.utils.timezone modules are available, so it is possible to provide e.g. timezone.now as
   a...
   Type 'exit' to exit this prompt
   Traceback (most recent call last):
     File "/home/jdev/code/manage.py", line 22, in <module>
       main()
   (35 lines truncated)
           ^^^^^^^^^^^^^^^^^^^^^^
       )
       ^
     File "/home/jdev/code/.venv_devbox00/lib/python3.13/site-packages/django/db/migrations/questioner.py", line
   192...
       return self._ask_default()
              ~~~~~~~~~~~~~~~~~^^
     File "/home/jdev/code/.venv_devbox00/lib/python3.13/site-packages/django/db/migrations/questioner.py", line
   154...
       code = input()
   EOFError: EOF when reading a line
   >>>



  Error executing tool open_files: Error opening clubs/migrations/0004_convert_clubstaff_user_to_contact.py: File
  clubs/migrations/0004_convert_clubstaff_user_to_contact.py not found in workspace.


╭─ Response ───────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Django is treating this as if there are existing records that need a default value, even though we confirmed there   │
│ are 0 ClubStaff records. This happens because Django analyzes the model structure rather than actual data.           │
│                                                                                                                      │
│ Let me create a proper migration manually that handles this conversion correctly:                                    │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯



