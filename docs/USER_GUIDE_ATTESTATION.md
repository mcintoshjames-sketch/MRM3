# Model Risk Attestation User Guide

## Overview

The Model Risk Attestation module enables organizations to conduct periodic attestations of their model inventory. Model owners review their assigned models and confirm that model information remains accurate, identifying any changes needed to keep the inventory current.

This guide explains how to use the attestation features from each user role's perspective.

---

## Table of Contents

1. [Key Concepts](#key-concepts)
2. [For Model Owners](#for-model-owners)
3. [For Administrators](#for-administrators)
4. [For Reviewers](#for-reviewers)
5. [Coverage Targets & Compliance](#coverage-targets--compliance)
6. [Scheduling Rules](#scheduling-rules)
7. [High Fluctuation Owners](#high-fluctuation-owners)
8. [All Records View](#all-records-view)
9. [Questions Configuration](#questions-configuration)
10. [Frequently Asked Questions](#frequently-asked-questions)

---

## Key Concepts

### Attestation Cycle
A time-bound period during which model owners must review and attest to their models. Each cycle has:
- **Period dates**: The timeframe being attested (e.g., Q4 2025)
- **Submission due date**: Deadline for model owners to submit attestations
- **Status**: PENDING (not yet started), OPEN (active), UNDER_REVIEW (admin review gating), or CLOSED (complete)

### Attestation Record
An individual attestation for a specific model within a cycle. Each record tracks:
- The model being attested
- The model owner responsible for attestation
- Responses to attestation questions
- Supporting evidence (documents, links)
- Any proposed inventory changes

### Coverage Target
The minimum percentage of models that must be attested within each risk tier to close a cycle. High-risk models typically require higher coverage percentages.

### Scheduling Rule
Rules that determine how frequently different model owners must attest. Some owners may need to attest quarterly instead of annually based on specific criteria.

---

## For Model Owners

### Finding Your Attestations

1. Click **"My Attestations"** in the navigation menu
2. You'll see a list of models requiring your attestation
3. Each model shows:
   - Model name and risk tier
   - Current status (Pending, Submitted - Pending Review, Accepted, or Rejected)
   - Due date with urgency indicator
4. Above the model list, you'll find the **"Register New Model"** button to add new models to the inventory

**Note:** If you have been granted delegate attestation rights for other models, those attestations appear here as well and can be completed the same way.

### Completing an Attestation

1. **Click on a model** to open the attestation form
2. **Answer each question** by selecting Yes or No:
   - "Yes" confirms the statement is accurate
   - "No" indicates an issue or change is needed
   - If you answer "No", you must provide an explanation
3. **Supporting evidence**: Evidence capture is not currently available in the attestation form UI. Document any supporting materials in your attestation comments if needed.
4. **Make inventory changes** if needed using the navigation buttons:
   - **Edit Model Details**: Opens the model edit form to update model information
   - **Submit Model Change**: Opens the model change submission form to create a versioned change record
   - **Decommission Model**: Opens the decommissioning request form
   - Changes made through these forms are automatically linked to your attestation
   - **Note**: To register a new model, use the "Register New Model" button on the My Attestations page
5. **Submit your attestation** when complete

**Note:** Clean attestations (all "Yes" answers with no comments or linked changes) are automatically accepted, so you'll see "Accepted" status immediately. Attestations with "No" answers go to the review queue.

### Delegating Attestation Rights

Model owners can assign delegates to attest on their behalf.

1. Open the model's details page
2. Expand **"Manage Delegates"**
3. Click **"Add Delegate"**
4. Select a user and enable **"Can submit attestations on behalf of the owner"**
5. Save the delegation

Delegates see the model on **"My Attestations"** and can submit attestations with the same due dates.

You can also grant optional permissions to submit model changes or manage regional configurations; attestation permission is separate.

**Who can manage delegates:** Model owners, validators, and administrators.

### Understanding Urgency Indicators

| Badge | Meaning |
|-------|---------|
| **Due Soon** (orange) | Within 7 days of the submission deadline |
| **Overdue** (red) | Past the submission deadline |
| *No badge* | Due date is more than 7 days away |

### If Your Attestation is Rejected

If an administrator rejects your attestation:
1. You'll see the rejection reason in the attestation details
2. Status becomes **Rejected** (the attestation remains editable)
3. You can edit your responses and resubmit

### Dashboard Attestation Alert

Your **My Dashboard** page displays a prominent alert when you have pending attestations:

- **Yellow alert**: You have pending attestations due within the deadline
  - Shows count of pending attestations
  - Shows days until due date
  - Links directly to "My Attestations" page

- **Red alert**: You have overdue attestations that need immediate attention
  - Shows count of overdue attestations
  - Shows any additional pending attestations
  - Links directly to "My Attestations" page

The alert appears automatically whenever you have attestations requiring action, ensuring you never miss a deadline.

### Bulk Attestation

If you own multiple models, you can use **Bulk Attestation** to submit attestations for all your models at once with the same responses, saving significant time.

#### When to Use Bulk Attestation

Bulk attestation is ideal when:
- You own many models requiring attestation
- The same answers apply to all (or most) of your models
- You want to complete attestations efficiently

#### Using Bulk Attestation

1. Navigate to **"My Attestations"**
2. Click **"Bulk Attest"** button (appears when you have 2+ pending models)
3. The Bulk Attestation page shows:
   - **All your pending models** listed with checkboxes
   - **Attestation questions** to answer once for all selected models
   - **Summary counts** showing pending, excluded, and submitted models

4. **Select models** to include:
   - By default, all pending models are selected
   - Uncheck any models you want to exclude from bulk attestation
   - Excluded models will need to be attested individually

5. **Answer the attestation questions**:
   - Your answers will apply to ALL selected models
   - If you answer "No", provide an explanation as required

6. **Save as Draft** (optional):
   - Click "Save Draft" to save your progress
   - Your selections and answers are preserved
   - Return later to complete and submit

7. **Submit** when ready:
   - Click "Submit Bulk Attestation"
   - All selected models are submitted with your responses
   - Excluded models remain pending for individual attestation
   - Clean attestations (all "Yes", no comments) are automatically accepted

#### Excluding Models from Bulk Attestation

If a model needs different answers than the rest:
1. **Uncheck the model** in the bulk attestation form
2. The model is marked as "Excluded"
3. After submitting bulk attestation, **attest the excluded model individually**
4. Individual attestation allows model-specific responses

#### Draft Mode

Bulk attestation supports auto-save drafts:
- Your selections and answers auto-save approximately 5 seconds after changes
- "Save Draft" is available for immediate persistence if needed
- If you leave the page, your progress is preserved
- Return to "My Attestations" > "Bulk Attest" to resume
- Drafts are cleared when you submit or the cycle closes

#### Important Notes

- You must answer all questions (Yes/No) before submitting; drafts can be incomplete
- Bulk attestation **does not support inventory changes** (new model, edit, decommission)
- If you need to make inventory changes for a model, exclude it and attest individually
- All selected models receive the same decision (I Attest / I Attest with Updates)
- Evidence links are not supported in bulk mode

---

## For Administrators

### Managing Attestation Cycles

Navigate to **"Attestations"** in the Admin section. This page has eight tabs: **Cycles**, **Scheduling Rules**, **Coverage Targets**, **Review Queue**, **High Fluctuation Owners**, **All Records**, **Linked Changes**, and **Questions**.

#### Creating a New Cycle

1. Click **"Create Cycle"**
2. Enter cycle details:
   - **Cycle Name**: Descriptive name (e.g., "Q1 2026 Annual Attestation")
   - **Period Start/End**: The business period being attested
   - **Submission Due Date**: Deadline for owner submissions
   - **Notes**: Optional instructions or context
3. Click **"Create"**

The cycle starts in "Pending" status and doesn't affect model owners until opened.

#### Opening a Cycle

1. Find the cycle in the list
2. Click **"Open Cycle"**
3. This action:
   - **Evaluates scheduling rules** to determine which models are due for attestation
   - **Generates attestation records** for each due model, assigned to the model's owner
   - **Sets status to OPEN** and records when/who opened the cycle
   - **Notifies model owners** via the sidebar badge count in "My Attestations"

**How Models Are Selected:**

When a cycle opens, the system evaluates each active model against the configured scheduling rules:

1. For each model, the system finds the highest-priority applicable rule
2. Rules are evaluated in priority order: Model Override > Regional Override > Owner Threshold > Global Default
3. The rule determines the attestation frequency (Annual or Quarterly)
4. If the model is due based on its frequency and last attestation date, an attestation record is created
5. The attestation is assigned to the model's owner with the cycle's submission due date

**Example:**
- If Global Default is Annual, most models attest once per year
- If an Owner Threshold rule requires Quarterly for high fluctuation owners, those owners' models appear in every cycle
- If a Model Override sets Quarterly for a specific critical model, that model appears in every cycle regardless of owner

#### Monitoring Progress

The Cycles tab shows real-time progress:
- **Progress bar**: Percentage of attestations completed
- **Counts**: Accepted/Total completed

Below the cycles table, the **Coverage vs. Targets** widget displays:
- Coverage percentage by risk tier
- Target percentage required
- Gap indicator (Met/Not Met)
- Blocking status (whether gaps prevent cycle closure)

#### Closing a Cycle

1. Ensure coverage targets are met (or override if necessary)
2. Click **"Close Cycle"**
3. The cycle becomes read-only for historical reference

### Dashboard Reminders

The Admin Dashboard displays a **Cycle Reminder Banner** when:
- A new quarter begins
- No attestation cycle is currently open
- It's time to create and open a new cycle

### Attestation Review Queue Alert

The Admin Dashboard displays a prominent **Review Queue Alert** when:
- There are attestations with SUBMITTED status awaiting review
- The alert shows the count of pending reviews
- Click **"View Review Queue"** to navigate directly to the Review Queue tab

This ensures administrators are promptly notified when model owners submit attestations that need approval.

### Delegation Management (Admin)

Administrators can manage delegates in bulk from **"Batch Delegates"** in the Admin navigation.

1. Select the target owner or developer
2. Choose the delegate user
3. Set permissions (attest, submit changes, manage regional)
4. Apply to all models, with an option to replace existing delegates

### Viewing Linked Inventory Changes

When model owners make inventory changes during attestation (edit models, submit model changes, register new models, or request decommissioning), these changes are automatically linked to their attestation for tracking purposes.

- **Linked changes are displayed** in the attestation detail view under "Linked Inventory Changes"
- **Approval happens in existing workflows** - model edits go through the Model Pending Edits approval queue, model changes follow the Submit Model Change workflow, and decommissioning requests go through the Decommissioning approval workflow
- **No duplicate approval** is needed in the attestation system

### Linked Changes Tab

Use the **Linked Changes** tab to review all inventory changes linked to attestations across cycles.

- Filter by cycle or change type (Model Edit, Model Change, New Model, Decommission)
- Open the related attestation from the Actions column
- Use the Target/Details links to navigate to the related model or workflow

---

## For Reviewers

Reviewers (Administrators) can review submitted attestations.

### Auto-Accepted Attestations

The system automatically accepts "clean" attestations to reduce reviewer workload. An attestation is auto-accepted when:
- **All questions are answered "Yes"** (no issues identified)
- **No optional comments are provided** (nothing requiring review)
- **No linked inventory changes** (no edits, new models, or decommissions linked)

Auto-accepted attestations:
- Move directly to ACCEPTED status without manual review
- Are recorded in the audit log with action "AUTO_ACCEPT"
- Still appear in historical reports and the All Records view
- Free up reviewer time to focus on attestations that need attention

### Reviewing Attestations

For attestations that require manual review:

1. Navigate to **"Attestations"** > **Review Queue** tab
2. Click on a submitted attestation
3. Review:
   - Model owner's responses to each question
   - Any comments or explanations provided
   - Supporting evidence attached
   - Linked inventory changes (view-only, approved through their own workflows)
4. Make a decision:
   - **Accept**: Approve the attestation as complete
   - **Reject**: Return to owner with feedback (comment required)

### Review Best Practices

- Verify "No" answers have adequate explanations
- Check linked changes are being processed through their respective approval workflows
- Ensure supporting evidence is relevant
- Provide clear, constructive feedback when rejecting

---

## Coverage Targets & Compliance

### Understanding Coverage Targets

Coverage targets ensure adequate attestation completion across the model inventory. Each risk tier has:

- **Target Percentage**: Minimum % of models that must be attested
- **Blocking Status**: Whether missing the target prevents cycle closure

### Typical Configuration

| Risk Tier | Target | Blocking |
|-----------|--------|----------|
| Tier 1 (High Risk) | 100% | Yes |
| Tier 2 (Medium Risk) | 95% | Yes |
| Tier 3 (Low Risk) | 80% | No |

### Managing Coverage Targets

1. Go to **Attestations** > **Coverage Targets** tab
2. View current targets by risk tier
3. Click **Edit** to modify a target:
   - Adjust the target percentage
   - Toggle blocking status
4. Save changes

### Blocking Gaps

If a cycle has blocking coverage gaps:
- A warning banner appears on the Cycles tab
- The cycle cannot be closed normally until gaps are resolved
- Options:
  - Follow up with model owners to complete attestations
  - Adjust targets if business circumstances warrant
  - **Force Close** (Admin only): Administrators can force-close a cycle with blocking gaps by clicking "Force Close", providing a required justification reason for audit purposes

---

## Scheduling Rules

Scheduling rules determine attestation frequency for model owners. By default, all owners attest annually, but rules can require more frequent attestation.

### Rule Types

| Type | Description |
|------|-------------|
| **Global Default** | Applies to all model owners (typically Annual) |
| **Owner Threshold** | Triggers quarterly attestation based on owner criteria |
| **Model Override** | Sets specific frequency for an individual model |
| **Regional Override** | Sets frequency for models deployed in a specific region |

### Rule Priority

When multiple rules could apply, the highest priority rule wins:
- Higher priority number = higher precedence
- Example: A Model Override (priority 50) beats Global Default (priority 10)

### Managing Rules

1. Go to **Attestations** > **Scheduling Rules** tab
2. View existing rules with their type, frequency, criteria, and date window
3. **Create Rule**:
   - Select rule type
   - Set frequency (Annual or Quarterly)
   - Configure type-specific criteria
   - Set priority
   - Set effective date (when rule starts applying)
   - Optionally set end date (when rule expires)
4. **Edit** existing rules to modify frequency, priority, criteria, or end date
5. **Deactivate** rules that are no longer needed (retained for audit purposes)

### Rule Date Windows

Each rule has an effective date and optional end date:
- **Effective Date**: When the rule starts applying (required, immutable after creation)
- **End Date**: When the rule expires (optional, can be modified)
- Rules without an end date remain active indefinitely

### Immutable Fields

After creation, certain rule fields cannot be changed:
- **Rule Type**: Cannot change from Global Default to Model Override, etc.
- **Effective Date**: Establishes when the rule started
- **Target**: Model or Region assignments cannot be modified

To change these fields, deactivate the existing rule and create a new one.

### Validation Requirements

- **Owner Threshold rules** must have at least one criterion (minimum model count or high fluctuation flag)
- **Global Default rules**: Only one active Global Default rule can exist at a time

### High Fluctuation Flag

Model owners can be flagged for "High Fluctuation" if their model portfolio changes frequently. This flag:
- Is set by administrators via the High Fluctuation Owners tab
- Can be used as criteria in Owner Threshold rules
- Typically triggers quarterly attestation requirements

---

## High Fluctuation Owners

### What is High Fluctuation?

Model owners flagged as "High Fluctuation" have portfolios that change frequently (models added, removed, or transferred between owners). These owners are typically required to attest **quarterly** instead of annually to ensure accurate model inventory records.

### When to Flag an Owner

Consider flagging an owner as high fluctuation when:
- They frequently acquire or transfer models (more than 5 changes per year)
- Their business unit undergoes frequent reorganization
- They manage models in rapidly evolving product areas
- Historical attestation data shows frequent inventory discrepancies

### Managing High Fluctuation Owners

1. Go to **Attestations** > **High Fluctuation Owners** tab
2. View the current list of flagged owners with their details

#### Adding an Owner

1. Use the search box to find the user by name or email
2. Click **"Add"** next to the user in the search results
3. The user is immediately added to the high fluctuation list

#### Removing an Owner

1. Find the owner in the current list
2. Click **"Remove"** in the Actions column
3. The flag is immediately removed

### How It Works with Scheduling Rules

The high fluctuation flag works in conjunction with **Owner Threshold** scheduling rules:

1. Create a rule with type "Owner Threshold"
2. Check "High Fluctuation Flag Required"
3. Set frequency to "Quarterly"
4. When a cycle opens, owners with the flag will be scheduled for quarterly attestation

**Example Configuration:**
- Rule: "High Fluctuation Quarterly"
- Type: Owner Threshold
- Criteria: High Fluctuation Flag = Yes
- Frequency: Quarterly
- Priority: 30

### Best Practices

- Review the high fluctuation list quarterly
- Remove the flag when an owner's portfolio stabilizes
- Document the reason for flagging in the user's notes
- Coordinate with business units on portfolio changes

---

## All Records View

The **All Records** tab provides administrators with a comprehensive view of all attestation records across the inventory, grouped by model owner.

### Overview

This view enables administrators to:
- Monitor attestation progress for all model owners
- Identify owners with pending or overdue attestations
- Track completion status across the entire model inventory
- Filter by specific attestation cycle

### Using the All Records Tab

1. Go to **Attestations** > **All Records** tab
2. Use the **Cycle Filter** dropdown to view records from a specific cycle or all cycles
3. Click on an **owner's row** to expand/collapse their model details
4. Use **Expand All** / **Collapse All** buttons for bulk control

### Summary Statistics

The top of the page displays:
- **Total Records**: Number of attestation records
- **Owners**: Count of unique model owners
- **Pending**: Attestations not yet submitted
- **Submitted**: Attestations awaiting review
- **Accepted**: Approved attestations
- **Overdue**: Past-due attestations

### Owner Groups

Each owner section shows:
- **Header**: Owner name, model count, and status badges
- **Status Badges**: Quick view of Pending, Submitted, Accepted, Rejected, and Overdue counts
- **Expandable Table**: Detailed view of each model's attestation

### Model Details (Expanded View)

When expanded, each model shows:
| Column | Description |
|--------|-------------|
| Model | Model name (clickable link to model details) |
| Risk Tier | Model's risk classification |
| Cycle | Attestation cycle name |
| Due Date | Submission deadline (highlighted red if overdue) |
| Status | Current attestation status |
| Decision | Owner's attestation decision |
| Attested At | Date/time of submission |
| Actions | Link to view full attestation |

### Visual Indicators

- **Red background**: Overdue attestation records
- **Days overdue**: Shown next to due date for overdue items
- **Color-coded badges**: Status and decision badges use consistent colors

---

## Questions Configuration

The **Questions** tab allows administrators to manage the attestation survey questions that model owners answer during the attestation process.

### Accessing Questions Configuration

1. Go to **Attestations** > **Questions** tab
2. View all attestation questions with their configuration settings

### Question Properties

Each question has the following configurable properties:

| Property | Description |
|----------|-------------|
| **Question Text** | The text shown to model owners during attestation |
| **Description** | Optional helper text explaining the question |
| **Sort Order** | Determines the display order in the attestation form |
| **Frequency Scope** | When the question appears (Annual, Quarterly, or Both) |
| **Require Comment if No** | If enabled, model owners must provide a comment when answering "No" |
| **Active** | Whether the question appears in attestations |

### Editing a Question

1. Click **Edit** next to the question you want to modify
2. Update the desired fields:
   - Modify the question text or description
   - Change the frequency scope to control when it appears
   - Adjust sort order to reorder questions
   - Toggle "Require comment if No" for mandatory explanations
   - Set Active/Inactive to show or hide the question
3. Click **Save Changes** to apply updates

### Frequency Scope Options

| Option | Description |
|--------|-------------|
| **Both** | Question appears in all attestation cycles (default) |
| **Annual** | Question only appears in annual attestation cycles |
| **Quarterly** | Question only appears in quarterly attestation cycles |

When a model owner opens an attestation, only questions matching the cycle's frequency appear. Annual cycles show Annual + Both questions, and quarterly cycles show Quarterly + Both.

### Important Notes

- **Question codes cannot be changed** after creation to maintain data integrity
- To add a new question, use the Taxonomy page to add a value to the "Attestation Question" taxonomy
- Changes take effect immediately for new attestations (existing in-progress attestations are not affected)
- Deactivating a question hides it from future attestations but preserves historical responses

---

## Frequently Asked Questions

### For Model Owners

**Q: How do I know which models I need to attest?**
A: Navigate to "My Attestations" - all models requiring your attestation are listed with their due dates.

**Q: What if I'm not the right person to attest a model?**
A: Contact your administrator to update the model ownership. Do not submit an attestation for a model you don't own.

**Q: Can I save my attestation and finish later?**
A: Your responses are retained in the page while you're working, but they are not persisted to the server until you submit. If you refresh the page, you may lose in-progress changes. For bulk attestation, drafts auto-save after a few seconds.

**Q: What evidence should I provide?**
A: Relevant documentation such as model validation reports, performance monitoring results, or change control records. Links to internal systems or document repositories are acceptable.

**Q: What happens if I miss the deadline?**
A: Your attestation will show as "Overdue" and may be escalated to management. Complete it as soon as possible.

**Q: How do I know if I have pending attestations?**
A: Check your "My Dashboard" page - a prominent alert appears at the top when you have pending or overdue attestations, showing the count and days until due. You can also check the "My Attestations" page directly.

**Q: Why was my attestation automatically accepted?**
A: Clean attestations (all "Yes" answers with no comments or linked changes) are auto-accepted to streamline the process. This means no issues were identified and no review is needed.

### For Administrators

**Q: Can I extend the deadline for a cycle?**
A: After a cycle is opened, you cannot edit any cycle fields (name, period dates, submission due date, or notes). Plan and verify details before opening.

**Q: What if a model owner leaves the company mid-cycle?**
A: Reassign model ownership to another user. The new owner will see the pending attestation.

**Q: How do I handle models that are being decommissioned?**
A: Model owners can propose decommissioning during attestation. Review and accept the proposal, then follow your organization's decommissioning process.

**Q: Can I manually mark an attestation as complete?**
A: Administrators can accept attestations on behalf of owners if necessary, but this should be documented with a clear reason.

**Q: How do I know when attestations need my review?**
A: The Admin Dashboard shows a prominent blue alert when there are attestations awaiting review, with a count and quick link to the Review Queue. You can also check the Review Queue tab in the Attestations page directly.

**Q: Why don't I see some submitted attestations in the review queue?**
A: Clean attestations (all "Yes" answers with no comments or linked changes) are automatically accepted and bypass the review queue. Only attestations requiring attention appear for manual review.

### Technical Questions

**Q: How are models assigned to owners for attestation?**
A: Each model has an assigned owner in the model inventory. When a cycle opens, attestation records are created for each model-owner pairing.

**Q: What determines if I attest annually or quarterly?**
A: Scheduling rules set by administrators. Check with your MRM team if you're unsure of your attestation schedule.

**Q: Are attestation records kept for audit purposes?**
A: Yes, all attestation history is retained including responses, evidence, linked inventory changes, and reviewer decisions.

---

## Getting Help

For questions or issues with the attestation module:
- Contact your Model Risk Management team
- Refer to your organization's MRM policies
- Report technical issues to IT support

---

*Last Updated: December 2025*
