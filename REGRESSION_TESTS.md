# Regression Testing Plan

This document tracks the regression testing strategy and test coverage for iterative feature development. **Update this document when adding new features or tests.**

## Quick Reference

```bash
# Run all backend tests (129 tests passing)
cd api && python -m pytest

# Run all frontend tests (59 tests passing)
cd web && pnpm test:run

# Run with coverage
cd api && python -m pytest --cov=app --cov-report=term-missing
cd web && pnpm test:coverage
```

## Current Test Coverage

### Backend API Tests (api/tests/) - ✅ FULLY OPERATIONAL

#### Authentication (`test_auth.py`)
- [x] Login with valid credentials returns JWT token
- [x] Login with wrong password returns 401
- [x] Login with non-existent user returns 401
- [x] Login with invalid email format returns 422
- [x] Get current user when authenticated
- [x] Get current user without token returns 403 (FastAPI OAuth2 behavior)
- [x] Get current user with invalid token returns 401
- [x] Register new user successfully
- [x] Register with duplicate email returns 400
- [x] Register with admin role
- [x] Register with invalid email format returns 422

#### Models CRUD (`test_models.py`)
- [x] List models when empty
- [x] List models with data
- [x] List models without auth returns 403 (FastAPI OAuth2 behavior)
- [x] Create model with all fields
- [x] Create model with minimal fields (defaults)
- [x] Create model without auth returns 403 (FastAPI OAuth2 behavior)
- [x] Create model without required field returns 422
- [x] Get specific model by ID
- [x] Get non-existent model returns 404
- [x] Get model without auth returns 403 (FastAPI OAuth2 behavior)
- [x] Update model single field
- [x] Update model multiple fields
- [x] Update non-existent model returns 404
- [x] Update model without auth returns 403 (FastAPI OAuth2 behavior)
- [x] Delete model successfully
- [x] Delete non-existent model returns 404
- [x] Delete model without auth returns 403 (FastAPI OAuth2 behavior)

#### Vendors CRUD (`test_vendors.py`)
- [x] List vendors when empty
- [x] List vendors with data
- [x] List vendors without auth returns 403
- [x] Create vendor with all fields
- [x] Create vendor with minimal fields
- [x] Create vendor with duplicate name returns 400
- [x] Create vendor without auth returns 403
- [x] Create vendor without name returns 422
- [x] Get vendor by ID
- [x] Get non-existent vendor returns 404
- [x] Get vendor without auth returns 403
- [x] Update vendor single field
- [x] Update vendor multiple fields
- [x] Update non-existent vendor returns 404
- [x] Update vendor with duplicate name returns 400
- [x] Update vendor without auth returns 403
- [x] Delete vendor successfully
- [x] Delete non-existent vendor returns 404
- [x] Delete vendor without auth returns 403
- [x] Verify deleted vendor is gone

#### Model Enhancements (`test_model_enhancements.py`)
- [x] Create in-house model
- [x] Create third-party model with vendor
- [x] Create third-party without vendor fails (400)
- [x] Update to third-party without vendor fails
- [x] Update to third-party with vendor succeeds
- [x] Model returns owner details
- [x] Create model with developer
- [x] Create model with invalid owner fails (404)
- [x] Create model with invalid developer fails (404)
- [x] Update model owner
- [x] Update model developer
- [x] Update model with invalid owner fails
- [x] Create model with users (many-to-many)
- [x] Create model with invalid user fails
- [x] Update model users
- [x] Model without users returns empty list
- [x] List models includes users
- [x] Create model with invalid vendor fails (404)
- [x] Update model with invalid vendor fails
- [x] List users endpoint works
- [x] List users without auth returns 403

#### Authorization & Audit Logging (`test_authorization_audit.py`)
- [x] Owner can update own model
- [x] Non-owner cannot update model (403)
- [x] Admin can update any model
- [x] Owner can delete own model
- [x] Non-owner cannot delete model (403)
- [x] Admin can delete any model
- [x] Create model creates audit log with entity details
- [x] Update model creates audit log with old/new values
- [x] Delete model creates audit log with model name
- [x] Update with no changes creates no audit log
- [x] Audit log tracks user_ids modification

#### Audit Logs API (`test_audit_logs.py`)
- [x] List audit logs when empty
- [x] List audit logs with data (ordered by most recent first)
- [x] Filter by entity type
- [x] Filter by entity ID
- [x] Filter by action
- [x] Filter by user ID
- [x] Combined filters (multiple filters at once)
- [x] Pagination limit
- [x] Pagination offset
- [x] Audit log includes user details (full_name, email)
- [x] Audit log changes field returns JSON diff
- [x] Get unique entity types endpoint
- [x] Get unique actions endpoint
- [x] Unauthenticated access returns 403

#### Model Validation Management (`test_validations.py`)
- [x] List validations when empty
- [x] List validations without auth returns 403
- [x] Create validation as Validator role succeeds
- [x] Create validation as Admin role succeeds
- [x] Create validation as regular User role fails (403)
- [x] Create validation with invalid model fails (404)
- [x] Create validation with invalid validator fails (404)
- [x] Create validation with invalid taxonomy fails (404)
- [x] Get validation by ID
- [x] Get non-existent validation returns 404
- [x] Update validation as Validator role succeeds
- [x] Update validation as regular User role fails (403)
- [x] Delete validation as Admin succeeds
- [x] Delete validation as Validator fails (403) - Admin only
- [x] Delete non-existent validation returns 404
- [x] Filter validations by model ID
- [x] Filter validations by outcome ID
- [x] Filter validations by date range
- [x] Pagination with limit and offset
- [x] List validation policies when empty
- [x] Create validation policy as Admin succeeds
- [x] Create validation policy as Validator fails (403)
- [x] Create duplicate policy for same risk tier fails (400)
- [x] Create policy with invalid risk tier fails (404)
- [x] Update validation policy as Admin succeeds
- [x] Update validation policy as Validator fails (403)
- [x] Delete validation policy as Admin succeeds
- [x] Delete non-existent policy returns 404
- [x] Create validation creates audit log
- [x] Update validation creates audit log with changes
- [x] Delete validation creates audit log
- [x] Overdue models endpoint requires Admin role
- [x] Overdue models returns empty when no policies
- [x] Pass-with-findings endpoint requires Admin role
- [x] Pass-with-findings returns correct validations

### Frontend Component Tests (web/src/) - ✅ FULLY OPERATIONAL

**Note**: All tests pass using happy-dom environment with direct module mocking (no MSW).

#### Login Page (`LoginPage.test.tsx`)
- [x] Renders login form with all fields
- [x] Shows default credentials hint
- [x] Allows typing in email/password fields
- [x] Displays error message on failed login
- [x] Clears error on resubmit
- [x] Has required fields
- [x] Email input has correct type
- [x] Password input has correct type

#### Models Page (`ModelsPage.test.tsx`)
- [x] Displays loading state initially
- [x] Renders navigation bar with user info
- [x] Displays models table after loading
- [x] Shows model details in table (includes owner, developer, vendor, users)
- [x] Displays empty state when no models
- [x] Shows Add Model button
- [x] Opens create form when Add Model clicked
- [x] Closes form when Cancel clicked
- [x] Creates new model when form submitted
- [x] Shows vendor field when Third-Party selected
- [x] Shows delete button for each model
- [x] Calls confirm before deleting
- [x] Does not delete when confirm cancelled
- [x] Displays table headers correctly (Name, Type, Owner, Developer, Vendor, Users, Status, Actions)
- [x] Calls logout when button clicked
- [x] Displays owner and developer names in table

#### Admin Dashboard Page (`AdminDashboardPage.test.tsx`)
- [x] Displays loading state initially
- [x] Displays welcome message with user name
- [x] Displays dashboard title
- [x] Displays overdue validations count
- [x] Displays pass with findings count
- [x] Displays quick action links
- [x] Displays overdue models table
- [x] Displays risk tier badges
- [x] Displays owner names in overdue table
- [x] Displays overdue status with days
- [x] Displays create validation links
- [x] Displays pass with findings table
- [x] Displays validation date and validator name
- [x] Displays findings summary
- [x] Displays no recommendations badge
- [x] Displays empty state for no overdue models
- [x] Displays empty state for no pass with findings
- [x] Displays zero counts when no data

#### Validations Page (`ValidationsPage.test.tsx`)
- [x] Displays loading state initially
- [x] Displays page title
- [x] Displays new validation button for Validator role
- [x] Displays validations table
- [x] Displays validation dates
- [x] Displays validator names
- [x] Displays validation types
- [x] Displays outcomes with proper styling
- [x] Displays scopes
- [x] Displays empty state when no validations
- [x] Opens create form when button clicked
- [x] Displays form fields when create form opened
- [x] Closes form when cancel clicked
- [x] Creates new validation when form submitted
- [x] Displays table headers correctly
- [x] Hides create button for regular User role

## Regression Testing Workflow

### Before Adding New Features
1. Run full test suite to ensure baseline passes
2. Document new feature requirements
3. Add test cases for new functionality (TDD approach preferred)

### After Adding New Features
1. Write/update tests for new functionality
2. Run full regression suite
3. Update this document with new test coverage
4. Commit tests alongside feature code

### Before Each PR/Commit
```bash
# Quick validation (full regression suite)
cd api && python -m pytest -x  # Stop on first failure
cd web && pnpm test:run        # Frontend tests
```

## Test Infrastructure

### Backend (pytest)
- **Location**: `api/tests/`
- **Config**: `api/pytest.ini`
- **Fixtures**: `api/tests/conftest.py`
- **Database**: In-memory SQLite for isolation
- **Key fixtures**:
  - `client` - Test HTTP client
  - `db_session` - Fresh database per test
  - `test_user` / `admin_user` - Pre-created users
  - `auth_headers` / `admin_headers` - JWT auth headers
  - `sample_model` - Pre-created model

### Frontend (vitest + React Testing Library)
- **Location**: `web/src/**/*.test.tsx`
- **Config**: `web/vite.config.ts`
- **Setup**: `web/src/test/setup.ts` (localStorage mock)
- **Utils**: `web/src/test/utils.tsx` (custom render with BrowserRouter)
- **Environment**: happy-dom (avoids jsdom localStorage issues)
- **Mocking Strategy**: Direct module mocking with vi.mock() - no MSW
  - Mock AuthContext for auth state
  - Mock api/client for API calls
- **Key patterns**:
  - Mock `../contexts/AuthContext` to control useAuth()
  - Mock `../api/client` to control API responses
  - Use vi.fn() for tracking function calls

## Adding Tests for New Features

### Backend Example
```python
# api/tests/test_new_feature.py
import pytest

class TestNewFeature:
    def test_feature_success(self, client, auth_headers):
        response = client.post("/new-endpoint", headers=auth_headers, json={...})
        assert response.status_code == 200
```

### Frontend Example
```tsx
// web/src/pages/NewPage.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '../test/utils';
import NewPage from './NewPage';

// Mock dependencies at module level
const mockApiGet = vi.fn();
vi.mock('../api/client', () => ({
    default: { get: (...args: any[]) => mockApiGet(...args) }
}));

vi.mock('../contexts/AuthContext', () => ({
    useAuth: () => ({
        user: { user_id: 1, email: 'test@example.com', full_name: 'Test', role: 'user' },
        login: vi.fn(),
        logout: vi.fn(),
        loading: false,
    }),
}));

describe('NewPage', () => {
    beforeEach(() => {
        mockApiGet.mockReset();
    });

    it('renders correctly', async () => {
        mockApiGet.mockResolvedValueOnce({ data: [] });
        render(<NewPage />);
        await waitFor(() => {
            expect(screen.getByText('Expected Text')).toBeInTheDocument();
        });
    });
});
```

## Feature Tracking

| Feature | Backend Tests | Frontend Tests | Date Added |
|---------|--------------|----------------|------------|
| JWT Authentication | ✅ test_auth.py (11 tests) | ✅ LoginPage.test.tsx (9 tests) | Initial |
| Models CRUD | ✅ test_models.py (17 tests) | ✅ ModelsPage.test.tsx (16 tests) | Initial |
| Vendors CRUD | ✅ test_vendors.py (20 tests) | N/A | 2025-11-16 |
| Model Enhancements | ✅ test_model_enhancements.py (21 tests) | ✅ Form + table updated | 2025-11-16 |
| Authorization & Audit | ✅ test_authorization_audit.py (11 tests) | N/A | 2025-11-16 |
| Audit Logs API | ✅ test_audit_logs.py (14 tests) | N/A | 2025-11-16 |
| Model Validation Management | ✅ test_validations.py (35 tests) | ✅ AdminDashboardPage (18) + ValidationsPage (16) | 2025-11-16 |

**Features Added:**
- Development type (In-House / Third-Party)
- Model owner (required, user lookup)
- Model developer (optional, user lookup)
- Model vendor (required for third-party, vendor lookup)
- Model users (many-to-many relationship)
- Authorization (only owner/admin can update/delete models)
- Audit logging (track CREATE, UPDATE, DELETE with user and changes)
- Audit log viewer with search/filter by entity type, entity ID, action, user
- Model Validation Management (validation tracking, policies, role-based access)
- Admin Dashboard (overdue validations, pass-with-findings alerts)
- Validator role (independent review capability)

**Total: 188 tests (129 backend + 59 frontend)**

---

**Remember**: Update this document whenever you add new features or tests!
