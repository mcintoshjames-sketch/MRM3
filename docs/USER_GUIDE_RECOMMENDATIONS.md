# Model Recommendations User Guide

## Overview
The **Model Recommendations** feature allows your organization to track, manage, and resolve issues identified during model validation. It provides a structured workflow for Validators to raise issues, Developers to respond with action plans or rebuttals, and Approvers to sign off on final closure.

This system ensures that all model weaknesses are documented, assigned clear ownership, and remediated according to governance policies.

---

## Key Roles & Responsibilities

| Role | What you do |
|------|-------------|
| **Validator** | Creates recommendations, reviews developer responses, and approves closure evidence. |
| **Developer / Owner** | Responds to recommendations, executes remediation tasks, and submits evidence for closure. |
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
5. When ready, click **Finalize & Send** to notify the developer. The recommendation moves to **Pending Response**.

### 2. Developer Response (Developer)
Once a recommendation is sent, the assigned developer has two options:

#### Option A: Submit a Rebuttal
If you believe the finding is invalid or factually incorrect:
1. Open the recommendation.
2. Click **Submit Rebuttal**.
3. Provide your **Rationale** and any **Supporting Evidence**.
4. Submit. The Validator will review your argument and either **Accept** it (dropping the recommendation) or **Override** it (requiring an action plan).
   * *Note: You only get one chance to rebut. If overridden, you must proceed with an action plan.*

#### Option B: Submit an Action Plan
If you accept the finding and plan to fix it:
1. Open the recommendation.
2. Click **Submit Action Plan**.
3. Add specific **Tasks**, assigning an owner and due date for each.
4. Submit. The recommendation moves to **Pending Validator Review**.
5. The Validator reviews the action plan and either:
   - Approves it (recommendation moves to **Pending Acknowledgement**), or
   - Requests changes (recommendation returns to **Pending Response**).

*Some low-priority recommendations may allow skipping the action plan step (when configured by Admin). In that case, the recommendation still moves through **Pending Validator Review** and **Pending Acknowledgement** before becoming **Open**.*

### 3. Remediation (Developer)
Once the action plan has been approved by the Validator:
1. The recommendation moves to **Pending Acknowledgement**.
2. The assigned developer **Acknowledges** it.
3. The recommendation moves to **Open**.
2. Work through your assigned tasks.
3. As tasks are finished, update their status to **Completed** in the **Action Plan** tab.

### 4. Closing a Recommendation (Developer & Validator)
When all work is done:
1. **Developer**: Upload **Evidence** in the Evidence tab.
2. **Developer**: Click **Submit for Closure**.
   - The system requires all action plan tasks to be completed.
   - The system requires at least one piece of evidence before submission.
2. **Validator**: Review the submission.
   - If satisfactory, click **Approve Closure**.
   - If changes are needed, click **Request Rework** to send it back to the developer (recommendation moves to **Rework Required**).

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

Administrators can customize how each recommendation priority level behaves through the **Priority Workflow Config** section in the Taxonomy page. This allows your organization to tailor the recommendation workflow to match your specific governance policies.

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

**Example Use Case:**
A model deployed in both the US and UK might have different closure requirements:
- **Base Setting (Medium Priority)**: Requires Final Approval = No (US standard)
- **UK Regional Override (Medium Priority)**: Requires Final Approval = Yes (stricter UK regulation)
- **Result**: The same Medium priority recommendation requires approver sign-off only for the UK deployment

### Timeframe Configurations

Timeframe configurations set the maximum number of days allowed for remediation based on priority level. These timeframes are enforced when the **Enforce Timeframes** setting is enabled for that priority.

**How Timeframe Enforcement Works:**
- When creating or editing a recommendation, the system validates the target date against the configured maximum days
- If **Enforce Timeframes** is enabled for the priority level, target dates exceeding the maximum are rejected
- If **Enforce Timeframes** is disabled, any target date is accepted (no validation)
- Timeframes provide guardrails to ensure high-priority issues are remediated within acceptable periods

**Configuration:**
- Each priority level has its own `max_days` setting (e.g., 90 days for High, 180 days for Medium)
- Admins can update max_days values to align with organizational policies
- Setting max_days to a higher value gives more flexibility; lower values enforce tighter deadlines

**Example Use Case:**
Your organization implements the following timeframe policy:
- **High Priority**: max_days = 90 (must be fixed within 3 months)
- **Medium Priority**: max_days = 180 (must be fixed within 6 months)
- **Low Priority**: max_days = 365 (must be fixed within 1 year)
- **Consideration**: max_days = null (no limit, informational only)

When a Validator creates a High priority recommendation with "Enforce Timeframes" enabled, the system will only accept target dates within 90 days of creation. This ensures critical issues receive timely attention according to governance standards.

### Accessing Priority Workflow Config

Admins can access these settings at:
1. Navigate to **Taxonomy** in the main menu
2. Select **Priority Workflow Config** from the dropdown
3. Click **Edit** next to any priority level to modify base settings
4. Expand a priority row (using the arrow icon) to view/add regional overrides
5. Use **+ Add Regional Override** to create region-specific rules

---

## Frequently Asked Questions

**Q: Can I edit a recommendation after sending it?**
A: Partially. Validators/Admins can edit recommendations in **Draft**, **Pending Response**, and **Pending Validator Review**. In **Pending Acknowledgement**, **Open**, and **Rework Required**, editing is limited (typically reassignment and/or target date updates only). Some statuses (e.g., pending closure review, pending approvals, or closed/dropped) do not allow edits.

**Q: What happens if my rebuttal is rejected?**
A: You must submit an Action Plan. The system enforces a "one-strike" rule for rebuttals to prevent indefinite arguments.

**Q: Who can close a Low priority recommendation?**
A: By default, Low priority items are closed immediately after the Validator approves the closure evidence—they do not require Global or Regional sign-off. However, this can be changed by an Admin through the Priority Workflow Config if your organization requires additional oversight.

**Q: Why do I need to provide a reason when changing the target date?**
A: Target dates are validated against configured timeframes (when "Enforce Timeframes" is enabled for that priority level) and require an explanation when changed, to preserve an audit trail.

**Q: Can different regions have different approval requirements?**
A: Yes! Admins can create Regional Overrides that modify workflow settings for specific regions. For example, High priority items might require final approval in the EU but not in the US, reflecting different regulatory requirements.
