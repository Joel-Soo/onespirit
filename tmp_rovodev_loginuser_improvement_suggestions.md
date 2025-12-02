# LoginUser Model Improvement Recommendations

## 1. Fix Type Hints (.pyi file)
Update people/models.pyi to match current implementation:
- Remove `is_club_owner: models.BooleanField`
- Add `def is_club_owner(self, club=None) -> bool: ...`
- Fix `get_managed_clubs` return type to `QuerySet`

## 2. Resolve Circular Import
Move the Club import to module level or use string reference:
```python
# Option A: Module level import with TYPE_CHECKING
if TYPE_CHECKING:
    from clubs.models import Club

# Option B: Use string reference
def get_managed_clubs(self, active_only: bool = True) -> 'QuerySet[Club]':
    Club = apps.get_model('clubs', 'Club')
```

## 3. Improve Error Handling
Make error conditions more explicit:
```python
def is_club_owner(self, club=None) -> bool:
    if not self.contact_id:
        raise ValueError("LoginUser must have an associated contact")
    
    if not hasattr(self.contact, 'club_assignments'):
        # Log warning or handle gracefully
        return False
```

## 4. Add Performance Optimization Methods
Create optimized versions for common use cases:
```python
@classmethod
def prefetch_club_data(cls, queryset):
    """Prefetch related club data for efficient querying"""
    return queryset.select_related('contact', 'user').prefetch_related(
        'contact__club_assignments__club'
    )

def get_owned_clubs(self) -> 'QuerySet[Club]':
    """Optimized method to get clubs owned by this user"""
    return self.get_managed_clubs().filter(
        staff_assignments__contact=self.contact,
        staff_assignments__role='owner'
    )
```

## 5. Separate Business Logic
Consider creating a service layer for complex business logic:
```python
# people/services.py
class LoginUserPermissionService:
    def __init__(self, login_user):
        self.login_user = login_user
    
    def can_manage_club(self, club):
        """Centralized club management permission logic"""
        # Move complex logic here
    
    def get_accessible_clubs(self, permission_type='any'):
        """Get clubs based on specific permission needs"""
        # Optimized queries here
```

## 6. Add Caching for Expensive Operations
For frequently accessed properties:
```python
from django.core.cache import cache

def is_club_owner(self, club=None) -> bool:
    cache_key = f"club_owner_{self.id}_{club.id if club else 'any'}"
    result = cache.get(cache_key)
    if result is None:
        # Perform query
        result = self._calculate_club_ownership(club)
        cache.set(cache_key, result, 300)  # 5 minutes
    return result
```