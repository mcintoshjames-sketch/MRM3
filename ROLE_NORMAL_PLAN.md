## Plan: Normalize User Roles (DB + API + UI) With Minimal Refactor Risk

### Goals
- Make user roles normalized and constrained at the database layer.
- Eliminate brittle string comparisons in backend/frontend authorization logic.
- Migrate safely with additive, backward-compatible steps and easy rollback.

### Non-goals (for this effort)
- Re-architecting the entire authorization model into full ABAC/OPA.
- Replacing the existing “approver roles” feature (that’s a separate concept) in approver_roles.py.

### Current State (as implemented)
- DB stores role as a free-form string column (`users.role`), no FK/check constraints.
- Backend defines `UserRole` enum with string values in user.py.
- `/auth/me` returns `"role": user.role` as a string (no normalization) in auth.py.
- Frontend stores `user.role` directly and uses many literal string comparisons via AuthContext.tsx.
- Backend role checks are scattered and mixed (sometimes `UserRole.ADMIN`, sometimes `"Admin"`), and privileged-role gating exists in rls.py.

---

## Target End State
### Database
- `roles` table is the source of truth:
  - `roles.role_id` (PK)
  - `roles.code` (unique, stable machine identifier: `ADMIN`, `REGIONAL_APPROVER`, etc.)
  - `roles.display_name` (human label: “Admin”, “Regional Approver”, etc.)
  - optional: `roles.is_system` / `roles.is_active` for governance and safe deprecation
- `users.role_id` is `NOT NULL` and FK → `roles.role_id`.
- Legacy `users.role` (string) is removed after full migration and stabilization.

### API Contract
- User responses include stable `role_code` in addition to the existing `role` display string during transition:
  - `role` remains for display/backward compatibility
  - `role_code` becomes the canonical field for authorization branching
- Add a `capabilities` object for contextual permissions, starting narrowly (recommended to avoid UI/backend drift without triggering a major refactor):
   - Initial scope should focus on permissions that are already enforced in backend logic and are needed for UI decisions (e.g., proxy-approval evidence requirements, ability to void).
   - Treat `capabilities` as additive “UI hints / permissions,” not a replacement for server-side enforcement.
 - Clarify write contract for role assignment (recommended):
    - API writes should accept `role_code` (stable) rather than `role_id` (internal DB identifier) or `role` (display string).
    - Backend maps `role_code → role_id` and keeps legacy `role` display in sync during the transition.

### Frontend
- UI gates are based on `role_code` and/or `capabilities`, not display strings.
- Role checks are centralized behind a helper (single source of truth client-side).

---

## Phase 0: Inventory & Canonicalization (pre-migration)
1. Define canonical role codes mapped to current display names:
   - `ADMIN` → “Admin”
   - `USER` → “User”
   - `VALIDATOR` → “Validator”
   - `GLOBAL_APPROVER` → “Global Approver”
   - `REGIONAL_APPROVER` → “Regional Approver”
2. Audit current production values in `users.role`:
   - Find any non-canonical variants (case, spacing, legacy names).
   - Decide whether to map them (recommended) or reject them (higher risk).
3. Decide how to handle unknown/malformed roles (recommended: strict by default with an explicit escape hatch):
   - Default behavior (strict): fail the backfill/migration (or at least hard-fail the “tighten constraints” step) if any unmapped role strings exist.
   - Escape hatch (explicit): allow an operator-controlled override to map unknowns to `USER` *and* emit a report for cleanup.

Deliverable: a mapping table (old string → canonical code) used during backfill.

---

## Phase 1: Add Normalized Role Structures (DB additive, safe)
1. Create Alembic migration(s) under versions:
   - Create `roles` table.
   - Insert seed rows for the canonical roles.
   - Add nullable `users.role_id` column.
   - Add index on `users.role_id`.
   - (Optional but recommended) Add `roles.code` unique index and `roles.display_name` non-null constraint.
2. Add a FK constraint but keep it initially “soft”:
   - Option A (recommended): add FK after backfill to avoid constraint failures.
   - Option B: add FK immediately but allow NULLs and only populate valid ids.
3. Do not drop or modify `users.role` yet.

4. Test strategy alignment (important):
   - If pytest uses SQLite without running Alembic migrations, update test setup/fixtures to create and seed the `roles` table so code paths that depend on `role_code`/`role_id` can run.

Rollback safety: this phase is fully additive; rollback is straightforward.

---

## Phase 2: Backfill & Dual-Write (DB + API, still backward compatible)
### DB backfill
1. Backfill `users.role_id` using the mapping from Phase 0:
   - Map existing `users.role` string values to `roles.code`.
   - Set `users.role_id` accordingly.
   - Prefer set-based SQL updates inside the migration (or a controlled one-off script) over ORM iteration to avoid long transactions and unexpected runtime dependencies.
2. Validate backfill:
   - Ensure 100% coverage (no users left with NULL role_id) before tightening constraints.
   - Produce a report of any unmapped roles if present.
   - If using the escape hatch, record the affected user_ids + original role strings in an audit artifact for cleanup.

### Backend dual-write / dual-read
1. Update ORM models to support normalization:
   - Add a `Role` model (for the `roles` table) and add `User.role_id` + relationship to `Role`.
   - Keep the legacy `User.role` string field during transition.

2. Update backend user serialization logic in auth.py:
   - Continue returning `role` display string unchanged for compatibility.
   - Add `role_code` derived from the normalized role (prefer `users.role_id → roles.code`).

3. Add a roles catalog endpoint (frontend dependency):
   - Expose `GET /roles` returning `{ role_code, display_name }` so the UI doesn’t hardcode role lists.

4. Update Pydantic schema in user.py:
   - Add optional `role_code` to response types.

5. Update user create/update paths to write both (using `role_code` as the input contract):
   - Accept `role_code` on create/update; resolve to `role_id`.
   - Keep `role` display string in sync temporarily (either copied from `roles.display_name` or computed in responses).
   - Define precedence rules during transition:
     - Prefer `role_id`/`role_code` as authoritative
     - Treat `role` as display/back-compat only

Risk control: dual-write means you can revert UI first without breaking auth.

---

## Phase 3: Centralize Backend Authorization & Reduce Drift
1. Introduce a single “role/capability resolution” layer (new module):
   - Derives role code from DB and exposes helpers like `is_admin(current_user)`.
   - Replaces scattered checks against `"Admin"` and mixed enum usage.
   - Define initial `capabilities` in code (not DB) to keep scope tight; base them on `role_code` and contextual checks where needed.
2. Update RLS privileged-role logic in rls.py:
   - Use role code comparisons, not raw display strings.
3. For flows with known UI/backend drift risk (like proxy approvals):
   - Prefer backend policy decisions that return explicit UI requirements.
   - Example pattern: return `approval_evidence_required` as a computed flag on approval payloads rather than inferring from role in the UI.

Outcome: backend becomes the single source of truth for “what is required/allowed”.

---

## Phase 4: Frontend Migration (incremental, low risk)
1. Update AuthContext.tsx `User` type:
   - Add optional `role_code` (and optional `capabilities` if implemented).
2. Add a single frontend helper module (new file) for role checks:
   - Use `role_code` if present; fallback to legacy `role` string during transition.
3. Migrate pages gradually:
   - Replace `user?.role === 'Admin'` with `isAdmin(user)` helper.
   - Prioritize security-critical and high-traffic flows first.
4. After migration coverage is high, consider tightening the UI to rely solely on `role_code`.

Success criterion: no user-facing logic depends on display-role strings.

---

## Phase 5: Enforce Constraints & Remove Legacy
1. Add a migration to enforce:
   - `users.role_id` set to `NOT NULL`
   - FK constraint enforced (if not already)
2. Stop dual-write:
   - Backend no longer treats `users.role` as authoritative.
   - Keep returning `role` as a display label (from `roles.display_name`) if desired.
3. Remove legacy column `users.role` only after:
   - All backend reads are via role_id
   - Frontend uses role_code/capabilities
   - A full release cycle passes without auth regressions

Optional: keep a DB view or computed display field if reporting depends on the old column.

---

## Rollback & Recovery
This migration is designed to keep rollback cheap by keeping early phases additive and backward compatible.

### Code rollback
- Use small, phased PRs so an incident rollback is a targeted `git revert` of the offending PR/merge commit.
- Maintain backward compatibility while migrating:
  - Frontend role checks should prefer `role_code` when present and fall back to legacy `role`.
  - Backend should continue returning legacy `role` throughout the migration window.

### Operational kill switch (recommended)
- Add a backend configuration flag to force legacy behavior during an incident (e.g., disable `role_code`/capability-based branching and use legacy `users.role` checks).
- Keep the fallback logic in place until Phase 5 is fully complete and stabilized.

### DB rollback strategy
- Phases 1–4 are additive (new table/column/fields). If application code is rolled back, the DB can remain in the “newer” state safely.
- For Phase 5 (hard constraints + dropping legacy), treat this as the true “point of no return”:
  - Before enforcing `NOT NULL`/FK or dropping `users.role`, take a DB snapshot/backup.
  - If Phase 5 causes issues:
    - Prefer a compensating migration to relax constraints (make `users.role_id` nullable and/or drop the FK constraint) rather than attempting to reconstruct dropped data.
    - If `users.role` has been dropped, restoration requires the pre-change backup.

### Data recovery artifacts
- During Phase 2 backfill, record a durable audit artifact containing at least `{user_id, legacy_role_string, resolved_role_code, role_id}`.
- If the escape hatch is used (unknown → `USER`), record those users explicitly for follow-up cleanup.

---

## Future Phases (recommended)
### Future Phase A: Capability-based authorization (more resilient than roles)
- Add a `capabilities` object to `/auth/me` and other relevant endpoints.
- For contextual rules (regional scoping, proxy approvals), make the backend return explicit flags per object (e.g., per approval requirement).

### Future Phase B: RBAC expansion without breaking API
- If roles become many-to-many in the future:
  - Introduce `user_roles` join table.
  - Keep `role_code` as a “primary role” for UI convenience (optional), while `capabilities` remains authoritative.

---

## Key Design Decisions Made Up Front
1. Keep `role` as a display name; make `role_code` canonical
   - Decision: retain `role` in API responses (medium-term) for backward compatibility and display.
   - Decision: add `role_code` and treat it as the canonical stable identifier for authorization branching.
   - Why: lowest-risk migration (no breaking clients), eliminates brittleness from display string changes.

2. Add `capabilities`, but start narrow
   - Decision: include a `capabilities` object in the initial cut, but only for a small set of high-value permissions that prevent UI/backend drift.
   - Why: roles alone won’t cover contextual rules (proxy vs direct approval, region scoping, delegation). Narrow capabilities deliver correctness without forcing a large refactor.

3. Be strict on unknown role strings, with an explicit escape hatch
   - Decision: default strictness—unknown roles should block constraint hardening (and ideally the backfill) so data issues are not silently normalized away.
   - Decision: provide an explicit override path to map unknowns to `USER` and generate an audit report.
   - Why: preserves data integrity and auditability, while maintaining operational flexibility.

