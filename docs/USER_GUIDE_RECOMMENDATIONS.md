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

## Frequently Asked Questions

**Q: Can I edit a recommendation after sending it?**
A: Partially. Validators/Admins can edit recommendations in **Draft**, **Pending Response**, and **Pending Validator Review**. In **Pending Acknowledgement**, **Open**, and **Rework Required**, editing is limited (typically reassignment and/or target date updates only). Some statuses (e.g., pending closure review, pending approvals, or closed/dropped) do not allow edits.

**Q: What happens if my rebuttal is rejected?**
A: You must submit an Action Plan. The system enforces a "one-strike" rule for rebuttals to prevent indefinite arguments.

**Q: Who can close a Low priority recommendation?**
A: Low priority items are closed immediately after the Validator approves the closure evidence. They do not require Global or Regional sign-off.

**Q: Why do I need to provide a reason when changing the target date?**
A: Target dates are validated against configured timeframes and require an explanation when changed, to preserve an audit trail.
