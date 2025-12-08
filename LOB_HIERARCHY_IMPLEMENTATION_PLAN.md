# LOB Hierarchy Implementation Plan

## Overview

Implement a configurable organizational hierarchy (Line of Business) to associate users with business units, enabling model statistics grouped by LOB through the Model Owner relationship. The system uses a self-referential database structure that supports CSV import of flat denormalized hierarchy data with dynamic depth detection.

## Requirements Summary

1. **Hierarchical Structure**: Self-referential LOB model supporting unlimited depth (SBU → LOB1 → LOB2 → ...)
2. **CSV Import**: Accept flat denormalized CSV files with columns like `SBU, LOB1, LOB2, ...` and dynamically detect depth. Use EXAMPLE_LOBS.json to test the imports and seed initial data.
3. **User Association**: Required LOB assignment for all users (non-nullable foreign key)
4. **Admin Management**: Full CRUD operations via Admin UI with tree visualization
5. **Deactivation Rules**: Prevent deactivation of LOB nodes that have active children or assigned users

## Architecture

### Database Schema

#### New Table: `lob_units`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `lob_id` | Integer | PK, auto-increment | Unique identifier |
| `parent_id` | Integer | FK → `lob_units.lob_id`, nullable | Self-reference for hierarchy |
| `code` | String(50) | NOT NULL | Short code (e.g., "RETAIL", "PB") |
| `name` | String(255) | NOT NULL | Display name (e.g., "Retail Banking", "Private Banking") |
| `level` | Integer | NOT NULL | Hierarchy depth: 1=SBU, 2=LOB1, 3=LOB2, etc. |
| `sort_order` | Integer | NOT NULL, default=0 | Display ordering within parent |
| `is_active` | Boolean | NOT NULL, default=True | Soft delete / deactivation flag |
| `created_at` | DateTime | NOT NULL, default=now | Audit timestamp |
| `updated_at` | DateTime | NOT NULL, auto-update | Audit timestamp |

**Indexes:**
- Unique constraint on `(parent_id, code)` to prevent duplicate codes within same parent
- Index on `parent_id` for efficient tree traversal
- Index on `is_active` for filtered queries

**Relationships:**
- `parent`: Many-to-One self-reference to parent LOBUnit
- `children`: One-to-Many self-reference to child LOBUnits
- `users`: One-to-Many relationship to User model

#### Modified Table: `users`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `lob_id` | Integer | FK → `lob_units.lob_id`, NOT NULL | User's assigned LOB |

**New Relationship:**
- `lob`: Many-to-One relationship to LOBUnit

### Synthetic Test Data

Use EXAMPLE_LOBS.json to test the imports and seed initial data.

**Existing User Assignment**: All existing users will be assigned to a leaf-level LOB node distributed across the hierarchy to simulate realistic data. 

### API Design

#### New Router: `/api/lob-units`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/lob-units` | Any authenticated | List all LOB units (flat with parent info) |
| `GET` | `/lob-units/tree` | Any authenticated | Get hierarchical tree structure |
| `GET` | `/lob-units/{lob_id}` | Any authenticated | Get single LOB unit with ancestors/descendants |
| `POST` | `/lob-units` | Admin only | Create new LOB unit |
| `PUT` | `/lob-units/{lob_id}` | Admin only | Update LOB unit |
| `DELETE` | `/lob-units/{lob_id}` | Admin only | Deactivate LOB unit (soft delete) |
| `POST` | `/lob-units/import-csv` | Admin only | Import hierarchy from CSV file |
| `GET` | `/lob-units/export-csv` | Admin only | Export current hierarchy as flat CSV |

#### CSV Import Endpoint Details

**Request**: `multipart/form-data` with CSV file upload

**CSV Format** (flat denormalized, dynamic column detection):
Use EXAMPLE_LOBS.json for details on future import data.

**Processing Logic**:
1. Parse CSV headers to detect hierarchy columns (SBU, LOB1, LOB2, ..., LOBN)
2. Validate all required columns present (at minimum SBU)
3. Build unique node set per level, tracking parent relationships
4. Upsert nodes level-by-level (SBU first, then LOB1, etc.)
5. Match existing nodes by `(parent_id, code)` to avoid duplicates
6. Return import summary: created, updated, skipped counts

**Error Handling**:
- Return 400 with validation errors if CSV malformed
- Return 422 with row-level errors for data issues
- Support dry-run mode (`?dry_run=true`) to preview changes

#### Updated User Endpoints

Modify existing user CRUD in `/api/auth/users`:

- `POST /auth/users`: Require `lob_id` in request body
- `PUT /auth/users/{user_id}`: Allow `lob_id` update
- `GET /auth/users`: Include `lob` object in response with full path
- `GET /auth/users/{user_id}`: Include `lob` object with hierarchy details

### Pydantic Schemas

#### LOB Schemas (new file: `schemas/lob.py`)

```
LOBUnitBase:
  - code: str (max 50 chars)
  - name: str (max 255 chars)
  - sort_order: int = 0

LOBUnitCreate(LOBUnitBase):
  - parent_id: Optional[int]

LOBUnitUpdate:
  - code: Optional[str]
  - name: Optional[str]
  - sort_order: Optional[int]
  - is_active: Optional[bool]

LOBUnitResponse(LOBUnitBase):
  - lob_id: int
  - parent_id: Optional[int]
  - level: int
  - is_active: bool
  - full_path: str  # Computed: "Retail > Private Banking > Wealth Management"
  - created_at: datetime
  - updated_at: datetime

LOBUnitTreeNode(LOBUnitResponse):
  - children: List[LOBUnitTreeNode]

LOBImportResult:
  - created_count: int
  - updated_count: int
  - skipped_count: int
  - errors: List[str]
```

#### User Schema Updates

Extend existing schemas in `schemas/user.py`:

```
UserCreate:
  - Add: lob_id: int (required)

UserUpdate:
  - Add: lob_id: Optional[int]

UserResponse:
  - Add: lob_id: int
  - Add: lob: LOBUnitResponse (nested object with full_path)
```

### Service Layer

#### New Service: `services/lob_service.py`

**Functions:**

1. `get_lob_tree(db, include_inactive=False)` → List[LOBUnitTreeNode]
   - Build nested tree structure from flat query
   - Use recursive CTE or application-level tree building

2. `get_lob_full_path(db, lob_id)` → str
   - Return formatted path: "SBU > LOB1 > LOB2"
   - Cache results for performance

3. `can_deactivate_lob(db, lob_id)` → Tuple[bool, str]
   - Check for active children
   - Check for assigned users
   - Return (allowed, reason_if_blocked)

4. `import_lob_csv(db, file_content, dry_run=False)` → LOBImportResult
   - Parse CSV with dynamic column detection
   - Validate hierarchy consistency
   - Upsert records maintaining referential integrity

5. `export_lob_csv(db)` → str
   - Generate flat denormalized CSV from tree
   - Include all levels as separate columns

### Frontend Components

#### New Tab in TaxonomyPage.tsx: "Organizations"

**Location**: Add as new tab alongside existing taxonomy management tabs

**Components**:

1. **LOB Tree View**
   - Expandable/collapsible tree visualization
   - Show code, name, user count per node
   - Visual indicator for inactive nodes
   - Drag-drop reordering (optional, phase 2)

2. **LOB Node Form** (modal or side panel)
   - Fields: Code, Name, Parent (dropdown/tree selector), Sort Order
   - Create new node under selected parent
   - Edit existing node

3. **CSV Import Panel**
   - File upload dropzone
   - Preview parsed data before import
   - Show column detection results
   - Dry-run validation with error display
   - Confirm/cancel import actions

4. **Action Buttons**
   - Add Root LOB (SBU level)
   - Add Child LOB (under selected)
   - Edit Selected
   - Deactivate Selected (with confirmation if users assigned)
   - Import CSV
   - Export CSV

#### UsersPage.tsx Updates

1. **User Form Changes**
   - Add required LOB dropdown field
   - Use hierarchical selector showing full path
   - Group options by SBU for easier navigation

2. **Users Table Changes**
   - Add "LOB" column showing full path or abbreviated
   - Add LOB filter dropdown in table header
   - Support filtering by any level (SBU, LOB1, etc.)

### Migration Strategy

#### Alembic Migration Steps

1. **Create `lob_units` table** with all columns and constraints

2. **Seed synthetic hierarchy data** using the structure defined above

3. **Add `lob_id` column to `users`** as nullable initially

4. **Distribute existing users across LOB nodes**
   - Query all leaf-level LOB nodes (nodes with no children)
   - Assign users round-robin to distribute evenly
   - Log assignments for audit purposes

5. **Alter `users.lob_id` to NOT NULL** after all users assigned

6. **Create indexes** for performance

#### Rollback Strategy

- `lob_id` column removal from users
- Drop `lob_units` table
- No data loss for existing user records (column simply removed)

### Validation Rules

1. **LOB Code**: Required, max 50 chars, alphanumeric + underscore only, unique within parent
2. **LOB Name**: Required, max 255 chars
3. **Parent Assignment**: Cannot create circular references
4. **Deactivation**: Blocked if active children exist or users assigned
5. **User LOB**: Required field, must reference active LOB unit
6. **CSV Import**: Validate hierarchy consistency before committing

### Security Considerations

1. **Authorization**: Only Admin role can create/update/delete LOB units or import CSV
2. **Audit Logging**: Log all LOB CRUD operations and CSV imports
3. **Input Validation**: Sanitize CSV content, validate file size limits
4. **Rate Limiting**: Consider limiting CSV import frequency

### Testing Requirements

#### Unit Tests

1. LOBUnit model CRUD operations
2. Tree building and path computation
3. CSV parsing with various column configurations
4. Deactivation rule enforcement
5. User LOB assignment validation

#### Integration Tests

1. Full CSV import workflow
2. User creation with LOB assignment
3. LOB hierarchy API endpoints
4. Deactivation cascading behavior

#### UI Tests

1. Tree view expand/collapse
2. CSV upload and preview
3. User form LOB selector
4. Filter functionality

### File Changes Summary

#### New Files

| File | Purpose |
|------|---------|
| `api/app/models/lob.py` | LOBUnit SQLAlchemy model |
| `api/app/schemas/lob.py` | Pydantic schemas for LOB |
| `api/app/routers/lob.py` | API router for LOB endpoints |
| `api/app/services/lob_service.py` | Business logic for LOB operations |
| `api/alembic/versions/xxxx_add_lob_hierarchy.py` | Database migration |
| `api/tests/test_lob.py` | Unit and integration tests |
| `web/src/components/LOBTreeView.tsx` | Tree visualization component |
| `web/src/components/LOBImportPanel.tsx` | CSV import UI component |

#### Modified Files

| File | Changes |
|------|---------|
| `api/app/models/__init__.py` | Import and export LOBUnit |
| `api/app/models/user.py` | Add lob_id FK and relationship |
| `api/app/schemas/user.py` | Add lob_id to create/update, lob to response |
| `api/app/routers/auth.py` | Update user CRUD for LOB field |
| `api/app/main.py` | Register LOB router |
| `web/src/pages/TaxonomyPage.tsx` | Add Organizations tab |
| `web/src/pages/UsersPage.tsx` | Add LOB field to form and table |
| `web/src/lib/api.ts` | Add LOB API client functions |

### Implementation Order

1. **Phase 1: Backend Model & Migration**
   - Create LOBUnit model
   - Create Alembic migration with seed data
   - Update User model with lob_id
   - Run migration to populate hierarchy and assign users

2. **Phase 2: Backend API**
   - Create LOB schemas
   - Implement LOB service layer
   - Create LOB router with all endpoints
   - Update user schemas and endpoints
   - Register router in main.py

3. **Phase 3: Frontend - Admin UI**
   - Add LOB API client functions
   - Create LOB tree view component
   - Create CSV import panel component
   - Add Organizations tab to TaxonomyPage

4. **Phase 4: Frontend - User Management**
   - Update UsersPage form with LOB selector
   - Add LOB column to users table
   - Implement LOB filtering

5. **Phase 5: Testing & Validation**
   - Write unit tests for all new code
   - Write integration tests for workflows
   - Manual testing of UI components
   - Performance testing with large hierarchies

### Success Criteria

1. Admin can create, edit, and deactivate LOB hierarchy nodes via UI
2. Admin can import LOB hierarchy from CSV with dynamic depth detection
3. All users have required LOB assignment
4. User forms enforce LOB selection
5. Users table displays LOB information with filtering
6. Deactivation is blocked when children or users exist
7. All existing users are assigned to synthetic LOB nodes after migration
8. API returns proper error messages for validation failures
