# Comprehensive Role Privilege Audit

**Date:** December 31, 2025
**Auditor:** GitHub Copilot

## 1. Executive Summary

The system implements a Role-Based Access Control (RBAC) system with five canonical roles. Authorization is enforced primarily through imperative checks within API route handlers using helper functions (`is_admin`, `is_validator`, etc.). While the system effectively restricts access to sensitive operations, the reliance on scattered imperative checks rather than declarative decorators makes the security posture harder to verify and maintain.

A key finding is the "Immutable Approved Models" pattern, where non-admin users cannot directly edit approved models and must instead submit "Pending Edits" for approval.

## 2. Role Definitions

The system defines the following canonical roles (in `app.core.roles`):

| Role Code | Display Name | Description |
|-----------|--------------|-------------|
| `ADMIN` | Admin | Full system access. Can edit approved models directly. |
| `VALIDATOR` | Validator | Focus on validation workflows, risk assessments, and attestations. |
| `GLOBAL_APPROVER` | Global Approver | Approves decommissioning, recommendations, and monitoring globally. |
| `REGIONAL_APPROVER` | Regional Approver | Approves decommissioning, recommendations, and monitoring for specific regions. |
| `USER` | User | Basic access. Can view models. Can edit own models only if in 'Draft' state. Must use "Pending Edits" for approved models. |

## 3. Enforcement Mechanisms

### 3.1 Authentication
All protected endpoints use the `get_current_user` dependency (`app.core.deps`), which validates the JWT token and retrieves the user from the database.

### 3.2 Authorization
Authorization is implemented via helper functions in `app.core.roles`:
- `is_admin(user)`
- `is_validator(user)`
- `is_global_approver(user)`
- `is_regional_approver(user)`

These helpers are called explicitly inside route handlers. If a check fails, an `HTTPException(403)` is raised.

**Example Pattern:**
```python
if not (is_admin(current_user) or is_validator(current_user)):
    raise HTTPException(status_code=403, detail="Not authorized")
```

### 3.3 Workflow Enforcement (The "Pending Edit" Pattern)
For the `Model` entity, a specific workflow enforcement exists in `app.api.models.update_model`:
- If the user is **NOT** an Admin AND the model is **Approved** (`row_approval_status is None`):
    - The update is **intercepted**.
    - A `ModelPendingEdit` record is created instead of updating the `Model` table.
    - This effectively enforces a "Change Control" process for non-admins on live data.

## 4. Detailed Privilege Matrix

| Feature Area | ADMIN | VALIDATOR | GLOBAL APPROVER | REGIONAL APPROVER | USER |
|--------------|-------|-----------|-----------------|-------------------|------|
| **User Mgmt** | Full | — | — | — | — |
| **Model Inventory** | Full (Direct Edit) | View | View | View | View / Edit (Drafts) / Propose (Approved) |
| **Validation** | Full | Full Access | — | — | View |
| **Risk Assessment**| Full | Full Access | — | — | View |
| **Attestations** | Full | Full Access | — | — | View |
| **Decommissioning**| Full | View | Approve | Approve (Region) | Request |
| **Recommendations**| Full | View | Approve | Approve (Region) | View |
| **Monitoring** | Full | View | Approve | Approve (Region) | View |
| **Limitations** | Full | Full Access | — | — | View |

*(Note: "Full" for Admin usually implies ability to override or manage configuration, though some specific workflow steps might be designed for other roles)*

## 5. Findings & Recommendations

### Finding 1: Imperative vs. Declarative Authorization
**Severity:** Medium
**Observation:** Role checks are embedded inside function bodies (e.g., `if not is_admin...`).
**Risk:** It is easy for a developer to forget to add this check when creating a new endpoint, defaulting the endpoint to "Open to all authenticated users".
**Recommendation:** Refactor to use `Depends` based role checkers or decorators (e.g., `@require_role(Role.ADMIN)`) to make authorization declarative and visible in the function signature.

### Finding 2: Incomplete Automated Analysis
**Severity:** Low
**Observation:** The existing `analyze_role_privileges.py` script only detects `ADMIN` checks effectively. It misses `VALIDATOR` and `APPROVER` checks because it looks for the string "admin" in function calls.
**Recommendation:** Update the analysis script to detect all role helper functions defined in `app.core.roles`.

### Finding 3: Implicit "User" Permissions
**Severity:** Low
**Observation:** The `USER` role often has access by virtue of *not* being blocked. If an endpoint has no specific role check, any authenticated user (including `USER`) can access it.
**Recommendation:** Adopt a "Deny by Default" strategy where every endpoint must explicitly declare allowed roles, even if it is "Any Authenticated User".

### Finding 4: Hardcoded Role Logic
**Severity:** Low
**Observation:** Logic like `if not is_admin_user and model.row_approval_status is None` is hardcoded in the business logic.
**Recommendation:** Abstract this into a policy layer or service method (e.g., `ModelService.can_edit(user, model)`) to centralize complex permission logic.
