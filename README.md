# OneSpirit

Multi-tenant martial arts club membership backend built with Django and django-organizations.

- Data isolation per tenant via context-aware managers and middleware
- Club/association modeling with staff and member roles
- People directory with tenant-scoped contacts and login profiles
- Payment history with enums and strong validation
- Admin experience with tenant selection support


## Repository layout

- apps
  - `accounts/`: tenant model, member accounts, payment history, managers, middleware, services
  - `people/`: contacts and login users (tenant- and organization-aware)
  - `clubs/`: club (extends django-organizations Organization), club staff, club members, affiliations
- project
  - `onespirit_project/settings/`: split settings `base.py`, `dev.py`, `prod.py`
  - `onespirit_project/urls.py`: admin + people URLs


## Quick start (development)

Prereqs: Python 3.13, pip/uv, SQLite (default in dev).

1) Install dependencies
- Using uv (recommended): `pip install uv && uv pip install --system .`
- Or using pip: `pip install -r <generated requirements>` (pyproject defines deps)

2) Environment
- Create a `.env` at repo root (optional in dev). `base.py` loads it using python-dotenv if available.
  - SECRET_KEY=dev-secret

3) Migrate and create a superuser
- `python manage.py migrate`
- `python manage.py createsuperuser`

4) Run the server
- `python manage.py runserver`

Admin: http://127.0.0.1:8000/admin/


## Settings overview

- `onespirit_project/settings/base.py`
  - Apps: `organizations`, `people`, `accounts`, `clubs`
  - Middleware: `TenantContextMiddleware`, `AdminTenantContextMiddleware`, `TenantAccessControlMiddleware`
  - Loads `.env` if present
- `dev.py`
  - DEBUG=True, SQLite, LocMem cache, verbose logging for tenant managers
  - ALLOWED_HOSTS includes localhost and test domains
- `prod.py`
  - DEBUG=False, env-driven Postgres, Redis cache, security flags (HSTS, secure cookies, SSL redirect)
  - ALLOWED_HOSTS from env, STATIC_ROOT configured

Set DJANGO_SETTINGS_MODULE as needed (manage.py defaults to dev):
- Dev: `onespirit_project.settings.dev`
- Prod: `onespirit_project.settings.prod`


## Multi-tenancy: how it works

Tenant detection (accounts.middleware.TenantContextMiddleware):
- Subdomain: `tenant1.example.com` -> tenant slug `tenant1`
- URL path: `/tenant/tenant1/...`
- Admin session: stored as `selected_tenant_id` when chosen in the admin

Access control (TenantAccessControlMiddleware):
- Verifies the authenticated user can access the resolved tenant
- Superusers bypass; regular users must be linked via their `LoginUser` -> `Contact.tenant`

Admin tenant selection (AdminTenantContextMiddleware):
- On `/admin/`, a selected tenant is stored in session and used to set context


## Context-aware managers

Tenant context is thread-local via ContextVar and automatically applied by managers.

- `TenantAwareManager`: filters by `tenant` if present in context
- `MemberAccountManager` (extends TenantAwareManager): helpers like `get_active()`,
  `get_by_status("active|expired|inactive")`, `get_expiring_soon(days=30)`
- `OrganizationAwareManager`: applies both tenant and organization context when present (used by `people.Contact`)
- `ClubRelatedManager`: for through models without a direct tenant FK; filters via `club.tenant` and optionally by current user’s staff assignments when tenant context is set (used by `clubs.ClubStaff` and `clubs.ClubMember`)

Setting context is handled by middleware; in scripts, you can set it manually:

```python
from accounts.managers import set_current_tenant
from accounts.models import TenantAccount

tenant = TenantAccount.objects.get(tenant_slug="tenant1")
set_current_tenant(tenant)
```


## Core data model highlights

Accounts (`accounts.models`)
- `TenantAccount`: top-level customer; slug/domain, subscription metadata, quotas, contacts through `TenantAccountContact`
- `MemberAccount`: one-to-one with `people.Contact`, belongs to a `TenantAccount`, membership dates and type; enforced validation (dates, primary vs member contact alignment)
- `PaymentHistory`: generic relation to TenantAccount or MemberAccount with enums:
  - `PaymentMethod`, `PaymentStatus`, `PaymentType`
  - Validation for positive amounts (except refunds), non-negative processor fee, date sanity

People (`people.models`)
- `Contact`: personal info with tenant and optional organization; tenant/email uniqueness (`UniqueConstraint` on `(tenant, email)`); default manager is `OrganizationAwareManager`
- `LoginUser`: one-to-one with Django `auth.User` and `Contact`; permission flags; helper methods: `can_access_tenant`, organization permission helpers; signals keep `User.is_active/is_staff` aligned

Clubs (`clubs.models`)
- `Club`: extends `organizations.Organization`; belongs to a tenant; contact/address/social fields; uniqueness of name per tenant enforced in `clean()`
- `ClubStaff`: through model linking `LoginUser` to `Club` with roles/permissions; optional link to `organizations.OrganizationUser`; validation ensures consistency
- `ClubMember`: links `MemberAccount` to `Club`; status/dates; post-save membership number generation; emergency/medical fields are centralized here
- `ClubAffiliation`: relationships between clubs with constraints and same-tenant enforcement


## URLs and admin

- Project URLs: `/admin/` and placeholder `people/` app URLs
- Admin registered models:
  - People: `Contact`, `LoginUser`
  - Accounts: multiple admin customizations (index titles, filters)
  - Clubs: `Club`, `ClubStaff`, `ClubMember`, `ClubAffiliation` with rich admin configuration


## Testing

- Run tests: `python manage.py test`
- Tests cover tenant-aware managers, middleware behavior, people model isolation and uniqueness, club operations and organization integration, and account services.


## Docker (note)

A simple Dockerfile is included for development; production hardening still recommended:
- Add a proper CMD (e.g., `gunicorn onespirit_project.wsgi:application`), non-root user, HEALTHCHECK
- Consider multi-stage builds and removing dev tools from the final image


## Security and production notes

- Ensure SECRET_KEY and ALLOWED_HOSTS are set in production; use TLS and the provided security flags in `prod.py`
- Configure Redis (or your cache) via `REDIS_URL` for production caching
- Consider Postgres Row-Level Security as an optional defense-in-depth


## Roadmap / TODOs

Integrate [Undfold](https://github.com/unfoldadmin/django-unfold)

High-priority items from the audits:
- Make `Contact.tenant` non-nullable via staged migration and keep email uniqueness per tenant
- Complete migration of emergency/medical fields out of `people.Contact` (centralize on `clubs.ClubMember`)
- Restrict `PaymentHistory.account_content_type` to allowed models in `clean()` and tests
- Guard `AdminTenantContextMiddleware` to staff/admin only for session-based selection
- Improve `TenantCacheManager`: read TTL from settings and add invalidation signals or cache IDs only
- Add middleware to set/clear current user context for `ClubRelatedManager`
- Docker and pyproject hardening; move dev-only deps to dev group; add python-dotenv or adjust settings

See the audit docs for the full discussion and rationale.


## License

TBD.
