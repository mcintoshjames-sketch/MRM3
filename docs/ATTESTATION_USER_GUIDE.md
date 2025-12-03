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
8. [Frequently Asked Questions](#frequently-asked-questions)

---

## Key Concepts

### Attestation Cycle
A time-bound period during which model owners must review and attest to their models. Each cycle has:
- **Period dates**: The timeframe being attested (e.g., Q4 2025)
- **Submission due date**: Deadline for model owners to submit attestations
- **Status**: Pending (not yet started), Open (active), or Closed (complete)

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
   - Current status (Pending, Submitted, Accepted, Rejected)
   - Due date with urgency indicator

### Completing an Attestation

1. **Click on a model** to open the attestation form
2. **Answer each question** by selecting Yes or No:
   - "Yes" confirms the statement is accurate
   - "No" indicates an issue or change is needed
   - If you answer "No", you must provide an explanation
3. **Add supporting evidence** (optional but recommended):
   - Click "Add Evidence"
   - Enter a URL to supporting documentation
   - Provide a brief description
4. **Propose inventory changes** if needed:
   - **Update Model**: Suggest changes to an existing model's information
   - **Register New Model**: Report a new model that should be added to inventory
   - **Decommission Model**: Request removal of a model no longer in use
5. **Submit your attestation** when complete

### Understanding Urgency Indicators

| Indicator | Meaning |
|-----------|---------|
| Green | On track - due date is more than 7 days away |
| Yellow | Due soon - within 7 days of deadline |
| Red | Overdue - past the submission deadline |

### If Your Attestation is Rejected

If an administrator rejects your attestation:
1. You'll see the rejection reason in the attestation details
2. The attestation returns to "Pending" status
3. Address the feedback and resubmit

---

## For Administrators

### Managing Attestation Cycles

Navigate to **"Attestations"** in the Admin section. This page has five tabs: **Cycles**, **Scheduling Rules**, **Coverage Targets**, **Review Queue**, and **High Fluctuation Owners**.

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
   - Generates attestation records for all eligible models
   - Notifies model owners (if notifications are enabled)
   - Starts the attestation period

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

### Reviewing Attestation Change Proposals

When model owners propose inventory changes during attestation:

1. Navigate to **Admin Dashboard**
2. Find the **"Pending Attestation Changes"** widget
3. Click a proposal to view details
4. Review the proposed change:
   - **Update Existing**: Changes to model metadata
   - **New Model**: Request to add a model to inventory
   - **Decommission**: Request to remove a model
5. **Accept** to approve the change, or **Reject** with an explanation

---

## For Reviewers

Reviewers (Administrators) can review submitted attestations.

### Reviewing Attestations

1. Navigate to **"Attestations"** > **Review Queue** tab
2. Click on a submitted attestation
3. Review:
   - Model owner's responses to each question
   - Any comments or explanations provided
   - Supporting evidence attached
   - Proposed inventory changes
4. Make a decision:
   - **Accept**: Approve the attestation as complete
   - **Reject**: Return to owner with feedback (comment required)

### Review Best Practices

- Verify "No" answers have adequate explanations
- Check that proposed changes are actionable
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
- The cycle cannot be closed until gaps are resolved
- Options:
  - Follow up with model owners to complete attestations
  - Adjust targets if business circumstances warrant

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
2. View existing rules with their type, frequency, and criteria
3. **Create Rule**:
   - Select rule type
   - Set frequency (Annual or Quarterly)
   - Configure type-specific criteria
   - Set priority
4. **Edit** or **Delete** existing rules as needed

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

## Frequently Asked Questions

### For Model Owners

**Q: How do I know which models I need to attest?**
A: Navigate to "My Attestations" - all models requiring your attestation are listed with their due dates.

**Q: What if I'm not the right person to attest a model?**
A: Contact your administrator to update the model ownership. Do not submit an attestation for a model you don't own.

**Q: Can I save my attestation and finish later?**
A: Yes, your responses are saved as you go. The attestation remains in "Pending" status until you click Submit.

**Q: What evidence should I provide?**
A: Relevant documentation such as model validation reports, performance monitoring results, or change control records. Links to internal systems or document repositories are acceptable.

**Q: What happens if I miss the deadline?**
A: Your attestation will show as "Overdue" and may be escalated to management. Complete it as soon as possible.

### For Administrators

**Q: Can I extend the deadline for a cycle?**
A: The submission due date cannot be changed after the cycle is opened. Plan deadlines carefully before opening.

**Q: What if a model owner leaves the company mid-cycle?**
A: Reassign model ownership to another user. The new owner will see the pending attestation.

**Q: How do I handle models that are being decommissioned?**
A: Model owners can propose decommissioning during attestation. Review and accept the proposal, then follow your organization's decommissioning process.

**Q: Can I manually mark an attestation as complete?**
A: Administrators can accept attestations on behalf of owners if necessary, but this should be documented with a clear reason.

### Technical Questions

**Q: How are models assigned to owners for attestation?**
A: Each model has an assigned owner in the model inventory. When a cycle opens, attestation records are created for each model-owner pairing.

**Q: What determines if I attest annually or quarterly?**
A: Scheduling rules set by administrators. Check with your MRM team if you're unsure of your attestation schedule.

**Q: Are attestation records kept for audit purposes?**
A: Yes, all attestation history is retained including responses, evidence, change proposals, and reviewer decisions.

---

## Getting Help

For questions or issues with the attestation module:
- Contact your Model Risk Management team
- Refer to your organization's MRM policies
- Report technical issues to IT support

---

*Last Updated: December 2025*
