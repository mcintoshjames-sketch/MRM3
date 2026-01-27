# Inherent Model Risk Assessment Implementation Plan

## Overview

Implement a risk assessment system that derives Model Tier from qualitative and quantitative factors, with override capabilities. Assessments are per-model AND per-region (global + deployment regions).

## Business Rules

1. **Regional assessments**: Users manually create regional assessments
2. **Partial saves**: Users can save incomplete assessments
3. **Model tier fallback**: `risk_tier_id` remains directly editable for models without assessments, but becomes read-only once an assessment exists

## Risk Calculation Flow

```
4 Qualitative Factors → Weighted Score → Qualitative Level (H/M/L)
                                              ↓
                              [Override opportunity #2]
                                              ↓
Quantitative Factor (H/M/L) → [Override opportunity #1] → Effective Quantitative
                                              ↓
Qualitative + Quantitative → Matrix Lookup → Derived Inherent Risk
                                              ↓
                              [Override opportunity #3]
                                              ↓
                              Final Model Tier (TIER_1/2/3/4)
```

## Qualitative Assessment Methodology

| Factor | Weight | Options |
|--------|--------|---------|
| Reputation, Legal, Regulatory Compliance and/or Financial Reporting | 30% | High(3), Medium(2), Low(1) |
| Model Complexity | 30% | High(3), Medium(2), Low(1) |
| Model Usage and Model Dependency | 20% | High(3), Medium(2), Low(1) |
| Stability | 20% | High(3), Medium(2), Low(1) |

**Score → Level Mapping:**
- High: 2.1 ≤ score ≤ 3.0
- Medium: 1.6 ≤ score < 2.1
- Low: 1.0 < score < 1.6

## Inherent Risk Matrix

| Quantitative ↓ / Qualitative → | High | Medium | Low |
|-------------------------------|------|--------|-----|
| **High** | High | Medium | Low |
| **Medium** | Medium | Medium | Low |
| **Low** | Low | Low | Very Low |

## Tier Mapping

- High → Tier 1 (TIER_1)
- Medium → Tier 2 (TIER_2)
- Low → Tier 3 (TIER_3)
- Very Low → Tier 4 (TIER_4)

## Permissions

- Admin or Validator can create/edit assessments and apply overrides

---

## Phase 1: Database Schema

### New Tables

**QualitativeRiskFactor** (Admin-customizable taxonomy)
```sql
CREATE TABLE qualitative_risk_factors (
    factor_id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,           -- e.g., 'REPUTATION_LEGAL'
    name VARCHAR(200) NOT NULL,                 -- e.g., 'Reputation, Regulatory Compliance and/or Financial Reporting Risk'
    description TEXT,                           -- Full description of the factor
    weight DECIMAL(5,4) NOT NULL,               -- e.g., 0.3000 (30%)
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**QualitativeFactorGuidance** (Rating guidance per factor)
```sql
CREATE TABLE qualitative_factor_guidance (
    guidance_id SERIAL PRIMARY KEY,
    factor_id INTEGER NOT NULL REFERENCES qualitative_risk_factors(factor_id) ON DELETE CASCADE,
    rating VARCHAR(10) NOT NULL,                -- HIGH/MEDIUM/LOW
    points INTEGER NOT NULL,                    -- 3/2/1
    description TEXT NOT NULL,                  -- Guidance text for this rating
    sort_order INTEGER NOT NULL DEFAULT 0,

    UNIQUE(factor_id, rating)
);
```

**ModelRiskAssessment**
```sql
CREATE TABLE model_risk_assessments (
    assessment_id SERIAL PRIMARY KEY,
    model_id INTEGER NOT NULL REFERENCES models(model_id),
    region_id INTEGER REFERENCES regions(region_id),  -- NULL = Global

    -- Quantitative Assessment
    quantitative_rating VARCHAR(10),  -- HIGH/MEDIUM/LOW
    quantitative_comment TEXT,
    quantitative_override VARCHAR(10),  -- HIGH/MEDIUM/LOW
    quantitative_override_comment TEXT,

    -- Qualitative Assessment (calculated from factors)
    qualitative_calculated_score DECIMAL(5,2),  -- e.g., 2.30
    qualitative_calculated_level VARCHAR(10),  -- HIGH/MEDIUM/LOW
    qualitative_override VARCHAR(10),  -- HIGH/MEDIUM/LOW
    qualitative_override_comment TEXT,

    -- Derived Inherent Risk (from matrix lookup)
    derived_risk_tier VARCHAR(10),  -- HIGH/MEDIUM/LOW/VERY_LOW
    derived_risk_tier_override VARCHAR(10),  -- HIGH/MEDIUM/LOW/VERY_LOW
    derived_risk_tier_override_comment TEXT,

    -- Final tier (mapped to taxonomy)
    final_tier_id INTEGER REFERENCES taxonomy_values(value_id),

    -- Metadata
    assessed_by_id INTEGER REFERENCES users(user_id),
    assessed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(model_id, region_id)  -- One assessment per model per region
);
```

**QualitativeFactorAssessment**
```sql
CREATE TABLE qualitative_factor_assessments (
    factor_assessment_id SERIAL PRIMARY KEY,
    assessment_id INTEGER NOT NULL REFERENCES model_risk_assessments(assessment_id) ON DELETE CASCADE,
    factor_id INTEGER NOT NULL REFERENCES qualitative_risk_factors(factor_id),  -- Links to customizable factor
    rating VARCHAR(10),  -- HIGH/MEDIUM/LOW (nullable for partial saves)
    comment TEXT,
    weight_at_assessment DECIMAL(5,4) NOT NULL,  -- Snapshot of weight at time of assessment
    score DECIMAL(5,2),  -- 3.00, 2.00, 1.00 (calculated from rating)

    UNIQUE(assessment_id, factor_id)
);
```

### Seed Data (Initial Qualitative Factors)

```python
INITIAL_QUALITATIVE_FACTORS = [
    {
        "code": "REPUTATION_LEGAL",
        "name": "Reputation, Regulatory Compliance and/or Financial Reporting Risk",
        "description": "Reputation Risk is defined as the risk of negative publicity regarding business conduct or practices which, whether true or not, could significantly harm the institution's reputation as a leading financial institution, or could materially and adversely affect business, operations or financial condition.",
        "weight": 0.30,
        "sort_order": 1,
        "guidance": [
            {
                "rating": "HIGH",
                "points": 3,
                "description": "Failure of the model could significantly impact the institution's reputation, regulatory compliance and/or financial reporting."
            },
            {
                "rating": "MEDIUM",
                "points": 2,
                "description": "Misuse or errors in the model could impact the institution's reputation, regulatory compliance, and/or financial reporting with moderate to low impact."
            },
            {
                "rating": "LOW",
                "points": 1,
                "description": "Misuse or errors in the model would have limited impact on the institution's reputation, regulatory compliance, and/or financial reporting."
            }
        ]
    },
    {
        "code": "COMPLEXITY",
        "name": "Complexity of the Model",
        "description": "The complexity of the model refers to the mathematical sophistication of the model including the number of model inputs, data sources, transformations, and assumptions.",
        "weight": 0.30,
        "sort_order": 2,
        "guidance": [
            {
                "rating": "HIGH",
                "points": 3,
                "description": "Multiple inputs or data sources or complex transformation of input data/parameters or non-standard methodologies and assumptions. Mathematical sophistication: Complex mathematical calculation, analysis, or assumptions or simplifications (e.g. regression, calculus, etc.)"
            },
            {
                "rating": "MEDIUM",
                "points": 2,
                "description": "A few inputs or data sources or simple transformation of input data/parameters. Mathematical sophistication: Moderate mathematics or calculations, few assumptions or simplifications, etc."
            },
            {
                "rating": "LOW",
                "points": 1,
                "description": "Limited inputs or data sources. Mathematical sophistication: Basic mathematics and limited calculations."
            }
        ]
    },
    {
        "code": "USAGE_DEPENDENCY",
        "name": "Model Usage and Model Dependency",
        "description": "The model usage and model dependency assesses the strategic importance of the model usage, any model interdependence and potential impact across the organization.",
        "weight": 0.20,
        "sort_order": 3,
        "guidance": [
            {
                "rating": "HIGH",
                "points": 3,
                "description": "If error occurs, it would impact institutions reporting to third parties (e.g., rating agencies, shareholders, etc.). Business decisions are taken based on the individual model. The model is a key input to other models. If error occurs, it would impact several LOBs (departments) at the bank."
            },
            {
                "rating": "MEDIUM",
                "points": 2,
                "description": "Business decisions are taken using the model results, however, other inputs are also taken into account. The model is fed to other models. If a model error occurs, it would impact several LOBs (departments)."
            },
            {
                "rating": "LOW",
                "points": 1,
                "description": "If a model error occurs, it would impact one department. Business decisions are taken using different inputs, the model is only one factor."
            }
        ]
    },
    {
        "code": "STABILITY",
        "name": "Stability of the Model",
        "description": "The stability of the model refers to the likelihood of model error, the uncertainty of the model outcomes (unobservable factors), and the ability to monitor the model.",
        "weight": 0.20,
        "sort_order": 4,
        "guidance": [
            {
                "rating": "HIGH",
                "points": 3,
                "description": "The likelihood of error is high, and/or the magnitude of the impact of an error is high. The output of the model is not predictable. Third party models where the Bank does not have access to proprietary elements and performance monitoring is not conducted."
            },
            {
                "rating": "MEDIUM",
                "points": 2,
                "description": "If there is a model error, the magnitude of the impact may be low to moderate. The output of the model is predictable and an occurrence of error is moderate. Third party models with little or no information, regular performance monitoring is conducted, or models whose information is known, but proper regular monitoring process has not been developed."
            },
            {
                "rating": "LOW",
                "points": 1,
                "description": "The likelihood of error is low, and/or the magnitude of the impact of an error is immaterial. The outputs or factors predictable enough, and therefore the likelihood that an error occurs is low. Third party models with detailed information and can be monitored regularly."
            }
        ]
    }
]
```

### Audit Logging

All risk assessment operations must create audit log entries:

| Entity Type | Actions Logged |
|-------------|----------------|
| `ModelRiskAssessment` | CREATE, UPDATE, DELETE |
| `QualitativeRiskFactor` | CREATE, UPDATE, DELETE (Admin only) |
| `QualitativeFactorGuidance` | CREATE, UPDATE, DELETE (Admin only) |

**Audit Log Fields for Risk Assessment**:
- `entity_type`: "ModelRiskAssessment"
- `entity_id`: assessment_id
- `action`: "CREATE" / "UPDATE" / "DELETE"
- `changes`: JSON diff of changed fields (including overrides)
- `user_id`: User who made the change
- `timestamp`: When change occurred

**Special Audit Cases**:
- When override is applied: Log includes `override_type` (quantitative/qualitative/final)
- When model tier synced: Log includes `model_tier_changed_from` and `model_tier_changed_to`

### Migration File
`api/alembic/versions/xxx_add_model_risk_assessment.py`

---

## Phase 2: Backend API

### New Files

| File | Purpose |
|------|---------|
| `api/app/models/risk_assessment.py` | SQLAlchemy models |
| `api/app/schemas/risk_assessment.py` | Pydantic schemas |
| `api/app/api/risk_assessment.py` | Assessment API endpoints |
| `api/app/api/qualitative_factors.py` | Factor configuration API (Admin) |
| `api/app/core/risk_calculation.py` | Business logic |

### API Endpoints

**Risk Assessments** (`/models/{model_id}/risk-assessments/`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| `GET` | `/` | List all assessments for model | Any user |
| `GET` | `/{assessment_id}` | Get specific assessment | Any user |
| `POST` | `/` | Create new assessment | Admin/Validator |
| `PUT` | `/{assessment_id}` | Full update of assessment | Admin/Validator |
| `DELETE` | `/{assessment_id}` | Delete assessment | Admin/Validator |

**Qualitative Factor Configuration** (`/risk-assessment/factors/`) - Admin Only

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List all factors (with guidance) |
| `GET` | `/{factor_id}` | Get specific factor with guidance |
| `POST` | `/` | Create new factor |
| `PUT` | `/{factor_id}` | Update factor (name, description, weight) |
| `PATCH` | `/{factor_id}/weight` | Update weight only |
| `DELETE` | `/{factor_id}` | Soft-delete (set is_active=false) |
| `POST` | `/{factor_id}/guidance` | Add rating guidance |
| `PUT` | `/guidance/{guidance_id}` | Update guidance text |
| `DELETE` | `/guidance/{guidance_id}` | Delete guidance |
| `POST` | `/validate-weights` | Validate weights sum to 1.0 |
| `POST` | `/reorder` | Reorder factors |

**Weight Validation Rules**:
- Weights must sum to exactly 1.0 (100%)
- Warning if weight changed affects existing assessments
- Cannot delete factor if used in existing assessments (soft-delete only)

### Business Logic (`risk_calculation.py`)

```python
# Rating scores are fixed (High=3, Medium=2, Low=1)
RATING_SCORES = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}

def calculate_qualitative_score(
    factor_assessments: List[QualitativeFactorAssessment],
    factors: List[QualitativeRiskFactor]  # From database
) -> tuple[float | None, str | None]:
    """
    Calculate weighted qualitative score using configurable factors.
    Uses weight_at_assessment (snapshot) for existing assessments,
    or current factor weights for new calculations.
    """
    rated = [fa for fa in factor_assessments if fa.rating]
    if not rated:
        return None, None

    # Use the weight snapshot stored at assessment time
    total = sum(
        fa.weight_at_assessment * RATING_SCORES[fa.rating]
        for fa in rated
    )

    # Level thresholds (could also be configurable in future)
    if total >= 2.1:
        return round(total, 2), 'HIGH'
    elif total >= 1.6:
        return round(total, 2), 'MEDIUM'
    else:
        return round(total, 2), 'LOW'

def get_active_factors(db: Session) -> List[QualitativeRiskFactor]:
    """Get all active factors ordered by sort_order."""
    return db.query(QualitativeRiskFactor).filter(
        QualitativeRiskFactor.is_active == True
    ).order_by(QualitativeRiskFactor.sort_order).all()

def validate_factor_weights(factors: List[QualitativeRiskFactor]) -> bool:
    """Validate that active factor weights sum to 1.0."""
    total = sum(f.weight for f in factors if f.is_active)
    return abs(total - 1.0) < 0.0001  # Allow small floating point tolerance

INHERENT_RISK_MATRIX = {
    ('HIGH', 'HIGH'): 'HIGH',
    ('HIGH', 'MEDIUM'): 'MEDIUM',
    ('HIGH', 'LOW'): 'LOW',
    ('MEDIUM', 'HIGH'): 'MEDIUM',
    ('MEDIUM', 'MEDIUM'): 'MEDIUM',
    ('MEDIUM', 'LOW'): 'LOW',
    ('LOW', 'HIGH'): 'LOW',
    ('LOW', 'MEDIUM'): 'LOW',
    ('LOW', 'LOW'): 'VERY_LOW',
}

def lookup_inherent_risk(quantitative: str, qualitative: str) -> str | None:
    """Matrix lookup for derived inherent risk tier."""
    return INHERENT_RISK_MATRIX.get((quantitative, qualitative))

TIER_MAPPING = {
    'HIGH': 'TIER_1',
    'MEDIUM': 'TIER_2',
    'LOW': 'TIER_3',
    'VERY_LOW': 'TIER_4'
}

def get_effective_values(assessment: ModelRiskAssessment) -> dict:
    """Calculate all effective values after applying overrides."""
    eff_quantitative = assessment.quantitative_override or assessment.quantitative_rating
    eff_qualitative = assessment.qualitative_override or assessment.qualitative_calculated_level

    derived = None
    if eff_quantitative and eff_qualitative:
        derived = lookup_inherent_risk(eff_quantitative, eff_qualitative)

    eff_final = assessment.derived_risk_tier_override or derived
    tier_code = TIER_MAPPING.get(eff_final) if eff_final else None

    return {
        'effective_quantitative': eff_quantitative,
        'effective_qualitative': eff_qualitative,
        'derived_risk_tier': derived,
        'effective_risk_tier': eff_final,
        'tier_code': tier_code
    }

def create_audit_log(
    db: Session,
    entity_type: str,
    entity_id: int,
    action: str,
    user_id: int,
    changes: dict
):
    """Create audit log entry for risk assessment changes."""
    from app.models.audit_log import AuditLog
    log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        changes=changes
    )
    db.add(log)
```

### Response Schema

```python
class QualitativeFactorResponse(BaseModel):
    factor_assessment_id: int
    factor_type: str
    factor_label: str  # Human-readable name
    rating: str | None
    comment: str | None
    weight: float
    score: float | None

class ModelRiskAssessmentResponse(BaseModel):
    assessment_id: int
    model_id: int
    region: RegionResponse | None  # null = Global

    # Qualitative
    qualitative_factors: List[QualitativeFactorResponse]
    qualitative_calculated_score: float | None
    qualitative_calculated_level: str | None
    qualitative_override: str | None
    qualitative_override_comment: str | None
    qualitative_effective_level: str | None

    # Quantitative
    quantitative_rating: str | None
    quantitative_comment: str | None
    quantitative_override: str | None
    quantitative_override_comment: str | None
    quantitative_effective_rating: str | None

    # Derived risk
    derived_risk_tier: str | None
    derived_risk_tier_override: str | None
    derived_risk_tier_override_comment: str | None
    derived_risk_tier_effective: str | None

    # Final
    final_tier: TaxonomyValueResponse | None

    # Metadata
    assessed_by: UserResponse | None
    assessed_at: datetime | None
    is_complete: bool

    created_at: datetime
    updated_at: datetime
```

---

## Phase 3: Frontend UI

### New Files

| File | Purpose |
|------|---------|
| `web/src/api/riskAssessment.ts` | API client functions |
| `web/src/api/qualitativeFactors.ts` | Factor config API client |
| `web/src/components/ModelRiskAssessmentTab.tsx` | Main tab container |
| `web/src/components/risk-assessment/QualitativeSection.tsx` | Factor inputs with guidance |
| `web/src/components/risk-assessment/QuantitativeSection.tsx` | Quantitative input |
| `web/src/components/risk-assessment/InherentRiskMatrix.tsx` | Visual matrix |
| `web/src/components/risk-assessment/OverrideInput.tsx` | Reusable override component |
| `web/src/components/risk-assessment/AssessmentSummary.tsx` | Final tier display |
| `web/src/components/risk-assessment/FactorGuidanceTooltip.tsx` | Shows guidance on hover |

**Admin Factor Configuration (in Taxonomy page)**:
| File | Purpose |
|------|---------|
| `web/src/components/QualitativeFactorConfig.tsx` | Factor management section |
| `web/src/components/FactorEditModal.tsx` | Edit factor name/weight/description |
| `web/src/components/GuidanceEditModal.tsx` | Edit rating guidance text |

### UI Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Risk Assessment                                                         │
│                                                                          │
│  Region: [Global ▼]  [+ Add Regional Assessment]                        │
│                                                                          │
│  ┌─ Qualitative Assessment ──────────────────────────────────────────┐  │
│  │                                                                    │  │
│  │  Factor                                    Weight  Rating  Comment │  │
│  │  ───────────────────────────────────────────────────────────────  │  │
│  │  Reputation/Legal/Regulatory/Financial     30%    [High▼]   [📝]  │  │
│  │  Model Complexity                          30%    [Med ▼]   [📝]  │  │
│  │  Model Usage & Dependency                  20%    [Low ▼]   [📝]  │  │
│  │  Stability                                 20%    [High▼]   [📝]  │  │
│  │  ───────────────────────────────────────────────────────────────  │  │
│  │  Calculated: 2.30 → HIGH                                          │  │
│  │                                                                    │  │
│  │  □ Override: [____▼]  Comment: [_________________________]        │  │
│  │  Effective: HIGH                                                   │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌─ Quantitative Assessment ─────────────────────────────────────────┐  │
│  │  Rating: [High ▼]   Comment: [_________________________]          │  │
│  │  □ Override: [____▼]  Comment: [_________________________]        │  │
│  │  Effective: HIGH                                                   │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌─ Inherent Risk Matrix ────────────────────────────────────────────┐  │
│  │           │  High   │ Medium  │  Low    │                         │  │
│  │  High     │ [HIGH]  │ Medium  │  Low    │  ← Current position     │  │
│  │  Medium   │ Medium  │ Medium  │  Low    │                         │  │
│  │  Low      │  Low    │  Low    │Very Low │                         │  │
│  │                                                                    │  │
│  │  Derived: HIGH                                                     │  │
│  │  □ Override: [____▼]  Comment: [_________________________]        │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ╔════════════════════════════════════════════════════════════════════╗  │
│  ║  FINAL MODEL TIER: Tier 1 (High)                                   ║  │
│  ╚════════════════════════════════════════════════════════════════════╝  │
│                                                                          │
│  Last assessed by John Smith on 2025-11-30                               │
│                                                                          │
│  [Save Assessment]  [Delete Assessment]                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Model Details Page Changes

1. Add "Risk Assessment" tab to `ModelDetailPage.tsx`
2. When assessment exists with a `final_tier_id`:
   - Show `risk_tier_id` field as read-only with note: "Derived from Risk Assessment"
   - Link to Risk Assessment tab
3. When no assessment exists:
   - Keep `risk_tier_id` editable as normal

### Admin Factor Configuration UI (Taxonomy Page)

Add new "Risk Factors" tab to Taxonomy page (Admin only):

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Taxonomy Configuration                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  [General] [Change Type] [Model Type] [KPM] [Risk Factors] [Priority]   │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  Qualitative Risk Factors                                                │
│                                                                          │
│  Total Weight: 100% ✓  (must sum to 100%)                               │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ # │ Factor Name                                    │ Weight │ Action ││
│  ├───┼────────────────────────────────────────────────┼────────┼────────┤│
│  │ 1 │ Reputation/Legal/Regulatory/Financial Risk     │  30%   │ [Edit] ││
│  │ 2 │ Complexity of the Model                        │  30%   │ [Edit] ││
│  │ 3 │ Model Usage and Model Dependency               │  20%   │ [Edit] ││
│  │ 4 │ Stability of the Model                         │  20%   │ [Edit] ││
│  └───┴────────────────────────────────────────────────┴────────┴────────┘│
│                                                                          │
│  [+ Add Factor]  [Reorder]  [Validate Weights]                          │
│                                                                          │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                          │
│  Selected Factor: Reputation/Legal/Regulatory/Financial Risk             │
│                                                                          │
│  Description:                                                            │
│  [Reputation Risk is defined as the risk of negative publicity...]      │
│                                                                          │
│  Rating Guidance:                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ Rating │ Points │ Guidance                                │ Action  ││
│  ├────────┼────────┼─────────────────────────────────────────┼─────────┤│
│  │ HIGH   │   3    │ Failure could significantly impact...   │ [Edit]  ││
│  │ MEDIUM │   2    │ Misuse could impact with moderate...    │ [Edit]  ││
│  │ LOW    │   1    │ Limited impact on reputation...         │ [Edit]  ││
│  └────────┴────────┴─────────────────────────────────────────┴─────────┘│
│                                                                          │
│  [+ Add Guidance]                                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

**Factor Edit Modal**:
- Edit name, description, weight (0-100%)
- Weight validation warning if total ≠ 100%
- Cannot change if assessments exist using this factor (show warning)

**Guidance Edit Modal**:
- Edit rating level (HIGH/MEDIUM/LOW)
- Edit points (typically 3/2/1)
- Edit description text (rich text editor)

---

## Phase 4: Model Tier Synchronization

When saving an assessment:

1. Calculate all effective values
2. Derive final tier from matrix
3. Look up `taxonomy_value_id` for the tier code (e.g., TIER_1)
4. Update `assessment.final_tier_id`
5. **Update `model.risk_tier_id`** to match (for Global assessment only)
6. Create audit log entry

**Note**: Only the Global assessment updates the model's `risk_tier_id`. Regional assessments are informational.

---

## Implementation Order (TDD Approach)

Following Test-Driven Development: **Red → Green → Refactor**

### Step 1: Database & Models Setup
1. Create migration with new tables
2. Create SQLAlchemy models (minimal, just structure)

### Step 2: Risk Calculation Logic (TDD)

**2a. Write tests FIRST** (`api/tests/test_risk_calculation.py`):
```python
# Test: calculate_qualitative_score
def test_qualitative_score_all_high():
    """All HIGH ratings should yield score 3.0 and level HIGH"""

def test_qualitative_score_all_low():
    """All LOW ratings should yield score 1.0 and level LOW"""

def test_qualitative_score_mixed_yields_medium():
    """Mixed ratings yielding 1.6-2.1 should be MEDIUM"""

def test_qualitative_score_boundary_2_1():
    """Score exactly 2.1 should be HIGH"""

def test_qualitative_score_boundary_1_6():
    """Score exactly 1.6 should be MEDIUM"""

def test_qualitative_score_partial_factors():
    """Partial factors should still calculate (for incomplete assessments)"""

def test_qualitative_score_no_factors():
    """No rated factors should return None, None"""

# Test: lookup_inherent_risk (all 9 matrix combinations)
def test_matrix_high_high():
    assert lookup_inherent_risk('HIGH', 'HIGH') == 'HIGH'

def test_matrix_high_medium():
    assert lookup_inherent_risk('HIGH', 'MEDIUM') == 'MEDIUM'

# ... (all 9 combinations)

def test_matrix_low_low():
    assert lookup_inherent_risk('LOW', 'LOW') == 'VERY_LOW'

# Test: get_effective_values with overrides
def test_effective_values_no_overrides():
    """Without overrides, effective = calculated"""

def test_effective_values_quantitative_override():
    """Quantitative override should replace quantitative rating"""

def test_effective_values_qualitative_override():
    """Qualitative override should replace calculated level"""

def test_effective_values_final_override():
    """Final override should replace derived tier"""

def test_effective_values_all_overrides():
    """All three overrides applied together"""

# Test: tier mapping
def test_tier_mapping_high():
    assert map_to_tier_code('HIGH') == 'TIER_1'

def test_tier_mapping_very_low():
    assert map_to_tier_code('VERY_LOW') == 'TIER_4'
```

**2b. Run tests** → All RED (failing)

**2c. Implement** `api/app/core/risk_calculation.py` → All GREEN

**2d. Refactor** if needed

### Step 3: API Endpoints (TDD)

**3a. Write tests FIRST** (`api/tests/test_risk_assessment_api.py`):
```python
# Test: GET /models/{id}/risk-assessments/
def test_list_assessments_empty():
    """Model with no assessments returns empty list"""

def test_list_assessments_with_global():
    """Returns global assessment"""

def test_list_assessments_with_regional():
    """Returns global and regional assessments"""

# Test: POST /models/{id}/risk-assessments/
def test_create_global_assessment():
    """Create assessment with region_id=null"""

def test_create_regional_assessment():
    """Create assessment with specific region_id"""

def test_create_duplicate_global_fails():
    """Cannot create second global assessment for same model"""

def test_create_partial_assessment():
    """Can save with only some factors rated"""

def test_create_assessment_calculates_score():
    """Creating assessment auto-calculates qualitative score"""

# Test: PUT /models/{id}/risk-assessments/{id}
def test_update_assessment_recalculates():
    """Updating factors recalculates score and derived tier"""

def test_update_with_override():
    """Can add override to existing assessment"""

def test_update_global_syncs_model_tier():
    """Updating global assessment updates model.risk_tier_id"""

# Test: DELETE /models/{id}/risk-assessments/{id}
def test_delete_assessment():
    """Can delete assessment"""

def test_delete_global_clears_model_tier():
    """Deleting global assessment clears model.risk_tier_id (or leaves editable)"""

# Test: Permissions
def test_create_assessment_requires_admin_or_validator():
    """Regular user cannot create assessment"""

def test_update_assessment_requires_admin_or_validator():
    """Regular user cannot update assessment"""

def test_read_assessment_any_user():
    """Any authenticated user can read assessments"""
```

**3b. Run tests** → All RED

**3c. Implement** `api/app/api/risk_assessment.py` → All GREEN

**3d. Refactor** if needed

### Step 4: Factor Configuration API (TDD) - Admin Only

**4a. Write tests FIRST** (`api/tests/test_qualitative_factors_api.py`):
```python
# Test: GET /risk-assessment/factors/
def test_list_factors_returns_seeded_factors():
    """Returns 4 default factors with guidance"""

def test_list_factors_includes_guidance():
    """Each factor includes HIGH/MEDIUM/LOW guidance"""

# Test: POST /risk-assessment/factors/
def test_create_factor_admin_only():
    """Only admin can create factors"""

def test_create_factor_with_guidance():
    """Can create factor with initial guidance"""

def test_create_factor_validates_weight():
    """Weight must be between 0 and 1"""

# Test: PUT /risk-assessment/factors/{id}
def test_update_factor_name():
    """Can update factor name and description"""

def test_update_factor_weight():
    """Can update factor weight"""

def test_update_factor_creates_audit_log():
    """Factor update creates audit log entry"""

# Test: DELETE /risk-assessment/factors/{id}
def test_delete_factor_soft_deletes():
    """Delete sets is_active=false, not hard delete"""

def test_delete_factor_in_use_fails():
    """Cannot delete factor used in existing assessments"""

# Test: Weight validation
def test_validate_weights_pass():
    """Weights summing to 1.0 passes validation"""

def test_validate_weights_fail():
    """Weights not summing to 1.0 fails validation"""

# Test: Guidance management
def test_add_guidance_to_factor():
    """Can add guidance for a rating level"""

def test_update_guidance_text():
    """Can update guidance description"""

def test_guidance_requires_unique_rating():
    """Cannot have duplicate rating guidance for same factor"""
```

**4b. Run tests** → RED

**4c. Implement** `api/app/api/qualitative_factors.py` → GREEN

### Step 5: Model Tier Sync & Audit Logging (TDD)

**5a. Write tests FIRST**:
```python
# Model Tier Sync
def test_global_assessment_updates_model_tier():
    """When global assessment saved, model.risk_tier_id updates"""

def test_regional_assessment_does_not_update_model_tier():
    """Regional assessment does not change model.risk_tier_id"""

def test_model_tier_readonly_when_assessment_exists():
    """Cannot directly edit model.risk_tier_id when global assessment exists"""

def test_model_tier_editable_when_no_assessment():
    """Can edit model.risk_tier_id when no global assessment"""

# Audit Logging
def test_create_assessment_creates_audit_log():
    """Creating assessment logs to audit trail"""

def test_update_assessment_creates_audit_log():
    """Updating assessment logs changes to audit trail"""

def test_delete_assessment_creates_audit_log():
    """Deleting assessment logs to audit trail"""

def test_override_logged_with_type():
    """Override changes include override_type in audit log"""

def test_model_tier_sync_logged():
    """Model tier change logged with before/after values"""

def test_factor_config_change_creates_audit_log():
    """Factor configuration changes are logged"""
```

**5b. Run tests** → RED

**5c. Implement sync and audit logic** → GREEN

### Step 6: Frontend (Component Testing)

**6a. Write component tests FIRST** (`web/src/components/__tests__/`):
```typescript
// QualitativeSection.test.tsx
describe('QualitativeSection', () => {
  it('displays all 4 factors with correct weights', () => {})
  it('calculates score when all factors selected', () => {})
  it('shows calculated level based on score', () => {})
  it('enables override input when checkbox checked', () => {})
  it('shows effective level with override applied', () => {})
})

// QuantitativeSection.test.tsx
describe('QuantitativeSection', () => {
  it('allows selecting HIGH/MEDIUM/LOW', () => {})
  it('shows override controls', () => {})
  it('displays effective rating', () => {})
})

// InherentRiskMatrix.test.tsx
describe('InherentRiskMatrix', () => {
  it('highlights correct cell based on inputs', () => {})
  it('shows derived tier', () => {})
  it('allows final override', () => {})
})

// ModelRiskAssessmentTab.test.tsx
describe('ModelRiskAssessmentTab', () => {
  it('loads existing assessment on mount', () => {})
  it('allows switching between regions', () => {})
  it('saves assessment on button click', () => {})
  it('shows final tier prominently', () => {})
})
```

**6b. Run tests** → RED

**6c. Implement components** → GREEN

**6d. Refactor** and style

### Step 7: Integration Testing

**7a. Write E2E-style integration tests**:
```python
def test_full_assessment_workflow():
    """
    1. Create model without assessment
    2. Verify risk_tier_id is editable
    3. Create global assessment with all factors
    4. Verify calculated score and derived tier
    5. Verify model.risk_tier_id updated
    6. Verify risk_tier_id now read-only
    7. Add override
    8. Verify final tier changes
    9. Delete assessment
    10. Verify risk_tier_id editable again
    """
```

---

## Detailed Test Specifications

### Backend Unit Tests (`api/tests/test_risk_calculation.py`)

| Test | Input | Expected Output |
|------|-------|-----------------|
| `test_qualitative_all_high` | All 4 factors = HIGH | score=3.0, level=HIGH |
| `test_qualitative_all_medium` | All 4 factors = MEDIUM | score=2.0, level=MEDIUM |
| `test_qualitative_all_low` | All 4 factors = LOW | score=1.0, level=LOW |
| `test_qualitative_mixed_high` | REP=H, COMP=H, USE=M, STAB=M | score=2.4, level=HIGH |
| `test_qualitative_mixed_medium` | REP=M, COMP=M, USE=L, STAB=L | score=1.6, level=MEDIUM |
| `test_qualitative_mixed_low` | REP=L, COMP=M, USE=L, STAB=L | score=1.3, level=LOW |
| `test_qualitative_boundary_high` | Score exactly 2.1 | level=HIGH |
| `test_qualitative_boundary_medium` | Score exactly 1.6 | level=MEDIUM |
| `test_qualitative_partial` | Only 2 factors rated | Calculates with available |
| `test_qualitative_empty` | No factors rated | None, None |

### Backend API Tests (`api/tests/test_risk_assessment_api.py`)

| Test | Action | Expected |
|------|--------|----------|
| `test_list_empty` | GET with no assessments | `[]` |
| `test_create_global` | POST with region_id=null | 201, assessment created |
| `test_create_regional` | POST with region_id=1 | 201, assessment created |
| `test_create_duplicate` | POST second global | 409 Conflict |
| `test_create_partial` | POST with 2 factors | 201, partial saved |
| `test_update_recalculates` | PUT with new factors | Score recalculated |
| `test_delete` | DELETE | 204, assessment removed |
| `test_permission_user` | POST as regular user | 403 Forbidden |
| `test_permission_validator` | POST as validator | 201 Created |
| `test_permission_admin` | POST as admin | 201 Created |

### Backend Factor Configuration Tests (`api/tests/test_qualitative_factors_api.py`)

| Test | Action | Expected |
|------|--------|----------|
| `test_list_factors` | GET /risk-assessment/factors/ | Returns 4 seeded factors |
| `test_list_includes_guidance` | GET /risk-assessment/factors/ | Each factor has 3 guidance entries |
| `test_create_factor_admin` | POST as admin | 201, factor created |
| `test_create_factor_non_admin` | POST as validator | 403 Forbidden |
| `test_update_factor_weight` | PUT weight=0.25 | 200, weight updated |
| `test_validate_weights_sum` | POST /validate-weights | 200 if sum=1.0, 400 otherwise |
| `test_soft_delete` | DELETE factor | is_active=false, still queryable |
| `test_delete_in_use` | DELETE used factor | 409 Conflict |
| `test_add_guidance` | POST guidance | 201, guidance added |
| `test_duplicate_guidance` | POST duplicate rating | 409 Conflict |

### Backend Audit Logging Tests (`api/tests/test_risk_assessment_audit.py`)

| Test | Action | Expected Audit Log |
|------|--------|-------------------|
| `test_create_audit` | Create assessment | entity_type=ModelRiskAssessment, action=CREATE |
| `test_update_audit` | Update assessment | action=UPDATE, changes include diff |
| `test_delete_audit` | Delete assessment | action=DELETE |
| `test_override_audit` | Add override | changes includes override_type |
| `test_tier_sync_audit` | Save triggers tier sync | changes includes model_tier_changed_from/to |
| `test_factor_create_audit` | Create factor | entity_type=QualitativeRiskFactor, action=CREATE |
| `test_factor_update_audit` | Update factor | action=UPDATE, changes show weight change |
| `test_guidance_update_audit` | Update guidance | entity_type=QualitativeFactorGuidance |

### Frontend Component Tests

| Component | Test | Behavior |
|-----------|------|----------|
| QualitativeSection | renders factors | Shows factors from API with weights |
| QualitativeSection | shows guidance | Displays guidance text on hover/click |
| QualitativeSection | calculates score | Updates on factor change |
| QualitativeSection | override toggle | Enables override dropdown |
| QuantitativeSection | rating select | Allows H/M/L selection |
| InherentRiskMatrix | cell highlight | Highlights based on inputs |
| InherentRiskMatrix | derived display | Shows derived tier text |
| ModelRiskAssessmentTab | region switch | Loads different assessment |
| ModelRiskAssessmentTab | save button | Calls API and shows success |
