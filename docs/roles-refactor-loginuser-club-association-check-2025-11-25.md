# How to Check if LoginUser is Associated with a Club

## Question

How to check if a `LoginUser` instance is associated with a `Club`?

## Answer

Given the refactored model structure, here's how you can check if a `LoginUser` instance is associated with a `Club` (in any staff role):

### Approach 1: Query from LoginUser side

```python
def is_staff_at_club(login_user, club):
    """Check if login_user has any staff assignment at the club."""
    return login_user.contact.club_assignments.filter(club=club).exists()
```

### Approach 2: Query from Club side

```python
def is_staff_at_club(login_user, club):
    """Check if login_user has any staff assignment at the club."""
    return club.staff_assignments.filter(contact=login_user.contact).exists()
```

### Approach 3: Check only active assignments

```python
def is_active_staff_at_club(login_user, club):
    """Check if login_user has an active staff assignment at the club."""
    return login_user.contact.club_assignments.filter(
        club=club,
        is_active=True
    ).exists()
```

### Approach 4: Get the staff assignment details

```python
def get_club_assignment(login_user, club):
    """Get the staff assignment for this user at this club (if any)."""
    try:
        return login_user.contact.club_assignments.get(club=club)
    except ClubStaff.DoesNotExist:
        return None
    except ClubStaff.MultipleObjectsReturned:
        # This shouldn't happen due to unique constraint, but handle it
        return login_user.contact.club_assignments.filter(club=club).first()
```

Then use it as:
```python
assignment = get_club_assignment(login_user, club)
if assignment:
    print(f"User role: {assignment.role}")
    print(f"Is active: {assignment.is_active}")
```

### Approach 5: Add a method to LoginUser model

You could add a helper method to the `LoginUser` model:

```python
def has_club_assignment(self, club) -> bool:
    """Check if this user has any staff assignment at a specific club."""
    if not hasattr(self, 'contact') or not self.contact:
        return False

    return self.contact.club_assignments.filter(club=club).exists()

def get_club_assignment(self, club):
    """Get the staff assignment for this user at this club (if any)."""
    if not hasattr(self, 'contact') or not self.contact:
        return None

    try:
        return self.contact.club_assignments.get(club=club)
    except:
        return None
```

## Notes

- The `club_assignments` relationship comes from `ClubStaff.contact` ForeignKey with `related_name="club_assignments"`
- These approaches check for **any** role (owner, admin, instructor, assistant)
- Add `.filter(is_active=True)` if you only want to check active assignments
- The unique constraint on `["club", "contact"]` ensures each contact can only have one assignment per club
