# OneSpirit Django Project Audit (Clean Code, Security, Performance)

Date: 2025-10-01
Scope: Full repository review (settings, middleware, models, managers, services, tests, Dockerfile, pyproject)

## Summary
The codebase demonstrates solid multi-tenant design with context-based filtering, thoughtful model validations, and good use of Django features (choices enums, constraints, indexes). Security and correctness are generally strong. There are several important improvements recommended, primarily around tenant non-null enforcement, cache invalidation/configuration, completion of data model TODOs, and production container/runtime hygiene.

## Architecture and Design
- Multi-tenancy
  - Strengths:
    - ContextVar-based tenant context with TenantAwareManager and OrganizationAwareManager.
    - Tenant detection middleware (subdomain, URL, session) and access-control middleware.
    - Organization-aware patterns for dual filtering.
  - Improvements:
    - Tenant cache invalidation: TenantCacheManager caches model instances without automatic invalidation. Either cache IDs (and fetch fresh instances) or add post_save/post_delete signals to invalidate. Read TTL from settings.
    - Current user context is settable in clubs.models but not wired through middleware. Add middleware to set/clear current user for request-scoped filtering in ClubRelatedManager.
    - Consider optional Postgres RLS in production for defense-in-depth.

- Models and constraints
  - Strengths:
    - Extensive clean() validations and index/constraint coverage.
    - Correct use of TextChoices for Payment enums.
    - Proper use of all_objects to bypass tenant filtering where appropriate.
  - Improvements:
    - Contact.tenant is nullable while there’s a unique (tenant, email) constraint. Multiple NULLs weaken uniqueness and isolation. Make tenant non-nullable via staged migration.
    - Emergency/medical fields duplicated on Contact and ClubMember. Complete the migration by keeping fields only on ClubMember and removing from Contact.
    - PaymentHistory GenericForeignKey: restrict account_content_type to TenantAccount or MemberAccount in clean() to prevent linkage to arbitrary models.
    - full_clean() in model save methods is safe but can be heavy. Confirm this is desired globally; provide bypass for bulk operations if needed.

## Security
- Settings and secrets
  - SECRET_KEY fallback is fine for dev; enforce presence in production (fail fast if missing).
  - ALLOWED_HOSTS via env in prod is correct; dev hosts include wildcard—fine if non-internet accessible.
  - SECURE_BROWSER_XSS_FILTER is legacy/no-op in Django; remove to avoid confusion.

- Middleware and access control
  - Prefer request.user.is_authenticated rather than isinstance(AnonymousUser) for access checks.
  - Admin tenant selection via session is reasonable; CSRF protection applies in admin.

- PII and sensitive data
  - Centralize sensitive emergency/medical fields on ClubMember only and consider field-level encryption for medical_conditions. Ensure strict access control and auditing of read/write operations.

## Performance and Scalability
- Caching
  - Avoid caching full model objects in Redis; cache IDs or small dicts and re-fetch with select_related.
  - Drive cache TTL and max entries from settings (TENANT_SETTINGS) rather than hard-coded values.

- Query patterns
  - Good batching of ContentType lookups in services; optionally memoize ct per model per process or request.
  - Indexes are sensible; revisit partial indexes as data grows (is_active, status fields).

- Validation
  - ClubMember membership_number set post-save works with conditional unique constraint; extremely low risk of race issues.

## Clean Code and Maintainability
- Typing and linting
  - Good type hints; move django-stubs and ruff to dev dependencies (not runtime).

- Boundaries and APIs
  - Favor accounts.services as the canonical API; avoid reintroducing monkey-patching patterns.

- Consistency
  - Use is_authenticated consistently.
  - Read TenantCacheManager TTL and other parameters from settings.

## DevOps and Docker
- Dockerfile
  - Current approach installs the project package via uv without a build-system section; this may fail or be unnecessary. Options:
    - Add [build-system] to pyproject and install with -e .
    - Or install dependencies explicitly (uv pip install --system <deps>) without packaging the app.
  - Remove dev tools (vim, git, curl) for production images; use multi-stage builds, non-root user, HEALTHCHECK, and a proper CMD (e.g., gunicorn onespirit_project.wsgi:application).
  - RotatingFileHandler writes to BASE_DIR/logs; ensure the directory exists or prefer console logging for containers.

- pyproject
  - base.py imports dotenv; add python-dotenv to dependencies or remove load_dotenv if not using .env files in production.
  - Move ruff and django-stubs to dev dependency group. Consider pinning compatible major versions.

## Testing and CI
- Tests are substantial—great. Add:
  - Middleware tests for tenant detection (subdomain/path/session) and access-control denials.
  - Tests for TenantCacheManager invalidation and cache behavior.
  - Tests for PaymentHistory content type restriction.
- Add CI for ruff, type-check, and unit tests.

## Small fixes and tidy-ups
- people.models.Contact.get_absolute_url references people:contact_detail but no URL exists; add route or remove method.
- accounts.apps ready() is a stub—either document intended signals or remove the method to avoid confusion.
- Add .env.example to match .gitignore expectations.
- Reduce info-level logs for tenant detection to debug in public paths.

## Prioritized Recommendations
1) Security and correctness
- Make Contact.tenant non-nullable via staged migration and enforce unique (tenant, email).
- Restrict PaymentHistory.account_content_type to allowed models in clean().
- Use request.user.is_authenticated in middleware.
- Centralize emergency/medical fields on ClubMember and remove from Contact (data migration).

2) Multi-tenancy hardening
- Add signals to invalidate TenantCacheManager or cache IDs only; read TTL from settings.
- Add middleware to set/clear current user context for ClubRelatedManager.

3) DevOps improvements
- Fix Dockerfile dependency installation; add production CMD; remove dev tools; add non-root user and HEALTHCHECK.
- Add python-dotenv to dependencies or remove load_dotenv usage in prod.

4) Cleanup and consistency
- Move ruff and django-stubs to dev group; remove SECURE_BROWSER_XSS_FILTER; read tenant cache config from settings.
- Address missing people:contact_detail route or remove get_absolute_url.

5) Performance polish
- Memoize ContentType lookups and review indexes/partial indexes as data grows.

## Suggested Next Steps
- Create Jira items under an “Audit Remediation” epic for:
  - Contact.tenant non-null migration and uniqueness enforcement.
  - Emergency/medical fields migration completion.
  - Tenant cache strategy: invalidation signals or ID-only caching + settings-driven TTL.
  - Middleware for current user context.
  - Dockerfile and pyproject hardening.
  - PaymentHistory content type restriction and tests.
- Create a Confluence page summarizing this audit and linking to Jira.
- Open a PR with initial changes: middleware user context, TenantCacheManager reading settings + signals, request.user.is_authenticated, prod settings cleanup, Dockerfile + pyproject fixes.

