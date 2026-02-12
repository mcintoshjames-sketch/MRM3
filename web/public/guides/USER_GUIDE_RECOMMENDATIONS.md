# Model Recommendations User Guide

## Overview
The **Model Recommendations** feature allows your organization to track, manage, and resolve issues identified during model validation. It provides a structured workflow for Validators to raise issues, Developers to respond with action plans or rebuttals, and Approvers to sign off on final closure.

This system ensures that all model weaknesses are documented, assigned clear ownership, and remediated according to governance policies.

---

## Complete Workflow States

The recommendation system uses 12 distinct workflow states to track progress through the lifecycle:

| Status | Description | Who Acts |
|--------|-------------|----------|
| **Draft** | Initial creation; recommendation is being prepared | Validator |
| **Pending Response** | Sent to developer; awaiting rebuttal or action plan | Developer |
| **In Rebuttal** | Developer submitted a rebuttal; awaiting validator review | Validator |
| **Pending Action Plan** | Rebuttal was overridden; developer must submit action plan | Developer |
| **Pending Validator Review** | Action plan submitted; awaiting validator approval | Validator |
| **Pending Acknowledgement** | Action plan approved; developer must acknowledge | Developer |
| **Open** | Acknowledged; remediation work in progress | Developer |
| **Rework Required** | Closure rejected; additional work needed | Developer |
| **Pending Closure Review** | Closure submitted; awaiting validator review | Validator |
| **Pending Final Approval** | Validator approved; awaiting Global/Regional sign-offs | Approvers |
| **Closed** | All approvals received; recommendation complete | — |
| **Dropped** | Recommendation voided (rebuttal accepted or admin action) | — |

---

## Key Roles & Responsibilities

| Role | What you do |
|------|-------------|
| **Validator** | Creates recommendations, reviews developer responses, and approves closure requests (evidence links optional). |
| **Developer / Owner** | Responds to recommendations, executes remediation tasks, and optionally adds evidence links for closure. |
| **Global / Regional Approver** | Provides final sign-off for closing high-priority or regionally sensitive recommendations. |
| **Admin** | Can perform actions on behalf of any role and manage system configurations. |

---

## The Recommendation Lifecycle

The lifecycle follows a negotiation phase (validator ↔ developer) followed by remediation and closure.

### 1. Creating a Recommendation (Validator)
1. Navigate to the **Recommendations** page or the **Recommendations** tab on a specific Model.
2. Click **+ New Recommendation**.
3. Fill in the required details:
   - **Model**: The model where the issue was found.
   - **Title & Description**: Clear summary of the finding.
   - **Priority**: High, Medium, or Low (affects approval requirements).
   - **Assigned To**: The developer responsible for fixing it.
   - **Target Date**: When remediation should be complete.
4. Click **Create**. The recommendation starts in **Draft** status.
   - Draft recommendations are visible to the validation team while the recommendation is being prepared.
5. When ready, click **Submit to Developer** to notify the developer. The recommendation moves to **Pending Response**.

### 2. Developer Response (Developer)
Once a recommendation is sent, the assigned developer has two options:

#### Option A: Submit a Rebuttal
If you believe the finding is invalid or factually incorrect:
1. Open the recommendation.
2. Click **Submit Rebuttal**.
3. Provide your **Rationale** and any **Supporting Evidence** (URL or file path).
4. Submit. The recommendation moves to **In Rebuttal** status.
5. The Validator will review your argument and either:
   - **Accept** it → The recommendation is **Dropped** (voided)
   - **Override** it → The recommendation moves to **Pending Action Plan**

**Important: One-Strike Rule**
- You only get one chance to rebut. If your rebuttal is overridden, you must proceed with an action plan.
- The system blocks further rebuttal attempts once a previous rebuttal has been overridden.

#### Option B: Submit an Action Plan
If you accept the finding and plan to fix it:
1. Open the recommendation.
2. Click **Submit Action Plan**.
3. Add specific **Tasks**, assigning an owner and due date for each.
4. Submit. The recommendation moves to **Pending Validator Review**.
5. The Validator reviews the action plan and either:
   - Approves it (recommendation moves to **Pending Acknowledgement**), or
   - Requests changes (recommendation returns to **Pending Response**).

#### Option C: Skip Action Plan (Low-Priority Only)
For recommendations where the Admin has configured "Requires Action Plan = No" (typically **Consideration** priority):
1. Open the recommendation.
2. Click **Skip Action Plan** (if available).
3. The recommendation moves directly to **Pending Validator Review** without requiring tasks.
4. The Validator reviews and approves, then the recommendation moves to **Pending Acknowledgement**.

*Use the `/recommendations/{id}/can-skip-action-plan` endpoint to check if skipping is allowed for a specific recommendation.*

### 3. Acknowledgement & Remediation (Developer)
Once the action plan has been approved by the Validator:
1. The recommendation moves to **Pending Acknowledgement**.
2. The assigned developer has two options:
   - **Acknowledge** → The recommendation moves to **Open** for remediation work
   - **Decline** (with reason) → The recommendation returns to **Pending Validator Review** for reconsideration
3. Once in **Open** status, work through your assigned tasks.
4. As tasks are finished, update their status to **Completed** in the **Action Plan** tab.

**Note:** The system validates that all tasks are marked **Completed** at the moment of submitting for closure, not during earlier phases.

### 4. Closing a Recommendation (Developer & Validator)
When all work is done:
1. **Developer**: (Optional) Add **Evidence** in the Evidence tab. The system supports:
   - **URLs**: Links to external documents or systems
   - **File paths**: Absolute paths to documents on shared drives
   - **Metadata**: File name, file type, file size, and description
2. **Developer**: Click **Submit for Closure**.
   - The system requires all action plan tasks to be completed.
   - The recommendation moves to **Pending Closure Review**.
3. **Validator**: Review the submission.
   - If satisfactory, click **Approve Closure** → Moves to **Pending Final Approval** (if approvers required) or **Closed**
   - If changes are needed, click **Request Rework** → Moves to **Rework Required**

**Important: Approval Reset on Rejection**
If any approver (Validator, Global, or Regional) rejects a closure request:
- **ALL** previously granted approvals for that recommendation are reset to **Pending**
- The recommendation returns to **Rework Required** status
- The developer must address the feedback and resubmit for closure

### 5. Final Approvals (Approvers)
For **Medium** and **High** priority items, Validator approval is not enough. The system will automatically request final sign-off:
- **Global Approvers**: Sign off on the overall closure.
- **Regional Approvers**: Sign off if the model is deployed in your region.

Once all required approvals are collected, the recommendation status automatically changes to **Closed**.

---

## Understanding Source Icons

Recommendations can originate from different sources. Visual indicators help you quickly identify where a recommendation came from:

| Icon | Source | Description |
|------|--------|-------------|
| 🔵 (Blue checkmark badge) | **From Validation** | This recommendation was raised during a model validation. Click to view the linked validation request. |
| 🟣 (Purple chart badge) | **From Monitoring** | This recommendation was raised during ongoing model monitoring. Click to view the linked monitoring cycle. |
| *(No icon)* | **Standalone** | This recommendation was created independently, not tied to a validation or monitoring cycle. |

### Where Source Icons Appear

- **Recommendations List**: A small colored badge appears next to the recommendation code (e.g., `REC-2025-00001 🔵`).
- **Recommendation Detail Page**: The "Source" row displays a clickable link to the originating validation request or monitoring cycle, including additional context like validation type or monitoring period dates.

### Filtering by Source

You can add the **Validation ID** or **Monitoring Cycle** columns to your view using the column picker to see and sort by source information. These columns are hidden by default but can be enabled for traceability reporting.

---

## Dashboards & Tracking

### My Tasks
On the **Recommendations** page, use the **My Tasks Only** toggle to see items requiring your immediate attention:
- **Action Required**: Recommendations assigned to you that need a response or closure submission.
- **Review Pending**: Items waiting for your review (as a Validator).
- **Approval Pending**: Closures waiting for your final sign-off (as an Approver).

### Overdue Reports
Use the **Show overdue only** toggle to highlight recommendations that have passed their target date without being closed. This helps management identify at-risk remediation efforts.

---

## Admin Configuration: Priority Workflow Settings

Administrators can customize how each recommendation priority level behaves through the **Recommendation Priority Config** section in the Taxonomy page. This allows your organization to tailor the recommendation workflow to match your specific governance policies.

### Base Priority Configuration

For each priority level (High, Medium, Low, Consideration), admins can configure three key workflow settings:

| Setting | Description | Impact |
|---------|-------------|--------|
| **Requires Action Plan** | Whether developers must submit a detailed action plan before remediation. | When enabled, developers must create tasks with owners and due dates. When disabled, developers can skip straight to remediation after acknowledging the recommendation. |
| **Requires Final Approval** | Whether Global/Regional Approvers must sign off on closure. | When enabled, Validator approval alone is insufficient—Global and Regional approvers must also approve before the recommendation closes. When disabled, Validator approval is final. |
| **Enforce Timeframes** | Whether target dates are validated against configured max timeframes. | When enabled, the system enforces maximum allowed remediation periods (e.g., 90 days for High priority). When disabled, any target date is accepted. |

**Example Use Case:**
- **High Priority**: Requires Action Plan = Yes, Requires Final Approval = Yes, Enforce Timeframes = Yes (strictest oversight)
- **Low Priority**: Requires Action Plan = No, Requires Final Approval = No, Enforce Timeframes = No (streamlined closure)
- **Consideration**: Requires Action Plan = No, Requires Final Approval = No, Enforce Timeframes = No (minimal process for informational items)

### Regional Overrides

For organizations operating across multiple jurisdictions, admins can create **Regional Overrides** that modify priority settings for specific regions. This is useful when regulatory requirements differ by geography.

**How Regional Overrides Work:**
- Each override applies to a specific priority level + region combination
- Override settings take precedence over base priority configuration
- You can override any combination of the three workflow settings (action plan, final approval, timeframes)
- Overrides only affect recommendations for models deployed in that region

**"Most Restrictive Wins" Logic:**
When a model is deployed in multiple regions, the system applies the **most restrictive** setting across all applicable overrides:
1. If **ANY** regional override requires an action plan → action plan is required
2. If **ANY** regional override requires final approval → final approval is required
3. If **ANY** regional override enforces timeframes → timeframes are enforced
4. `NULL` values in overrides inherit from the base configuration

**Example Use Case:**
A model deployed in both the US and UK might have different closure requirements:
- **Base Setting (Medium Priority)**: Requires Final Approval = No (US standard)
- **UK Regional Override (Medium Priority)**: Requires Final Approval = Yes (stricter UK regulation)
- **US Regional Override (Medium Priority)**: Requires Final Approval = No
- **Result**: Since the UK requires final approval (most restrictive), the recommendation requires approver sign-off regardless of where it was created

### Timeframe Configurations

Timeframe configurations use a **three-dimensional matrix** to determine the maximum number of days allowed for remediation:

1. **Recommendation Priority**: High, Medium, Low, Consideration
2. **Model Risk Tier**: Tier 1, Tier 2, Tier 3, Tier 4
3. **Model Usage Frequency**: Daily, Monthly, Quarterly, Annually

This means the same priority level may have different deadlines depending on the model's risk tier and how frequently it's used. For example, a High-priority finding on a Tier 1 daily-use model would have a shorter deadline than the same finding on a Tier 3 annually-used model.

**How Timeframe Enforcement Works:**
- When creating or editing a recommendation, the system validates the target date against the configured maximum days for the specific priority + tier + frequency combination
- If **Enforce Timeframes** is enabled for the priority level:
  - At **creation** time, target dates exceeding the maximum are rejected
  - At **edit** time, users can override the maximum by providing a required reason/explanation when changing the target date
- If **Enforce Timeframes** is disabled, any target date is accepted (no validation)
- Timeframes provide guardrails to ensure high-priority issues are remediated within acceptable periods

**Configuration:**
- Admins configure max_days for each combination in the timeframe matrix
- More critical combinations (high priority + high tier + frequent use) should have shorter deadlines
- Less critical combinations can have longer or no limits (null)

**Example Use Case:**
Your organization implements a tiered timeframe policy:

| Priority | Tier 1 Daily | Tier 2 Monthly | Tier 3 Quarterly |
|----------|--------------|----------------|------------------|
| High | 30 days | 60 days | 90 days |
| Medium | 90 days | 120 days | 180 days |
| Low | 180 days | 270 days | 365 days |

When a Validator creates a High priority recommendation for a Tier 1 daily-use model with "Enforce Timeframes" enabled, the system will only accept target dates within 30 days. The same High priority finding on a Tier 3 model would allow 90 days.

### Accessing Recommendation Priority Config

Admins can access these settings at:
1. Navigate to **Taxonomy** in the main menu
2. Select **Recommendation Priority Config** from the dropdown
3. Click **Edit** next to any priority level to modify base settings
4. Expand a priority row (using the arrow icon) to view/add regional overrides
5. Use **+ Add Regional Override** to create region-specific rules

---

## Frequently Asked Questions

**Q: Can I edit a recommendation after sending it?**
A: Yes, but editing permissions vary by status:

| Status | Full Edit | Limited Edit (Assignee/Date) | No Edit |
|--------|-----------|------------------------------|---------|
| Draft | ✓ | — | — |
| Pending Response | ✓ | — | — |
| Pending Validator Review | ✓ | — | — |
| Pending Acknowledgement | — | ✓ | — |
| Open | — | ✓ | — |
| Rework Required | — | ✓ | — |
| Pending Closure Review | — | — | ✓ |
| Pending Final Approval | — | — | ✓ |
| Closed | — | — | ✓ |
| Dropped | — | — | ✓ |

**Q: What happens if my rebuttal is rejected?**
A: You must submit an Action Plan. The system enforces a "one-strike" rule for rebuttals—once a rebuttal has been overridden, you cannot submit another rebuttal for the same recommendation, regardless of current status.

**Q: Who can close a Low priority recommendation?**
A: By default, Low priority items are closed immediately after the Validator approves the closure request—they do not require Global or Regional sign-off. However, this can be changed by an Admin through the Recommendation Priority Config if your organization requires additional oversight.

**Q: Why do I need to provide a reason when changing the target date?**
A: Target dates are validated against the three-dimensional timeframe matrix (priority × tier × usage frequency). A reason is required whenever the target date changes to preserve an audit trail, and it is required to override enforced maximum timeframes during edits.

**Q: Can different regions have different approval requirements?**
A: Yes! Admins can create Regional Overrides that modify workflow settings for specific regions. When a model is deployed across multiple regions, the "Most Restrictive Wins" logic ensures the strictest requirement applies.

**Q: What happens if an approver rejects a closure after others have approved?**
A: All previously granted approvals are reset to **Pending**, and the recommendation returns to **Rework Required**. The developer must address the feedback and resubmit for a fresh round of approvals.

---

## API Reference (Technical Users)

For integrations and automation, the following endpoints are available:

| Endpoint | Action | Status Transition |
|----------|--------|-------------------|
| `POST /recommendations/{id}/submit` | Submit to Developer | Draft → Pending Response |
| `POST /recommendations/{id}/rebuttal` | Submit Rebuttal | Pending Response → In Rebuttal |
| `POST /recommendations/{id}/rebuttal/{rebuttal_id}/review` | Review Rebuttal | In Rebuttal → Dropped or Pending Action Plan |
| `POST /recommendations/{id}/skip-action-plan` | Skip Action Plan | Pending Response → Pending Validator Review |
| `GET /recommendations/{id}/can-skip-action-plan` | Check if Skip Allowed | — (read-only) |
| `POST /recommendations/{id}/finalize` | Finalize Action Plan Review | Pending Validator Review → Pending Acknowledgement |
| `POST /recommendations/{id}/acknowledge` | Acknowledge | Pending Acknowledgement → Open |
| `POST /recommendations/{id}/decline-acknowledgement` | Decline | Pending Acknowledgement → Pending Validator Review |
| `POST /recommendations/{id}/submit-closure` | Submit for Closure | Open/Rework Required → Pending Closure Review |
| `POST /recommendations/{id}/approvals/{approval_id}/void` | Void Approval (Admin) | — (removes approval requirement) |

All transition endpoints enforce the workflow state machine and return appropriate error messages for invalid transitions.
