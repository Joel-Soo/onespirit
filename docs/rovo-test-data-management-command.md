# Test Data Management Command

## Overview

The `create_test_data` management command automatically generates test data for the OneSpirit Django application in the correct dependency order. It creates realistic test data including tenants, contacts, member accounts, clubs, and payment history.

## Installation

The management command has been created at `accounts/management/commands/create_test_data.py` and is ready to use.

## Basic Usage

```bash
# Create basic test data (2 tenants, 5 members each, 2 clubs each)
python manage.py create_test_data

# Create test data with specific parameters
python manage.py create_test_data --scenario full --tenants 3 --members 10 --clubs 3

# Clear existing test data and create new data
python manage.py create_test_data --clear-existing --scenario basic

# Create minimal test data for quick testing
python manage.py create_test_data --scenario minimal --tenants 1 --members 3 --clubs 1

# Create test data without payment history (faster)
python manage.py create_test_data --no-payments
```

## Command Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--scenario` | choice | `basic` | Test data scenario: `minimal`, `basic`, or `full` |
| `--tenants` | int | `2` | Number of tenant accounts to create |
| `--members` | int | `5` | Number of member accounts per tenant |
| `--clubs` | int | `2` | Number of clubs per tenant |
| `--clear-existing` | flag | `False` | Clear existing test data before creating new data |
| `--no-payments` | flag | `False` | Skip creating payment history data |

## Scenarios

### Minimal Scenario
- Perfect for unit testing
- Quick creation (< 30 seconds)
- 1 tenant, 3 members, 1 club

### Basic Scenario (Default)
- Good for development and manual testing
- Moderate creation time (1-2 minutes)
- 2 tenants, 5 members each, 2 clubs each

### Full Scenario
- Complete test environment
- Longer creation time (2-5 minutes)
- Uses custom tenant/member/club counts
- Includes payment history

## Created Test Data

### Users & Authentication
- **Admin User**: `testadmin` / `testpass123` (superuser)
- **Staff Users**: `teststaff1`, `teststaff2`, etc. / `testpass123`
- **Member Users**: `testmember1`, `testmember2`, etc. / `testpass123`

### Tenants
- **Test Martial Arts Academy 1**: Premium subscription
- **Test Fitness Center 2**: Basic subscription
- **Test Combat Sports Club 3**: Enterprise subscription

### Organizations (if django-organizations available)
- Test Karate Association
- Test Jiu-Jitsu Federation
- Test MMA Organization
- Test Fitness Network

### Contacts
- Realistic names and contact information
- Emergency contacts and medical information
- Proper tenant associations

### Member Accounts
- Sequential membership numbers (`TEST000001`, etc.)
- Various membership types (student, instructor, honorary, lifetime)
- Realistic start/end dates

### Clubs
- Various martial arts styles (Karate, Jiu-Jitsu, MMA, Boxing)
- Different skill levels (Beginner, Intermediate, Advanced)
- Complete club information (address, phone, email, website)

### Club Staff & Memberships
- Instructors, assistant instructors, managers
- Member-club associations with belt ranks
- Realistic join dates and status

### Payment History (optional)
- Member fee payments with various methods
- Tenant subscription payments
- Different payment statuses and types

## Data Dependencies

The command creates data in the correct order to handle Django model dependencies:

1. **Django Users** → Authentication foundation
2. **TenantAccounts** → Multi-tenant structure
3. **Organizations** → External django-organizations models
4. **Contacts** → People information
5. **LoginUsers** → User profiles
6. **MemberAccounts** → Club memberships
7. **Clubs** → Club structure
8. **ClubStaff** → Staff assignments
9. **ClubMembers** → Member-club relationships
10. **PaymentHistory** → Financial records

## Examples

### Quick Development Setup
```bash
python manage.py create_test_data --scenario basic
```

### Testing Environment
```bash
python manage.py create_test_data --clear-existing --scenario minimal --no-payments
```

### Full Demo Environment
```bash
python manage.py create_test_data --scenario full --tenants 5 --members 20 --clubs 4
```

### Reset Test Data
```bash
python manage.py create_test_data --clear-existing
```

## Verification

After running the command:

1. **Login to Django Admin**: `http://localhost:8000/admin/`
   - Username: `testadmin`
   - Password: `testpass123`

2. **Check Created Data**:
   - Navigate to Accounts → Tenant Accounts
   - Navigate to People → Contacts
   - Navigate to Clubs → Clubs
   - Verify relationships and data integrity

3. **Test Multi-tenancy**:
   - Switch between different tenant contexts
   - Verify data isolation between tenants

## Troubleshooting

### Common Issues

**Error: django-organizations not available**
- Install django-organizations: `pip install django-organizations`
- Or run with organizations disabled (warning will appear)

**Error: Circular dependency**
- The command handles TenantAccount ↔ Contact circular dependency automatically
- If errors persist, use `--clear-existing` flag

**Error: Unique constraint violation**
- Use `--clear-existing` to remove conflicting test data
- Check for existing users/emails that conflict

### Performance Tips

- Use `--no-payments` for faster creation during development
- Use `--scenario minimal` for unit testing
- Use `--clear-existing` sparingly (slower due to cascade deletes)

## Customization

To modify the test data:

1. **Edit Templates**: Modify the data templates in `create_test_data.py`
2. **Add New Scenarios**: Add new scenario types in the command
3. **Custom Data**: Create your own management command based on this template

---

## 🎉 **Management Command Implementation Complete!**

### **Files Created:**
1. **`accounts/management/commands/create_test_data.py`** - The main management command
2. **`docs/rovo-test-data-management-command.md`** - Complete usage guide
3. **`tmp_rovodev_test_data_creation.py`** - Test script (temporary)

### **Command Features:**
✅ **Handles all dependency relationships** in correct order  
✅ **Creates realistic test data** with proper relationships  
✅ **Multiple scenarios** (minimal, basic, full)  
✅ **Configurable parameters** (tenants, members, clubs)  
✅ **Clear existing data** option  
✅ **Skip payments** for faster testing  
✅ **Comprehensive error handling** and validation  
✅ **Detailed progress output** and summary  

### **Quick Start:**
```bash
# View all options
python manage.py create_test_data --help

# Create basic test data (recommended)
python manage.py create_test_data

# Create minimal data for quick testing
python manage.py create_test_data --scenario minimal --tenants 1 --members 3 --clubs 1

# Full demo environment
python manage.py create_test_data --scenario full --tenants 3 --members 10 --clubs 4
```

### **Login Credentials Created:**
- **Admin**: `testadmin` / `testpass123` (superuser)
- **Staff**: `teststaff1`, `teststaff2` / `testpass123`  
- **Members**: `testmember1`, `testmember2`, etc. / `testpass123`

The command creates data in the exact dependency order we documented and handles the circular dependency between TenantAccount and Contact automatically. It also includes realistic test data for clubs, memberships, staff assignments, and optional payment history.

---

*Generated by Rovo Dev - Django Test Data Management*