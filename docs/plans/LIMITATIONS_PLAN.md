# Model Limitations Tracking - Implementation Plan

## Overview

Model limitations are inherent constraints, weaknesses, or boundaries of a model that users and stakeholders need to be aware of. This feature introduces comprehensive tracking of limitations discovered during validation reviews, with classification, impact assessment, and conclusion tracking.

## Requirements Summary

### Core Attributes per Limitation
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Model | FK | Yes | The model this limitation applies to |
| Originating Validation | FK | No | The validation request that discovered this limitation |
| Originating Model Version | FK | No | The model version under review when discovered |
| Significance | Enum | Yes | Critical or Non-Critical |
| Category | FK (Taxonomy) | Yes | Data, Implementation, Methodology, Model Output, Other |
| Description | Text | Yes | Narrative description of the limitation |
| Impact Assessment | Text | Yes | Narrative assessment of the limitation's impact |
| Conclusion | Enum | Yes | Mitigate or Accept |
| Conclusion Rationale | Text | Yes | Explanation for the mitigate/accept decision |
| User Awareness Description | Text | Conditional | How users are made aware (required if Critical) |
| Linked Recommendation | FK | No | Optional link to a recommendation for mitigation |

### Lifecycle
- **Creation**: Validators or Admin can create limitations
- **Updates**: Validators or Admin can edit limitations
- **Retirement**: Validators or Admin can retire limitations with commentary
- **No workflow states**: Limitations are immediately active upon creation
- **Accept approval**: Implicitly approved as part of the validation approval

### Access Control
- **Create/Edit/Retire**: Validators and Admin only
- **View**: All authenticated users

---

## Database Schema

### New Table: `model_limitation`

```sql
CREATE TABLE model_limitation (
    limitation_id SERIAL PRIMARY KEY,

    -- Relationships
    model_id INTEGER NOT NULL REFERENCES models(model_id),
    validation_request_id INTEGER REFERENCES validation_requests(request_id),
    model_version_id INTEGER REFERENCES model_versions(version_id),
    recommendation_id INTEGER REFERENCES recommendations(recommendation_id),

    -- Classification
    significance VARCHAR(20) NOT NULL CHECK (significance IN ('Critical', 'Non-Critical')),
    category_id INTEGER NOT NULL REFERENCES taxonomy_values(value_id),

    -- Narratives
    description TEXT NOT NULL,
    impact_assessment TEXT NOT NULL,
    conclusion VARCHAR(20) NOT NULL CHECK (conclusion IN ('Mitigate', 'Accept')),
    conclusion_rationale TEXT NOT NULL,
    user_awareness_description TEXT,  -- Required if significance = 'Critical'

    -- Retirement
    is_retired BOOLEAN NOT NULL DEFAULT FALSE,
    retirement_date TIMESTAMP,
    retirement_reason TEXT,
    retired_by_id INTEGER REFERENCES users(user_id),

    -- Audit
    created_by_id INTEGER NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_critical_awareness CHECK (
        significance != 'Critical' OR user_awareness_description IS NOT NULL
    ),
    CONSTRAINT chk_retirement_fields CHECK (
        (is_retired = FALSE AND retirement_date IS NULL AND retirement_reason IS NULL AND retired_by_id IS NULL)
        OR
        (is_retired = TRUE AND retirement_date IS NOT NULL AND retirement_reason IS NOT NULL AND retired_by_id IS NOT NULL)
    )
);

CREATE INDEX idx_limitation_model ON model_limitation(model_id);
CREATE INDEX idx_limitation_validation ON model_limitation(validation_request_id);
CREATE INDEX idx_limitation_significance ON model_limitation(significance);
CREATE INDEX idx_limitation_category ON model_limitation(category_id);
CREATE INDEX idx_limitation_retired ON model_limitation(is_retired);
```

### New Taxonomy: Limitation Category

Seed data for `taxonomy` and `taxonomy_values`:

```sql
-- Taxonomy
INSERT INTO taxonomies (taxonomy_name, description, is_system)
VALUES ('Limitation Category', 'Classification of model limitation types', TRUE);

-- Values (assuming taxonomy_id is assigned)
INSERT INTO taxonomy_values (taxonomy_id, code, label, description, sort_order, is_active)
VALUES
    ({id}, 'DATA', 'Data', 'Limitations related to data quality, availability, or representativeness', 1, TRUE),
    ({id}, 'IMPLEMENTATION', 'Implementation', 'Limitations in model implementation or technical constraints', 2, TRUE),
    ({id}, 'METHODOLOGY', 'Methodology', 'Limitations in modeling approach or theoretical foundation', 3, TRUE),
    ({id}, 'MODEL_OUTPUT', 'Model Output', 'Limitations in model outputs or their interpretation', 4, TRUE),
    ({id}, 'OTHER', 'Other', 'Other limitations not covered by above categories', 5, TRUE);
```

---

## API Design

### Endpoints

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| GET | `/models/{model_id}/limitations` | List limitations for a model | All users |
| POST | `/models/{model_id}/limitations` | Create a limitation | Validator, Admin |
| GET | `/limitations/{limitation_id}` | Get limitation details | All users |
| PATCH | `/limitations/{limitation_id}` | Update a limitation | Validator, Admin |
| POST | `/limitations/{limitation_id}/retire` | Retire a limitation | Validator, Admin |
| GET | `/reports/critical-limitations` | Critical limitations report | All users |

### Request/Response Schemas

#### Create Limitation Request
```json
{
    "validation_request_id": 123,        // Optional
    "model_version_id": 45,              // Optional
    "significance": "Critical",          // Required: "Critical" | "Non-Critical"
    "category_id": 201,                  // Required: Taxonomy value ID
    "description": "Model assumes...",   // Required
    "impact_assessment": "This may...",  // Required
    "conclusion": "Mitigate",            // Required: "Mitigate" | "Accept"
    "conclusion_rationale": "Given...",  // Required
    "user_awareness_description": "...", // Required if Critical
    "recommendation_id": 567             // Optional
}
```

#### Limitation Response
```json
{
    "limitation_id": 1,
    "model_id": 42,
    "model": {
        "model_id": 42,
        "model_name": "Credit Risk Model A"
    },
    "validation_request_id": 123,
    "validation_request": {
        "request_id": 123,
        "request_name": "Annual Validation 2025"
    },
    "model_version_id": 45,
    "model_version": {
        "version_id": 45,
        "version_number": "2.1.0"
    },
    "significance": "Critical",
    "category_id": 201,
    "category": {
        "value_id": 201,
        "code": "DATA",
        "label": "Data"
    },
    "description": "Model assumes normal distribution...",
    "impact_assessment": "During market stress...",
    "conclusion": "Accept",
    "conclusion_rationale": "The limitation is documented...",
    "user_awareness_description": "Users are notified via...",
    "recommendation_id": null,
    "recommendation": null,
    "is_retired": false,
    "retirement_date": null,
    "retirement_reason": null,
    "retired_by": null,
    "created_by": {
        "user_id": 5,
        "full_name": "Jane Validator"
    },
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
}
```

#### Retire Request
```json
{
    "retirement_reason": "Limitation addressed in model version 3.0"
}
```

#### Critical Limitations Report Response
```json
{
    "filters_applied": {
        "region_id": 5
    },
    "total_count": 12,
    "items": [
        {
            "limitation_id": 1,
            "model_id": 42,
            "model_name": "Credit Risk Model A",
            "region_name": "North America",
            "category_label": "Data",
            "description": "Model assumes...",
            "impact_assessment": "During market stress...",
            "conclusion": "Accept",
            "conclusion_rationale": "...",
            "user_awareness_description": "Users notified via...",
            "originating_validation": "Annual Validation 2025",
            "created_at": "2025-01-15T10:30:00Z"
        }
    ]
}
```

---

## Frontend Design

### Model Details Page - Limitations Tab

New tab on `/models/{id}` page showing:

1. **Summary Cards**
   - Total Limitations (active)
   - Critical Limitations count
   - Non-Critical Limitations count

2. **Limitations Table**
   | Column | Description |
   |--------|-------------|
   | Category | Limitation category (from taxonomy) |
   | Significance | Critical/Non-Critical badge |
   | Description | Truncated with tooltip for full text |
   | Conclusion | Mitigate/Accept badge |
   | Originating Validation | Link to validation request |
   | Created | Date created |
   | Actions | View, Edit, Retire (Validator/Admin) |

3. **Filters**
   - Significance (Critical/Non-Critical/All)
   - Category (multi-select from taxonomy)
   - Conclusion (Mitigate/Accept/All)
   - Include Retired (checkbox)

4. **Actions**
   - "Add Limitation" button (Validator/Admin only)
   - CSV Export

### Limitation Create/Edit Modal

Form fields:
- **Originating Validation** (optional dropdown of model's validations)
- **Model Version** (optional dropdown of model's versions)
- **Significance** (radio: Critical / Non-Critical)
- **Category** (dropdown from taxonomy)
- **Description** (textarea, required)
- **Impact Assessment** (textarea, required)
- **Conclusion** (radio: Mitigate / Accept)
- **Conclusion Rationale** (textarea, required)
- **User Awareness Description** (textarea, conditionally required if Critical)
- **Linked Recommendation** (optional dropdown/search)

### Retire Limitation Modal

- Display limitation summary (read-only)
- **Retirement Reason** (textarea, required)
- Confirm/Cancel buttons

### Validation Request Detail Page

Add "Limitations" section showing limitations that originated from this validation:
- Read-only list with links to model limitation detail
- "Add Limitation" button to create limitation linked to this validation

### Reports Page - Critical Limitations Report

New report in `/reports` gallery:
- **Path**: `/reports/critical-limitations`
- **Filters**: Region (dropdown)
- **Table Columns**: Model Name, Region, Category, Description, Impact, Conclusion, User Awareness, Origin Validation, Created Date
- **Export**: CSV

---

## Implementation Phases

### Phase 1: Database & Backend Foundation
**Estimated: Core schema and CRUD APIs**

1. Create Alembic migration for `model_limitation` table
2. Add "Limitation Category" taxonomy to seed data
3. Create SQLAlchemy model: `ModelLimitation`
4. Create Pydantic schemas: `LimitationCreate`, `LimitationUpdate`, `LimitationResponse`, `LimitationRetire`
5. Implement API endpoints:
   - `GET /models/{model_id}/limitations`
   - `POST /models/{model_id}/limitations`
   - `GET /limitations/{limitation_id}`
   - `PATCH /limitations/{limitation_id}`
   - `POST /limitations/{limitation_id}/retire`
6. Add audit logging for limitation CRUD operations
7. Write pytest tests for all endpoints

### Phase 2: Frontend - Model Limitations Tab
**Estimated: UI for viewing and managing limitations**

1. Create `LimitationsTab` component for Model Details page
2. Create `LimitationModal` for create/edit
3. Create `RetireLimitationModal` for retirement
4. Add API client functions in `web/src/api/limitations.ts`
5. Integrate tab into `ModelDetailsPage`
6. Implement table sorting and filtering
7. Add CSV export functionality
8. Write frontend tests

### Phase 3: Validation Integration
**Estimated: Link limitations to validations**

1. Add "Limitations" section to `ValidationRequestDetailPage`
2. Enable creating limitations from validation context
3. Show limitation count on validation request list

### Phase 4: Critical Limitations Report
**Estimated: Report page**

1. Implement `GET /reports/critical-limitations` endpoint
2. Create `CriticalLimitationsReportPage` component
3. Add to Reports gallery
4. Implement region filter
5. Add CSV export

### Phase 5: Testing & Documentation
**Estimated: Comprehensive testing**

1. End-to-end testing
2. Update ARCHITECTURE.md
3. Update CLAUDE.md with limitations section
4. Regression testing

---

## File Changes Summary

### New Files
| File | Description |
|------|-------------|
| `api/alembic/versions/xxx_add_model_limitations.py` | Migration |
| `api/app/models/limitation.py` | SQLAlchemy model |
| `api/app/schemas/limitation.py` | Pydantic schemas |
| `api/app/api/limitations.py` | API routes |
| `api/tests/test_limitations.py` | Backend tests |
| `web/src/api/limitations.ts` | API client |
| `web/src/components/LimitationsTab.tsx` | Limitations tab |
| `web/src/components/LimitationModal.tsx` | Create/Edit modal |
| `web/src/components/RetireLimitationModal.tsx` | Retire modal |
| `web/src/pages/CriticalLimitationsReportPage.tsx` | Report page |

### Modified Files
| File | Changes |
|------|---------|
| `api/app/models/__init__.py` | Export ModelLimitation |
| `api/app/main.py` | Register limitations router |
| `api/app/seed.py` | Add Limitation Category taxonomy |
| `web/src/pages/ModelDetailsPage.tsx` | Add Limitations tab |
| `web/src/pages/ValidationWorkflowDetailPage.tsx` | Add Limitations section |
| `web/src/pages/ReportsPage.tsx` | Add Critical Limitations report |
| `web/src/App.tsx` | Add report route |

---

## Open Questions / Future Considerations

1. **Limitation Templates**: Pre-defined limitation templates for common issues?
2. **Bulk Operations**: Import/export limitations in bulk?
3. **Limitation History**: Track changes to limitation fields over time (beyond audit log)?
4. **Cross-Model Limitations**: Limitations that apply to multiple related models?
5. **Periodic Reviews**: Future phase for mandatory review cycles on accepted limitations
6. **Notifications**: Alert model owners when critical limitations are added?

---

## Approval

- [ ] Requirements confirmed
- [ ] Schema design approved
- [ ] API design approved
- [ ] UI mockups approved
- [ ] Implementation phases approved
