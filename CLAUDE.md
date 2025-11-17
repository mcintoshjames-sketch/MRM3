# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Model Risk Management (MRM) inventory system with FastAPI backend, React/TypeScript frontend, and PostgreSQL database.

## Common Commands

### Start All Services
```bash
docker compose up --build
```
- Backend: http://localhost:8001
- Frontend: http://localhost:5174
- API docs: http://localhost:8001/docs

### Database Migrations
**IMPORTANT**: Migrations must be run inside the Docker container because the database uses Docker networking (hostname "db"). Running locally will fail with "could not translate host name 'db' to address".

```bash
# Apply migrations (run inside container)
docker compose exec api alembic upgrade head

# Rollback one step
docker compose exec api alembic downgrade -1

# Create new migration (can be done locally or in container)
docker compose exec api alembic revision --autogenerate -m "description"
```

### Frontend Development (in web/ directory)
```bash
pnpm install
pnpm dev          # Development server
pnpm build        # Production build (runs tsc first)
pnpm preview      # Preview production build
```

### Seeding
Database is automatically seeded via `python -m app.seed` when docker-compose starts:
- Default admin: `admin@example.com` / `admin123`
- Sample vendors: Bloomberg, Moody's Analytics, MSCI, S&P Global, FactSet
- Mock Microsoft Entra directory with 8 sample employees (for SSO simulation)
- Taxonomies: Model Risk Tier (3), Validation Type (5), Validation Outcome (3), Validation Scope (5)

### Testing

**Backend (pytest):**
```bash
cd api
python -m pytest                    # Run all tests (94 tests)
python -m pytest tests/test_auth.py # Run specific test file
python -m pytest -x                 # Stop on first failure
python -m pytest --cov=app          # With coverage
```

**Frontend (vitest):**
```bash
cd web
pnpm test                # Watch mode
pnpm test:run            # Single run (25 tests)
pnpm test:coverage       # With coverage
```

**Full Regression Suite (119 tests total):**
```bash
cd api && python -m pytest && cd ../web && pnpm test:run
```

## Regression Testing Workflow

**IMPORTANT**: See [REGRESSION_TESTS.md](REGRESSION_TESTS.md) for the full regression testing plan and current test coverage.

### When Adding Features
1. Run full test suite first: `cd api && python -m pytest && cd ../web && pnpm test:run`
2. Write tests for new functionality (TDD preferred)
3. Implement feature
4. Run regression tests again
5. Update [REGRESSION_TESTS.md](REGRESSION_TESTS.md) with new test coverage

### Test Infrastructure
- **Backend**: pytest with in-memory SQLite, fixtures in `api/tests/conftest.py`
- **Frontend**: vitest + React Testing Library + happy-dom, direct module mocking (no MSW)
  - Mock `AuthContext` for auth state
  - Mock `api/client` for API responses

## Architecture

### Backend (api/)
- **Framework**: FastAPI with Pydantic v2 schemas
- **ORM**: SQLAlchemy 2.x with async-compatible patterns
- **Auth**: JWT tokens via python-jose, passwords hashed with passlib/bcrypt
- **Structure**:
  - `app/api/` - Route handlers (auth.py, models.py, vendors.py, taxonomies.py, audit_logs.py, validations.py)
  - `app/core/` - Config, database setup, security utilities, dependencies
  - `app/models/` - SQLAlchemy ORM models (User, Model, Vendor, EntraUser, Taxonomy, TaxonomyValue, AuditLog, Validation, ValidationPolicy)
  - `app/schemas/` - Pydantic request/response schemas
  - `alembic/` - Database migrations
- **User Roles**: Admin, Validator, User
  - **Admin**: Full access, can configure validation policies, view dashboard
  - **Validator**: Can create/edit validations (independent review)
  - **User**: Basic access to view models and data
- **Key API Endpoints**:
  - `/auth/` - Login, register, get current user, list/update/delete users
  - `/auth/users/{id}` - Get specific user details
  - `/auth/users/{id}/models` - Get models where user is owner or developer
  - `/auth/entra/` - Microsoft Entra directory search and user provisioning
  - `/models/` - CRUD with owner/developer/vendor relationships
  - `/vendors/` - CRUD for third-party model vendors
  - `/taxonomies/` - CRUD for configurable taxonomy values
  - `/audit-logs/` - Search and filter audit logs with pagination
  - `/validations/` - CRUD for model validation records (role-based access)
  - `/validations/policies/` - Admin-only validation policy configuration
  - `/validations/dashboard/overdue` - Models overdue for validation
  - `/validations/dashboard/pass-with-findings` - Validations needing recommendations
- **Model Features**:
  - Development type: In-House or Third-Party
  - Owner (required), Developer (optional) - user lookups
  - Vendor (required for third-party)
  - Risk Tier and Validation Type (configurable via taxonomy)
  - Model users (many-to-many relationship)

### Frontend (web/)
- **Stack**: React 18 + TypeScript + Vite + TailwindCSS
- **Routing**: react-router-dom v6
- **HTTP Client**: Axios with centralized client in `src/api/client.ts`
- **State**: React Context for auth (`src/contexts/AuthContext.tsx`)
- **Layout**: Side panel navigation with Dashboard (Admin), Models, Validations, Vendors, Users, Taxonomy, Audit Logs
- **Standard Table Features**: All table views must include:
  - **CSV Export**: Button to export displayed data as CSV file
  - Implementation: `utils/csvExport.ts` helper or inline generation
  - Filename format: `{entity_name}_{YYYY-MM-DD}.csv`
  - Export current filtered/sorted view (not full dataset)
- **Pages**:
  - `/login` - Authentication
  - `/dashboard` - Admin dashboard (overdue validations, pass-with-findings alerts)
  - `/models` - Model list with CRUD + CSV export
  - `/models/:id` - Model details with edit functionality (includes taxonomy dropdowns)
  - `/validations` - Validation records list with create form (Validator/Admin only)
  - `/vendors` - Vendor management CRUD + CSV export
  - `/vendors/:id` - Vendor details with related models list
  - `/users` - User management CRUD with Entra directory lookup + CSV export
  - `/users/:id` - User details with Models Owned and Models Developed
  - `/taxonomy` - Taxonomy management (add/edit/delete taxonomy values) + CSV export
  - `/audit` - Audit logs with search/filter by entity type, entity ID, action, and user
- **Cross-Reference Navigation Pattern**:
  - Related records should be clickable links, not static text
  - Example: Vendor name in Model details links to `/vendors/{id}`
  - Example: Model names in Vendor details link to `/models/{id}`
  - Example: User names in Users list link to `/users/{id}` showing related models
  - Use React Router `<Link>` with consistent styling: `text-blue-600 hover:text-blue-800 hover:underline`
  - Detail pages should show related records in tables with View/navigation links
  - API should provide endpoints like `/vendors/{id}/models` to fetch related data
  - This pattern improves UX by enabling seamless navigation between related entities

### Taxonomy System
- **Purpose**: Configurable classification values for models
- **Database**:
  - `Taxonomy` - Categories of values (e.g., Model Risk Tier, Validation Type)
  - `TaxonomyValue` - Individual values with code, label, description, sort order, active status
- **Pre-seeded Taxonomies**:
  - **Model Risk Tier**: Tier 1 (High), Tier 2 (Medium), Tier 3 (Low)
  - **Validation Type**: Initial, Annual Review, Comprehensive, Targeted Review, Ongoing Monitoring
  - **Validation Outcome**: Pass, Pass with Findings, Fail
  - **Validation Scope**: Full Scope, Conceptual Soundness, Data Quality, Implementation Testing, Performance Monitoring
- **Features**:
  - System taxonomies (is_system=True) cannot be deleted
  - Values can be deactivated without deletion
  - Sort order controls dropdown display order
  - Models can optionally reference taxonomy values
- **Frontend**:
  - Taxonomy management page with master-detail layout
  - Add new taxonomies and values
  - Edit code, label, description, sort order, active status
  - Models edit form includes taxonomy dropdowns

### Model Validation Management
- **Purpose**: Track independent model validations for regulatory compliance
- **Core Components**:
  - **Validation**: Records of model reviews with date, validator, type, outcome, scope, findings
  - **ValidationPolicy**: Admin-configurable re-validation frequency by risk tier
- **User Roles for Validation**:
  - **Admin/Validator**: Can create, edit, delete validation records
  - **User**: View-only access to validation records
- **Database Models**:
  - `Validation` - validation_id, model_id, validation_date, validator_id, validation_type_id, outcome_id, scope_id, findings_summary, report_reference
  - `ValidationPolicy` - policy_id, risk_tier_id, frequency_months, description
- **Admin Dashboard**:
  - Default landing page for Admin users
  - Shows models overdue for validation (based on policy frequency)
  - Shows validations with "Pass with Findings" needing issue recommendations (placeholder for future Issue Management)
  - Quick action links to validation list and policy configuration
- **Validation Workflow**:
  1. Admin configures validation frequency per risk tier (e.g., Tier 1 = 6 months)
  2. Validator performs model review
  3. Validator records validation with outcome (Pass/Pass with Findings/Fail)
  4. System calculates next due date based on policy
  5. Dashboard alerts for overdue models and findings requiring attention
- **Future Enhancement**: Issue Management for tracking findings and recommendations

### Mock Microsoft Entra Integration
- **Purpose**: Simulates SSO integration with Microsoft Entra ID (Azure AD)
- **Backend**:
  - `EntraUser` model stores mock organizational directory
  - `/auth/entra/users` - Search directory by name, email, department, job title
  - `/auth/entra/provision` - Admin-only endpoint to create app users from directory
- **Frontend**:
  - "Import from Entra" button (Admin only) opens directory search modal
  - Search employees, view details (job title, department, office, phone)
  - Select role and provision as application user
- **Mock Data**: 8 sample employees with realistic titles and departments
- **Production Note**: In production, replace mock data with actual Microsoft Graph API calls

### Database
- PostgreSQL 15 running on port 5433 (mapped from container's 5432)
- Connection string provided via DATABASE_URL environment variable
- Volume-persisted data via `postgres_data` volume
