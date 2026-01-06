This review document has been cleaned for clarity, structural integrity, and proper Markdown formatting. I have corrected the malformed escapes, fixed the section numbering, and ensured consistent formatting for code blocks and tables.

# Review: USER_GUIDE_MODEL_CHANGES.md

**Reviewed:** 2026-01-05
**Reviewer:** Claude Code (Automated Review)
**Document Path:** `/Users/jamesmcintosh/Desktop/mrm_inv_3/docs/USER_GUIDE_MODEL_CHANGES.md`

---

## Summary

This document reviews the Model Changes & Version Management user guide against the current codebase implementation. The review covers model version management, change types and taxonomy, version status transitions, deployment tasks, API endpoints, and frontend page functionality.

Overall, the user guide is well-written and comprehensive. However, several areas require updates to reflect the current implementation.

---

## Material Omissions

### 1. Missing Task Status: ADJUSTED

**Location:** Section 9 - Managing Deployment Tasks (Task Status Icons)

**Issue:** The documentation lists four task statuses: Confirmed, Pending, Overdue, and Cancelled. However, the code defines a fifth status: `ADJUSTED`.

**Evidence:**

* `/api/app/models/version_deployment_task.py`:
```python
status: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default="PENDING"
)  # PENDING | CONFIRMED | ADJUSTED | CANCELLED

```



**Recommendation:** Add ADJUSTED status to the Task Status Icons table:

| Icon | Status | Description |
| --- | --- | --- |
| Blue | **Adjusted** | Planned date has been modified |

### 2. Missing Change Type Taxonomy System (L1/L2 Hierarchy)

**Location:** Section 6 - Change Types & Categories

**Issue:** The documentation describes a simple MAJOR/MINOR change type with six categories as a flat list. The actual implementation uses a hierarchical **two-level taxonomy system**:

* **L1 (ModelChangeCategory):** Top-level categories (e.g., "New Model").
* **L2 (ModelChangeType):** Specific types within each category with metadata.

**Evidence:**

* `/api/app/models/model_change_taxonomy.py`:
```python
class ModelChangeCategory(Base):
    """L1 - Model change category (e.g., New Model, Change to Model)."""
    change_types: Mapped[List["ModelChangeType"]] = relationship(...)

class ModelChangeType(Base):
    """L2 - Specific model change type within a category."""
    requires_mv_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

```



### 3. Missing Version Regional Scope Feature

**Location:** Section 2 - Understanding Model Versions (Version Anatomy)

**Issue:** The documentation does not mention the **Regional Scope** feature. Versions can be:

* `GLOBAL`: Change affects all regions.
* `REGIONAL`: Change affects only specific regions.

**Evidence:**

* `/api/app/models/model_version.py`:
```python
scope: Mapped[str] = mapped_column(String(20), default="GLOBAL") # GLOBAL | REGIONAL

```



### 4. Missing API Endpoint Documentation

**Location:** Throughout document

**Key Model Version Endpoints:**

| Endpoint | Method | Description |
| --- | --- | --- |
| `/models/{model_id}/versions` | POST | Create new version |
| `/models/{model_id}/versions/next-version` | GET | Preview next version number |
| `/versions/{version_id}/activate` | PATCH | Mark as ACTIVE |

**Deployment Task Endpoints (prefix: `/deployment-tasks`):**

| Endpoint | Method | Description |
| --- | --- | --- |
| `/my-tasks` | GET | Get current user's deployment tasks |
| `/{task_id}/adjust` | PATCH | Adjust planned date |

---

## Important Inconsistencies

### 1. Version Status: IN_VALIDATION Editability Rules

**Issue:** Documentation states `IN_VALIDATION` versions are conditionally editable.
**Finding:** The API (`/api/app/api/model_versions.py`) strictly enforces that **only DRAFT** versions can be edited.

```python
if version.status != VersionStatus.DRAFT:
    raise HTTPException(status_code=400, detail="Only DRAFT versions can be edited.")

```

### 2. Blocker B2 Description

**Issue:** Blocker B2 states a version is blocked if a validation is not `APPROVED`.
**Finding:** Code allows progression if status is `APPROVED`, `CANCELLED`, or `ON_HOLD`.
**Recommendation:** Update text to "NOT in a terminal state (APPROVED, CANCELLED, or ON_HOLD)."

### 3. Page Title Discrepancy

**Issue:** Doc refers to "My Deployment Tasks Page"; code renders "Pending Deployments."
**Evidence:** `/web/src/pages/MyDeploymentTasksPage.tsx`:

```jsx
<h1 className="text-3xl font-bold text-gray-900">Pending Deployments</h1>

```

---

## Key Clarifications Needed

### 1. Activate vs Deploy: Two Separate Actions

* **Activate:** Updates the global inventory record.
* **Deploy:** Creates regional tasks for physical rollout.

### 2. Regional Approval Workflow

Deploying to a locked region triggers a `ValidationApproval` record with `approval_type="Regional"`. This needs explicit documentation regarding who manages these requests.

---

## Recommendations Summary

| Priority | Item | Action |
| --- | --- | --- |
| **High** | Editability rules | Align docs with code (only DRAFT is editable) |
| **High** | Blocker B2 | Update terminal states to include CANCELLED/ON_HOLD |
| **Medium** | Taxonomy | Document L1/L2 hierarchy |
| **Medium** | Regional Scope | Add GLOBAL vs REGIONAL explanation |
| **Low** | Typos | Fix section numbering and Intro markdown |

---

*This review was generated automatically. Manual verification is recommended before updating the master documentation.*

Would you like me to generate the specific Markdown text for the missing "Regional Scope" subsection?