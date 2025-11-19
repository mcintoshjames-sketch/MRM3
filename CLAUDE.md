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
  - **Table Sorting**: All tables must be sortable using the `useTableSort` hook
  - Implementation: See "Table Sorting Pattern" below
  - Three-state sorting: ascending → descending → unsorted
  - Support for nested properties (e.g., `owner.full_name`)
  - Visual indicators with SVG icons
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

### Table Sorting Pattern

All table views must implement sorting using the `useTableSort` custom hook located at `web/src/hooks/useTableSort.tsx`.

**Implementation Steps**:

1. **Import the hook**:
```typescript
import { useTableSort } from '../hooks/useTableSort';
```

2. **Use the hook in your component**:
```typescript
// For a simple table with string initial sort
const { sortedData, requestSort, getSortIcon } = useTableSort<Model>(models, 'model_name');

// For tables that should default to descending order (e.g., dates)
const { sortedData, requestSort, getSortIcon } = useTableSort<Validation>(validations, 'validation_date', 'desc');
```

3. **Update table headers** to be clickable with sort icons:
```typescript
<th
    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
    onClick={() => requestSort('column_name')}
>
    <div className="flex items-center gap-2">
        Column Name
        {getSortIcon('column_name')}
    </div>
</th>
```

4. **Replace data.map() with sortedData.map()** in the table body:
```typescript
<tbody className="bg-white divide-y divide-gray-200">
    {sortedData.length === 0 ? (
        <tr>
            <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                No data available.
            </td>
        </tr>
    ) : (
        sortedData.map((item) => (
            <tr key={item.id}>
                {/* table cells */}
            </tr>
        ))
    )}
</tbody>
```

**Features of useTableSort**:
- **Generic type support**: Works with any data type using TypeScript generics
- **Nested property access**: Supports sorting by nested properties like `owner.full_name` or `vendor.name`
- **Three-state sorting**: Clicking a column cycles through: ascending → descending → unsorted
- **Null handling**: Properly handles null/undefined values (pushes to end)
- **Type detection**: Automatically detects and handles strings, numbers, and dates
- **Visual indicators**: SVG icons show current sort state (up arrow, down arrow, or unsorted)
- **Performance**: Uses React's useMemo for efficient re-rendering

**Columns to Sort**:
- Include sorting for all data columns that users might want to order
- Exclude sorting for action columns or columns with complex UI elements
- Common sortable columns: IDs, names, dates, statuses, email addresses

**Examples**:
- **Simple property**: `requestSort('model_name')`, `requestSort('email')`
- **Nested property**: `requestSort('owner.full_name')`, `requestSort('vendor.name')`
- **Dates**: `requestSort('created_at')`, `requestSort('validation_date')`

**Reference Implementations**:
- [ModelsPage.tsx](web/src/pages/ModelsPage.tsx) - Sorting with nested properties (owner.full_name, developer.full_name)
- [ValidationsPage.tsx](web/src/pages/ValidationsPage.tsx) - Date-based default sort (descending)
- [VendorsPage.tsx](web/src/pages/VendorsPage.tsx) - Simple property sorting
- [UsersPage.tsx](web/src/pages/UsersPage.tsx) - Multi-column sorting example

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

### Model Validation Workflow Management
- **Purpose**: Full lifecycle management of model validation requests with proper workflow states
- **Core Architecture**:
  - **ValidationRequest**: Main workflow entity tracking validation lifecycle
  - **ValidationStatusHistory**: Complete audit trail of status changes
  - **ValidationAssignment**: Validator assignments with independence checks
  - **ValidationWorkComponent**: Track individual work areas (conceptual soundness, data quality, etc.)
  - **ValidationOutcome**: Final outcome - ONLY created after work is complete
  - **ValidationApproval**: Multi-stakeholder approval workflow
  - **ValidationPolicy**: Admin-configurable re-validation frequency by risk tier

- **Workflow States**:
  1. **Intake** - Initial request submission
  2. **Planning** - Scoping and resource allocation
  3. **In Progress** - Active validation work
  4. **Review** - Internal QA and compilation
  5. **Pending Approval** - Awaiting stakeholder sign-offs
  6. **Approved** - Validation complete with all approvals
  7. **On Hold** - Temporarily paused (with reason tracking)
  8. **Cancelled** - Terminated before completion (with justification)

- **Business Rules**:
  - Status transitions enforce valid state machine (cannot skip stages)
  - Validator independence enforced (cannot be model owner/developer)
  - Outcome entry only allowed when all work components are completed AND status >= Review
  - Request locked from editing once in Pending Approval or Approved status
  - Complete audit trail for compliance

- **New Taxonomy Values**:
  - **Validation Priority**: Critical, High, Medium, Low
  - **Validation Request Status**: All 8 workflow states
  - **Work Component Type**: Conceptual Soundness, Data Quality, Implementation Testing, Performance Testing, Documentation Review
  - **Work Component Status**: Not Started, In Progress, Completed
  - **Overall Rating**: Fit for Purpose, Fit with Conditions, Not Fit for Purpose

- **API Endpoints** (prefix: `/validation-workflow`):
  - `POST /requests/` - Create new validation request (NO outcome required!)
  - `GET /requests/` - List requests with filters
  - `GET /requests/{id}` - Get detailed request with all relationships
  - `PATCH /requests/{id}` - Update request details
  - `PATCH /requests/{id}/status` - Update status with workflow validation
  - `POST /requests/{id}/assignments` - Assign validators with independence check
  - `PATCH /components/{id}` - Update work component status/notes
  - `POST /requests/{id}/outcome` - Create outcome (only when work complete)
  - `POST /requests/{id}/approvals` - Add approval requirements
  - `PATCH /approvals/{id}` - Submit approval/rejection
  - `GET /dashboard/aging` - Aging report by status
  - `GET /dashboard/workload` - Validator workload report

- **Frontend Routes**:
  - `/validation-workflow` - Main validation request list with workflow management
  - Navigation updated to use new workflow page

- **Legacy Support**:
  - Old `/validations` endpoints still available (tagged as legacy)
  - Old validation model and schemas retained for backwards compatibility
  - Old frontend page accessible at `/validations` route

- **Future Enhancements** (separate phases):
  - Detailed Findings and Issues tracking module
  - Validation request detail page with full workflow UI
  - Kanban board view for status management
  - Email notifications for status changes
  - Bulk operations for periodic validation scheduling

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
