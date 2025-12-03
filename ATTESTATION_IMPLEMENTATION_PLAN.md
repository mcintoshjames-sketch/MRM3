# Model Risk Attestations — MVP Implementation Plan

## Executive Summary

This plan describes a greenfield MVP for **Model Risk Attestations** that enables model owners/delegates to complete in-app attestations, proposes inventory changes through an existing suspense queue, and provides dashboards/reports for quarterly governance oversight.

**Key Architectural Principle:** This design maximizes reuse of existing infrastructure (suspense queue, delegates, audit logging, scheduling patterns, risk tiers, regions) and introduces only the new entities required for attestation-specific functionality.

---

## Table of Contents

1. [High-Level Components and Data Entities](#1-high-level-components-and-data-entities)
2. [Scheduling and Frequency Application](#2-scheduling-and-frequency-application)
3. [Attestation and Inventory Update Flows](#3-attestation-and-inventory-update-flows)
4. [Dashboard and Report Definitions](#4-dashboard-and-report-definitions)
5. [Role-Based Access and Audit Approach](#5-role-based-access-and-audit-approach)
6. [MVP Phasing and Acceptance Criteria](#6-mvp-phasing-and-acceptance-criteria)
7. [Assumptions and Risks](#7-assumptions-and-risks)
8. [Appendix A: API Endpoints Summary](#appendix-a-api-endpoints-summary)
9. [Appendix B: Database Migration Order](#appendix-b-database-migration-order)
10. [Appendix C: Attestation Questions (from Policy)](#appendix-c-attestation-questions-from-policy)

---

## Existing Infrastructure Reuse Summary

| Existing System | How It's Reused |
|-----------------|-----------------|
| **ModelPendingEdit** | UPDATE_EXISTING changes link to existing suspense queue via `pending_edit_id` |
| **ModelDelegate** | Extended with new `can_attest` permission for attestation-specific delegation |
| **AuditLog** | All actions logged via existing `create_audit_log()` pattern |
| **Risk Tiers** | CoverageTarget links to existing TIER_1-4 taxonomy (for coverage targets only, NOT frequency) |
| **MonitoringCycle** | AttestationCycle follows same status flow pattern |
| **Dashboard Widgets** | New widgets follow existing border-left feed item pattern |
| **Report Pages** | New reports follow existing hub + detail page pattern |
| **Region System** | Regional overrides use existing Region entity |
| **RLS Pattern** | Permission checks use existing `can_modify_model()` pattern |
| **Taxonomy System** | Attestation questions stored as configurable taxonomy values |

---

## 1. High-Level Components and Data Entities

### 1.1 New Database Entities

#### **AttestationCycle** (follows MonitoringCycle pattern)

Represents a scheduled attestation period for governance reporting.

| Column | Type | Description |
|--------|------|-------------|
| `cycle_id` | INT PK | Primary key |
| `cycle_name` | VARCHAR(100) | e.g., "Q4 2025 Attestation Cycle" |
| `period_start_date` | DATE | Start of attestation period |
| `period_end_date` | DATE | End of attestation period |
| `submission_due_date` | DATE | Deadline for owner submissions |
| `status` | ENUM | PENDING, OPEN, UNDER_REVIEW, CLOSED |
| `opened_at` | DATETIME | When cycle was opened for submissions |
| `opened_by_user_id` | INT FK | Admin who opened cycle |
| `closed_at` | DATETIME | When cycle was closed |
| `closed_by_user_id` | INT FK | Admin who closed cycle |
| `notes` | TEXT | Admin notes |
| `created_at`, `updated_at` | DATETIME | Timestamps |

**Status Flow:** `PENDING → OPEN → UNDER_REVIEW → CLOSED`

**Key Behavior:**
- Cycles are created and opened **manually** by Admin
- **Multiple cycles CAN be OPEN simultaneously** (e.g., annual and quarterly cycles overlap)
- **No grace period** - past-due immediately when due_date passes
- Cycle close may be blocked if blocking coverage targets are not met (see CoverageTarget)

---

#### **AttestationQuestion** (Configurable via Taxonomy)

Attestation questions are stored in the existing taxonomy system, allowing Admin to edit, add, or deactivate questions without code changes.

| Column | Type | Description |
|--------|------|-------------|
| `value_id` | INT PK | From TaxonomyValue |
| `taxonomy_id` | INT FK | FK to "Attestation Questions" taxonomy |
| `code` | VARCHAR(50) | Unique question code (e.g., "POLICY_COMPLIANCE") |
| `label` | VARCHAR(500) | Full question text |
| `description` | TEXT | Help text / additional context |
| `frequency_scope` | ENUM | ANNUAL, QUARTERLY, BOTH |
| `requires_comment_if_no` | BOOLEAN | If true, comment required when answered "No" |
| `sort_order` | INT | Display order in form |
| `is_active` | BOOLEAN | Soft disable |

**New Taxonomy:** "Attestation Questions" (is_system=true)

**Seeded Questions (from policy):**

| Code | Question Text | Frequency | Comment Required |
|------|---------------|-----------|------------------|
| `POLICY_COMPLIANCE` | I attest to the best of my knowledge that the models that I am responsible for are in compliance with the Model Risk and Validation Policy. | BOTH | Yes (if No) |
| `INVENTORY_AWARENESS` | I have made Model Validation aware of all the models/procedures that my team owns, develops and/or uses that are subject to validation. | BOTH | Yes (if No) |
| `NO_MATERIAL_CHANGES` | I have made Model Validation aware that there are no material changes to those models since last time they were validated, and therefore no material model change should be implemented before Model Validation approval. | BOTH | Yes (if No) |
| `PURPOSE_DOCUMENTED` | I am responsible to identify, understand and document the purpose of the models and ensure that the modeling choices are documented (Section 6.1). | ANNUAL | No |
| `MONITORING_ISSUES` | I have made Model Validation aware of the models with deteriorating performance or issues that triggered the monitoring thresholds, and hence the applicable remediation plan (Section 6.4). | BOTH | Yes (if No) |
| `ESCALATION_COMMITMENT` | I will bring to the attention of Model Validation and other stakeholders, any model risk issues that have significant impact on P&L, economic capital, regulatory capital or models that pose material level of model risk (Section 6.4.3). | ANNUAL | No |
| `ROLES_COMPLIANCE` | I comply with the related Roles and Responsibilities for my team within the Policy (Section 8.0). | ANNUAL | No |
| `EXCEPTIONS_REPORTED` | I have made Model Validation aware of any additional comments and/or any exceptions to the Policy. | BOTH | Yes (if No) |
| `LIMITATIONS_NOTIFIED` | I will notify model users of critical model limitations to support appropriate and informed model usage. | BOTH | No |
| `RESTRICTIONS_IMPLEMENTED` | I confirm any restrictions on model use have been implemented. | BOTH | Yes (if No) |

See [Appendix C](#appendix-c-attestation-questions-from-policy) for full question text.

---

#### **AttestationRecord** (core attestation entity)

One record per model per cycle, representing the owner/delegate's attestation.

| Column | Type | Description |
|--------|------|-------------|
| `attestation_id` | INT PK | Primary key |
| `cycle_id` | INT FK | Which cycle this belongs to |
| `model_id` | INT FK | Model being attested |
| `attesting_user_id` | INT FK | Owner or delegate who attested |
| `attested_at` | DATETIME NULL | When attestation was submitted |
| `due_date` | DATE | Calculated due date for this model |
| `status` | ENUM | PENDING, SUBMITTED, ADMIN_REVIEW, ACCEPTED, REJECTED |
| `decision` | ENUM NULL | I_ATTEST, I_ATTEST_WITH_UPDATES, OTHER |
| `decision_comment` | TEXT NULL | Required if decision != I_ATTEST |
| `reviewed_by_user_id` | INT FK NULL | Admin who reviewed |
| `reviewed_at` | DATETIME NULL | Review timestamp |
| `review_comment` | TEXT NULL | Admin review notes |
| `created_at`, `updated_at` | DATETIME | Timestamps |

**Relationships:**
- Many-to-one with `AttestationCycle`
- Many-to-one with `Model`
- Many-to-one with `User` (attesting_user)
- One-to-many with `AttestationResponse` (answers to questions)
- One-to-many with `AttestationEvidence` (URL attachments - optional)
- One-to-many with `AttestationChangeProposal` (linked inventory updates)

---

#### **AttestationResponse** (answers to configurable questions)

Stores individual question responses for each attestation.

| Column | Type | Description |
|--------|------|-------------|
| `response_id` | INT PK | Primary key |
| `attestation_id` | INT FK | Parent attestation |
| `question_id` | INT FK | FK to TaxonomyValue (attestation question) |
| `answer` | BOOLEAN | True = confirmed/yes, False = no |
| `comment` | TEXT NULL | Required if answer=false and question.requires_comment_if_no |
| `created_at` | DATETIME | Timestamp |

---

#### **AttestationEvidence** (URL attachments only - OPTIONAL)

Stores evidence URLs attached to attestations. **Evidence is entirely optional.**

| Column | Type | Description |
|--------|------|-------------|
| `evidence_id` | INT PK | Primary key |
| `attestation_id` | INT FK | Parent attestation |
| `evidence_type` | ENUM | MONITORING_REPORT, VALIDATION_REPORT, POLICY_DOC, EXCEPTION_DOC, OTHER |
| `url` | VARCHAR(2000) | Evidence URL (validated as URL format) |
| `description` | VARCHAR(500) | Description of evidence |
| `added_by_user_id` | INT FK | Who added |
| `added_at` | DATETIME | When added |

**Validation:** URL format validation only (must start with `http://` or `https://`). No file uploads. No evidence is required.

---

#### **AttestationSchedulingRule** (Admin-configurable rules engine)

Defines when attestations are required for which models/owners. **Risk tier does NOT affect frequency.**

| Column | Type | Description |
|--------|------|-------------|
| `rule_id` | INT PK | Primary key |
| `rule_name` | VARCHAR(100) | Human-readable name |
| `rule_type` | ENUM | GLOBAL_DEFAULT, OWNER_THRESHOLD, MODEL_OVERRIDE, REGIONAL_OVERRIDE |
| `frequency` | ENUM | ANNUAL, QUARTERLY |
| `priority` | INT | Higher priority rules override lower (100=highest) |
| `is_active` | BOOLEAN | Soft disable |
| `owner_model_count_min` | INT NULL | Threshold for owner model count rule (default: 30) |
| `owner_high_fluctuation_flag` | BOOLEAN NULL | High fluctuation owner flag |
| `model_id` | INT FK NULL | Specific model override |
| `region_id` | INT FK NULL | Regional override |
| `effective_date` | DATE | When rule becomes active |
| `end_date` | DATE NULL | When rule expires (NULL = indefinite) |
| `created_by_user_id`, `updated_by_user_id` | INT FK | Audit |
| `created_at`, `updated_at` | DATETIME | Timestamps |

**Note:** No `risk_tier_id` column. Risk tier affects only coverage targets, NOT attestation frequency.

**Rule Evaluation Logic:**
1. Start with GLOBAL_DEFAULT (Annual for all)
2. Apply OWNER_THRESHOLD (Quarterly if owner.model_count >= 30 OR owner.high_fluctuation_flag = true)
3. Apply REGIONAL_OVERRIDE (if model deployed to region with stricter rule)
4. Apply MODEL_OVERRIDE (specific model frequency - highest priority)

---

#### **AttestationChangeProposal** (links attestation to suspense queue)

Links attestation-driven inventory changes to existing ModelPendingEdit.

| Column | Type | Description |
|--------|------|-------------|
| `proposal_id` | INT PK | Primary key |
| `attestation_id` | INT FK | Parent attestation |
| `pending_edit_id` | INT FK NULL | Link to ModelPendingEdit (for existing model changes) |
| `change_type` | ENUM | UPDATE_EXISTING, NEW_MODEL, DECOMMISSION |
| `model_id` | INT FK NULL | Model being changed (NULL if NEW_MODEL) |
| `proposed_data` | JSON | Full proposed changes (for new models or decommissions) |
| `status` | ENUM | PENDING, ACCEPTED, REJECTED |
| `admin_comment` | TEXT NULL | Admin decision rationale |
| `decided_by_user_id` | INT FK NULL | Admin who decided |
| `decided_at` | DATETIME NULL | Decision timestamp |
| `created_at` | DATETIME | Timestamp |

**Integration with Existing Suspense Queue:**
- For **UPDATE_EXISTING**: Creates a `ModelPendingEdit` record using existing pattern; `pending_edit_id` links to it
- For **NEW_MODEL**: `proposed_data` contains full model creation payload; Admin approval creates the model
- For **DECOMMISSION**: `proposed_data` contains decommission rationale; Admin approval triggers decommissioning workflow

---

#### **CoverageTarget** (configurable per risk tier - GLOBAL)

Admin-configurable coverage targets by inherent risk tier. Targets are **global** (not cycle-specific).

| Column | Type | Description |
|--------|------|-------------|
| `target_id` | INT PK | Primary key |
| `risk_tier_id` | INT FK | Link to taxonomy value (TIER_1, TIER_2, etc.) |
| `target_percentage` | DECIMAL(5,2) | Target % (e.g., 100.00, 95.00) |
| `is_blocking` | BOOLEAN | If true, cycle cannot close until target is met |
| `effective_date` | DATE | When this target becomes active |
| `end_date` | DATE NULL | When this target expires |
| `created_by_user_id` | INT FK | Audit |
| `created_at`, `updated_at` | DATETIME | Timestamps |

**Default Values (seeded):**

| Risk Tier | Target | Blocking |
|-----------|--------|----------|
| TIER_1 (High) | 100% | Yes |
| TIER_2 (Medium) | 100% | Yes |
| TIER_3 (Low) | 95% | No |
| TIER_4 (Very Low) | 95% | No |

**Cycle Close Behavior:**
- When Admin attempts to close a cycle, system checks all coverage targets
- If any `is_blocking=true` target is not met, cycle close is **blocked** with error message
- If `is_blocking=false` targets are not met, cycle can still close (warning only)

---

#### **ModelDelegate Extension** (modify existing)

Add new permission column to existing `model_delegates` table:

| Column | Type | Description |
|--------|------|-------------|
| `can_attest` | BOOLEAN | Can submit attestations on behalf of owner (default: false) |

**Behavior:**
- Delegates with `can_attest=true` can submit attestations for the model **without owner notification**
- This is separate from `can_submit_changes` (which controls model edits)
- Owner or Admin can grant `can_attest` permission

---

#### **User Extension** (modify existing)

Add new column to existing `users` table:

| Column | Type | Description |
|--------|------|-------------|
| `high_fluctuation_flag` | BOOLEAN | Manual toggle set by Admin; triggers quarterly attestations (default: false) |

---

### 1.2 Entity Relationship Diagram (Textual)

```
AttestationCycle (1) ──────< (M) AttestationRecord
                                    │
                                    ├──< (M) AttestationResponse ──> TaxonomyValue (Question)
                                    │
                                    ├──< (M) AttestationEvidence (optional)
                                    │
                                    └──< (M) AttestationChangeProposal
                                              │
                                              └──> (1) ModelPendingEdit (EXISTING)

AttestationSchedulingRule ──> Region (EXISTING, optional)
                          ──> Model (EXISTING, optional)

CoverageTarget ──> TaxonomyValue/RiskTier (EXISTING)

AttestationRecord ──> Model (EXISTING)
                  ──> User (EXISTING, attesting_user)
                  ──> User (EXISTING, reviewed_by)

Taxonomy ("Attestation Questions") ──< TaxonomyValue (questions)
```

---

## 2. Scheduling and Frequency Application

### 2.1 Rule Resolution Algorithm

When determining attestation frequency for a model, the system evaluates rules in priority order. **Risk tier does NOT affect frequency.**

```python
def resolve_attestation_frequency(model_id: int, owner_id: int, db: Session) -> Frequency:
    """
    Returns the effective frequency for a model based on all applicable rules.
    Higher priority rules override lower priority rules.

    NOTE: Risk tier does NOT affect frequency - only coverage targets.
    """
    model = get_model(model_id)
    owner = get_user(owner_id)

    # Get all active rules, ordered by priority DESC
    rules = db.query(AttestationSchedulingRule).filter(
        AttestationSchedulingRule.is_active == True,
        AttestationSchedulingRule.effective_date <= today(),
        or_(
            AttestationSchedulingRule.end_date == None,
            AttestationSchedulingRule.end_date >= today()
        )
    ).order_by(AttestationSchedulingRule.priority.desc()).all()

    effective_frequency = Frequency.ANNUAL  # Default fallback

    for rule in rules:
        if rule_applies(rule, model, owner):
            effective_frequency = rule.frequency
            break  # Highest priority matching rule wins

    return effective_frequency

def rule_applies(rule: AttestationSchedulingRule, model: Model, owner: User) -> bool:
    """Check if a rule applies to this model/owner combination."""

    # MODEL_OVERRIDE: Specific model
    if rule.rule_type == 'MODEL_OVERRIDE':
        return rule.model_id == model.model_id

    # REGIONAL_OVERRIDE: Model deployed to this region
    if rule.rule_type == 'REGIONAL_OVERRIDE':
        return model_deployed_to_region(model.model_id, rule.region_id)

    # OWNER_THRESHOLD: Owner model count or high fluctuation flag
    if rule.rule_type == 'OWNER_THRESHOLD':
        owner_model_count = count_owner_models(owner.user_id)
        # Default threshold is 30 models
        if rule.owner_model_count_min and owner_model_count >= rule.owner_model_count_min:
            return True
        # High fluctuation is a MANUAL toggle set by Admin
        if rule.owner_high_fluctuation_flag and owner.high_fluctuation_flag:
            return True
        return False

    # GLOBAL_DEFAULT: Always applies
    if rule.rule_type == 'GLOBAL_DEFAULT':
        return True

    return False
```

### 2.2 Default Rule Configuration (Seeded)

| Rule Name | Type | Priority | Frequency | Conditions |
|-----------|------|----------|-----------|------------|
| "Global Annual Default" | GLOBAL_DEFAULT | 10 | ANNUAL | None (applies to all) |
| "High Volume Owner Quarterly" | OWNER_THRESHOLD | 50 | QUARTERLY | owner_model_count_min=**30** |
| "High Fluctuation Owner Quarterly" | OWNER_THRESHOLD | 50 | QUARTERLY | owner_high_fluctuation_flag=true |

**Admin can add:**
- Model-specific overrides (priority 100)
- Regional overrides (priority 75)
- Custom threshold rules

### 2.3 Due Date Generation

When an `AttestationCycle` is opened, the system generates `AttestationRecord` entries:

```python
def generate_attestation_records(cycle: AttestationCycle, db: Session):
    """
    Generate AttestationRecord for each in-scope model when cycle opens.
    Uses scheduling rules to determine which models are due in this cycle.
    """
    # Get all approved, active models
    models = db.query(Model).filter(
        Model.row_approval_status == None,  # Approved models only
        Model.status == 'Active'            # Active status
    ).all()

    for model in models:
        frequency = resolve_attestation_frequency(model.model_id, model.owner_id, db)

        # Check if model is due in this cycle
        if is_model_due_in_cycle(model, frequency, cycle, db):
            # Due date = cycle submission deadline (no grace period)
            due_date = cycle.submission_due_date

            record = AttestationRecord(
                cycle_id=cycle.cycle_id,
                model_id=model.model_id,
                attesting_user_id=model.owner_id,  # Default to owner
                due_date=due_date,
                status='PENDING'
            )
            db.add(record)

    db.commit()

def is_model_due_in_cycle(model: Model, frequency: Frequency, cycle: AttestationCycle, db: Session) -> bool:
    """
    Determine if model needs attestation in this cycle based on:
    - Frequency rule
    - Last attestation date
    - Cycle period boundaries
    """
    last_attestation = get_last_accepted_attestation(model.model_id, db)

    if frequency == Frequency.QUARTERLY:
        # Quarterly models are due every cycle
        return True

    if frequency == Frequency.ANNUAL:
        if last_attestation is None:
            return True  # Never attested, due now

        # Due if last attestation > 12 months ago
        months_since = months_between(last_attestation.attested_at, cycle.period_start_date)
        return months_since >= 12

    return True  # Default: include in cycle
```

### 2.4 Cycle Lifecycle

| Phase | Status | Actions |
|-------|--------|---------|
| **Creation** | PENDING | Admin creates cycle with period dates and submission deadline |
| **Open** | OPEN | Admin opens cycle; AttestationRecords generated |
| **Collection** | OPEN | Owners/delegates submit attestations; Changes enter suspense |
| **Review** | UNDER_REVIEW | Admin reviews attestations and change proposals |
| **Close** | CLOSED | Admin closes cycle (may be blocked by coverage targets) |

**Key Behaviors:**
- Cycles are **manually created and opened** by Admin
- **Multiple cycles CAN be OPEN simultaneously** (overlapping cycles allowed)
- **No grace period** - attestations are past-due immediately after due_date
- Cycle close blocked if any `is_blocking=true` coverage target not met

---

## 3. Attestation and Inventory Update Flows

### 3.1 Attestation Submission Flow (Owner/Delegate)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ATTESTATION SUBMISSION FLOW                      │
└─────────────────────────────────────────────────────────────────────┘

1. Owner/Delegate navigates to "My Attestations" page
   └── Shows all AttestationRecords where:
       - attesting_user_id = current_user OR
       - user is active delegate for model with can_attest=true
       - status = PENDING
       - cycle.status = OPEN

2. User selects model to attest
   └── Opens AttestationForm with:
       - Model summary (name, tier, owner, last validation)
       - Dynamic questions from "Attestation Questions" taxonomy
       - Filtered by frequency_scope matching cycle type

3. User completes attestation form:
   ┌─────────────────────────────────────────────────────────────┐
   │ ATTESTATION FORM - Q4 2025 Cycle                            │
   │ Model: ALM QRM v2 | Tier: Tier 1 | Owner: John Smith        │
   ├─────────────────────────────────────────────────────────────┤
   │                                                             │
   │ POLICY COMPLIANCE                                           │
   │ I attest to the best of my knowledge that the models that   │
   │ I am responsible for are in compliance with the Model Risk  │
   │ and Validation Policy.                                      │
   │   ○ Yes   ○ No                                              │
   │   If No, explain: [___________________________________]     │
   │                                                             │
   │ INVENTORY AWARENESS                                         │
   │ I have made Model Validation aware of all the models/       │
   │ procedures that my team owns, develops and/or uses that     │
   │ are subject to validation.                                  │
   │   ○ Yes   ○ No                                              │
   │   If No, explain: [___________________________________]     │
   │                                                             │
   │ [... additional questions based on taxonomy ...]            │
   │                                                             │
   │ ─────────────────────────────────────────────────────────── │
   │ DECISION:                                                   │
   │   ○ I Attest                                                │
   │   ○ I Attest with Updates (requires inventory changes)      │
   │   ○ Other (requires comment)                                │
   │   Comment: [___________________________________]            │
   │                                                             │
   │ EVIDENCE (Optional URLs):                                   │
   │   [+ Add Evidence URL]                                      │
   │   (No evidence is required)                                 │
   └─────────────────────────────────────────────────────────────┘

4. If decision = "I Attest with Updates":
   └── User is prompted to propose inventory changes
       ├── Update Existing Model → Creates ModelPendingEdit (existing pattern)
       ├── Register New Model → Creates AttestationChangeProposal (NEW_MODEL)
       └── Decommission Model → Creates AttestationChangeProposal (DECOMMISSION)

5. User submits attestation:
   └── Validation:
       - If decision != "I Attest", comment required
       - All questions must be answered
       - If answer=No and question.requires_comment_if_no=true, comment required
       - Evidence URLs validated for format only (optional)
   └── Creates AttestationResponse for each question
   └── Creates/Updates AttestationRecord with status=SUBMITTED
   └── Creates AttestationChangeProposals linked to attestation
   └── Audit log: entity_type="AttestationRecord", action="SUBMIT"
```

### 3.2 Inventory Change Suspense Queue (Reuses Existing Pattern)

**For UPDATE_EXISTING (modifying existing model):**

```python
# When owner proposes change during attestation
def propose_model_update(attestation_id: int, model_id: int, changes: dict, db: Session):
    """
    Uses EXISTING ModelPendingEdit pattern for model updates.
    Links to attestation via AttestationChangeProposal.
    """
    model = db.query(Model).get(model_id)

    # Capture original values (existing pattern from models.py:765-844)
    original_values = {}
    for field in changes.keys():
        original_values[field] = getattr(model, field, None)

    # Create pending edit using EXISTING pattern
    pending_edit = ModelPendingEdit(
        model_id=model_id,
        requested_by_id=current_user.user_id,
        proposed_changes=changes,
        original_values=original_values,
        status="pending"
    )
    db.add(pending_edit)
    db.flush()  # Get pending_edit_id

    # Link to attestation
    proposal = AttestationChangeProposal(
        attestation_id=attestation_id,
        pending_edit_id=pending_edit.pending_edit_id,
        change_type='UPDATE_EXISTING',
        model_id=model_id,
        proposed_data=changes,
        status='PENDING'
    )
    db.add(proposal)

    # Audit log using EXISTING pattern
    create_audit_log(
        db=db,
        entity_type="AttestationChangeProposal",
        entity_id=proposal.proposal_id,
        action="CREATE",
        user_id=current_user.user_id,
        changes={
            "attestation_id": attestation_id,
            "change_type": "UPDATE_EXISTING",
            "model_id": model_id,
            "proposed_changes": changes
        }
    )
```

**For NEW_MODEL or DECOMMISSION:**

```python
def propose_new_model(attestation_id: int, model_data: dict, db: Session):
    """
    Proposes a new model registration through attestation.
    Does NOT create model immediately - goes to suspense queue.
    """
    proposal = AttestationChangeProposal(
        attestation_id=attestation_id,
        pending_edit_id=None,  # No existing model
        change_type='NEW_MODEL',
        model_id=None,
        proposed_data=model_data,  # Full model creation payload
        status='PENDING'
    )
    db.add(proposal)

    create_audit_log(db, "AttestationChangeProposal", proposal.proposal_id, "CREATE", ...)
```

### 3.3 Admin Review and Approval Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ADMIN REVIEW FLOW                                │
└─────────────────────────────────────────────────────────────────────┘

1. Admin navigates to "Attestation Admin" dashboard
   └── Widgets:
       - Pending Attestations (status=SUBMITTED, awaiting review)
       - Pending Change Proposals (suspense queue)
       - Cycle Progress (coverage by tier)
       - ⚠️ CYCLE REMINDER (conspicuous if new cycle is due)

2. For each SUBMITTED attestation:
   └── Admin reviews:
       - Question responses (Yes/No with comments)
       - Evidence URLs (clickable links) - optional
       - Any linked change proposals
   └── Admin action:
       ○ Accept → status=ACCEPTED, no inventory changes
       ○ Accept with Changes → Review change proposals first
       ○ Reject → status=REJECTED, requires comment

3. For each change proposal:
   ┌─────────────────────────────────────────────────────────────┐
   │ CHANGE PROPOSAL REVIEW                                      │
   ├─────────────────────────────────────────────────────────────┤
   │ Type: UPDATE_EXISTING                                       │
   │ Model: ALM QRM v2 (ID: 1)                                   │
   │ Proposed By: John Smith                                     │
   │ Attestation: Q4 2025 Cycle                                  │
   │                                                             │
   │ PROPOSED CHANGES:                                           │
   │ ┌──────────────┬──────────────┬──────────────┐              │
   │ │ Field        │ Current      │ Proposed     │              │
   │ ├──────────────┼──────────────┼──────────────┤              │
   │ │ description  │ "Old desc"   │ "New desc"   │              │
   │ │ status       │ "Active"     │ "Active"     │              │
   │ └──────────────┴──────────────┴──────────────┘              │
   │                                                             │
   │ Admin Decision:                                             │
   │   ○ Accept (apply changes)                                  │
   │   ○ Reject (no changes applied)                             │
   │   Comment: [___________________________________]            │
   └─────────────────────────────────────────────────────────────┘

4. When Admin accepts UPDATE_EXISTING:
   └── Calls EXISTING approve_pending_edit() function
   └── Updates AttestationChangeProposal.status = 'ACCEPTED'
   └── Audit log captures both actions

5. When Admin accepts NEW_MODEL:
   └── Creates new Model from proposed_data
   └── Sets row_approval_status = NULL (approved)
   └── Updates AttestationChangeProposal.status = 'ACCEPTED'
   └── Audit log: Model CREATE + AttestationChangeProposal ACCEPT

6. When Admin accepts DECOMMISSION:
   └── Triggers existing decommissioning workflow
   └── Updates AttestationChangeProposal.status = 'ACCEPTED'

7. Closing a Cycle:
   └── Admin clicks "Close Cycle"
   └── System checks coverage targets:
       - If any is_blocking=true target not met → BLOCK with error
       - If only is_blocking=false targets not met → WARN but allow
   └── If allowed: status=CLOSED, audit log created

8. All actions logged via EXISTING create_audit_log() pattern
```

### 3.4 Audit Trail Structure

All attestation actions use the **existing AuditLog** entity:

| Action | entity_type | action | changes JSON |
|--------|-------------|--------|--------------|
| Submit attestation | AttestationRecord | SUBMIT | `{decision, question_responses...}` |
| Admin accept attestation | AttestationRecord | ACCEPT | `{reviewed_by, comment}` |
| Admin reject attestation | AttestationRecord | REJECT | `{reviewed_by, comment, reason}` |
| Propose model update | AttestationChangeProposal | CREATE | `{change_type, proposed_changes}` |
| Admin accept change | AttestationChangeProposal | ACCEPT | `{decided_by, applied_changes}` |
| Admin reject change | AttestationChangeProposal | REJECT | `{decided_by, reason}` |
| Open cycle | AttestationCycle | OPEN | `{opened_by, models_in_scope}` |
| Close cycle | AttestationCycle | CLOSE | `{closed_by, coverage_stats}` |
| Close blocked | AttestationCycle | CLOSE_BLOCKED | `{blocking_targets, coverage_gaps}` |

---

## 4. Dashboard and Report Definitions

### 4.1 Owner Dashboard - Attestation Notifications

**Add to existing owner dashboard (or Models page):**

```tsx
// Widget: "My Upcoming Attestations"
// Shows attestations due in next 14 days + any past-due

<div className="bg-white rounded-lg shadow-md p-4">
    <div className="flex items-center gap-2 mb-3 pb-2 border-b">
        <h3>My Attestation Deadlines</h3>
        {overdueCount > 0 && (
            <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full">
                {overdueCount} Past Due
            </span>
        )}
    </div>

    {/* Past Due Section - RED */}
    {pastDueAttestations.length > 0 && (
        <div className="mb-4">
            <h4 className="text-red-600 font-semibold text-sm mb-2">⚠️ Past Due</h4>
            {pastDueAttestations.map(a => (
                <div className="border-l-4 border-red-500 pl-3 py-2 mb-2 bg-red-50">
                    <Link to={`/attestations/${a.attestation_id}`}>
                        {a.model_name}
                    </Link>
                    <span className="text-xs text-red-600 ml-2">
                        {a.days_overdue} days overdue
                    </span>
                </div>
            ))}
        </div>
    )}

    {/* Upcoming Section - Next 14 days */}
    {upcomingAttestations.length > 0 && (
        <div>
            <h4 className="text-orange-600 font-semibold text-sm mb-2">📅 Due Soon (Next 14 Days)</h4>
            {upcomingAttestations.map(a => (
                <div className="border-l-4 border-orange-400 pl-3 py-2 mb-2">
                    <Link to={`/attestations/${a.attestation_id}`}>
                        {a.model_name}
                    </Link>
                    <span className="text-xs text-gray-500 ml-2">
                        Due {a.due_date}
                    </span>
                </div>
            ))}
        </div>
    )}
</div>
```

**API Endpoint:** `GET /attestations/my-upcoming?days_ahead=14`

Returns attestations for current user (as owner or delegate with can_attest=true) that are:
- Past due (due_date < today AND status = PENDING)
- Due within next 14 days

---

### 4.2 Admin Dashboard - Cycle Reminder

**Conspicuous reminder when new cycle should be opened:**

```tsx
// Admin Dashboard - Top of page if reminder needed
{shouldShowCycleReminder && (
    <div className="bg-yellow-100 border-l-4 border-yellow-500 p-4 mb-6">
        <div className="flex items-center">
            <span className="text-2xl mr-3">📢</span>
            <div>
                <h3 className="font-bold text-yellow-800">Attestation Cycle Reminder</h3>
                <p className="text-yellow-700">
                    It's time to open a new attestation cycle for {suggestedCycleName}.
                    The last cycle ended on {lastCycleEndDate}.
                </p>
                <Link to="/attestations/cycles/new" className="btn-primary mt-2">
                    Create New Cycle
                </Link>
            </div>
        </div>
    </div>
)}
```

**Logic for reminder:**
- Check if current date is within first 2 weeks of a new quarter
- Check if no OPEN cycle exists for that quarter
- Show reminder until Admin creates/opens a cycle

---

### 4.3 Admin Attestation Dashboard Widgets

**New Widget: "Attestation Overview"**

```tsx
// Add to AdminDashboardPage.tsx KPI grid
<div className="col-span-2 bg-white rounded-lg shadow-md p-4">
    <h3>Attestation Overview</h3>
    <div className="grid grid-cols-4 gap-4">
        <KPICard
            label="Pending Submissions"
            value={stats.pending_count}
            color="orange"
            link="/attestations?status=PENDING"
        />
        <KPICard
            label="Awaiting Review"
            value={stats.submitted_count}
            color="blue"
            link="/attestations?status=SUBMITTED"
        />
        <KPICard
            label="Past Due"
            value={stats.overdue_count}
            color="red"
            link="/attestations?overdue=true"
        />
        <KPICard
            label="Change Proposals"
            value={stats.pending_changes}
            color="purple"
            link="/attestations/changes"
        />
    </div>
</div>
```

**New Widget: "Attestation Change Proposals Awaiting Approval"**

Following existing "Model Changes Awaiting Approval" pattern (see Section 3.3).

---

### 4.4 Attestation Reports (add to ReportsPage.tsx)

**New Report Cards:**

```typescript
const attestationReports: Report[] = [
    {
        id: 'attestation-coverage',
        name: 'Attestation Coverage Report',
        description: 'Coverage vs. targets by risk tier with drill-down to individual models',
        path: '/reports/attestation-coverage',
        icon: '📊',
        category: 'Attestation'
    },
    {
        id: 'attestation-timeliness',
        name: 'Attestation Timeliness Report',
        description: 'On-time completion rates and past-due attestations',
        path: '/reports/attestation-timeliness',
        icon: '⏱️',
        category: 'Attestation'
    },
    {
        id: 'attestation-exceptions',
        name: 'Attestation Exceptions & Changes',
        description: 'Exceptions reported and inventory changes by cycle',
        path: '/reports/attestation-exceptions',
        icon: '⚠️',
        category: 'Attestation'
    },
    {
        id: 'attestation-compliance',
        name: 'Attestation Compliance Summary',
        description: 'High-level compliance summaries with evidence links',
        path: '/reports/attestation-compliance',
        icon: '✅',
        category: 'Attestation'
    }
];
```

### 4.5 Coverage vs. Targets Report

**API Endpoint:** `GET /attestations/reports/coverage`

**Response Structure:**

```json
{
    "cycle": {"cycle_id": 1, "cycle_name": "Q4 2025", "status": "OPEN"},
    "coverage_by_tier": [
        {
            "risk_tier_code": "TIER_1",
            "risk_tier_label": "Tier 1 - High Risk",
            "total_models": 15,
            "attested_count": 15,
            "coverage_pct": 100.0,
            "target_pct": 100.0,
            "is_blocking": true,
            "meets_target": true,
            "gap": 0
        },
        {
            "risk_tier_code": "TIER_2",
            "risk_tier_label": "Tier 2 - Medium Risk",
            "total_models": 42,
            "attested_count": 40,
            "coverage_pct": 95.24,
            "target_pct": 100.0,
            "is_blocking": true,
            "meets_target": false,
            "gap": 2
        }
    ],
    "overall_coverage": {
        "total_models": 120,
        "attested_count": 108,
        "coverage_pct": 90.0
    },
    "can_close_cycle": false,
    "blocking_gaps": ["TIER_2: 2 models missing (blocking)"],
    "models_not_attested": [
        {"model_id": 45, "model_name": "...", "owner": "...", "risk_tier": "TIER_2", "due_date": "2025-03-31"}
    ]
}
```

**Coverage Calculation:**

```python
def calculate_coverage(cycle_id: int, risk_tier_id: int, db: Session) -> dict:
    """
    Coverage = (Models with ACCEPTED attestation in cycle) / (Total in-scope models for tier)
    """
    # Total in-scope models for this tier
    total = db.query(func.count(AttestationRecord.attestation_id)).filter(
        AttestationRecord.cycle_id == cycle_id,
        AttestationRecord.model.has(Model.risk_tier_id == risk_tier_id)
    ).scalar()

    # Attested (ACCEPTED or SUBMITTED)
    attested = db.query(func.count(AttestationRecord.attestation_id)).filter(
        AttestationRecord.cycle_id == cycle_id,
        AttestationRecord.model.has(Model.risk_tier_id == risk_tier_id),
        AttestationRecord.status.in_(['ACCEPTED', 'SUBMITTED'])
    ).scalar()

    coverage_pct = (attested / total * 100) if total > 0 else 0

    target = get_coverage_target(risk_tier_id, db)

    return {
        "total_models": total,
        "attested_count": attested,
        "coverage_pct": round(coverage_pct, 2),
        "target_pct": target.target_percentage,
        "is_blocking": target.is_blocking,
        "meets_target": coverage_pct >= target.target_percentage,
        "gap": total - attested
    }
```

### 4.6 Timeliness Report

**API Endpoint:** `GET /attestations/reports/timeliness`

**Key Metrics:**
- **On-Time Rate:** % of attestations submitted by due_date
- **Average Days to Submit:** Mean days from cycle open to submission
- **Past-Due List:** Models with PENDING status where today > due_date (no grace period)

**Response:**

```json
{
    "cycle": {"cycle_id": 1, "cycle_name": "Q4 2025"},
    "timeliness_summary": {
        "total_due": 120,
        "submitted_on_time": 95,
        "submitted_late": 15,
        "still_pending": 10,
        "on_time_rate_pct": 79.2,
        "avg_days_to_submit": 12.5
    },
    "past_due_items": [
        {
            "attestation_id": 45,
            "model_id": 12,
            "model_name": "Credit Model X",
            "owner_name": "John Smith",
            "due_date": "2025-03-15",
            "days_overdue": 16,
            "risk_tier": "TIER_1"
        }
    ]
}
```

### 4.7 Exceptions & Changes Report

See original plan - unchanged.

### 4.8 Compliance Summary Report

See original plan - unchanged.

### 4.9 CSV Export

All reports include CSV export following existing pattern.

---

## 5. Role-Based Access and Audit Approach

### 5.1 Permission Matrix

| Action | Admin | Validator | Model Owner | Delegate (can_attest) | Delegate (can_submit) | User |
|--------|-------|-----------|-------------|----------------------|----------------------|------|
| View all attestations | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| View own attestations | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Submit attestation | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ |
| Propose inventory changes | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ |
| Review/approve attestations | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Accept/reject changes | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Configure scheduling rules | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Configure coverage targets | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Configure attestation questions | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Open/close cycles | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| View reports | ✓ | ✓ | ✓ (own models) | ✓ (delegated) | ✗ | ✗ |
| Set high_fluctuation_flag | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Grant can_attest permission | ✓ | ✗ | ✓ (own models) | ✗ | ✗ | ✗ |

**Key Change:** `can_attest` is a **separate permission** from `can_submit_changes`. A delegate with `can_attest=true` can submit attestations on behalf of the owner **without owner notification**.

### 5.2 Permission Enforcement

```python
# In api/app/api/attestations.py

def can_submit_attestation(attestation: AttestationRecord, user: User, db: Session) -> bool:
    """
    Check if user can submit this attestation.
    Uses NEW can_attest permission on ModelDelegate.
    """
    if user.role == "Admin":
        return True

    model = attestation.model

    # Owner can always attest their own models
    if model.owner_id == user.user_id:
        return True

    # Check delegate with can_attest permission (NEW PERMISSION)
    delegate = db.query(ModelDelegate).filter(
        ModelDelegate.model_id == model.model_id,
        ModelDelegate.user_id == user.user_id,
        ModelDelegate.revoked_at == None,
        ModelDelegate.can_attest == True  # NEW FIELD
    ).first()

    return delegate is not None
```

### 5.3 Comprehensive Audit Logging

All attestation actions logged via **existing AuditLog** - see Section 3.4.

---

## 6. MVP Phasing and Acceptance Criteria

### Phase 1: Core Attestation Workflow (4-5 weeks)

**Deliverables:**
1. Database migrations for new entities (including new taxonomy for questions)
2. Seed attestation questions from policy (see Appendix C)
3. `AttestationCycle` CRUD API + Admin UI
4. `AttestationRecord` + `AttestationResponse` submission API + Owner/Delegate UI
5. `AttestationEvidence` URL attachment support (optional)
6. Basic Admin review workflow (accept/reject attestations)
7. `can_attest` permission on ModelDelegate
8. Audit logging integration

**Acceptance Criteria:**
- [ ] **AC1:** Owners can view their pending attestations in "My Attestations" page
- [ ] **AC2:** Owners can complete attestation form with dynamic questions from taxonomy
- [ ] **AC3:** Questions filter by frequency_scope (ANNUAL/QUARTERLY/BOTH)
- [ ] **AC4:** Evidence URLs can be attached (optional) and are validated as URL format
- [ ] **AC5:** Admin can open/close attestation cycles
- [ ] **AC6:** Admin can review and accept/reject submitted attestations
- [ ] **AC7:** All actions are logged in existing AuditLog
- [ ] **AC8:** Delegates with can_attest=true can submit attestations

### Phase 2: Inventory Change Integration (3-4 weeks)

**Deliverables:**
1. `AttestationChangeProposal` entity and API
2. Integration with existing `ModelPendingEdit` for UPDATE_EXISTING
3. NEW_MODEL proposal workflow
4. DECOMMISSION proposal workflow
5. Admin change review UI (extends existing pending edits widget)

**Acceptance Criteria:**
- [ ] **AC9:** "I Attest with Updates" prompts for inventory changes
- [ ] **AC10:** Model updates create `ModelPendingEdit` via existing pattern
- [ ] **AC11:** New model proposals enter suspense queue, not created immediately
- [ ] **AC12:** Decommission proposals enter suspense queue
- [ ] **AC13:** Admin can accept/reject change proposals with full audit trail
- [ ] **AC14:** Accepted changes apply to inventory atomically

### Phase 3: Scheduling Rules Engine (2-3 weeks)

**Deliverables:**
1. `AttestationSchedulingRule` entity and Admin CRUD UI
2. Rule evaluation engine (global default, owner threshold=30, regional, model overrides)
3. Due date generation when cycle opens
4. `high_fluctuation_flag` on User entity (manual toggle by Admin)

**Acceptance Criteria:**
- [ ] **AC15:** Admin can configure global default frequency (annual)
- [ ] **AC16:** Admin can set owner model-count threshold (default 30) for quarterly
- [ ] **AC17:** Admin can manually toggle high_fluctuation_flag on users
- [ ] **AC18:** Admin can add model-specific frequency overrides
- [ ] **AC19:** Admin can add regional frequency overrides
- [ ] **AC20:** Due dates generated correctly based on rule priority
- [ ] **AC21:** Risk tier does NOT affect frequency (only coverage targets)

### Phase 4: Coverage Targets & Dashboards (2-3 weeks)

**Deliverables:**
1. `CoverageTarget` entity with `is_blocking` flag and Admin configuration UI
2. Coverage calculation engine with blocking check
3. Admin dashboard widget for attestation overview + cycle reminder
4. Owner dashboard widget for upcoming/past-due attestations (14 days)
5. Pending change proposals widget
6. Past-due attestations surfacing

**Acceptance Criteria:**
- [ ] **AC22:** Admin can configure global coverage targets by risk tier
- [ ] **AC23:** Admin can set is_blocking flag per target
- [ ] **AC24:** Cycle close blocked if blocking target not met
- [ ] **AC25:** Dashboard shows real-time coverage vs. targets
- [ ] **AC26:** Admin sees conspicuous cycle reminder when new cycle due
- [ ] **AC27:** Owners see upcoming (14 days) and past-due attestations on their dashboard
- [ ] **AC28:** Past-due items surfaced immediately (no grace period)

### Phase 5: Reports & Governance (2-3 weeks)

**Deliverables:**
1. Coverage Report (page + API) with blocking indicator
2. Timeliness Report (page + API)
3. Exceptions & Changes Report (page + API)
4. Compliance Summary Report (page + API)
5. CSV export for all reports
6. Add attestation reports to ReportsPage hub
7. Seed one historical attestation cycle

**Acceptance Criteria:**
- [ ] **AC29:** Coverage report shows % by tier vs. targets with blocking indicator
- [ ] **AC30:** Timeliness report shows on-time rate and past-due list
- [ ] **AC31:** Exceptions report aggregates by type, business line, materiality
- [ ] **AC32:** Compliance summary suitable for governance committee
- [ ] **AC33:** All reports support CSV export
- [ ] **AC34:** Reports filterable by cycle, risk tier, region
- [ ] **AC35:** One historical cycle exists in seed data

### Phase Summary

| Phase | Duration | Key Outcome |
|-------|----------|-------------|
| Phase 1 | 4-5 weeks | End-to-end attestation submission with configurable questions |
| Phase 2 | 3-4 weeks | Full suspense queue integration for inventory updates |
| Phase 3 | 2-3 weeks | Configurable scheduling rules engine (threshold=30) |
| Phase 4 | 2-3 weeks | Coverage targets with blocking + dashboard notifications |
| Phase 5 | 2-3 weeks | Governance reports + historical seed data |
| **Total** | **13-18 weeks** | Full MVP |

---

## 7. Assumptions and Risks

### 7.1 Assumptions

1. **Model Status Field Exists:** Models have an "Active" status; only active models are in scope for attestations
2. **Taxonomy System Sufficient:** Existing taxonomy infrastructure can store attestation questions with extended fields
3. **Risk Tiers Stable:** TIER_1 through TIER_4 taxonomy is fixed and won't change frequently
4. **Quarterly Cycles Align to Calendar:** Q1=Jan-Mar, Q2=Apr-Jun, etc.
5. **No File Uploads:** MVP uses URL attachments only; file storage is out of scope
6. **No Email Notifications:** MVP surfaces deadlines in UI only; email notifications are future work
7. **Owner Model Count Available:** Can query `count(models where owner_id = X)`

### 7.2 Key Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Complex rule evaluation performance** | Slow cycle opening for large inventories | Medium | Cache rule evaluation results; batch generate records |
| **Change proposal conflicts** | Two attestations propose conflicting changes to same model | Low | Lock model when first proposal created; warn on second |
| **Overlapping cycles confusion** | Admin unsure which cycle to use | Low | Clear cycle naming; UI shows all open cycles |
| **Evidence URL validation bypass** | Users submit non-URLs | Low | Server-side URL format validation; display as clickable links |
| **Audit log volume** | Large number of attestations creates many audit records | Low | Existing audit log handles this; add index on timestamp |
| **Migration complexity** | New tables reference existing tables | Low | Standard Alembic migrations; test on staging first |
| **Blocking target prevents cycle close** | Cycle stuck open indefinitely | Medium | Admin can override or adjust is_blocking flag |

---

## Appendix A: API Endpoints Summary

### Cycles

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/attestations/cycles` | Create cycle | Admin |
| GET | `/attestations/cycles` | List cycles | Admin, Validator |
| GET | `/attestations/cycles/{id}` | Get cycle details | Admin, Validator |
| PATCH | `/attestations/cycles/{id}` | Update cycle | Admin |
| POST | `/attestations/cycles/{id}/open` | Open cycle (generates records) | Admin |
| POST | `/attestations/cycles/{id}/close` | Close cycle (may be blocked) | Admin |
| GET | `/attestations/cycles/reminder` | Check if cycle reminder needed | Admin |

### Attestation Records

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/attestations/my-attestations` | My pending attestations | Owner, Delegate |
| GET | `/attestations/my-upcoming` | Upcoming (14 days) + past-due | Owner, Delegate |
| GET | `/attestations/records` | All attestations (filtered) | Admin, Validator |
| GET | `/attestations/records/{id}` | Get attestation details | Owner, Delegate, Admin |
| POST | `/attestations/records/{id}/submit` | Submit attestation | Owner, Delegate (can_attest) |
| POST | `/attestations/records/{id}/accept` | Accept attestation | Admin |
| POST | `/attestations/records/{id}/reject` | Reject attestation | Admin |

### Questions (via Taxonomy)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/attestations/questions` | List active questions | All authenticated |
| GET | `/attestations/questions?frequency=QUARTERLY` | Filter by frequency | All authenticated |
| POST | `/taxonomies/{taxonomy_id}/values` | Add question (existing) | Admin |
| PATCH | `/taxonomies/values/{value_id}` | Update question (existing) | Admin |

### Evidence

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/attestations/records/{id}/evidence` | Add evidence URL (optional) | Owner, Delegate |
| DELETE | `/attestations/evidence/{id}` | Remove evidence | Owner, Delegate, Admin |

### Change Proposals

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/attestations/records/{id}/changes` | Propose change | Owner, Delegate |
| GET | `/attestations/changes` | List pending changes | Admin |
| GET | `/attestations/changes/{id}` | Get change details | Admin |
| POST | `/attestations/changes/{id}/accept` | Accept change | Admin |
| POST | `/attestations/changes/{id}/reject` | Reject change | Admin |

### Scheduling Rules

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/attestations/rules` | List rules | Admin |
| POST | `/attestations/rules` | Create rule | Admin |
| PATCH | `/attestations/rules/{id}` | Update rule | Admin |
| DELETE | `/attestations/rules/{id}` | Deactivate rule | Admin |

### Coverage Targets

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/attestations/targets` | List targets (global) | Admin, Validator |
| PATCH | `/attestations/targets/{tier_id}` | Update target + is_blocking | Admin |

### Reports

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/attestations/reports/coverage` | Coverage report with blocking info | Admin, Validator |
| GET | `/attestations/reports/timeliness` | Timeliness report | Admin, Validator |
| GET | `/attestations/reports/exceptions` | Exceptions report | Admin, Validator |
| GET | `/attestations/reports/compliance-summary` | Summary report | Admin, Validator |

---

## Appendix B: Database Migration Order

```
1. b1_add_attestation_questions_taxonomy.py
   - Create new taxonomy "Attestation Questions" (is_system=true)
   - Add frequency_scope, requires_comment_if_no columns to taxonomy_values
   - Seed 10 questions from policy

2. b2_create_attestation_cycles.py
   - Create attestation_cycles table

3. b3_create_attestation_scheduling_rules.py
   - Create attestation_scheduling_rules table
   - FKs to regions, models (NO risk_tier_id)
   - Seed default rules (threshold=30)

4. b4_create_coverage_targets.py
   - Create coverage_targets table with is_blocking column
   - FK to taxonomy_values (risk_tier)
   - Seed default targets with is_blocking flags

5. b5_create_attestation_records.py
   - Create attestation_records table
   - FKs to cycles, models, users

6. b6_create_attestation_responses.py
   - Create attestation_responses table
   - FKs to attestation_records, taxonomy_values (questions)

7. b7_create_attestation_evidence.py
   - Create attestation_evidence table
   - FK to attestation_records

8. b8_create_attestation_change_proposals.py
   - Create attestation_change_proposals table
   - FKs to attestation_records, model_pending_edits, models

9. b9_add_can_attest_to_model_delegates.py
   - Add can_attest column to model_delegates table

10. b10_add_high_fluctuation_flag_to_users.py
    - Add high_fluctuation_flag column to users table

11. b11_seed_historical_attestation_cycle.py
    - Create one historical CLOSED cycle (e.g., Q3 2025)
    - Create sample attestation records for that cycle
```

---

## Appendix C: Attestation Questions (from Policy)

These questions are seeded into the "Attestation Questions" taxonomy and can be edited by Admin.

### Questions for BOTH Annual and Quarterly Cycles

1. **POLICY_COMPLIANCE** (requires comment if No)
   > I attest to the best of my knowledge that the models that I am responsible for are in compliance with the Model Risk and Validation Policy.

2. **INVENTORY_AWARENESS** (requires comment if No)
   > I have made Model Validation aware of all the models/procedures that my team owns, develops and/or uses that are subject to validation.

3. **NO_MATERIAL_CHANGES** (requires comment if No)
   > I have made Model Validation aware that there are no material changes to those models since last time they were validated, and therefore no material model change should be implemented before Model Validation approval.

4. **MONITORING_ISSUES** (requires comment if No)
   > I have made Model Validation aware of the models with deteriorating performance or issues that triggered the monitoring thresholds, and hence the applicable remediation plan to mitigate the potential model risk. (Section 6.4 Ongoing monitoring and review)

5. **EXCEPTIONS_REPORTED** (requires comment if No)
   > I have made Model Validation aware of any additional comments and/or any exceptions to the Policy.

6. **LIMITATIONS_NOTIFIED**
   > I will notify model users of critical model limitations to support appropriate and informed model usage.

7. **RESTRICTIONS_IMPLEMENTED** (requires comment if No)
   > I confirm any restrictions on model use have been implemented.

### Questions for ANNUAL Cycles Only

8. **PURPOSE_DOCUMENTED**
   > I am responsible to identify, understand and document the purpose of the models and ensure that the modeling choices are documented (Section 6.1 Rationale for Modeling and Model Development).

9. **ESCALATION_COMMITMENT**
   > I will bring to the attention of Model Validation and other stakeholders, any model risk issues that have significant impact on P&L, economic capital, regulatory capital or models to pose material level of model risk (Section 6.4.3 Escalation process).

10. **ROLES_COMPLIANCE**
    > I comply with the related Roles and Responsibilities for my team within the Policy. (Section 8.0 Roles and responsibilities)

---

## Appendix D: File Locations (New Files to Create)

### Backend (api/)

```
api/app/models/attestation.py          # New models: AttestationCycle, AttestationRecord, etc.
api/app/schemas/attestation.py         # Pydantic schemas
api/app/api/attestations.py            # API routes
api/alembic/versions/b1_*.py           # Migrations (11 files per Appendix B)
api/tests/test_attestations.py         # Unit tests
```

### Frontend (web/)

```
web/src/pages/MyAttestationsPage.tsx           # Owner/delegate attestation list + upcoming widget
web/src/pages/AttestationFormPage.tsx          # Attestation submission form (dynamic questions)
web/src/pages/AttestationAdminPage.tsx         # Admin review queue
web/src/pages/AttestationCyclesPage.tsx        # Cycle management (Admin)
web/src/pages/AttestationRulesPage.tsx         # Scheduling rules config (Admin)
web/src/pages/AttestationCoverageReportPage.tsx    # Coverage report with blocking
web/src/pages/AttestationTimelinessReportPage.tsx  # Timeliness report
web/src/pages/AttestationExceptionsReportPage.tsx  # Exceptions report
web/src/pages/AttestationComplianceReportPage.tsx  # Compliance summary
web/src/components/AttestationForm.tsx         # Reusable attestation form (dynamic questions)
web/src/components/AttestationChangeModal.tsx  # Inventory change proposal modal
web/src/components/AttestationDeadlineWidget.tsx   # Owner dashboard widget (14 days + past-due)
web/src/components/CycleReminderBanner.tsx     # Admin cycle reminder banner
```

---

*Document Version: 1.1*
*Created: 2025-12-02*
*Updated: 2025-12-02 (incorporated product owner clarifications)*
*Author: Claude Code (Implementation Planning)*
