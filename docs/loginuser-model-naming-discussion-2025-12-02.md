# LoginUser Model Naming Discussion

**Date:** 2025-12-02

## Question: Is LoginUser a good name for a user model?

### Analysis

No, "LoginUser" is a problematic name for several technical reasons:

#### Issues with the name:

1. **"Login" is a verb, not a noun modifier** - "Login" refers to the action of authenticating, not a type of user. This makes the name semantically awkward.

2. **Redundant** - All User models are expected to authenticate. The name doesn't distinguish this model from other user models.

3. **Doesn't describe what it represents** - Looking at people/models.py:180-196, this model:
   - Links Django's User (authentication) with Contact (business data)
   - Manages permissions for club/organization operations
   - Acts as an extended user profile

4. **Not Django-idiomatic** - Django convention is to use "Profile" or "UserProfile" for models that extend the built-in User model via OneToOneField.

#### Better alternatives:

Given the model's purpose, consider:

- **`UserProfile`** - Standard Django convention for extending User
- **`ContactProfile`** - Emphasizes the Contact relationship
- **`AuthenticatedContact`** - Clearly shows a Contact that can authenticate
- **`MemberProfile`** - If this represents system membership

The most conventional choice would be **`UserProfile`**, which immediately signals to other Django developers that this is the standard user extension pattern.

#### What it should convey:

The name should communicate that this model bridges authentication (User) with your business domain (Contact + permissions), which "LoginUser" fails to do.

---

## Follow-up: What if there are separate types of users (admins who can create clubs vs members)?

### Response

That actually reinforces why you should keep a **single model with roles**, not separate models.

#### Why NOT separate models:

1. **Same core entity** - Both admins and members:
   - Authenticate with username/password (Django User)
   - Have personal information (Contact)
   - Belong to organizations/clubs
   - The only difference is **permissions**, not data structure

2. **Anti-pattern** - Separate models for permission levels creates:
   - Duplicate code and queries
   - Complex authentication ("which table do I check?")
   - Nightmare when someone's role changes
   - Polymorphic relationships from other models

3. **Django convention** - Django's built-in auth uses `User.is_staff`, `User.is_superuser` for this exact reason

#### Current approach is correct:

Looking at people/models.py:202-221, the existing structure already has the right approach:

```python
PERMISSION_CHOICES = [
    ("member", "Member"),
    ("staff", "Staff"),
    ("owner", "Owner"),
    ("admin", "Administrator"),
]
permissions_level = models.CharField(...)
can_create_clubs = models.BooleanField(...)
can_manage_members = models.BooleanField(...)
```

This is role-based access control (RBAC) - the standard solution.

#### Better naming for this scenario:

Given that you have both admin and member users, consider:

- **`SystemUser`** - Emphasizes system-level participant (encompasses all roles)
- **`UserProfile`** - Django convention, role-agnostic
- **`Member`** - Since even admins are "members" of the system
- **`Participant`** - Neutral term for anyone in the system
- **`AuthenticatedContact`** - Technical but accurate

**Recommendation: `SystemUser` or `UserProfile`**

`SystemUser` clearly indicates "a user of this system with varying privileges" while `UserProfile` is most Django-idiomatic. Both work better than "LoginUser" because they don't imply the model's purpose is authentication - it's to extend User with business logic and permissions.

The name should be **role-neutral** since the same model handles all permission levels.

---

## Follow-up: If the name is role-neutral, how to differentiate between "system users" and "member users"?

### Response

You differentiate them **by their role/permissions**, not by the model name. The model name describes **what the entity is** (a user), while the fields describe **what they can do** (their role).

#### How you differentiate in practice:

##### 1. Query by permission level:

```python
# Get all admin users
admins = UserProfile.objects.filter(permissions_level='admin')

# Get all member users
members = UserProfile.objects.filter(permissions_level='member')

# Get users who can create clubs
club_creators = UserProfile.objects.filter(can_create_clubs=True)
```

##### 2. Check instance permissions:

```python
user_profile = request.user.login_profile  # or request.user.profile

if user_profile.permissions_level == 'admin':
    # Admin logic
elif user_profile.permissions_level == 'member':
    # Member logic

# Or use helper methods
if user_profile.can_create_clubs:
    # Allow club creation
```

##### 3. Use manager methods:

```python
class UserProfileManager(models.Manager):
    def admins(self):
        return self.filter(permissions_level='admin')

    def members(self):
        return self.filter(permissions_level='member')

    def club_creators(self):
        return self.filter(can_create_clubs=True)

# Usage:
UserProfile.objects.admins()
UserProfile.objects.members()
```

#### The key insight:

**The model name is not for differentiation** - it's for identification. Think about Django's built-in User model:
- It doesn't have separate `AdminUser` and `RegularUser` models
- It has `is_staff`, `is_superuser` fields
- You query `User.objects.filter(is_staff=True)` to get staff users

#### Analogy:

It's like having a "Person" model with an `age` field. You don't create separate `ChildPerson` and `AdultPerson` models - you query:
- `Person.objects.filter(age__lt=18)` for children
- `Person.objects.filter(age__gte=18)` for adults

#### For this codebase:

The current `permissions_level` field already differentiates:
- `permissions_level='admin'` → System admins who can create clubs/contacts
- `permissions_level='member'` → Regular members

The name should describe the entity type, not a specific role. Hence `UserProfile` or `SystemUser` works - it encompasses everyone who authenticates with the system, and you use the permission fields to differentiate what they can do.

## Summary

- **Problem**: "LoginUser" is not a good name - it's semantically awkward and non-idiomatic
- **Solution**: Rename to `UserProfile` (Django convention) or `SystemUser` (descriptive)
- **Pattern**: Use a single model with role/permission fields (RBAC), not separate models per role
- **Differentiation**: Query by `permissions_level` field, not by model type

---

## Follow-up: Is "permissions_level" field a good practice or pattern?

### Analysis

No, `permissions_level` as currently implemented has several significant design problems.

#### Problems with the current approach:

##### 1. Multiple overlapping permission systems

You have:
- `LoginUser.permissions_level` with choices: member, staff, owner, admin (people/models.py:202-213)
- `LoginUser.is_club_staff` boolean (people/models.py:198-200)
- `LoginUser.can_create_clubs` boolean (people/models.py:216-218)
- `LoginUser.can_manage_members` boolean (people/models.py:219-221)
- `ClubStaff.role` with choices: owner, admin, instructor, assistant (clubs/models.py:258-263)
- Organization permissions via django-organizations

This creates confusion: what's the difference between `permissions_level='owner'` and `ClubStaff.role='owner'`?

##### 2. Ambiguous semantics

Looking at people/models.py:266-272:
```python
def has_club_permissions(self) -> bool:
    return (
        self.is_club_owner()  # Checks ClubStaff.role='owner'
        or self.is_club_staff  # Boolean flag
        or self.permissions_level in ["owner", "admin"]  # Permission level
    )
```

This checks THREE different things. Which "owner" means what?

##### 3. Global vs resource-specific confusion

- Line 313-316: `permissions_level='admin'` grants access to ALL clubs in tenant (global)
- Line 289: `is_club_owner(club)` checks ownership of specific club (resource-specific)

Mixing global and resource-specific permissions in the same field is problematic.

##### 4. No clear permission hierarchy

What can each level actually do? The help text says "General permission level for club operations" but:
- "member" - member of what? System? Organization? Club?
- "staff" - staff of what? Different from `is_club_staff`?
- "owner" - owner of what? Conflicts with club-specific ownership
- "admin" - gets special treatment as "system admin"

#### Better patterns:

##### Option 1: Use Django's built-in permission system

```python
class UserProfile(models.Model):
    user = models.OneToOneField(User, ...)
    contact = models.OneToOneField(Contact, ...)

    # System-level flags only
    is_system_admin = models.BooleanField(default=False)

    class Meta:
        permissions = [
            ("can_create_clubs", "Can create clubs"),
            ("can_manage_global_members", "Can manage members globally"),
        ]

# Usage:
user.has_perm('people.can_create_clubs')
```

##### Option 2: Explicit boolean flags (clearer than "levels")

```python
class UserProfile(models.Model):
    user = models.OneToOneField(User, ...)
    contact = models.OneToOneField(Contact, ...)

    # System-level permissions (explicit, not hierarchical)
    is_system_admin = models.BooleanField(default=False)
    can_create_clubs = models.BooleanField(default=False)
    can_create_organizations = models.BooleanField(default=False)

    # Resource-specific permissions handled by through models:
    # - ClubStaff for club permissions
    # - OrganizationUser for org permissions
```

##### Option 3: Simplified permission levels (if you must use them)

```python
class UserProfile(models.Model):
    # Only system-level distinction
    SYSTEM_ROLE_CHOICES = [
        ('user', 'Regular User'),      # Can only access via resource assignments
        ('admin', 'System Administrator'),  # Can manage everything in tenant
    ]
    system_role = models.CharField(
        max_length=20,
        choices=SYSTEM_ROLE_CHOICES,
        default='user'
    )

    # Specific capabilities
    can_create_clubs = models.BooleanField(default=False)
```

#### Recommended approach for your codebase:

Based on your current structure:

1. **Remove `permissions_level`** entirely
2. **Add `is_system_admin`** boolean for tenant-wide admin access
3. **Keep capability flags** (`can_create_clubs`, `can_manage_members`)
4. **Use existing models** for resource-specific permissions:
   - `ClubStaff` for club-level roles (already has `role` field)
   - `OrganizationUser/OrganizationOwner` for organization-level roles

This eliminates ambiguity: system-level permissions live on UserProfile, resource-level permissions live on through models.

#### Summary of permissions_level issues:

- **Problem**: Multiple overlapping permission systems with ambiguous semantics
- **Root cause**: Mixing global (system-wide) and resource-specific (club/org) permissions
- **Solution**:
  - Use `is_system_admin` boolean for system-level admin status
  - Keep capability flags (`can_create_clubs`, etc.) for specific permissions
  - Use through models (`ClubStaff`, `OrganizationUser`) for resource-specific roles
- **Benefit**: Clear separation of concerns - system permissions vs resource permissions
