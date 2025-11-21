# Regional Deployment & Compliance Report

## Executive Summary

This document explains the implementation of a "Regional Deployment & Compliance Report" that attempts to answer the regulatory question:

> **"Show me all models deployed in region X, with the deployed version number, validation status, and regional approval status for that specific version."**

**⚠️ CRITICAL FINDING:** The current database schema **CANNOT** fully answer this question due to missing fields in the `validation_approvals` table.

---

## Schema Gap Identified

### Problem Statement

The `validation_approvals` table lacks two critical fields needed to support region-specific approval tracking:

1. **`region_id`** - To identify which region an approval applies to
2. **`approval_type`** - To distinguish between "Global" and "Regional" approvals

### Current Schema (Incomplete)

```sql
CREATE TABLE validation_approvals (
    approval_id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES validation_requests(request_id),
    approver_id INTEGER NOT NULL REFERENCES users(user_id),
    approver_role VARCHAR(100) NOT NULL,  -- e.g., 'Validator', 'Model Owner', etc.
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    approval_status VARCHAR(50) NOT NULL DEFAULT 'Pending',
    comments TEXT,
    approved_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### Impact on Reporting

**Scenario:** A model version needs validation approval for deployment to multiple regions (US, EU, APAC).

**Question:** "Did the US regional approver approve this version for US deployment?"

**Current Capability:** ❌ **CANNOT ANSWER**
- We can see that regional approvals exist
- We can see who approved
- We CANNOT determine which approval is for which region

**Example Data Problem:**
```
Validation Request #123 has 3 approvals:
- John Doe (Regional Approver) - Approved
- Jane Smith (Regional Approver) - Approved
- Bob Johnson (Regional Approver) - Rejected

Which approval is for US? EU? APAC? → UNKNOWN
```

---

## Proposed Schema Fix

### Required Changes

```sql
-- Add approval_type and region_id columns
ALTER TABLE validation_approvals
ADD COLUMN approval_type VARCHAR(20) NOT NULL DEFAULT 'Global'
    CHECK (approval_type IN ('Global', 'Regional'));

ALTER TABLE validation_approvals
ADD COLUMN region_id INTEGER REFERENCES regions(region_id);

-- Enforce constraint: Regional approvals must have region_id
ALTER TABLE validation_approvals
ADD CONSTRAINT chk_regional_approval_has_region
    CHECK (
        (approval_type = 'Regional' AND region_id IS NOT NULL)
        OR
        (approval_type = 'Global' AND region_id IS NULL)
    );

-- Add index for performance
CREATE INDEX idx_validation_approvals_region
    ON validation_approvals(region_id)
    WHERE region_id IS NOT NULL;
```

### After Fix - Complete Schema

```sql
CREATE TABLE validation_approvals (
    approval_id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES validation_requests(request_id),
    approver_id INTEGER NOT NULL REFERENCES users(user_id),
    approver_role VARCHAR(100) NOT NULL,

    -- NEW FIELDS
    approval_type VARCHAR(20) NOT NULL DEFAULT 'Global',  -- 'Global' or 'Regional'
    region_id INTEGER REFERENCES regions(region_id),       -- Required if Regional

    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    approval_status VARCHAR(50) NOT NULL DEFAULT 'Pending',
    comments TEXT,
    approved_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraint
    CONSTRAINT chk_regional_approval_has_region
        CHECK (
            (approval_type = 'Regional' AND region_id IS NOT NULL)
            OR (approval_type = 'Global' AND region_id IS NULL)
        )
);
```

---

## Current Implementation (Workaround)

Despite the schema limitation, we've implemented a report that provides **partial** information:

### What the Report CAN Show ✅

1. **Models deployed in each region** - from `model_regions` table
2. **Deployed version numbers** - from `model_versions` table
3. **Deployment dates** - from `model_regions.deployed_at`
4. **Validation workflow status** - from `validation_requests` table
5. **Whether ANY regional approvals exist** - by counting approvals
6. **List of ALL regional approvers** - across ALL regions (not specific to one region)

### What the Report CANNOT Show ❌

1. **Region-specific approval status** - Cannot determine which approval is for which region
2. **Per-region compliance** - Cannot definitively say "US deployment is approved by US approver"

### Current Workaround Logic

```python
# ⚠️ WORKAROUND: Cannot filter by region
approval_query = (
    select(ValidationApproval)
    .where(ValidationApproval.request_id == validation_request_id)
    # ❌ MISSING: .where(ValidationApproval.region_id == specific_region_id)
)

# Result: Shows ALL regional approvals, not specific to this region
if any('regional' in approval.approver_role.lower() for approval in approvals):
    regional_approval_status = "Approved (ALL regions)"  # ⚠️ Not region-specific!
```

---

## Files Created/Modified

### Backend

1. **`api/app/api/regional_compliance_report.py`** - New API endpoint
   - SQLAlchemy query implementation
   - Documents schema limitations in code
   - Returns warnings in API response

2. **`api/app/main.py`** - Updated to register new router

### Frontend

1. **`web/src/pages/RegionalComplianceReportPage.tsx`** - New UI page
   - Displays regional deployment data
   - Shows prominent schema limitation warning
   - CSV export functionality
   - Filter by region and deployment status

2. **`web/src/App.tsx`** - Added route for `/regional-compliance-report`

3. **`web/src/components/Layout.tsx`** - Added navigation link

---

## API Endpoint

### Request

```http
GET /regional-compliance-report/?region_code=US&only_deployed=true
Authorization: Bearer <token>
```

### Response Structure

```typescript
interface RegionalComplianceReportResponse {
    report_generated_at: string;
    region_filter: string | null;
    total_records: number;
    records: RegionalDeploymentRecord[];
    schema_limitations: string[];  // ⚠️ Lists all known limitations
}

interface RegionalDeploymentRecord {
    // Region Information
    region_code: string;
    region_name: string;
    requires_regional_approval: boolean;

    // Model Information
    model_id: number;
    model_name: string;

    // Deployment Information
    deployed_version: string | null;
    deployment_date: string | null;
    deployment_notes: string | null;

    // Validation Information
    validation_request_id: number | null;
    validation_status: string | null;
    validation_completion_date: string | null;

    // Regional Approval (⚠️ LIMITED DATA)
    has_regional_approvals: boolean;
    regional_approval_count: number;  // Count across ALL regions
    regional_approvers: string[];      // List of ALL approvers (all regions)
    regional_approval_status: string;  // "Approved (ALL regions)" - NOT region-specific

    // Compliance Flags
    is_deployed_without_validation: boolean;
    is_validation_pending: boolean;
    is_validation_approved: boolean;
}
```

### Example Response (Showing Limitation)

```json
{
    "report_generated_at": "2025-01-21T14:00:00Z",
    "region_filter": "US",
    "total_records": 5,
    "schema_limitations": [
        "⚠️ CRITICAL: Cannot determine which regional approval belongs to which region",
        "Missing field: validation_approvals.region_id",
        "Missing field: validation_approvals.approval_type (Global/Regional)",
        "Impact: Cannot answer 'Did US regional approver approve this US deployment?'",
        "Current data shows ALL regional approvals but cannot map them to specific regions"
    ],
    "records": [
        {
            "region_code": "US",
            "region_name": "United States",
            "requires_regional_approval": true,
            "model_id": 42,
            "model_name": "Credit Risk Model",
            "deployed_version": "2.1.0",
            "deployment_date": "2025-01-15T10:00:00Z",
            "validation_request_id": 123,
            "validation_status": "Approved",
            "validation_completion_date": "2025-01-10T16:00:00Z",
            "has_regional_approvals": true,
            "regional_approval_count": 3,
            "regional_approvers": [
                "John Doe (Regional Approver US) - Approved on 2025-01-09",
                "Jane Smith (Regional Approver EU) - Approved on 2025-01-08",
                "Bob Johnson (Regional Approver APAC) - Rejected on 2025-01-07"
            ],
            "regional_approval_status": "Approved (ALL regions)",
            "is_deployed_without_validation": false,
            "is_validation_pending": false,
            "is_validation_approved": true
        }
    ]
}
```

**⚠️ Notice:** The response shows approvers from US, EU, and APAC all together. We cannot determine which one is the "US" approval for this "US" deployment.

---

## UI Features

### Regional Compliance Report Page

Located at: `/regional-compliance-report`

**Features:**
- ✅ Filter by region code
- ✅ Toggle "only deployed" models
- ✅ CSV export
- ✅ Prominent schema warning banner
- ✅ Compliance status badges
- ✅ Direct links to model details

**Warning Display:**
- Large red warning banner at top of page
- Explains exact schema limitation
- Shows example of the problem
- Provides technical fix details
- Dismissible but re-appears on page reload

**Table Columns:**
1. Region (with approval requirement indicator)
2. Model (linked to details page)
3. Deployed Version
4. Deployment Date
5. Validation Status (badged)
6. ⚠️ Regional Approval (with warning indicator)
7. Compliance Status (badged)

**Regional Approval Column Indicator:**
```
⚠️ Regional Approval*

* Schema Limitation: Shows ALL regional approvals across ALL regions
  but cannot determine which approval applies to this specific region.
```

---

## Migration Path

### Phase 1: Add Schema Fields (Database)

```sql
-- Run in production database
BEGIN;

-- Add new columns
ALTER TABLE validation_approvals
ADD COLUMN approval_type VARCHAR(20) NOT NULL DEFAULT 'Global'
    CHECK (approval_type IN ('Global', 'Regional'));

ALTER TABLE validation_approvals
ADD COLUMN region_id INTEGER REFERENCES regions(region_id);

-- Add constraint
ALTER TABLE validation_approvals
ADD CONSTRAINT chk_regional_approval_has_region
    CHECK (
        (approval_type = 'Regional' AND region_id IS NOT NULL)
        OR (approval_type = 'Global' AND region_id IS NULL)
    );

-- Add index
CREATE INDEX idx_validation_approvals_region
    ON validation_approvals(region_id)
    WHERE region_id IS NOT NULL;

COMMIT;
```

### Phase 2: Backfill Existing Data (if applicable)

```sql
-- If you need to classify existing approvals as Regional and assign regions
-- This requires business logic to determine which approvals go to which regions

-- Example: Update approvals where approver_role suggests regional scope
UPDATE validation_approvals
SET approval_type = 'Regional',
    region_id = (
        -- Logic to determine region from approver_role or other context
        -- This will vary based on your data
    )
WHERE approver_role ILIKE '%regional%'
  AND approval_type = 'Global';  -- Only update those not yet set
```

### Phase 3: Update SQLAlchemy Models

```python
# api/app/models/validation.py

class ValidationApproval(Base):
    __tablename__ = "validation_approvals"

    approval_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(Integer, ForeignKey("validation_requests.request_id"))
    approver_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"))
    approver_role: Mapped[str] = mapped_column(String(100))

    # NEW FIELDS
    approval_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="Global"
    )  # 'Global' or 'Regional'
    region_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("regions.region_id"), nullable=True
    )

    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    approval_status: Mapped[str] = mapped_column(String(50), default="Pending")
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    request = relationship("ValidationRequest", back_populates="approvals")
    approver = relationship("User", foreign_keys=[approver_id])
    region = relationship("Region")  # NEW
```

### Phase 4: Update API Query

```python
# api/app/api/regional_compliance_report.py

# AFTER SCHEMA FIX - This query will work correctly
approval_query = (
    select(ValidationApproval)
    .where(ValidationApproval.request_id == validation_request_id)
    .where(ValidationApproval.approval_type == 'Regional')
    .where(ValidationApproval.region_id == current_region_id)  # ✅ NOW POSSIBLE!
)

# Can now accurately report:
# "US Regional Approval: Approved by John Doe on 2025-01-09"
```

### Phase 5: Update UI (Remove Warning)

After schema fix, update `RegionalComplianceReportPage.tsx`:
- Remove schema warning banner
- Update column header from "⚠️ Regional Approval*" to "Regional Approval"
- Show region-specific approval status

---

## Testing the Report

### Test Scenario 1: Model Deployed to US Region

**Setup:**
```sql
-- Insert test data
INSERT INTO model_regions (model_id, region_id, version_id, deployed_at)
VALUES (42, 1, 15, '2025-01-15 10:00:00');

-- Validation request for that version
UPDATE model_versions SET validation_request_id = 123 WHERE version_id = 15;

-- Validation approved
UPDATE validation_requests
SET current_status_id = (SELECT value_id FROM taxonomy_values WHERE code = 'APPROVED')
WHERE request_id = 123;

-- Regional approvals (but cannot link to specific regions yet)
INSERT INTO validation_approvals (request_id, approver_id, approver_role, approval_status)
VALUES
(123, 10, 'Regional Approver US', 'Approved'),
(123, 11, 'Regional Approver EU', 'Approved');
```

**Expected Report Output:**
- ✅ Shows deployment in US region
- ✅ Shows version 2.1.0
- ✅ Shows validation status "Approved"
- ⚠️ Shows 2 regional approvals BUT cannot identify which is for US
- ⚠️ Regional approval status: "Approved (ALL regions)" - ambiguous

### Test Scenario 2: After Schema Fix

**With region_id added:**
```sql
-- Now approvals can be region-specific
INSERT INTO validation_approvals (
    request_id,
    approver_id,
    approver_role,
    approval_type,
    region_id,  -- ✅ NOW TRACKED
    approval_status
)
VALUES
(123, 10, 'Regional Approver', 'Regional', 1, 'Approved'),  -- US
(123, 11, 'Regional Approver', 'Regional', 2, 'Approved');  -- EU
```

**Expected Report Output:**
- ✅ Shows deployment in US region
- ✅ Shows version 2.1.0
- ✅ Shows validation status "Approved"
- ✅ Shows regional approval status: "Approved by John Doe (US) on 2025-01-09"
- ✅ Does NOT show EU approval (not relevant to US deployment)

---

## Conclusion

### Current State

The Regional Deployment & Compliance Report has been **implemented** but is **functionally limited** by schema gaps.

**What Works:**
- ✅ Report generation
- ✅ Data retrieval from all relevant tables
- ✅ Filtering and CSV export
- ✅ Clear documentation of limitations

**What Doesn't Work:**
- ❌ Region-specific approval mapping
- ❌ Accurate compliance determination per region

### Required Action

To fully support regional compliance reporting, the database schema **must** be updated with the proposed changes to `validation_approvals` table.

**Priority:** **HIGH** - This affects regulatory compliance reporting capability.

### Benefits After Fix

1. **Regulatory Compliance**: Can accurately answer auditor questions about regional approvals
2. **Data Accuracy**: Removes ambiguity from approval tracking
3. **Multi-Region Support**: Enables proper multi-region deployment workflow
4. **Audit Trail**: Complete record of which region approved which deployment

---

## Contact

For questions about this implementation or to discuss the schema fix:
- Review the API code: `api/app/api/regional_compliance_report.py`
- Review the UI code: `web/src/pages/RegionalComplianceReportPage.tsx`
- Schema change script: See "Migration Path" section above

**Note:** This report is available to all authenticated users at `/regional-compliance-report` with a prominent warning about data limitations.
