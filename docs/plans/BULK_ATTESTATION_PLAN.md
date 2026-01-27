# Bulk Attestation Implementation Plan

## Executive Summary

This plan describes a refactoring of the attestation process to allow respondents to view their complete list of models and respond once, rather than clicking through each model individually. The approach accommodates model-by-model exceptions through exclusion from the bulk attestation, with excluded models reverting to the existing model-specific form.

**Key Insight:** Attestation questions are fundamentally **owner-level declarations**, not model-level. Questions like "I attest that the models I am responsible for are in compliance..." apply to all models an owner manages. The current model-by-model approach creates unnecessary friction.

**Outcome:** An owner with 30 models completes **1 form** instead of **30 forms**.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Design Decisions](#2-design-decisions)
3. [User Experience](#3-user-experience)
4. [Technical Design](#4-technical-design)
5. [API Specification](#5-api-specification)
6. [Frontend Implementation](#6-frontend-implementation)
7. [Edge Cases & Business Rules](#7-edge-cases--business-rules)
8. [Migration & Rollout Plan](#8-migration--rollout-plan)
9. [Acceptance Criteria](#9-acceptance-criteria)

---

## 1. Problem Statement

### Current Experience

1. Owner navigates to "My Attestations" page → sees a table listing each model separately
2. For each model, clicks "Submit" → navigates to individual attestation form
3. Answers the same 10 questions for each model
4. Submits → repeats for every model

### Pain Point

An owner with 30 models must click through **30 separate forms**, answering the same compliance questions 30 times. This is tedious and creates friction for quarterly attestations.

### Root Cause

The attestation questions are fundamentally **owner-level declarations**, not model-level:

- "I attest that the models I am responsible for are in compliance..."
- "I have made Model Validation aware of all the models..."
- "I comply with the related Roles and Responsibilities..."

The current model-by-model approach is artificial and doesn't match the nature of the compliance statements.

---

## 2. Design Decisions

| Decision Area | Choice | Rationale |
|---------------|--------|-----------|
| **Exception Handling** | Excluded models revert to model-specific form | Preserves full flexibility for edge cases without complicating bulk flow |
| **Question Answers** | Owner-level only; no model-specific overrides | If a model needs different answers, exclude it and handle individually |
| **Change Proposals** | Removed from bulk attestation | Use separate Model Changes workflow; keeps bulk form focused |
| **Partial Submissions** | Draft mode supported | Owners can save progress and return later |
| **Delegate Handling** | One bulk form per owner | Clear separation of responsibility; delegates see separate cards per owner |

---

## 3. User Experience

### 3.1 Flow Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ATTESTATION WORKFLOW                               │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────┐
    │  My Attestations │
    │      Page        │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────────────────────────────────────────────────┐
    │  "You have 30 models requiring attestation for Q4 2025"      │
    │                                                              │
    │  [Start Bulk Attestation]                                    │
    │                                                              │
    │  Or attest individually:                                     │
    │  ┌─────────────────────────────────────────────────────────┐ │
    │  │ Model Name          │ Status    │ Action                │ │
    │  │ ALM QRM v2          │ Pending   │ [Submit Individually] │ │
    │  │ Credit Scorecard    │ Pending   │ [Submit Individually] │ │
    │  └─────────────────────────────────────────────────────────┘ │
    └──────────────────────────────────────────────────────────────┘
             │
             │ Click "Start Bulk Attestation"
             ▼
    ┌──────────────────────────────────────────────────────────────┐
    │               BULK ATTESTATION FORM                          │
    │                                                              │
    │  Step 1: Select models to include                            │
    │  ┌─────────────────────────────────────────────────────────┐ │
    │  │ ☑ ALM QRM v2              │ Tier 1 │                    │ │
    │  │ ☑ Credit Scorecard        │ Tier 1 │                    │ │
    │  │ ☐ CECL Loss Model         │ Tier 1 │ ← EXCLUDED         │ │
    │  │ ☑ Market Risk VaR         │ Tier 2 │                    │ │
    │  └─────────────────────────────────────────────────────────┘ │
    │                                                              │
    │  Step 2: Answer attestation questions (for 29 models)        │
    │  ┌─────────────────────────────────────────────────────────┐ │
    │  │ 1. Policy Compliance    ○ Yes  ○ No                     │ │
    │  │ 2. Inventory Awareness  ○ Yes  ○ No                     │ │
    │  └─────────────────────────────────────────────────────────┘ │
    │                                                              │
    │  [Save Draft]                        [Submit 29 Attestations]│
    └──────────────────────────────────────────────────────────────┘
             │                                    │
             │ Excluded model                     │ Bulk submit
             ▼                                    ▼
    ┌─────────────────────┐          ┌─────────────────────────────┐
    │  MODEL-SPECIFIC     │          │  29 AttestationRecords      │
    │  FORM (existing)    │          │  created with SUBMITTED     │
    │                     │          │  status                     │
    │  For: CECL Loss     │          └─────────────────────────────┘
    │  Model              │
    │                     │
    │  [All questions]    │
    │  [Change proposals] │
    │  [Submit]           │
    └─────────────────────┘
```

### 3.2 My Attestations Page (Updated)

```
┌────────────────────────────────────────────────────────────────────────────┐
│  MY ATTESTATIONS                                                           │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │  📋 Q4 2025 ATTESTATION CYCLE                                      │   │
│  │  Due: 2025-12-31 (15 days remaining)                               │   │
│  │                                                                    │   │
│  │  30 models require attestation                                     │   │
│  │  ├─ 28 pending                                                     │   │
│  │  ├─ 1 draft saved                                                  │   │
│  │  └─ 1 excluded (requires individual submission)                    │   │
│  │                                                                    │   │
│  │  [Continue Bulk Attestation]  ← if draft exists                    │   │
│  │  [Start Bulk Attestation]     ← if no draft                        │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  ─────────────────────────────────────────────────────────────────────────  │
│  INDIVIDUAL ATTESTATIONS                                                   │
│  Models excluded from bulk attestation or requiring resubmission:          │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ Model              │ Tier   │ Status              │ Action          │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │ CECL Loss Model    │ Tier 1 │ ⚠️ Excluded         │ [Submit]        │  │
│  │ FX Pricing Model   │ Tier 3 │ 🔴 Rejected         │ [Resubmit]      │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ─────────────────────────────────────────────────────────────────────────  │
│  COMPLETED ATTESTATIONS                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ Model              │ Tier   │ Status              │ Action          │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │ ALM QRM v2         │ Tier 1 │ ✅ Accepted         │ [View]          │  │
│  │ Credit Scorecard   │ Tier 1 │ 🔵 Submitted        │ [View]          │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Bulk Attestation Form (New Page)

```
┌────────────────────────────────────────────────────────────────────────────┐
│  ← Back to My Attestations                                                 │
│                                                                            │
│  BULK ATTESTATION - Q4 2025 Cycle                                          │
│  Due: 2025-12-31 (15 days remaining)                           [Save Draft]│
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  STEP 1: SELECT MODELS                                                     │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Select the models you can fully attest to. Unchecked models will need     │
│  to be attested individually using the model-specific form.                │
│                                                                            │
│  ☑ Select All (30 models)                         [Expand/Collapse List]   │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │    │ Model Name              │ Risk Tier │ Status  │ Last Attested  │  │
│  ├─────────────────────────────────────────────────────────────────────┤  │
│  │ ☑  │ ALM QRM v2              │ Tier 1    │ Active  │ 2024-12-15     │  │
│  │ ☑  │ Credit Risk Scorecard   │ Tier 1    │ Active  │ 2024-12-15     │  │
│  │ ☑  │ Market Risk VaR         │ Tier 2    │ Active  │ 2024-12-15     │  │
│  │ ☐  │ CECL Loss Model         │ Tier 1    │ Active  │ 2024-12-15     │  │
│  │ ☑  │ Liquidity Stress Test   │ Tier 2    │ Active  │ 2024-12-15     │  │
│  │ ☐  │ FX Pricing Model        │ Tier 3    │ Review  │ 2024-06-20     │  │
│  │ ☑  │ Interest Rate Model     │ Tier 2    │ Active  │ 2024-12-15     │  │
│  │    │ ... (23 more)           │           │         │                │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  📊 Summary                                                         │  │
│  │  • 28 models selected for bulk attestation                          │  │
│  │  • 2 models excluded (will require individual attestation)          │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  STEP 2: ATTESTATION QUESTIONS                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│  The following statements apply to ALL 28 selected models.                 │
│  If any statement does not apply to a specific model, please exclude       │
│  that model above and attest to it individually.                           │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  1. POLICY COMPLIANCE *                                             │  │
│  │  ───────────────────────────────────────────────────────────────────│  │
│  │  I attest to the best of my knowledge that the models I am          │  │
│  │  responsible for are in compliance with the Model Risk and          │  │
│  │  Validation Policy.                                                 │  │
│  │                                                                     │  │
│  │  ┌──────────────┐  ┌──────────────┐                                 │  │
│  │  │  ◉ Yes       │  │  ○ No        │                                 │  │
│  │  └──────────────┘  └──────────────┘                                 │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  2. INVENTORY AWARENESS *                                           │  │
│  │  ───────────────────────────────────────────────────────────────────│  │
│  │  I have made Model Validation aware of all the models/procedures    │  │
│  │  that my team owns, develops and/or uses that are subject to        │  │
│  │  validation.                                                        │  │
│  │                                                                     │  │
│  │  ┌──────────────┐  ┌──────────────┐                                 │  │
│  │  │  ◉ Yes       │  │  ○ No        │                                 │  │
│  │  └──────────────┘  └──────────────┘                                 │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ... (remaining questions)                                                 │
│                                                                            │
│  STEP 3: ADDITIONAL COMMENTS (Optional)                                    │
│  ─────────────────────────────────────────────────────────────────────────  │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ─────────────────────────────────────────────────────────────────────────  │
│  ⚠️  2 models excluded from this bulk attestation:                         │
│      • CECL Loss Model - requires individual attestation                   │
│      • FX Pricing Model - requires individual attestation                  │
│                                                                            │
│  By submitting, I confirm that I have reviewed all 28 selected models      │
│  and that the statements above apply to each of them.                      │
│                                                                            │
│                                    [Save Draft]  [Submit 28 Attestations]  │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Technical Design

### 4.1 Database Changes

#### New Table: `attestation_bulk_submissions`

Tracks bulk submission sessions and draft state.

```sql
CREATE TABLE attestation_bulk_submissions (
    bulk_submission_id SERIAL PRIMARY KEY,
    cycle_id INT NOT NULL REFERENCES attestation_cycles(cycle_id),
    user_id INT NOT NULL REFERENCES users(user_id),

    -- Draft state
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',  -- DRAFT, SUBMITTED

    -- Snapshot of selections (for draft persistence)
    selected_model_ids JSONB,      -- [1, 2, 3, 5, ...]
    excluded_model_ids JSONB,      -- [4, 7]
    draft_responses JSONB,         -- [{question_id, answer, comment}, ...]
    draft_comment TEXT,

    -- Submission tracking
    submitted_at TIMESTAMP,
    attestation_count INT,         -- How many records were created

    -- Audit
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(cycle_id, user_id)  -- One bulk submission per user per cycle
);
```

#### Modify Table: `attestation_records`

Add reference to bulk submission for traceability.

```sql
ALTER TABLE attestation_records
ADD COLUMN bulk_submission_id INT REFERENCES attestation_bulk_submissions(bulk_submission_id),
ADD COLUMN is_excluded BOOLEAN DEFAULT FALSE;
```

**Column Descriptions:**

| Column | Purpose |
|--------|---------|
| `bulk_submission_id` | Links to the bulk submission that created this record (NULL for individual submissions) |
| `is_excluded` | TRUE if model was explicitly excluded from bulk attestation; requires individual submission |

#### No Changes Required

- `attestation_responses` - Responses are cloned to each AttestationRecord during bulk submission
- `attestation_cycles` - No changes needed
- `attestation_evidence` - Evidence is per-record, works as-is

### 4.2 SQLAlchemy Models

#### New Model: `AttestationBulkSubmission`

```python
# api/app/models/attestation.py

class AttestationBulkSubmission(Base):
    __tablename__ = "attestation_bulk_submissions"

    bulk_submission_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cycle_id: Mapped[int] = mapped_column(Integer, ForeignKey("attestation_cycles.cycle_id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)

    # Draft state
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")  # DRAFT, SUBMITTED

    # Selections (JSONB)
    selected_model_ids: Mapped[Optional[list]] = mapped_column(JSONB)
    excluded_model_ids: Mapped[Optional[list]] = mapped_column(JSONB)
    draft_responses: Mapped[Optional[list]] = mapped_column(JSONB)
    draft_comment: Mapped[Optional[str]] = mapped_column(Text)

    # Submission tracking
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    attestation_count: Mapped[Optional[int]] = mapped_column(Integer)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    cycle: Mapped["AttestationCycle"] = relationship(back_populates="bulk_submissions")
    user: Mapped["User"] = relationship()
    attestation_records: Mapped[list["AttestationRecord"]] = relationship(back_populates="bulk_submission")

    __table_args__ = (
        UniqueConstraint("cycle_id", "user_id", name="uq_bulk_submission_cycle_user"),
    )
```

#### Modify Model: `AttestationRecord`

```python
# Add to existing AttestationRecord model

class AttestationRecord(Base):
    # ... existing fields ...

    # New fields for bulk attestation
    bulk_submission_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("attestation_bulk_submissions.bulk_submission_id"),
        nullable=True
    )
    is_excluded: Mapped[bool] = mapped_column(Boolean, default=False)

    # New relationship
    bulk_submission: Mapped[Optional["AttestationBulkSubmission"]] = relationship(
        back_populates="attestation_records"
    )
```

---

## 5. API Specification

### 5.1 New Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/attestations/bulk/{cycle_id}` | Get bulk attestation state for current user | Owner, Delegate |
| `POST` | `/attestations/bulk/{cycle_id}/draft` | Save draft (selections + partial answers) | Owner, Delegate |
| `POST` | `/attestations/bulk/{cycle_id}/submit` | Submit bulk attestation | Owner, Delegate |
| `DELETE` | `/attestations/bulk/{cycle_id}/draft` | Discard draft | Owner, Delegate |

### 5.2 Request/Response Schemas

#### GET `/attestations/bulk/{cycle_id}`

Returns the bulk attestation state including models, draft data, and questions.

**Response:**

```json
{
  "cycle": {
    "cycle_id": 1,
    "cycle_name": "Q4 2025",
    "submission_due_date": "2025-12-31",
    "status": "OPEN",
    "days_until_due": 15
  },
  "models": [
    {
      "attestation_id": 101,
      "model_id": 1,
      "model_name": "ALM QRM v2",
      "risk_tier_code": "TIER_1",
      "risk_tier_label": "Tier 1 - High Risk",
      "model_status": "Active",
      "last_attested_date": "2024-12-15",
      "attestation_status": "PENDING",
      "is_excluded": false
    },
    {
      "attestation_id": 102,
      "model_id": 4,
      "model_name": "CECL Loss Model",
      "risk_tier_code": "TIER_1",
      "risk_tier_label": "Tier 1 - High Risk",
      "model_status": "Active",
      "last_attested_date": "2024-12-15",
      "attestation_status": "PENDING",
      "is_excluded": true
    }
  ],
  "draft": {
    "exists": true,
    "bulk_submission_id": 5,
    "selected_model_ids": [1, 2, 3, 5, 6],
    "excluded_model_ids": [4, 7],
    "responses": [
      {"question_id": 101, "answer": true, "comment": null},
      {"question_id": 102, "answer": true, "comment": null}
    ],
    "comment": "Draft comment...",
    "last_saved": "2025-12-15T10:30:00Z"
  },
  "questions": [
    {
      "value_id": 101,
      "code": "POLICY_COMPLIANCE",
      "label": "I attest to the best of my knowledge that the models I am responsible for are in compliance with the Model Risk and Validation Policy.",
      "description": "Section reference...",
      "requires_comment_if_no": true,
      "sort_order": 1
    }
  ],
  "summary": {
    "total_models": 30,
    "pending_count": 28,
    "excluded_count": 2,
    "submitted_count": 0,
    "accepted_count": 0,
    "rejected_count": 0
  }
}
```

#### POST `/attestations/bulk/{cycle_id}/draft`

Saves current progress as a draft.

**Request:**

```json
{
  "selected_model_ids": [1, 2, 3, 5, 6],
  "excluded_model_ids": [4, 7],
  "responses": [
    {"question_id": 101, "answer": true, "comment": null},
    {"question_id": 102, "answer": false, "comment": "Explanation..."}
  ],
  "comment": "Work in progress..."
}
```

**Response:**

```json
{
  "success": true,
  "bulk_submission_id": 5,
  "last_saved": "2025-12-15T10:30:00Z",
  "message": "Draft saved successfully"
}
```

#### POST `/attestations/bulk/{cycle_id}/submit`

Submits the bulk attestation, creating AttestationRecords for all selected models.

**Request:**

```json
{
  "selected_model_ids": [1, 2, 3, 5, 6, 8, 9, 10],
  "responses": [
    {"question_id": 101, "answer": true, "comment": null},
    {"question_id": 102, "answer": true, "comment": null},
    {"question_id": 103, "answer": false, "comment": "Explanation here"}
  ],
  "decision_comment": "Optional overall comment"
}
```

**Response:**

```json
{
  "success": true,
  "bulk_submission_id": 5,
  "submitted_count": 28,
  "excluded_count": 2,
  "attestation_ids": [101, 102, 103, 105, 106, ...],
  "message": "Successfully submitted 28 attestations. 2 models require individual attestation."
}
```

**Backend Logic:**

1. Validate all selected models belong to current user and are PENDING
2. Validate all required questions are answered
3. For each selected model:
   - Update AttestationRecord status to SUBMITTED
   - Set `bulk_submission_id`
   - Create AttestationResponse records (clone responses)
   - Set `decision` based on answers (I_ATTEST or I_ATTEST_WITH_UPDATES)
4. For excluded models:
   - Set `is_excluded = true` on AttestationRecord
5. Update BulkSubmission status to SUBMITTED
6. Create audit log entry

#### DELETE `/attestations/bulk/{cycle_id}/draft`

Discards the current draft.

**Response:**

```json
{
  "success": true,
  "message": "Draft discarded"
}
```

---

## 6. Frontend Implementation

### 6.1 New Files

| File | Purpose |
|------|---------|
| `web/src/pages/BulkAttestationPage.tsx` | Main bulk attestation form |
| `web/src/components/BulkModelSelectionTable.tsx` | Model checklist with checkboxes |
| `web/src/hooks/useBulkAttestation.ts` | State management and API calls |

### 6.2 Modified Files

| File | Changes |
|------|---------|
| `web/src/pages/MyAttestationsPage.tsx` | Add bulk attestation CTA, reorganize into sections |
| `web/src/App.tsx` | Add route for `/attestations/bulk/:cycleId` |

### 6.3 State Management Hook

```typescript
// web/src/hooks/useBulkAttestation.ts

interface BulkAttestationState {
  // Data from API
  cycle: CycleInfo | null;
  models: BulkAttestationModel[];
  questions: AttestationQuestion[];

  // Selection state
  selectedModelIds: Set<number>;
  excludedModelIds: Set<number>;

  // Form state
  responses: Map<number, { answer: boolean; comment: string }>;
  decisionComment: string;

  // Draft state
  isDirty: boolean;
  lastSaved: Date | null;
  isSaving: boolean;
  draftExists: boolean;

  // Loading states
  isLoading: boolean;
  isSubmitting: boolean;
  error: string | null;

  // Computed
  selectedCount: number;
  excludedCount: number;
  canSubmit: boolean;
}

interface BulkAttestationActions {
  // Model selection
  toggleModel: (modelId: number) => void;
  selectAll: () => void;
  deselectAll: () => void;
  excludeModel: (modelId: number) => void;
  includeModel: (modelId: number) => void;

  // Form
  setResponse: (questionId: number, answer: boolean, comment?: string) => void;
  setDecisionComment: (comment: string) => void;

  // Persistence
  saveDraft: () => Promise<void>;
  discardDraft: () => Promise<void>;
  submit: () => Promise<SubmitResult>;

  // Lifecycle
  loadData: () => Promise<void>;
}

export function useBulkAttestation(cycleId: number): BulkAttestationState & BulkAttestationActions {
  // Implementation...
}
```

### 6.4 Auto-Save Behavior

The bulk attestation form implements auto-save:

1. **Debounced saves**: Save draft 5 seconds after last change
2. **Save on blur**: Save when user tabs away from page
3. **Save indicator**: Show "Saving..." / "Saved" / "Save failed" status
4. **Conflict detection**: If draft was modified elsewhere, show warning

```typescript
// Auto-save implementation
useEffect(() => {
  if (!isDirty) return;

  const timer = setTimeout(() => {
    saveDraft();
  }, 5000);

  return () => clearTimeout(timer);
}, [isDirty, selectedModelIds, responses, decisionComment]);

// Save on page unload
useEffect(() => {
  const handleBeforeUnload = (e: BeforeUnloadEvent) => {
    if (isDirty) {
      saveDraft();
      e.preventDefault();
      e.returnValue = '';
    }
  };

  window.addEventListener('beforeunload', handleBeforeUnload);
  return () => window.removeEventListener('beforeunload', handleBeforeUnload);
}, [isDirty]);
```

---

## 7. Edge Cases & Business Rules

### 7.1 All Models Excluded

If owner excludes ALL models from bulk attestation:

- Show warning: "You have excluded all models. Please use individual attestation for each model."
- Disable submit button
- Show link back to My Attestations page

### 7.2 Draft Expiration

Drafts persist until:

- **Cycle closes**: Drafts are auto-deleted when cycle status changes to CLOSED
- **User submits**: Draft is converted to submission
- **User discards**: Draft is manually deleted

### 7.3 Concurrent Sessions

If user has bulk form open in multiple tabs:

- Last save wins (optimistic concurrency)
- Show warning on load: "This draft was modified in another session at [time]. Load latest?"
- Option to load latest or continue with current

### 7.4 Partial Completion After Bulk Submit

After bulk submit, if some models were excluded:

- Excluded models remain with `status = PENDING` and `is_excluded = TRUE`
- Shown in "Individual Attestations" section on My Attestations page
- Owner must complete them individually before cycle closes

### 7.5 Resubmission After Rejection

If admin rejects a bulk-submitted attestation:

- Only that specific AttestationRecord is rejected
- Owner sees it in "Individual Attestations" section with "Rejected" status
- Must resubmit using model-specific form (not bulk)
- Rejection reason is displayed

### 7.6 Delegate with Multiple Owners

Per design decision: **One bulk form per owner**.

If delegate has `can_attest=true` for models owned by multiple users:

- My Attestations shows separate bulk attestation cards per owner
- "Bulk Attestation for Owner A's Models (10)"
- "Bulk Attestation for Owner B's Models (5)"
- Each card links to a separate bulk form for that owner's models

### 7.7 Mixed Attestation States

If some models are already submitted/accepted when starting bulk:

- Already submitted models shown as read-only (grayed out, not selectable)
- Only PENDING models can be selected for bulk attestation
- Summary shows breakdown: "15 pending, 10 already submitted, 5 accepted"

### 7.8 Questions with "No" Answers

If owner answers "No" to any question:

- Same validation as individual form: require comment if `requires_comment_if_no`
- Decision is set to `I_ATTEST_WITH_UPDATES` for all selected models
- No change proposal UI (per design decision); owner uses separate workflow

---

## 8. Migration & Rollout Plan

### Phase 1: Database & API (Backend)

**Duration:** 1 week

**Tasks:**

1. Create Alembic migration for `attestation_bulk_submissions` table
2. Create Alembic migration to add columns to `attestation_records`
3. Add `AttestationBulkSubmission` SQLAlchemy model
4. Implement new API endpoints:
   - `GET /attestations/bulk/{cycle_id}`
   - `POST /attestations/bulk/{cycle_id}/draft`
   - `POST /attestations/bulk/{cycle_id}/submit`
   - `DELETE /attestations/bulk/{cycle_id}/draft`
5. Add Pydantic schemas for request/response
6. Write comprehensive backend tests

### Phase 2: Frontend - Bulk Form

**Duration:** 1-2 weeks

**Tasks:**

1. Create `useBulkAttestation` hook
2. Create `BulkModelSelectionTable` component
3. Create `BulkAttestationPage` with:
   - Model selection step
   - Questions form step
   - Summary and submit
4. Implement auto-save functionality
5. Add route in App.tsx

### Phase 3: Frontend - Integration

**Duration:** 1 week

**Tasks:**

1. Update `MyAttestationsPage`:
   - Add bulk attestation CTA card
   - Reorganize into sections (Bulk, Individual, Completed)
   - Handle delegate scenarios
2. Add navigation between pages
3. Handle edge cases (no models, all excluded, etc.)

### Phase 4: Testing & Polish

**Duration:** 1 week

**Tasks:**

1. E2E testing with various scenarios:
   - Happy path: 30 models, select all, submit
   - Exclusions: exclude 5, submit 25
   - Draft: save, close, resume
   - Delegate: attest for multiple owners
2. Performance testing with large model counts (50+)
3. UX polish based on feedback
4. Documentation updates

---

## 9. Acceptance Criteria

### Core Functionality

- [ ] **AC1:** Owner can start bulk attestation from My Attestations page
- [ ] **AC2:** Bulk form shows all pending models for the cycle with checkboxes
- [ ] **AC3:** Owner can select/deselect individual models
- [ ] **AC4:** Owner can use "Select All" / "Deselect All" controls
- [ ] **AC5:** Attestation questions are displayed once (not per model)
- [ ] **AC6:** Submitting creates AttestationRecords for all selected models
- [ ] **AC7:** Excluded models remain PENDING and require individual submission

### Draft Mode

- [ ] **AC8:** Owner can save draft at any point
- [ ] **AC9:** Returning to the page loads saved draft
- [ ] **AC10:** Auto-save triggers after 5 seconds of inactivity
- [ ] **AC11:** Owner can discard draft and start fresh

### Validation

- [ ] **AC12:** Cannot submit with zero models selected
- [ ] **AC13:** All questions must be answered before submission
- [ ] **AC14:** Comments required for "No" answers where specified

### Integration

- [ ] **AC15:** My Attestations page shows bulk CTA when multiple pending models exist
- [ ] **AC16:** Excluded models shown in separate "Individual Attestations" section
- [ ] **AC17:** Rejected attestations require individual resubmission
- [ ] **AC18:** Delegates see separate bulk cards per owner

### Audit & Compliance

- [ ] **AC19:** Bulk submission creates audit log entry
- [ ] **AC20:** Each AttestationRecord links to bulk_submission_id
- [ ] **AC21:** Coverage reports correctly count bulk-submitted attestations

---

## Appendix A: File Locations

### Backend (api/)

```
api/app/models/attestation.py          # Add AttestationBulkSubmission model
api/app/schemas/attestation.py         # Add bulk attestation schemas
api/app/api/attestations.py            # Add bulk attestation endpoints
api/alembic/versions/xxx_add_bulk_attestation.py  # Migration
api/tests/test_bulk_attestation.py     # Unit tests
```

### Frontend (web/)

```
web/src/pages/BulkAttestationPage.tsx           # New: Main bulk form
web/src/pages/MyAttestationsPage.tsx            # Modified: Add bulk CTA
web/src/components/BulkModelSelectionTable.tsx  # New: Model checklist
web/src/hooks/useBulkAttestation.ts             # New: State management
web/src/App.tsx                                 # Modified: Add route
```

---

*Document Version: 1.0*
*Created: 2025-12-03*
*Author: Claude Code (Implementation Planning)*
