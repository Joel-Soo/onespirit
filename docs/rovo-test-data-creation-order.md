> i want to start populating the database with test data, what should be created first


# Test Data Creation Order for OneSpirit Django Application

Based on analysis of the models and their dependencies, here's the **recommended order for creating test data**:

## 🎯 **Test Data Creation Order**

### **1. First Priority - Foundation Data**

**Create these in order:**

1. **Django Users** (`auth.User`)
   - Required for: LoginUser, PaymentHistory.created_by
   - Example: Admin user, test staff users

2. **TenantAccount** (from `accounts.models`)
   - Required for: All other models (multi-tenancy foundation)
   - No dependencies except optional primary_contact (set after Contact creation)
   - Example: "Martial Arts Academy", "Fitness Center"

### **2. Second Priority - Organizations (External Package)**

3. **Organizations** (`organizations.Organization`) 
   - Required for: Contact.organization, Club.organization
   - Uses django-organizations package
   - Example: "Main Academy", "Branch Location"

### **3. Third Priority - People Data**

4. **Contact** (`people.models`)
   - Required for: MemberAccount, TenantAccount relationships
   - Dependencies: TenantAccount (nullable for migration), Organization (optional)
   - Example: John Doe, Jane Smith

5. **LoginUser** (`people.models`)
   - Required for: Club management, admin functions
   - Dependencies: User, Contact
   - Example: Admin users, club owners

### **4. Fourth Priority - Account Relationships**

6. **Update TenantAccount.primary_contact**
   - Set the primary_contact field using created Contacts
   - Resolves the circular dependency

7. **MemberAccount** (`accounts.models`)
   - Dependencies: TenantAccount, Contact (as member_contact and primary_contact)
   - Example: Student memberships, instructor accounts

### **5. Fifth Priority - Club Structure**

8. **Club** (`clubs.models`)
   - Dependencies: TenantAccount, Organization, Contact (for owner)
   - Example: "Beginner Karate", "Advanced Jiu-Jitsu"

9. **ClubStaff** (`clubs.models`)
   - Dependencies: Club, Contact, optional OrganizationUser
   - Example: Instructors, assistant coaches

10. **ClubMember** (`clubs.models`)
    - Dependencies: Club, MemberAccount
    - Creates the many-to-many relationship between members and clubs

### **6. Sixth Priority - Optional Data**

11. **ClubAffiliation** (`clubs.models`)
    - Dependencies: Club (parent/child relationships)
    - Example: Main dojo → satellite locations

12. **PaymentHistory** (`accounts.models`)
    - Dependencies: TenantAccount or MemberAccount, User (created_by)
    - Example: Membership fees, equipment purchases

---

## 🚀 **Quick Start Script Approach**

Recommended approaches for creating test data:

**Option A:** Create a management command (`python manage.py create_test_data`) that populates all the data in the correct order

**Option B:** Create Django fixtures (JSON/YAML files) that can be loaded with `python manage.py loaddata`

**Option C:** Create a simple Python script that you can run interactively to create specific types of test data

**Option D:** Show exact model creation sequence with sample code for each step

## 🔗 **Model Dependencies Summary**

```
User (Django auth)
├── LoginUser
│   └── Contact
│       ├── MemberAccount
│       └── TenantAccount (circular - resolve after Contact creation)
├── Organizations (django-organizations)
│   └── Contact (optional)
└── TenantAccount
    ├── Contact (tenant field)
    ├── MemberAccount (tenant field)
    └── Club
        ├── ClubStaff
        ├── ClubMember (links to MemberAccount)
        └── ClubAffiliation (self-referential)
```

## 📝 **Key Considerations**

- **Circular Dependencies:** TenantAccount ↔ Contact requires careful handling
- **Multi-tenancy:** All data must be properly scoped to tenants
- **Organizations:** External package dependency must be configured
- **Validation:** Models have extensive clean() methods that enforce business rules
- **Relationships:** Many complex foreign keys and through-models require specific order

## 🛠 **Next Steps**

1. Decide on test data approach (management command, fixtures, or script)
2. Define specific test scenarios and data volumes needed
3. Create sample data that represents realistic use cases
4. Consider creating separate datasets for different testing purposes (unit tests, integration tests, demo data)

---

## Initial data creation order

### 1. Super User
```
manage.py createsuperuser
```
* `is_super`

### 2. TenantAccount
TenantAccountContact
* LoginUser
* role is either `primary` or `admin`
* can create Clubs for the tenant
* can create contacts for the tenant

### 3. Club
Club staff
* LoginUser
* Contact

### 4. Organization
Organization Contact




Koala Kai
Maggie's Dojo





