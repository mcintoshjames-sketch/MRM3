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
    qualitative_calculated_score DECIMAL(3,2),  -- e.g., 2.30
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
    factor_type VARCHAR(20) NOT NULL,  -- REPUTATION_LEGAL/COMPLEXITY/USAGE_DEPENDENCY/STABILITY
    rating VARCHAR(10),  -- HIGH/MEDIUM/LOW (nullable for partial saves)
    comment TEXT,
    weight DECIMAL(3,2) NOT NULL,  -- 0.30, 0.30, 0.20, 0.20
    score DECIMAL(3,2),  -- 3.00, 2.00, 1.00 (calculated from rating)

    UNIQUE(assessment_id, factor_type)
);
```

### Migration File
`api/alembic/versions/xxx_add_model_risk_assessment.py`

---

## Phase 2: Backend API

### New Files

| File | Purpose |
|------|---------|
| `api/app/models/risk_assessment.py` | SQLAlchemy models |
| `api/app/schemas/risk_assessment.py` | Pydantic schemas |
| `api/app/api/risk_assessment.py` | API endpoints |
| `api/app/core/risk_calculation.py` | Business logic |

### API Endpoints

**Base path**: `/models/{model_id}/risk-assessments/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List all assessments for model (global + regional) |
| `GET` | `/{assessment_id}` | Get specific assessment |
| `POST` | `/` | Create new assessment (specify region_id or null for global) |
| `PUT` | `/{assessment_id}` | Full update of assessment |
| `DELETE` | `/{assessment_id}` | Delete assessment |

### Business Logic (`risk_calculation.py`)

```python
FACTOR_WEIGHTS = {
    'REPUTATION_LEGAL': 0.30,
    'COMPLEXITY': 0.30,
    'USAGE_DEPENDENCY': 0.20,
    'STABILITY': 0.20
}

RATING_SCORES = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}

def calculate_qualitative_score(factors: List[QualitativeFactorAssessment]) -> tuple[float | None, str | None]:
    """Calculate weighted qualitative score and map to level."""
    rated_factors = [f for f in factors if f.rating]
    if not rated_factors:
        return None, None

    total = sum(FACTOR_WEIGHTS[f.factor_type] * RATING_SCORES[f.rating] for f in rated_factors)

    if total >= 2.1:
        return total, 'HIGH'
    elif total >= 1.6:
        return total, 'MEDIUM'
    else:
        return total, 'LOW'

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
    # Effective quantitative
    eff_quantitative = assessment.quantitative_override or assessment.quantitative_rating

    # Effective qualitative
    eff_qualitative = assessment.qualitative_override or assessment.qualitative_calculated_level

    # Derived risk (before override)
    derived = None
    if eff_quantitative and eff_qualitative:
        derived = lookup_inherent_risk(eff_quantitative, eff_qualitative)

    # Effective final risk
    eff_final = assessment.derived_risk_tier_override or derived

    # Map to tier code
    tier_code = TIER_MAPPING.get(eff_final) if eff_final else None

    return {
        'effective_quantitative': eff_quantitative,
        'effective_qualitative': eff_qualitative,
        'derived_risk_tier': derived,
        'effective_risk_tier': eff_final,
        'tier_code': tier_code
    }
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
| `web/src/components/ModelRiskAssessmentTab.tsx` | Main tab container |
| `web/src/components/risk-assessment/QualitativeSection.tsx` | Factor inputs |
| `web/src/components/risk-assessment/QuantitativeSection.tsx` | Quantitative input |
| `web/src/components/risk-assessment/InherentRiskMatrix.tsx` | Visual matrix |
| `web/src/components/risk-assessment/OverrideInput.tsx` | Reusable override component |
| `web/src/components/risk-assessment/AssessmentSummary.tsx` | Final tier display |

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

## Implementation Order

1. **Database**: Create migration with new tables
2. **Backend Models**: Create SQLAlchemy models
3. **Backend Logic**: Create risk calculation service
4. **Backend API**: Create endpoints with tests
5. **Frontend API**: Create API client
6. **Frontend Components**: Build UI components
7. **Integration**: Wire up tab and model tier sync
8. **Testing**: End-to-end testing

---

## Test Cases

### Backend Tests
- Calculate qualitative score with all factors
- Calculate qualitative score with partial factors
- Matrix lookup for all 9 combinations
- Override application at each level
- Tier mapping
- API CRUD operations
- Permission checks (Admin/Validator only)

### Frontend Tests
- Factor input changes update calculated score
- Override checkbox enables/disables override fields
- Matrix highlights correct cell
- Save with partial data
- Regional assessment switching
