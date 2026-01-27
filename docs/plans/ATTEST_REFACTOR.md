# Attestation Change Proposal → Change Link Refactor

**Date:** 2025-12-03
**Status:** In Progress
**Purpose:** Simplify inventory change integration by reusing existing forms instead of custom modals

---

## Overview

This refactor simplifies the attestation inventory change workflow by:
1. **Removing** the full `AttestationChangeProposal` approval workflow
2. **Adding** a lightweight `AttestationChangeLink` tracking table
3. **Reusing** existing Model Edit, Model Create, and Decommissioning pages

### Benefits
- No duplicate forms or validation logic
- Consistent UX across the application
- Existing suspense queue workflows are reused
- Changes tracked for reporting without data duplication
- Reduced code to maintain

---

## Current State (Before Refactor)

### Database Entity: `AttestationChangeProposal`
```
attestation_change_proposals
├── proposal_id (PK)
├── attestation_id (FK)
├── pending_edit_id (FK, nullable)
├── change_type (ENUM: UPDATE_EXISTING, NEW_MODEL, DECOMMISSION)
├── model_id (FK, nullable)
├── proposed_data (JSON)           ← REMOVE
├── status (ENUM: PENDING/ACCEPTED/REJECTED)  ← REMOVE
├── admin_comment (TEXT)           ← REMOVE
├── decided_by_user_id (FK)        ← REMOVE
├── decided_at (DATETIME)          ← REMOVE
└── created_at (DATETIME)
```

### API Endpoints (Current)
- `POST /attestations/records/{id}/changes` - Create proposal with full data
- `GET /attestations/changes` - List pending proposals
- `POST /attestations/changes/{id}/accept` - Admin accept
- `POST /attestations/changes/{id}/reject` - Admin reject

---

## Target State (After Refactor)

### Database Entity: `AttestationChangeLink`
```
attestation_change_links
├── link_id (PK)
├── attestation_id (FK)
├── change_type (ENUM: MODEL_EDIT, NEW_MODEL, DECOMMISSION)
├── pending_edit_id (FK, nullable)
├── model_id (FK, nullable)
├── decommissioning_request_id (FK, nullable)  ← NEW
└── created_at (DATETIME)
```

### API Endpoints (New)
- `POST /attestations/records/{id}/link-change` - Create lightweight link
- `GET /attestations/records/{id}/linked-changes` - Get linked changes (read-only)

**Removed Endpoints:**
- ~~`POST /attestations/changes/{id}/accept`~~
- ~~`POST /attestations/changes/{id}/reject`~~

---

## Implementation Checklist

### Phase 1: Backend Model & Migration

- [ ] **1.1** Create Alembic migration to:
  - Rename table `attestation_change_proposals` → `attestation_change_links`
  - Rename column `proposal_id` → `link_id`
  - Drop columns: `proposed_data`, `status`, `admin_comment`, `decided_by_user_id`, `decided_at`
  - Add column: `decommissioning_request_id` (FK to decommissioning_requests)
  - Update enum values: `UPDATE_EXISTING` → `MODEL_EDIT`

- [ ] **1.2** Update `api/app/models/attestation.py`:
  - Rename class `AttestationChangeProposal` → `AttestationChangeLink`
  - Remove `AttestationChangeStatus` enum
  - Update `AttestationChangeType` enum values
  - Remove unnecessary columns/relationships

- [ ] **1.3** Update `api/app/models/__init__.py`:
  - Update export name

### Phase 2: Backend Schemas

- [ ] **2.1** Update `api/app/schemas/attestation.py`:
  - Rename `AttestationChangeProposalBase` → `AttestationChangeLinkBase`
  - Rename `AttestationChangeProposalCreate` → `AttestationChangeLinkCreate`
  - Rename `AttestationChangeProposalResponse` → `AttestationChangeLinkResponse`
  - Remove `AttestationChangeProposalDecision` class
  - Remove fields: `proposed_data`, `status`, `admin_comment`, `decided_by_user_id`, `decided_at`
  - Add field: `decommissioning_request_id`

### Phase 3: Backend API Endpoints

- [ ] **3.1** Update `api/app/api/attestations.py`:
  - Rename endpoint `POST /records/{id}/changes` → `POST /records/{id}/link-change`
  - Simplify to just create link record (no proposal data)
  - Remove `POST /changes/{id}/accept` endpoint
  - Remove `POST /changes/{id}/reject` endpoint
  - Update `GET /changes` → `GET /records/{id}/linked-changes` (read-only)
  - Update imports and references

- [ ] **3.2** Update admin dashboard endpoint to show linked changes as read-only

### Phase 4: Frontend Changes

- [ ] **4.1** Update `web/src/pages/AttestationDetailPage.tsx`:
  - Rename interface `ChangeProposal` → `LinkedChange`
  - Remove status/admin_comment/decided_by fields from interface
  - Remove Accept/Reject buttons from UI
  - Add navigation buttons: "Edit Model", "Register New Model", "Initiate Decommission"
  - Implement sessionStorage context for link tracking

- [ ] **4.2** Update linked changes display:
  - Show as read-only list with navigation to existing approval pages
  - Display status from linked entity (ModelPendingEdit or DecommissioningRequest)

- [ ] **4.3** Update any other pages referencing change proposals

### Phase 5: Tests

- [ ] **5.1** Update `api/tests/test_attestations.py`:
  - Rename test classes/functions
  - Remove tests for accept/reject workflow
  - Add tests for link creation
  - Update assertions for new schema

### Phase 6: Documentation

- [ ] **6.1** Update ARCHITECTURE.md if needed
- [ ] **6.2** Update user guide if needed

---

## Migration Strategy

### Pre-Migration Check
Before running migration, verify no pending proposals exist:
```sql
SELECT COUNT(*) FROM attestation_change_proposals WHERE status = 'PENDING';
```
If any exist, they must be resolved (accepted/rejected) before migration.

### Migration SQL (Conceptual)
```sql
-- Rename table
ALTER TABLE attestation_change_proposals RENAME TO attestation_change_links;

-- Rename primary key column
ALTER TABLE attestation_change_links RENAME COLUMN proposal_id TO link_id;

-- Drop unnecessary columns
ALTER TABLE attestation_change_links DROP COLUMN proposed_data;
ALTER TABLE attestation_change_links DROP COLUMN status;
ALTER TABLE attestation_change_links DROP COLUMN admin_comment;
ALTER TABLE attestation_change_links DROP COLUMN decided_by_user_id;
ALTER TABLE attestation_change_links DROP COLUMN decided_at;

-- Add new column
ALTER TABLE attestation_change_links ADD COLUMN decommissioning_request_id INTEGER REFERENCES decommissioning_requests(request_id);

-- Update enum values in change_type column
UPDATE attestation_change_links SET change_type = 'MODEL_EDIT' WHERE change_type = 'UPDATE_EXISTING';
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `api/app/models/attestation.py` | Rename class, remove columns, update enums |
| `api/app/models/__init__.py` | Update export |
| `api/app/schemas/attestation.py` | Rename classes, remove fields |
| `api/app/api/attestations.py` | Update endpoints, remove accept/reject |
| `api/tests/test_attestations.py` | Update tests |
| `api/alembic/versions/xxx_refactor_change_proposals.py` | New migration |
| `web/src/pages/AttestationDetailPage.tsx` | Update interface, remove buttons, add nav |
| `web/src/pages/AdminDashboardPage.tsx` | Update change proposals display |

---

## Rollback Plan

If issues arise:
1. Revert code changes via git
2. Run `alembic downgrade -1` to revert migration
3. Table and columns will be restored to original state

---

*Last Updated: 2025-12-03*
