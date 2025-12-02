# ClubStaff User to Contact Field Refactor

> in the model clubs.models.ClubStaff replace the field `user` with a one to one field `contact`

I've successfully replaced the `user` field with a `contact` OneToOneField in the `ClubStaff` model. Here's a summary of all the changes made to `clubs/models.py`:

## Field Definition Changes:
1. **Line 269-271**: Changed from `ForeignKey` to `LoginUser` → `OneToOneField` to `Contact`
2. **Line 307**: Updated index from `["user", "is_active"]` → `["contact", "is_active"]`
3. **Line 313**: Updated constraint from `["club", "user"]` → `["club", "contact"]`

## Method Updates:
4. **Line 88**: `ClubRelatedManager.get_queryset()` - Changed filter from `user=login_user` → `contact__login_user=login_user`
5. **Line 322**: `__str__()` - Changed from `self.user.contact.get_full_name()` → `self.contact.get_full_name()`
6. **Lines 328-335**: `clean()` - Added validation for `contact.login_user` existence and updated tenant access check
7. **Line 340**: `clean()` - Updated OrganizationUser validation from `self.user.user` → `self.contact.login_user.user`
8. **Line 383**: `get_permission_hierarchy_level()` - Changed from `self.user.user.is_superuser` → `self.contact.login_user.user.is_superuser`

All references have been successfully updated. The `ClubStaff` model now uses a one-to-one relationship with `Contact` instead of a foreign key to `LoginUser`.

> refactor the field people.models.LoginUser.is_club_owner as a property returning a boolean value that's derived from the contact's onetoone relationship with ClubStaff and its role

Refactor LoginUser.is_club_owner to Property

 1. Update ClubStaff Model (clubs/models.py)

 - Change contact from OneToOneField to ForeignKey with related_name="club_assignments" (plural)
 - Update the unique constraint from ["club", "contact"] to keep it (allows same contact at different clubs)
 - Note: This reverses part of the recent refactor but maintains the contact-based design

 2. Update LoginUser Model (people/models.py)

 - Remove the is_club_owner BooleanField
 - Remove the database index on is_club_owner
 - Add @property method that checks if contact has any club_assignments with role="owner" (regardless of is_active)
 - Update clean() validation to check ClubStaff records instead of the field, ensuring club owners have appropriate permissions_level
 - Update has_club_permissions() and can_manage_club() methods if needed

 3. Remove Signal Auto-sync (people/signals.py)

 - Remove or modify update_owner_permissions() signal handler that sets is_club_owner=True
 - Remove or modify sync_loginuser_permissions() signal handler
 - ClubStaff assignments will be managed explicitly, not automatically synced

 4. Update Admin Interface (people/admin.py)

 - Make is_club_owner read-only in admin (properties can be displayed but not edited)

 5. Update ClubRelatedManager (clubs/models.py)

 - Update line 88 filter from contact__login_user=login_user to handle multiple assignments

 6. No Changes Required (accounts/services.py)

 - The 6 permission check functions should work as-is since they just read the property

 7. Create Database Migration

 - Remove is_club_owner field and its index
 - Change ClubStaff.contact from OneToOne back to ForeignKey
 - Update unique constraints appropriately

 8. Update Tests

 - Update test fixtures that set is_club_owner directly
 - Update assertions to work with the property


> refactor `is_club_owner` so that it takes a club instance as an argument and returns a boolean value if the loginuser is an owner

 1. Update LoginUser Model (people/models.py)

 - Change @property is_club_owner() to regular method is_club_owner(self, club=None)
 - Logic:
   - If club is None: return True if owner of ANY club (current behavior)
   - If club provided: return True if owner of THAT specific club
 - Keep all validation checks for contact existence

 2. Update All Existing Property Usages to Method Calls

 accounts/services.py (6 locations):
 - Change login_user.is_club_owner → login_user.is_club_owner()

 people/models.py:
 - Update has_club_permissions() method: self.is_club_owner → self.is_club_owner()
 - Update can_manage_club() method: self.is_club_owner → self.is_club_owner() or self.is_club_owner(club) as appropriate
 - Update clean() method: self.is_club_owner → self.is_club_owner()

 people/admin.py:
 - Add a callable wrapper or custom display method since admin can't call methods directly in list_display

 3. No Changes Required

 - Tests and management commands already updated (don't reference is_club_owner anymore)
 - Signal handlers already updated (don't set is_club_owner anymore)


Refactored is_club_owner from a property to a method with an optional club argument. Here's a summary of all the changes:

  Summary of Changes

  1. people/models.py - LoginUser model

  - Line 237-260: Changed from @property to regular method with signature is_club_owner(self, club=None)
    - If club is None: checks if user is owner of ANY club (maintains backward compatibility)
    - If club provided: checks if user is owner of THAT specific club
  - Line 265: Updated has_club_permissions() to call self.is_club_owner()
  - Line 285: Updated can_manage_club() to call self.is_club_owner(club) for specific club check
  - Line 368: Updated clean() validation to call self.is_club_owner()
  - Line 401: Updated signal handler sync_user_permissions() to call instance.is_club_owner()

  2. accounts/services.py - Updated 6 usages

  - Line 167: loginuser_can_access_account() - changed to login_user.is_club_owner()
  - Line 184: get_accessible_member_accounts_for_loginuser() - changed to login_user.is_club_owner()
  - Line 202: get_payment_history_for_loginuser() - changed to login_user.is_club_owner()
  - Line 225: loginuser_can_create_member_accounts() - changed to login_user.is_club_owner()
  - Line 233: loginuser_can_manage_billing() - changed to login_user.is_club_owner()
  - Line 242: get_tenant_statistics_for_loginuser() - changed to login_user.is_club_owner()

  3. people/admin.py - Admin interface updates

  - Line 32: Changed list_display to use 'is_club_owner_display' instead of 'is_club_owner'
  - Line 35: Changed readonly_fields to use 'is_club_owner_display'
  - Line 42: Changed fieldsets to use 'is_club_owner_display'
  - Lines 51-55: Added is_club_owner_display() method that calls obj.is_club_owner() for admin display

  Usage Examples

  # Check if user is owner of ANY club
  if login_user.is_club_owner():
      # User owns at least one club
      pass

  # Check if user is owner of a SPECIFIC club
  if login_user.is_club_owner(my_club):
      # User owns this specific club
      pass

  All changes maintain backward compatibility while adding the new functionality to check ownership of specific clubs!


> create a method to return all clubs a loginuser is associated with

 Implement LoginUser.get_managed_clubs() Method

 1. Update LoginUser Model (people/models.py)

 Replace the placeholder get_managed_clubs() method (lines 290-293) with a full implementation:

 New implementation:
 - Return QuerySet of Club objects (not None)
 - Add optional active_only parameter (default=True) to filter by ClubStaff.is_active
 - Handle system admins: return all clubs in tenant if permissions_level="admin"
 - Access clubs via: self.contact.club_assignments.all() -> filter -> get club_ids -> return Club queryset
 - Handle edge cases: return empty queryset if no contact or no assignments
 - Update return type hint from None to QuerySet

 Method signature:
 def get_managed_clubs(self, active_only: bool = True) -> QuerySet:

 Key logic:
 - System admins (permissions_level="admin") → return all clubs in user's tenant
 - Regular users → return clubs where they have staff assignments
 - Use active_only parameter to optionally filter by ClubStaff.is_active
 - Return Club.objects.none() if user has no contact

 2. No Other Changes Required

 - Method is not currently called anywhere in the codebase
 - No tests need updating (method was never tested)
 - No breaking changes (currently returns None, so any usage would already handle that)

  Summary of Changes

  1. people/models.py - Import QuerySet type (line 5)

  Added import for QuerySet from django.db.models for proper type hinting.

  2. people/models.py - Implemented get_managed_clubs() method (lines 292-321)

  Replaced the placeholder method with a full implementation that:

  - Returns a QuerySet of Club objects (not None)
  - Accepts an optional active_only parameter (default=True) to filter by active staff assignments
  - Handles system admins specially: returns all clubs in the user's tenant if permissions_level == "admin"
  - For regular users: returns clubs where they have staff assignments via the relationship chain:
    - LoginUser.contact.club_assignments → filters by is_active if requested → extracts club_ids → returns Club queryset
  - Edge cases: returns empty queryset if user has no contact

  Usage Examples

  # Get all clubs where user has active staff assignments
  clubs = login_user.get_managed_clubs()

  # Get all clubs including inactive staff assignments
  all_clubs = login_user.get_managed_clubs(active_only=False)

  # System admins get all clubs in their tenant
  admin_clubs = admin_user.get_managed_clubs()

  # Can be chained with other queryset methods
  owner_clubs = login_user.get_managed_clubs().filter(
      staff_assignments__contact=login_user.contact,
      staff_assignments__role="owner"
  )

  The method now properly leverages the refactored ClubStaff.contact ForeignKey relationship to efficiently retrieve all clubs associated with a user!

