# How to Check if LoginUser is an Admin of a Club

## Question

How to check if a `LoginUser` instance is an admin of a `Club`?

## Answer

Given the refactored model structure, here's how you can check if a `LoginUser` instance is an admin of a specific `Club`:

### Approach 1: Query from LoginUser side

```python
def is_admin_of_club(login_user, club):
    """Check if login_user is admin of the specific club."""
    return login_user.contact.club_assignments.filter(
        club=club,
        role="admin"
    ).exists()
```

### Approach 2: Query from Club side

```python
def is_admin_of_club(login_user, club):
    """Check if login_user is admin of the specific club."""
    return club.staff_assignments.filter(
        contact=login_user.contact,
        role="admin"
    ).exists()
```

### Approach 3: Check for admin or owner (elevated permissions)

```python
def has_admin_permissions_at_club(login_user, club):
    """Check if login_user has admin-level permissions at the club (admin or owner)."""
    return login_user.contact.club_assignments.filter(
        club=club,
        role__in=["admin", "owner"]
    ).exists()
```

### Approach 4: Check only active admin assignments

```python
def is_active_admin_of_club(login_user, club):
    """Check if login_user is an active admin of the specific club."""
    return login_user.contact.club_assignments.filter(
        club=club,
        role="admin",
        is_active=True
    ).exists()
```

### Approach 5: Add a method to LoginUser model

You could add a helper method to the `LoginUser` model:

```python
def is_admin_of_club(self, club) -> bool:
    """Check if this user is admin of a specific club."""
    if not hasattr(self, 'contact') or not self.contact:
        return False

    return self.contact.club_assignments.filter(
        club=club,
        role="admin"
    ).exists()

def has_elevated_club_role(self, club) -> bool:
    """Check if this user is owner or admin of a specific club."""
    if not hasattr(self, 'contact') or not self.contact:
        return False

    return self.contact.club_assignments.filter(
        club=club,
        role__in=["owner", "admin"]
    ).exists()
```

## Notes

- `ClubStaff.role` choices include: `"owner"`, `"admin"`, `"instructor"`, `"assistant"`
- Admin has elevated permissions but is below owner in the hierarchy
- According to `ClubStaff.clean()` validation:
  - Owners get all permissions (can_manage_members, can_manage_schedule, can_view_finances)
  - Admins get can_manage_members and can_manage_schedule
- Add `.filter(is_active=True)` if you only want to check active assignments
- Consider using Approach 3 if you want to check for any elevated permissions (owner or admin)
