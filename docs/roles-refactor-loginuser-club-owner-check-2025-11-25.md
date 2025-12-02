# How to Check if LoginUser is Owner of a Specific Club

## Question

Given a `LoginUser` instance and a `Club` instance, how can I check if the `LoginUser` instance is the owner of the club?

## Answer

Given the recent refactoring, here's how you can check if a `LoginUser` instance is the owner of a specific `Club` instance:

### Approach 1: Query from LoginUser side

```python
def is_owner_of_club(login_user, club):
    """Check if login_user is owner of the specific club."""
    return login_user.contact.club_assignments.filter(
        club=club,
        role="owner"
    ).exists()
```

### Approach 2: Query from Club side

```python
def is_owner_of_club(login_user, club):
    """Check if login_user is owner of the specific club."""
    return club.staff_assignments.filter(
        contact=login_user.contact,
        role="owner"
    ).exists()
```

### Approach 3: Add a method to LoginUser model

You could add a helper method to the `LoginUser` model in `people/models.py`:

```python
def is_owner_of_club(self, club) -> bool:
    """Check if this user is owner of a specific club."""
    if not hasattr(self, 'contact') or not self.contact:
        return False

    return self.contact.club_assignments.filter(
        club=club,
        role="owner"
    ).exists()
```

Then use it as:
```python
if login_user.is_owner_of_club(club):
    # User is owner of this club
    pass
```

## Notes

- The current `is_club_owner` property returns `True` if the user is an owner of **any** club
- These approaches check ownership of a **specific** club
- None of these check `is_active` status - if you want to only check active ownership, add `.filter(is_active=True)`
- Both Approach 1 and 2 are equivalent in terms of performance and result
