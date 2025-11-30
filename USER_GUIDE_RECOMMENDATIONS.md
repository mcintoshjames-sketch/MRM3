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

The lifecycle follows a strict "negotiation" phase followed by a "remediation" phase.

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
5. When ready, click **Finalize & Send** to notify the developer.

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
4. Submit. The Validator will review the plan.

### 3. Remediation (Developer)
Once the Action Plan is approved by the Validator:
1. The recommendation moves to **Open** status.
2. Work through your assigned tasks.
3. As tasks are finished, update their status to **Completed** in the **Action Plan** tab.

### 4. Closing a Recommendation (Developer & Validator)
When all work is done:
1. **Developer**: Click **Submit for Closure**.
   - Upload **Evidence** (documents, screenshots) in the Evidence tab.
   - Provide a **Closure Summary** explaining what was done.
2. **Validator**: Review the submission.
   - If satisfactory, click **Approve Closure**.
   - If evidence is missing, click **Request Rework** to send it back to the developer.

### 5. Final Approvals (Approvers)
For **Medium** and **High** priority items, Validator approval is not enough. The system will automatically request final sign-off:
- **Global Approvers**: Sign off on the overall closure.
- **Regional Approvers**: Sign off if the model is deployed in your region.

Once all required approvals are collected, the recommendation status automatically changes to **Closed**.

---

## Dashboards & Tracking

### My Tasks
Navigate to **Recommendations > My Tasks** to see items requiring your immediate attention:
- **Action Required**: Recommendations assigned to you that need a response or closure submission.
- **Review Pending**: Items waiting for your review (as a Validator).
- **Approval Pending**: Closures waiting for your final sign-off (as an Approver).

### Overdue Reports
The **Overdue Report** highlights recommendations that have passed their target date without being closed. This helps management identify at-risk remediation efforts.

---

## Frequently Asked Questions

**Q: Can I edit a recommendation after sending it?**
A: No. Once sent to the developer, the recommendation is locked to preserve the audit trail. If critical changes are needed, the Validator may need to drop it and create a new one.

**Q: What happens if my rebuttal is rejected?**
A: You must submit an Action Plan. The system enforces a "one-strike" rule for rebuttals to prevent indefinite arguments.

**Q: Who can close a Low priority recommendation?**
A: Low priority items are closed immediately after the Validator approves the closure evidence. They do not require Global or Regional sign-off.
