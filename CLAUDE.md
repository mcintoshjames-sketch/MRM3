# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Model Risk Management (MRM) inventory system with FastAPI backend, React/TypeScript frontend, and PostgreSQL database.

## Keeping ARCHITECTURE.md Up To Date

Whenever you make non-trivial changes to the structure, data model, or main flows:

1. Open `ARCHITECTURE.md` in the repo.
2. Ask Claude:

   > Please re-sync `ARCHITECTURE.md` with the current codebase.
   > - First, read `CLAUDE.md` and treat it as the source of truth for intent.
   > - Then scan the repo for any changes to modules, data models, routes, and integrations.
   > - Update only the sections that are now stale, keeping wording concise and high-signal.
   > - Call out any places where the code and `CLAUDE.md` appear to disagree.

3. Review Claude's edits and commit `CLAUDE.md` + `ARCHITECTURE.md` together.

## Common Commands

### Start All Services
```bash
docker compose up --build
```
- Backend: http://localhost:8001
- Frontend: http://localhost:5174
- API docs: http://localhost:8001/docs

### Deployment to Production

**Preferred Method**: Use the `deploy.sh` script which combines git operations with production deployment:

```bash
# Full deployment flow (interactive - prompts for confirmation)
./scripts/deploy.sh

# Deploy with specific commit message
./scripts/deploy.sh "fix: resolve validation workflow bug"

# Check repository status only (no changes made)
./scripts/deploy.sh --status

# Deploy to production server only (skip git operations)
./scripts/deploy.sh --prod-only
```

**What the script does:**
1. Shows repository status (uncommitted changes, ahead/behind remote)
2. Stages all changes and commits with auto-generated or custom message
3. Pushes to origin/main
4. SSHs to production server via Cloudflare Access
5. Pulls latest code and rebuilds Docker containers
6. Verifies service health (frontend + API)

**Production Details:**
- **Server**: `mrm-admin@ssh.mrmqmistest.org` (via Cloudflare Access)
- **App Directory**: `/opt/mrm`
- **Docker Compose**: `docker-compose.prod.yml`
- **Public URL**: https://mrmqmistest.org

See [REMOTE_ACCESS.md](REMOTE_ACCESS.md) for SSH configuration and troubleshooting.

### Shell Command Patterns (for Claude Code)
**IMPORTANT**: When testing API endpoints with curl and auth tokens, avoid shell variable assignment with command substitution - it causes parse errors. Instead:

```bash
# DON'T DO THIS - causes "parse error near `('"
TOKEN=$(curl -s ... | grep -o ...)
curl -s "..." -H "Authorization: Bearer $TOKEN"

# DO THIS INSTEAD - save to file, then use inline
curl -s -X POST "http://localhost:8001/auth/login" -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' > /tmp/login.json

# Then either read the token manually or use it directly in subsequent commands
curl -s "http://localhost:8001/endpoint" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

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

**IMPORTANT**: Do NOT run `pnpm build` to check for TypeScript errors - it often freezes. Instead, use `npx tsc --noEmit` for type checking, which is faster and more reliable.

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
**Note**: Frontend tests are currently not running in the development environment. Use TypeScript type checking (`npx tsc --noEmit`) to verify frontend code compiles correctly.

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
- **Model Features**:
  - Development type: In-House or Third-Party
  - Owner (required), Developer (optional) - user lookups
  - Vendor (required for third-party)
  - Risk Tier (configurable via taxonomy; Validation Type is on ValidationRequest, not Model)
  - Model users (many-to-many relationship)

### Frontend (web/)
- **Stack**: React 18 + TypeScript + Vite + TailwindCSS
- **Routing**: react-router-dom v6
- **HTTP Client**: Axios with centralized client in `src/api/client.ts`
- **State**: React Context for auth (`src/contexts/AuthContext.tsx`)
- **Layout**: Side panel navigation with Dashboard (Admin), Models, Validations, Vendors, Users, Taxonomy, Audit Logs
- **Date Formatting**: All dates must display in ISO format (YYYY-MM-DD) like "2025-08-28", not locale format like "9/3/2025"
  - Use `value.split('T')[0]` to extract date from ISO datetime strings
  - Never use `toLocaleDateString()` - this creates inconsistent locale-based formatting
  - Apply to all UI displays, CSV exports, and data tables
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
  - `/validation-workflow` - Validation request management with workflow states
  - `/validation-workflow/:id` - Detailed validation request view
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
- **Searchable Dropdown Pattern**:
  - **IMPORTANT**: All dropdowns that select Models or Users MUST be searchable, not plain `<select>` elements
  - These lists can grow very large and become unusable without search
  - Implementation pattern:
    ```typescript
    // State variables
    const [searchQuery, setSearchQuery] = useState('');
    const [showDropdown, setShowDropdown] = useState(false);

    // In JSX - use text input with filtered dropdown
    <div className="relative">
        <input
            type="text"
            placeholder="Type to search..."
            value={searchQuery}
            onChange={(e) => {
                setSearchQuery(e.target.value);
                setShowDropdown(true);
            }}
            onFocus={() => setShowDropdown(true)}
            className="mt-1 input-field"
        />
        {showDropdown && searchQuery.length > 0 && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                {items
                    .filter((item) => item.name.toLowerCase().includes(searchQuery.toLowerCase()))
                    .slice(0, 50)  // Limit results for performance
                    .map((item) => (
                        <div
                            key={item.id}
                            className="px-4 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                            onClick={() => {
                                setSelectedId(item.id);
                                setSearchQuery(item.name);
                                setShowDropdown(false);
                            }}
                        >
                            {item.name}
                        </div>
                    ))}
                {filteredItems.length === 0 && (
                    <div className="px-4 py-2 text-sm text-gray-500">No results found</div>
                )}
            </div>
        )}
        {selectedId && (
            <p className="mt-1 text-sm text-green-600">✓ Selected: {selectedName}</p>
        )}
    </div>
    ```
  - Features to include:
    - Search input with placeholder text
    - Dropdown appears on focus and when typing
    - Filter results case-insensitively
    - Limit results (e.g., 50) for performance
    - Show "No results found" message when empty
    - Display confirmation of selection with green checkmark
    - Clear search state in form reset functions
  - Reference implementation: `AttestationCyclesPage.tsx` Model Override Settings section

### Reports System

The application includes a centralized Reports section for generating and exporting regulatory and operational reports.

**Architecture**:
- **Reports Gallery**: `/reports` - Central hub displaying all available canned reports
- **Report Detail Pages**: Individual pages for each report (e.g., `/reports/regional-compliance`)
- **Navigation**: "Reports" link in main navigation sidebar

**Current Reports**:
- **Regional Deployment & Compliance Report** (`/reports/regional-compliance`)
  - Shows models deployed by region with validation and approval status
  - Filters: Region, deployment status
  - Export: CSV with region-specific approval data
  - API: `GET /regional-compliance-report/`

**Extension Pattern - Adding New Reports**:

To add a new canned report to the Reports section, follow these three steps:

**Step 1**: Add report metadata to `web/src/pages/ReportsPage.tsx`:
```typescript
const availableReports: Report[] = [
    // ... existing reports ...
    {
        id: 'validation-aging',                    // Unique identifier
        name: 'Validation Aging Report',           // Display name
        description: 'Track validation requests by status and SLA compliance.',
        path: '/reports/validation-aging',         // Route path
        icon: '⏱️',                                 // Display icon (emoji)
        category: 'Validation'                      // Category for grouping
    },
];
```

**Step 2**: Create the report detail page component:
```typescript
// web/src/pages/ValidationAgingReportPage.tsx
import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import client from '../api/client';

const ValidationAgingReportPage: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [reportData, setReportData] = useState(null);

    const fetchReport = async () => {
        const response = await client.get('/validation-aging-report/');
        setReportData(response.data);
    };

    return (
        <Layout>
            {/* Report filters, table, and export functionality */}
        </Layout>
    );
};

export default ValidationAgingReportPage;
```

**Step 3**: Add route in `web/src/App.tsx`:
```typescript
import ValidationAgingReportPage from './pages/ValidationAgingReportPage';

// ... in Routes component:
<Route
    path="/reports/validation-aging"
    element={user ? <ValidationAgingReportPage /> : <Navigate to="/login" />}
/>
```

**Report Page Standard Features**:
- Filters for data (region, date range, status, etc.)
- Summary statistics cards (total records, key metrics)
- Data table with sortable columns
- CSV export button
- "Refresh Report" button
- Responsive layout with proper loading states

**Reference Implementation**: See [RegionalComplianceReportPage.tsx](web/src/pages/RegionalComplianceReportPage.tsx) for a complete example.

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
  - `taxonomy_type` column: 'standard' or 'bucket' to distinguish taxonomy types
- **Taxonomy Types**:
  - **Standard**: Simple list of values (e.g., Risk Tier, Validation Type)
  - **Bucket**: Range-based values with min_days/max_days for contiguous day ranges (e.g., Past Due Level)
- **Pre-seeded Taxonomies**:
  - **Model Risk Tier**: Tier 1 (High), Tier 2 (Medium), Tier 3 (Low)
  - **Validation Type**: Initial, Comprehensive, Targeted Review
  - **Validation Outcome**: Pass, Pass with Findings, Fail
  - **Validation Scope**: Full Scope, Conceptual Soundness, Data Quality, Implementation Testing, Performance Monitoring
  - **Past Due Level** (bucket): Current (≤0), Minimal (1-365), Moderate (366-730), Significant (731-1095), Critical (1096-1825), Obsolete (≥1826)
- **Bucket Taxonomy Features**:
  - Buckets must be contiguous with no gaps or overlaps
  - First bucket must have min_days=null (unbounded lower)
  - Last bucket must have max_days=null (unbounded upper)
  - Validation prevents invalid configurations (gaps, overlaps, boundary errors)
  - Admin-only editing for bucket taxonomies
  - Used in Overdue Revalidation Report to classify models by days overdue
- **Features**:
  - System taxonomies (is_system=True) cannot be deleted
  - Values can be deactivated without deletion
  - Sort order controls dropdown display order
  - Models can optionally reference taxonomy values
- **Frontend**:
  - Taxonomy management page with master-detail layout
  - Add new taxonomies and values
  - Edit code, label, description, sort order, active status
  - Bucket taxonomies show range column (e.g., "≤ 0 days", "1 - 365 days")
  - Admin-only editing for bucket taxonomy ranges
  - Models edit form includes taxonomy dropdowns

### Model Validation Workflow Management
- **Purpose**: Full lifecycle management of model validation requests with proper workflow states
- **Core Architecture**:
  - **ValidationRequest**: Main workflow entity tracking validation lifecycle
  - **ValidationStatusHistory**: Complete audit trail of status changes
  - **ValidationAssignment**: Validator assignments with independence checks
  - **ValidationOutcome**: Final outcome - ONLY created after work is complete
  - **ValidationApproval**: Multi-stakeholder approval workflow
  - **ValidationPolicy**: Admin-configurable validation scheduling per risk tier with `frequency_months` (re-validation interval), `grace_period_months` (overdue threshold after due date), and `model_change_lead_time_days` (completion lead time)

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
  - **Automatic Intake → Planning transition**: When a validator is assigned to a validation request in INTAKE status, the system automatically transitions it to PLANNING status
  - Validator independence enforced (cannot be model owner/developer)
  - Outcome entry only allowed when status >= Review
  - Request locked from editing once in Pending Approval or Approved status
  - Complete audit trail for compliance

- **Taxonomy Values**:
  - **Validation Priority**: Urgent, Standard
  - **Validation Request Status**: All 8 workflow states
  - **Overall Rating**: Fit for Purpose, Not Fit for Purpose

- **API Endpoints** (prefix: `/validation-workflow`):
  - `POST /requests/` - Create new validation request (NO outcome required!)
  - `GET /requests/` - List requests with filters
  - `GET /requests/{id}` - Get detailed request with all relationships
  - `PATCH /requests/{id}` - Update request details
  - `PATCH /requests/{id}/status` - Update status with workflow validation
  - `POST /requests/{id}/assignments` - Assign validators with independence check
  - `POST /requests/{id}/outcome` - Create outcome (only when work complete)
  - `POST /requests/{id}/approvals` - Add approval requirements
  - `PATCH /approvals/{id}` - Submit approval/rejection
  - `GET /dashboard/aging` - Aging report by status
  - `GET /dashboard/workload` - Validator workload report

- **Frontend Routes**:
  - `/validation-workflow` - Main validation request list with workflow management
  - `/validation-workflow/:id` - Detailed validation request view with full workflow UI

- **Future Enhancements** (separate phases):
  - Detailed Findings and Issues tracking module
  - Validation request detail page with full workflow UI
  - Kanban board view for status management
  - Email notifications for status changes
  - Bulk operations for periodic validation scheduling

### Model Relationships & Dependencies
- **Purpose**: Track model-to-model relationships (hierarchy and data dependencies) with DAG enforcement
- **Core Architecture**:
  - **ModelHierarchy**: Parent-child relationships (e.g., Enterprise Model → Sub-Models)
  - **ModelFeedDependency**: Feeder-consumer data flow relationships with cycle detection
  - **ModelDependencyMetadata**: Extended metadata (not yet exposed in UI)

- **Relationship Types**:
  - **Hierarchy**: SUB_MODEL (configurable via taxonomy)
  - **Dependencies**: INPUT_DATA, SCORE, PARAMETER, GOVERNANCE_SIGNAL, OTHER

- **Business Rules**:
  - Self-reference prevention (cannot link model to itself)
  - **Single-parent constraint**: A model can have at most ONE parent model (enforced via unique constraint)
    - Ensures clear ownership, accountability, and governance hierarchy
    - Prevents ambiguous approval chains and conflicting validation requirements
    - If a model is shared across contexts, use dependencies (data flow), not hierarchy
  - Cycle detection for dependencies (maintains DAG constraint)
  - Unique constraints on relationships
  - Date validation (end_date >= effective_date)
  - Admin-only write access for modifications

- **API Endpoints**:
  - Hierarchy: `/models/{id}/hierarchy/parents`, `/models/{id}/hierarchy/children`
  - Dependencies: `/models/{id}/dependencies/inbound`, `/models/{id}/dependencies/outbound`
  - CRUD: `POST /models/{id}/hierarchy`, `PATCH /hierarchy/{id}`, `DELETE /hierarchy/{id}`
  - CRUD: `POST /models/{id}/dependencies`, `PATCH /dependencies/{id}`, `DELETE /dependencies/{id}`

- **Frontend Components**:
  - `ModelHierarchySection` - Display and manage parent/child relationships (Phases 3-4 complete)
  - `ModelDependenciesSection` - Display and manage inbound/outbound dependencies (Phases 3-4 complete)
  - `ModelHierarchyModal` - Create/edit hierarchy relationships with validation
  - `ModelDependencyModal` - Create/edit dependencies with cycle detection feedback

- **Model Details Page Integration**:
  - "Hierarchy" tab shows parent models and sub-models with CRUD operations (Admin only)
  - "Dependencies" tab shows inbound (feeders) and outbound (consumers) with CRUD operations (Admin only)

- **Phase Status** (see MODEL_RELATIONSHIP_PLAN.md for details):
  - ✅ Phase 1: Database schema and taxonomies
  - ✅ Phase 2: API endpoints with comprehensive tests (52 tests)
  - ✅ Phase 3: UI read-only views
  - ✅ Phase 4: UI write operations (modals, validation, admin controls)
  - ⏳ Phase 5: Reporting (CSV exports, filters)
  - ⏳ Phase 6: Lineage preview visualization
  - ⏳ Phase 7: Advanced features (metadata fields, version-level links, map visualization)

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

### Screenshots

**Save to NAS** (for documentation/testing):
```bash
node scripts/screenshot.js <url> [filename] [width] [height]
node scripts/screenshot.js http://localhost:5174 login.png
node scripts/screenshot.js http://localhost:5174/dashboard --full-page
```
- Output: `/Volumes/Content/MCPScreenShots` (fallback: `./screenshots/`)

**MCP Puppeteer** (inline display):
- `mcp__puppeteer__puppeteer_navigate`, `_fill`, `_click`, `_screenshot`
- Screenshots display in conversation; Claude can read/understand them
- **IMPORTANT**: Always run in headless mode. When navigating, use:
  ```typescript
  mcp__puppeteer__puppeteer_navigate({
    url: "http://localhost:5174",
    launchOptions: { headless: true }
  })
  ```
- This prevents browser windows from opening on the user's desktop

### Time Utilities (Backend)

**IMPORTANT**: Never use `datetime.utcnow()` - it is deprecated in Python 3.12+.

The application uses a central time utility at `api/app/core/time.py` that provides the `utc_now()` function. This function returns a **naive datetime** (no timezone info) to maintain compatibility with existing database columns using `TIMESTAMP WITHOUT TIME ZONE`.

**Always use `utc_now()` instead of `datetime.utcnow()` for:**
- SQLAlchemy column defaults: `default=utc_now`
- SQLAlchemy column updates: `onupdate=utc_now`
- Direct datetime calls in code: `utc_now()` instead of `datetime.utcnow()`

**Example usage:**
```python
from app.core.time import utc_now

# In SQLAlchemy models
class MyModel(Base):
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

# In API code
from app.core.time import utc_now
current_time = utc_now()
```

**Why naive datetime?**
The database columns use `TIMESTAMP WITHOUT TIME ZONE`. Using timezone-aware datetimes would cause "can't compare offset-naive and offset-aware datetimes" errors. The `utc_now()` function uses the modern `datetime.now(timezone.utc).replace(tzinfo=None)` pattern to get UTC time without the deprecation warning while remaining compatible with existing data.
