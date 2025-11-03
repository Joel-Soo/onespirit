# OneSpirit Project Brief

## Problem Statement

Martial arts clubs and associations face administrative challenges managing memberships, payments, staff assignments, and member data across multiple locations. Current solutions are either:
- Generic membership systems that don't understand martial arts club hierarchies (dojos, instructors, affiliations)
- Single-tenant applications that require separate deployments for each organization
- Spreadsheet-based systems prone to data inconsistency and security issues

**Core Problem**: There is no purpose-built, multi-tenant backend system that provides secure data isolation while allowing martial arts associations to manage multiple affiliated clubs, track member progression, handle payments, and maintain proper access controls for instructors and administrators.

## Target Users

### Primary Users
1. **Martial Arts Association Administrators**
   - Manage multiple affiliated clubs/dojos
   - Oversee membership subscriptions
   - Track cross-club affiliations and relationships
   - Monitor payment history across the organization

2. **Club Instructors/Staff**
   - Manage member rosters within their assigned clubs
   - Track attendance and progression (future)
   - Handle grading and equipment sales
   - Access only their club's data (tenant isolation)

3. **Club Members** (future scope)
   - View personal training history
   - Make payments online
   - Update contact information

### Secondary Users
- **System Integrators**: Need APIs to connect with existing systems
- **Accountants**: Require payment audit trails and reporting

## Success Metrics

### Technical Metrics
- **Data Isolation**: 100% tenant separation with zero cross-tenant data leaks
- **Performance**: < 200ms response time for 95th percentile admin queries
- **Uptime**: 99.5% availability for production deployments
- **Test Coverage**: > 80% code coverage with comprehensive tenant isolation tests

### Business Metrics
- **Adoption Rate**: Number of martial arts organizations onboarded
- **Clubs Per Tenant**: Average clubs managed per association (target: 3-10)
- **Members Per Club**: Active members tracked per club (target: 20-100)
- **Data Accuracy**: Reduction in manual data errors vs. spreadsheet-based systems
- **Time Savings**: Reduction in administrative overhead (target: 30% reduction)

### User Satisfaction
- Admin task completion rate > 90%
- Staff adoption rate > 75% within 3 months
- Support ticket volume < 5 per tenant per month

## MVP Scope

### In Scope (Currently Implemented)
✅ **Multi-Tenant Architecture**
- Subdomain and URL path-based tenant detection
- Thread-safe context-aware managers
- Middleware-based access control and tenant isolation

✅ **Core Data Models**
- TenantAccount: Top-level customer with subscription metadata
- Contact: Personal information with tenant and organization awareness
- LoginUser: Authentication with tenant access permissions
- MemberAccount: Membership lifecycle and status tracking
- PaymentHistory: Comprehensive payment tracking with enums and validation
- Club: Organization model with staff and member relationships
- ClubStaff/ClubMember: Role-based assignments with permission management
- ClubAffiliation: Inter-club relationships within tenant boundaries

✅ **Access Control**
- Superuser bypass for system administration
- Tenant-scoped user access verification
- Admin tenant selection with session persistence
- Organization-level permissions for club staff

✅ **Admin Interface**
- Django admin with tenant selection support
- Custom list displays and filters for all models
- Inline editing for related models
- Validation at model and admin levels

✅ **Testing Suite**
- Unit tests for tenant-aware managers
- Integration tests for middleware behavior
- Model validation tests
- Service layer tests for account operations

### Out of Scope (Future Enhancements)
- Frontend UI for end users
- RESTful API endpoints
- Member self-service portal
- Attendance tracking
- Grading/belt progression system
- Reporting and analytics dashboard
- Email notifications and reminders
- Mobile application
- Document storage (certificates, waivers)
- Calendar and event management
- Integration with payment processors (Stripe, PayPal)

## Key Constraints

### Technical Constraints
1. **Technology Stack**
   - Python 3.13+ (required)
   - Django 5.2+ framework
   - PostgreSQL for production (SQLite for dev)
   - Redis for caching (production only)

2. **Architecture Constraints**
   - Must maintain strict tenant isolation at database query level
   - Thread-local context variables for tenant/organization/user state
   - No shared data between tenants except system-level metadata
   - All queries must be tenant-aware by default

3. **Performance Constraints**
   - Maximum query complexity: 3 joins for list views
   - Database indexes required on tenant, email, dates
   - Caching strategy for frequently accessed tenant metadata

4. **Security Constraints**
   - No cross-tenant data access (enforced by middleware and managers)
   - TLS required for production
   - Django security settings enforced (CSRF, XSS protection, HSTS)
   - User permissions tied to LoginUser.contact.tenant relationship

### Business Constraints
1. **Development Resources**
   - Single developer/small team
   - Limited budget for third-party services
   - Open-source dependencies preferred

2. **Timeline**
   - MVP completed (current state)
   - Production-ready hardening: 2-3 months
   - User-facing features: 6-12 months

3. **Compliance**
   - Data privacy considerations (GDPR-ready architecture)
   - Audit trail for payments and member data changes
   - Secure storage of personal and medical information

### Known Limitations (TODOs)
- Contact.tenant field currently nullable (migration planned)
- Emergency/medical fields not yet fully migrated to ClubMember
- PaymentHistory content_type validation incomplete
- Cache invalidation strategy needs improvement
- Docker configuration requires production hardening
- No current user context middleware for ClubRelatedManager

## Next Steps

### Immediate Priorities
1. Complete tenant model hardening (make Contact.tenant non-nullable)
2. Implement AdminTenantContextMiddleware access guards
3. Add current user context middleware for staff filtering
4. Enhance cache management with TTL settings and invalidation

### Short-Term Goals
1. Integrate django-unfold for improved admin UI
2. Add RESTful API layer (Django REST Framework)
3. Implement payment processor integration
4. Build reporting and analytics foundation

### Long-Term Vision
1. Self-service member portal
2. Mobile application (iOS/Android)
3. Advanced grading and progression tracking
4. Multi-language support for international martial arts organizations
5. Integration marketplace for third-party tools
