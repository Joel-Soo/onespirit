# TYPE_CHECKING and Circular Import Solutions - 2025-11-25

## Original Question

> what is TYPE_CHECKING and how can it fix circular imports

## What is `TYPE_CHECKING`?

`TYPE_CHECKING` is a special constant from Python's `typing` module that is **only `True` during static type checking** (like when mypy, PyChance, or your IDE analyzes your code), but is **`False` at runtime**.

```python
from typing import TYPE_CHECKING

print(TYPE_CHECKING)  # This will print: False
# But mypy/IDE treats it as True when type checking
```

## How It Fixes Circular Imports

### The Problem
In the LoginUser model, we have this risky pattern:

```python
def get_managed_clubs(self, active_only: bool = True) -> QuerySet:
    from clubs.models import Club  # 🚨 Local import inside method
    # ...
```

This can cause issues because:
1. **Unclear dependencies** - imports hidden inside methods
2. **Potential circular imports** - if Club model also imports from people
3. **Runtime overhead** - import happens every time method is called

### The TYPE_CHECKING Solution

```python
# Example: How TYPE_CHECKING fixes circular imports

from __future__ import annotations  # Enables forward references
from typing import TYPE_CHECKING, QuerySet
from django.db import models

# Only import during type checking, not at runtime
if TYPE_CHECKING:
    from clubs.models import Club

class LoginUser(models.Model):
    # ... other fields ...
    
    def get_managed_clubs(self, active_only: bool = True) -> QuerySet[Club]:
        # At runtime, we import here (no circular import risk)
        from django.apps import apps
        Club = apps.get_model('clubs', 'Club')
        
        # Or use lazy import pattern
        # from clubs.models import Club  # This is safe here
        
        if active_only:
            return Club.objects.filter(active=True, staff__contact=self.contact)
        return Club.objects.filter(staff__contact=self.contact)

# Alternative approach using string type annotation
class AlternativeLoginUser(models.Model):
    def get_managed_clubs(self, active_only: bool = True) -> 'QuerySet[Club]':
        # Using string annotation - no import needed for type hints
        from clubs.models import Club
        # ... implementation
```

## How TYPE_CHECKING Works

### 1. **At Type Checking Time** (mypy, IDE analysis):
```python
TYPE_CHECKING = True  # Special behavior for type checkers
```
- The import inside `if TYPE_CHECKING:` block **runs**
- Type checker sees `Club` and can validate `QuerySet[Club]`
- Your IDE gets autocomplete and type hints

### 2. **At Runtime** (actual Python execution):
```python
TYPE_CHECKING = False  # Normal Python behavior
```
- The import inside `if TYPE_CHECKING:` block is **skipped**
- No circular import can occur
- `Club` isn't available as a variable, but that's fine because we import it locally in the method

## Complete Example for LoginUser

```python
from __future__ import annotations
from typing import TYPE_CHECKING, QuerySet
from django.db import models

# Type-only imports - never execute at runtime
if TYPE_CHECKING:
    from clubs.models import Club

class LoginUser(models.Model):
    # ... existing fields ...
    
    def get_managed_clubs(self, active_only: bool = True) -> QuerySet[Club]:
        """Get clubs this user can manage."""
        # Safe runtime import - no circular dependency risk
        from clubs.models import Club
        
        queryset = Club.objects.filter(
            staff_assignments__contact=self.contact,
            staff_assignments__role__in=['owner', 'manager']
        )
        
        if active_only:
            queryset = queryset.filter(active=True)
            
        return queryset.distinct()
```

## Why This Pattern Works

1. **Type checkers get the info they need** from the `if TYPE_CHECKING:` block
2. **Runtime avoids the import** until the method actually runs
3. **No circular dependency** because imports happen later in execution
4. **Clear code organization** - all type imports at the top

## Alternative: String Annotations

You can also use string type hints:

```python
def get_managed_clubs(self, active_only: bool = True) -> 'QuerySet[Club]':
    # No TYPE_CHECKING block needed - string annotation
```

But `TYPE_CHECKING` is generally preferred because:
- Better IDE support
- More explicit about dependencies  
- Easier to refactor later

## When to Use TYPE_CHECKING

Use it when you need to:
- Reference models that might create circular imports
- Import expensive modules only for type hints
- Keep type information without runtime overhead

## Summary: TYPE_CHECKING Solution

**TYPE_CHECKING** solves circular imports by creating a **two-phase import system**:

1. **Type checking phase**: Imports happen, type checkers see all the types
2. **Runtime phase**: Imports are skipped, no circular dependency risk

**For the LoginUser model specifically:**

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from clubs.models import Club  # Only during type checking

def get_managed_clubs(self) -> QuerySet[Club]:  # Type hint works
    from clubs.models import Club  # Safe runtime import
    # ... method implementation
```

This pattern is widely used in Django projects and is considered a best practice for handling model relationships that could create circular imports.

## Context

This explanation was provided in response to questions about the LoginUser model audit findings, specifically regarding how to resolve the circular import issue identified in the `get_managed_clubs()` method where `Club` was being imported locally within the method.

## Documentation Date
2025-11-25 by Rovo Dev