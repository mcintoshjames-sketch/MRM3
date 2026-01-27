# MRSA and IRP Feature Implementation Plan

## Overview

Add Model Risk-Sensitive Application (MRSA) classification and Independent Review Process (IRP) management features to the existing MRM system.

## Key Design Decisions

| Decision | Choice |
|----------|--------|
| MRSA Storage | Use existing `Model` table with `is_model=false`, `is_mrsa=true` |
| MRSA Risk Level | Taxonomy-configurable (seed High-Risk, Low-Risk) |
| IRP-to-MRSA | Many-to-many (one IRP covers multiple MRSAs) |
| IRP Contact | Single user only |
| IRP Requirement | Controlled by `requires_irp` flag on MRSA Risk Level taxonomy values |
| UI Location | Sub-section under Models page + separate IRP management page |

---

## Phase 1: Database Schema

### 1.1 Add `requires_irp` to TaxonomyValue

**File:** `api/app/models/taxonomy.py`

```python
requires_irp: Mapped[Optional[bool]] = mapped_column(
    Boolean, nullable=True,
    comment="For MRSA Risk Level taxonomy: True if this risk level requires IRP"
)
```

### 1.2 Add MRSA fields to Model

**File:** `api/app/models/model.py`

```python
is_mrsa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
mrsa_risk_level_id: Mapped[Optional[int]] = mapped_column(
    Integer, ForeignKey("taxonomy_values.value_id", ondelete="SET NULL"), nullable=True
)
mrsa_risk_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

# Relationship
mrsa_risk_level: Mapped[Optional["TaxonomyValue"]] = relationship(
    "TaxonomyValue", foreign_keys=[mrsa_risk_level_id]
)
irps: Mapped[List["IRP"]] = relationship("IRP", secondary="mrsa_irp", back_populates="covered_mrsas")
```

### 1.3 Create IRP Models

**New File:** `api/app/models/irp.py`

```python
# Association table
mrsa_irp = Table(
    "mrsa_irp", Base.metadata,
    Column("model_id", Integer, ForeignKey("models.model_id", ondelete="CASCADE"), primary_key=True),
    Column("irp_id", Integer, ForeignKey("irps.irp_id", ondelete="CASCADE"), primary_key=True),
)

class IRP(Base):
    __tablename__ = "irps"
    irp_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    process_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
    # Relationships: contact_user, covered_mrsas, reviews, certifications

class IRPReview(Base):
    __tablename__ = "irp_reviews"
    review_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    irp_id: Mapped[int] = mapped_column(Integer, ForeignKey("irps.irp_id", ondelete="CASCADE"))
    review_date: Mapped[date] = mapped_column(Date, nullable=False)
    outcome_id: Mapped[int] = mapped_column(Integer, ForeignKey("taxonomy_values.value_id"))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    # Relationships: irp, outcome, reviewed_by

class IRPCertification(Base):
    __tablename__ = "irp_certifications"
    certification_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    irp_id: Mapped[int] = mapped_column(Integer, ForeignKey("irps.irp_id", ondelete="CASCADE"))
    certification_date: Mapped[date] = mapped_column(Date, nullable=False)
    certified_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"))
    conclusion_summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    # Relationships: irp, certified_by
```

### 1.4 Migration

**New File:** `api/alembic/versions/xxxx_add_mrsa_and_irp.py`

- Add `requires_irp` column to `taxonomy_values`
- Add MRSA columns to `models` table
- Create `irps`, `mrsa_irp`, `irp_reviews`, `irp_certifications` tables

---

## Phase 2: Seed Taxonomies

**File:** `api/app/seed.py`

### 2.1 Update `_upsert_taxonomy_with_values` Function

The existing function only handles bucket fields (`min_days`, `max_days`, `downgrade_notches`). Add support for `requires_irp`:

```python
# In the update section (existing record):
record.requires_irp = entry.get("requires_irp")

# In the create section (new record):
requires_irp=entry.get("requires_irp"),
```

### 2.2 MRSA Risk Level Taxonomy
```python
_upsert_taxonomy_with_values(
    db,
    name="MRSA Risk Level",
    description="Classification of MRSA (Model Risk-Sensitive Application) risk levels determining IRP requirements.",
    values=[
        {
            "code": "HIGH_RISK",
            "label": "High-Risk",
            "description": "High-risk MRSA requiring IRP coverage",
            "requires_irp": True,
        },
        {
            "code": "LOW_RISK",
            "label": "Low-Risk",
            "description": "Low-risk MRSA not requiring IRP coverage",
            "requires_irp": False,
        },
    ],
)
```

### 2.3 IRP Review Outcome Taxonomy
```python
_upsert_taxonomy_with_values(
    db,
    name="IRP Review Outcome",
    description="Outcomes for Independent Review Process (IRP) periodic assessments.",
    values=[
        {
            "code": "SATISFACTORY",
            "label": "Satisfactory",
            "description": "IRP review found MRSAs adequately managed",
        },
        {
            "code": "CONDITIONALLY_SATISFACTORY",
            "label": "Conditionally Satisfactory",
            "description": "IRP review found minor issues requiring attention",
        },
        {
            "code": "NOT_SATISFACTORY",
            "label": "Not Satisfactory",
            "description": "IRP review found significant deficiencies",
        },
    ],
)
```

### 🛑 UAT Checkpoint: Taxonomy Verification

**PAUSE HERE** after completing steps 1-8 to verify taxonomies before continuing.

**Verify in Taxonomy UI (`/taxonomy`):**
1. **MRSA Risk Level** taxonomy exists with:
   - "High-Risk" value (code: HIGH_RISK, requires_irp: true)
   - "Low-Risk" value (code: LOW_RISK, requires_irp: false)
2. **IRP Review Outcome** taxonomy exists with:
   - "Satisfactory" value
   - "Conditionally Satisfactory" value
   - "Not Satisfactory" value

**Verify via API:**
```bash
curl -s "http://localhost:8001/taxonomies/" -H "Authorization: Bearer $TOKEN" | jq '.[] | select(.name | contains("MRSA") or contains("IRP"))'
```

**Continue implementation only after user confirms taxonomies are correct.**

---

## Phase 3: Pydantic Schemas

### 3.1 Update Taxonomy Schema
**File:** `api/app/schemas/taxonomy.py` - Add `requires_irp: bool | None = None`

### 3.2 New IRP Schemas
**New File:** `api/app/schemas/irp.py`
- `IRPCreate`, `IRPUpdate`, `IRPResponse`, `IRPDetailResponse`
- `IRPReviewCreate`, `IRPReviewResponse`
- `IRPCertificationCreate`, `IRPCertificationResponse`
- `MRSASummary` (for IRP views)

### 3.3 Update Model Schemas
**File:** `api/app/schemas/model.py`
- Add `is_mrsa`, `mrsa_risk_level_id`, `mrsa_risk_rationale`, `irp_ids` to Create/Update
- Add `mrsa_risk_level` (nested), `irps` (list) to Response schemas

---

## Phase 4: API Endpoints

### 4.1 New IRP Router
**New File:** `api/app/api/irp.py`

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/irps/` | GET | List IRPs (filter by is_active) | User |
| `/irps/` | POST | Create IRP | Admin |
| `/irps/{id}` | GET | Get IRP with MRSAs, reviews, certifications | User |
| `/irps/{id}` | PATCH | Update IRP | Admin |
| `/irps/{id}` | DELETE | Delete IRP | Admin |
| `/irps/{id}/reviews` | GET | List IRP reviews | User |
| `/irps/{id}/reviews` | POST | Create review | User |
| `/irps/{id}/certifications` | GET | List certifications | User |
| `/irps/{id}/certifications` | POST | Create certification | Admin |

### 4.2 Update Models API
**File:** `api/app/api/models.py`

- Add `is_mrsa` query parameter to list endpoint
- Add validation: High-risk MRSAs require IRP coverage
- Add `GET /models/{id}/irps` - Get linked IRPs
- Add `PUT /models/{id}/irps` - Update linked IRPs (Admin)

### 4.3 Register Router
**File:** `api/app/main.py`
```python
app.include_router(irp_router, prefix="/irps", tags=["IRPs"])
```

---

## Phase 5: Frontend

### 5.1 API Client
**New File:** `web/src/api/irp.ts`
- IRP interfaces and CRUD functions
- Review and certification functions

### 5.2 Update ModelsPage
**File:** `web/src/pages/ModelsPage.tsx`
- Add view mode toggle: Models Only / MRSAs Only / All
- Add `is_mrsa`, `mrsa_risk_level` columns
- Filter models by `is_mrsa` based on view mode

### 5.3 IRP Management Pages
**New Files:**
- `web/src/pages/IRPsPage.tsx` - List IRPs with CRUD
- `web/src/pages/IRPDetailPage.tsx` - IRP detail with tabs:
  - Overview (name, contact, description, status)
  - Covered MRSAs (linked models)
  - Review History (table)
  - Certification History (table)

### 5.4 MRSA Detail Component
**New File:** `web/src/components/MRSADetailsSection.tsx`
- Display MRSA classification on model detail page
- Show risk level badge, rationale, linked IRPs

### 5.5 Routes
**File:** `web/src/App.tsx`
```typescript
<Route path="/irps" element={<IRPsPage />} />
<Route path="/irps/:id" element={<IRPDetailPage />} />
```

### 5.6 Navigation
**File:** `web/src/components/Layout.tsx`
- Add "IRPs" link in sidebar (Admin only, or as needed)

---

## Phase 6: Testing

### Backend Tests
**New File:** `api/tests/test_irp.py`
- CRUD operations for IRPs
- Review and certification creation
- MRSA validation (high-risk requires IRP)
- Permission checks (admin-only operations)

### Test Fixtures
**File:** `api/tests/conftest.py`
- `mrsa_risk_taxonomy` fixture
- `irp_outcome_taxonomy` fixture
- `sample_irp` fixture

---

## Implementation Order

| Step | Task | Files |
|------|------|-------|
| 1 | Update TaxonomyValue model | `api/app/models/taxonomy.py` ✅ |
| 2 | Create IRP models | `api/app/models/irp.py` ✅ |
| 3 | Update Model entity | `api/app/models/model.py` ✅ |
| 4 | Update models `__init__.py` | `api/app/models/__init__.py` ✅ |
| 5 | Create migration | `api/alembic/versions/xxxx_add_mrsa_and_irp.py` |
| 6 | Run migration | `docker compose exec api alembic upgrade head` |
| 7 | Update `_upsert_taxonomy_with_values` for `requires_irp` | `api/app/seed.py` |
| 8 | Add MRSA Risk Level and IRP Review Outcome taxonomies | `api/app/seed.py` |
| **🛑** | **UAT CHECKPOINT: Verify taxonomies in UI before continuing** | |
| 9 | Create IRP schemas | `api/app/schemas/irp.py` |
| 10 | Update taxonomy schemas | `api/app/schemas/taxonomy.py` |
| 11 | Update model schemas | `api/app/schemas/model.py` |
| 12 | Create IRP router | `api/app/api/irp.py` |
| 13 | Update models router | `api/app/api/models.py` |
| 14 | Register router | `api/app/main.py` |
| 15 | Add test fixtures | `api/tests/conftest.py` |
| 16 | Create IRP tests | `api/tests/test_irp.py` |
| 17 | Create frontend API client | `web/src/api/irp.ts` |
| 18 | Update ModelsPage | `web/src/pages/ModelsPage.tsx` |
| 19 | Create IRPsPage | `web/src/pages/IRPsPage.tsx` |
| 20 | Create IRPDetailPage | `web/src/pages/IRPDetailPage.tsx` |
| 21 | Create MRSADetailsSection | `web/src/components/MRSADetailsSection.tsx` |
| 22 | Update routes | `web/src/App.tsx` |
| 23 | Update navigation | `web/src/components/Layout.tsx` |
| 24 | Update ARCHITECTURE.md | `ARCHITECTURE.md` |

---

## Business Rules Summary

1. **MRSA Identification**: Set `is_model=false` and `is_mrsa=true` on Model entity
2. **Risk Classification**: Use taxonomy-based `mrsa_risk_level_id` with rationale text
3. **IRP Requirement**: Enforced based on `requires_irp` flag on risk level taxonomy value
4. **IRP Coverage**: Many-to-many relationship allows one IRP to cover multiple MRSAs
5. **Reviews**: Track periodic assessments with taxonomy-based outcomes
6. **Certifications**: MRM sign-off on IRP design adequacy (Admin only)
