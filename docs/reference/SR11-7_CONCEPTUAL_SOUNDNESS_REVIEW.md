# SR 11-7 Conceptual Soundness Review

## Executive Summary

This document presents a conceptual soundness review of the Model Risk Management (MRM) application architecture against the requirements of **SR 11-7 (Guidance on Model Risk Management)**.

**Overall Assessment:**
The application architecture demonstrates a **high degree of alignment** with SR 11-7 requirements, particularly in the areas of Model Validation workflow, Governance reporting, and Inventory management. The system moves beyond simple inventory tracking to enforce process controls (e.g., blocking model use without validation, requiring risk assessments) which is a hallmark of a mature MRM system.

However, specific gaps exist in **document management** (storage of model artifacts) and **upstream data lineage** (beyond simple dependency linking), which are critical for full Pillar 1 compliance.

---

## Pillar 1: Model Development, Implementation, and Use

SR 11-7 requires rigorous assessment of data relevance, methodology, and testing during development, along with comprehensive documentation.

### Strengths
*   **Model Versioning:** The `ModelVersion` entity with `change_type` and `change_requires_mv_approval` (as noted in `COMPLIANCE_SNAPSHOT.md`) provides excellent audit trails for model evolution, ensuring no changes go into production without appropriate classification.
*   **Dependency Tracking:** `ModelDependencyMetadata` and `ModelApplication` (MAP) integration allow for the identification of upstream dependencies and IT infrastructure, crucial for assessing implementation risk.
*   **Limitations Management:** The dedicated `ModelLimitation` entity (with "Critical" vs "Non-Critical" classification and "User Awareness" requirements) directly supports the SR 11-7 requirement to identify and communicate model limitations to users.

### Gaps & Recommendations
*   **Document Storage (Artifact Management):**
    *   *Finding:* The architecture describes metadata management but lacks explicit detail on the storage and versioning of actual model documentation (e.g., Whitepapers, Technical Specifications, Test Results).
    *   *Recommendation:* Implement an artifact management system (e.g., S3/Blob storage integration) linked to `ModelVersion` to ensure the "system of record" contains the actual evidence, not just the metadata.
*   **Testing Evidence:**
    *   *Finding:* While `ValidationScorecard` assesses testing, there is no dedicated schema for developers to log *their* testing results (unit tests, backtesting) prior to validation submission.
    *   *Recommendation:* Expand `ModelVersion` to include a "Developer Testing Declaration" or structured test result summary to evidence Pillar 1 testing before Pillar 2 engagement.

---

## Pillar 2: Model Validation

SR 11-7 requires effective challenge, independence, and robust validation processes.

### Strengths
*   **Structured Effective Challenge:** The `ValidationScorecard` system with its granular criteria (Conceptual Soundness, Outcome Analysis) and weighted scoring provides a standardized mechanism for effective challenge, reducing subjectivity.
*   **Independence Enforcement:** The data model explicitly prevents conflicts of interest (e.g., `shared_owner ≠ owner`, `shared_developer ≠ developer`). The `ValidationAssignment` workflow separates the "Validator" role from the "Model Owner".
*   **Process Control:** The `ModelApprovalStatus` logic (NEVER_VALIDATED, APPROVED, EXPIRED) programmatically enforces validation requirements. The system correctly treats validation as a gating item for "Approved" status.
*   **Issue Tracking:** The `Recommendation` system with "Action Plans," "Rebuttals," and "Closure Workflow" is highly aligned with the requirement to track validation findings to resolution.

### Gaps & Recommendations
*   **Validation Tiering Logic:**
    *   *Finding:* While `ValidationPolicy` defines frequency based on risk tier, SR 11-7 also emphasizes that the *intensity* of validation should vary.
    *   *Recommendation:* Ensure `ValidationPlan` creation allows for scoping the *depth* of review (e.g., Full Scope vs. Limited Scope) explicitly in the UI, driving different Scorecard templates.
*   **Vendor Model Validation:**
    *   *Finding:* The system tracks "Vendor" models, but SR 11-7 has specific requirements for vendor model validation (contingency plans, understanding proprietary code).
    *   *Recommendation:* Add specific `ValidationScorecard` sections or `RiskAssessment` factors unique to Vendor models (e.g., "Vendor Contingency Planning", "Black Box Testing Adequacy").

---

## Pillar 3: Governance, Policies, and Controls

SR 11-7 requires Board oversight, comprehensive policies, and an accurate inventory.

### Strengths
*   **Comprehensive Inventory:** The `Model` entity, combined with `Attestation` workflows, ensures the inventory remains accurate. The `ModelSubmissionWorkflow` captures "candidate" models, preventing shadow modeling.
*   **Risk Tiering:** The `ModelRiskAssessment` module (Qualitative/Quantitative factors) provides a defensible, standardized method for assigning Risk Tiers (Tier 1-4), which drives governance intensity.
*   **Performance Monitoring:** The `MonitoringPlan` and `MonitoringCycle` modules with `KPM` (Key Performance Metrics) directly support the requirement for ongoing monitoring. The "Red/Yellow/Green" thresholds enable exception-based reporting.
*   **Reporting:** The `KPI Report`, `Regional Compliance Report`, and `Overdue Revalidation` tracking provide Senior Management and the Board with the necessary visibility into the aggregate risk profile.

### Gaps & Recommendations
*   **Model Use Control (Inventory vs. Reality):**
    *   *Finding:* The system tracks where a model *should* be used (`ModelRegion`), but lacks a feedback loop to verify where it *is* actually running (e.g., via API logs or IT asset linkage).
    *   *Recommendation:* Strengthen the `ModelApplication` link to potentially ingest "Last Called Date" or "Execution Volume" from the IT environment to verify active status vs. inventory status.
*   **Policy Exception Management:**
    *   *Finding:* While `OverdueRevalidationComment` tracks delays, a broader "Policy Exception" framework might be needed for other deviations (e.g., using an unvalidated model in an emergency).
    *   *Recommendation:* Generalize the `Exceptions` tracking to cover non-validation exceptions (e.g., Monitoring delays, Risk Assessment overrides) for a consolidated "Breaches" report.

---

## Inventory Data Quality & Completeness

SR 11-7 requires banks to "maintain a comprehensive set of information for models," including purpose, design, functioning, and use.

### Findings
*   **Minimum Fields:** The current data model enforces very few fields at creation:
    *   `model_name` (Required)
    *   `owner_id` (Required)
    *   `usage_frequency_id` (Required)
    *   `development_type` (Defaults to "In-House")
*   **Critical Gaps:**
    *   **Description/Purpose:** The `description` field is **optional** in the database and API schema. A model inventory record without a description of purpose fails the basic "Identification" requirement of SR 11-7.
    *   **Developer Attribution:** `developer_id` is **optional**. While appropriate for "Vendor" models, "In-House" models must have an attributed developer or development team to ensure accountability (Pillar 1).
    *   **Implementation Date:** `initial_implementation_date` is optional, making it difficult to track the "age" of a model or its time-in-production.

### Recommendations
1.  **Enforce Description:** Make `description` a required field for all models to ensure the "Purpose" is documented.
2.  **Conditional Logic for Developer:** Enforce `developer_id` when `development_type` is "In-House".
3.  **Mandatory Dates:** Require `initial_implementation_date` (or "Target Implementation Date") to support aging analysis.

---

## Conclusion

The application is **conceptually sound** and provides a robust technical foundation for SR 11-7 compliance. It excels in workflow enforcement and reporting. The primary areas for enhancement involve deepening the integration with the "physical" model artifacts (documents, code, runtime stats) to bridge the gap between the "Inventory Record" and the "Actual Model."
