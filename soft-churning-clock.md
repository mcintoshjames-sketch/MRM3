# Performance Monitoring UAT Exercise Plan

## Overview
This UAT exercise will test the complete Performance Monitoring feature based on the USER_GUIDE_PERFORMANCE_MONITORING.md documentation. I will use Puppeteer MCP to navigate through the application, execute test scenarios, and capture screenshots at each step.

**All test data will be created from scratch** as part of this UAT to validate the full end-to-end workflow.

## Pre-requisites
- [x] Docker services running (`docker compose up`) - CONFIRMED
- [x] Backend accessible at http://localhost:8001
- [x] Frontend accessible at http://localhost:5174
- [x] Admin credentials: `admin@example.com` / `admin123`

## Implementation Verification (Confirmed via Code Review)

**Exception Detection Rules - VERIFIED:**
1. **Recommendation linkage is PER-METRIC** (`plan_metric_id`)
   - Code: `api/app/core/exception_detection.py` lines 219-234
   - A recommendation for PSI does NOT suppress KS Statistic exception
   - Scenario A test design is correct

2. **Persistent RED detection runs AUTOMATICALLY on cycle approval**
   - Code: `api/app/api/monitoring.py` lines 3923-3930
   - Called when all required approvals complete
   - Scenario B test design is correct

3. **Exception source linkage**: via `monitoring_result_id`
   - To view metric name: exception → monitoring_result → plan_metric → kpm.name
   - Exception description also includes result ID and cycle ID

## Screenshot Storage
Screenshots will be saved to NAS: `/Volumes/Content/MCPScreenShots/`
Using: `node scripts/screenshot.js <url> <filename>`

## UAT Test Scenarios

### Phase 0: Test Data Setup (3 screenshots)
**Note**: The seed data includes models but we need to verify/create models suitable for monitoring.

0a. **Verify Available Models**
    - Check existing seeded models (e.g., Credit Risk models)
    - Screenshot: Models list showing available models
    - Select 2-3 models for monitoring plan scope:
      - Model A: Will have GREEN results
      - Model B: Will have YELLOW results
      - Model C: Will have RED results (for exception testing)

0b. **Create Additional Test Model (if needed)**
    - If insufficient models exist, create via Models page
    - Required fields: Name, Owner, Risk Tier, etc.
    - Screenshot: Model creation form
    - Screenshot: Model created successfully

### Phase 1: Login & Navigation (2 screenshots)
1. **Login as Admin**
   - Navigate to http://localhost:5174/login
   - Enter admin credentials
   - Screenshot: Login page
   - Screenshot: Post-login dashboard

### Phase 2: Monitoring Teams Management (4 screenshots)
2. **Access Monitoring Plans Page**
   - Navigate to Monitoring Plans from sidebar
   - Screenshot: Monitoring Plans overview

3. **Create a Monitoring Team**
   - Go to "Monitoring Teams" tab
   - Click "Create Team"
   - Fill in: Name="Credit Risk Monitoring Team", add members
   - Screenshot: Team creation modal
   - Screenshot: Team list after creation

### Phase 3: Monitoring Plan Creation (6 screenshots)
4. **Create a New Monitoring Plan**
   - Go to "Monitoring Plans" tab
   - Click "Create Plan"
   - Fill in:
     - Name: "Credit Scorecard Monitoring Q4 2025"
     - Frequency: Quarterly
     - Monitoring Team: Select the team created
     - Data Provider: Select a user
   - Screenshot: Plan creation form
   - Screenshot: Plan created successfully

5. **Add Models to Plan**
   - Open the newly created plan
   - Go to "Models" tab
   - Add 2-3 models to the plan scope
   - Screenshot: Model selection interface
   - Screenshot: Models added to plan

6. **Configure Metrics**
   - Go to "Metrics" tab
   - Click "Add Metric"
   - Configure a quantitative metric (e.g., KS Statistic with thresholds)
   - Configure a qualitative metric
   - Screenshot: Metric configuration modal with thresholds
   - Screenshot: Metrics list after configuration

### Phase 4: Plan Versioning (3 screenshots)
7. **Publish a Version**
   - Go to "Versions" tab
   - Click "Publish New Version"
   - Enter version name: "Initial Configuration"
   - Set effective date
   - Screenshot: Version publish modal
   - Screenshot: Version published successfully
   - Screenshot: Version history showing snapshot

### Phase 5: Cycle 1 Workflow - Exception Scenario A (14 screenshots)
**Goal**: Complete Cycle 1 with ONE RED metric having NO recommendation → triggers Type 1 exception

8. **Create and Start Cycle 1**
   - Go to "Cycles" tab (or use advance-cycle)
   - Verify cycle is created in PENDING status
   - Screenshot: Cycle list showing PENDING cycle (capture status transition evidence)
   - Start the cycle
   - Screenshot: Cycle started (DATA_COLLECTION status)

9. **Enter Monitoring Results for Cycle 1**
   - Navigate to cycle detail page
   - Go to "Results" tab
   - Enter results for each model-metric combination:
     - **Model A / KS Statistic**: 0.45 → GREEN
     - **Model B / KS Statistic**: 0.33 → YELLOW
     - **Model C / KS Statistic**: 0.25 → RED (NO recommendation - for exception test)
     - **Model C / PSI**: 0.30 → RED (WITH recommendation - for comparison)
   - Screenshot: Empty results grid
   - Screenshot: Results entry in progress
   - Screenshot: Results with color-coded outcomes (GREEN/YELLOW/RED visible)

10. **Add Narratives for Breaches**
    - Click on Model C / KS Statistic RED cell
    - Add justification narrative (but NO recommendation)
    - Screenshot: Breach annotation panel for KS Statistic
    - Click on Model C / PSI RED cell
    - Add justification narrative
    - Screenshot: Breach annotation panel for PSI

11. **Create Recommendation for PSI Breach ONLY**
    - From Model C / PSI RED result, click "Create Recommendation"
    - Verify pre-populated fields:
      - Model: Model C
      - Monitoring Cycle: Current cycle
      - Linked Metric: PSI (plan_metric_id)
    - Fill in recommendation details
    - Screenshot: Recommendation creation modal (showing linked metric)
    - Screenshot: Recommendation created
    - **DO NOT create recommendation for KS Statistic** (exception test)

12. **Submit Cycle 1**
    - Click "Submit Cycle"
    - Screenshot: Status transition to UNDER_REVIEW (evidence of transition)

13. **Request Approval for Cycle 1**
    - Review all results
    - Add report URL
    - Click "Request Approval"
    - Screenshot: Request approval dialog
    - Screenshot: Status transition to PENDING_APPROVAL

13b. **NEGATIVE TEST: Verify Results Read-Only in PENDING_APPROVAL**
    - Try to edit a result value
    - Screenshot: Error/blocked state showing results are read-only
    - Verify edit controls are disabled or blocked

### Phase 6: Approvals & Exception Verification for Cycle 1 (6 screenshots)
14. **View Approvals Tab**
    - Go to "Approvals" tab
    - View required approvals (Global, Regional if applicable)
    - Screenshot: Approvals list with pending items

15. **Grant Approval for Cycle 1**
    - As admin, approve the cycle
    - Add approval comments
    - Screenshot: Approval dialog
    - Screenshot: Cycle 1 APPROVED status (transition evidence)

16. **VERIFY EXCEPTION SCENARIO A: Unmitigated RED**
    - Navigate to Model C Details → Exceptions tab
    - Screenshot: Exception created for KS Statistic (no recommendation)
    - Verify:
      - Exception type: UNMITIGATED_PERFORMANCE
      - Description mentions the monitoring result ID and cycle
      - Status: OPEN
    - Click exception to view details - note the linked `monitoring_result_id`
    - Cross-reference: That result should be the KS Statistic RED result from Cycle 1
    - Verify NO exception exists for PSI (had linked recommendation)
    - Screenshot: Exception details showing result linkage

### Phase 5b: Cycle 2 Workflow - Exception Scenario B (8 screenshots)
**Goal**: Keep Model C / KS Statistic RED in Cycle 2 → triggers "Persistent RED" exception

17. **Create and Start Cycle 2**
    - Create new cycle (advance-cycle or manual)
    - Start the cycle
    - Screenshot: Cycle 2 in DATA_COLLECTION status

18. **Enter Results for Cycle 2 - Keep KS Statistic RED**
    - Enter results:
      - **Model A / KS Statistic**: 0.42 → GREEN
      - **Model B / KS Statistic**: 0.36 → GREEN (improved)
      - **Model C / KS Statistic**: 0.28 → RED (SAME metric still RED)
      - **Model C / PSI**: 0.08 → GREEN (improved)
    - Screenshot: Cycle 2 results grid

19. **Add Narrative but NO Recommendation for KS Statistic**
    - Add justification narrative for the RED KS Statistic
    - DO NOT create recommendation (testing persistent RED detection)
    - Screenshot: Breach annotation without recommendation

20. **Complete Cycle 2 Through Approval**
    - Submit cycle → UNDER_REVIEW
    - Request approval → PENDING_APPROVAL
    - Grant approval → APPROVED
    - Screenshot: Cycle 2 APPROVED status

21. **VERIFY EXCEPTION SCENARIO B: Persistent RED**
    - Navigate to Model C Details → Exceptions tab
    - Screenshot: NEW exception for "Persistent RED" on KS Statistic
    - Verify:
      - Exception indicates consecutive RED across 2 APPROVED cycles
      - Both cycles referenced
    - Screenshot: Exception list showing multiple exceptions for Model C

### Phase 7: CSV Import with Validation Testing (6 screenshots)
22. **Test CSV Import - Happy Path**
    - Create a new cycle (Cycle 3) or use existing
    - Click "Import CSV"
    - Download template
    - Screenshot: CSV import dialog with template download
    - Prepare valid CSV with test data

23. **Test CSV Import - Error Handling**
    - Modify CSV to include ONE deliberately invalid row:
      - Invalid metric code (e.g., "INVALID_METRIC")
      - OR wrong value type (text in numeric field)
    - Upload file with invalid data
    - Screenshot: Preview showing validation ERRORS (red highlighting)
    - Verify error message identifies the problematic row/field

24. **Execute Valid Import**
    - Fix/remove invalid row
    - Re-upload corrected CSV
    - Screenshot: Preview with all rows validated (green)
    - Execute import
    - Screenshot: Import success summary with row count

### Phase 8: Role-Based Testing - Data Provider Experience (5 screenshots)
**Goal**: Verify non-admin user experience and permissions

25. **Login as Data Provider User**
    - Logout from admin account
    - Login as user assigned as Data Provider (e.g., `user@example.com`)
    - **Fallback**: If `user@example.com` doesn't exist, first create a standard user via Users page and assign as Data Provider on the plan
    - Screenshot: Data Provider dashboard view

26. **My Monitoring Tasks - Data Provider View**
    - Navigate to "My Monitoring Tasks"
    - Verify Data Provider sees their assigned plans/cycles
    - Screenshot: My Monitoring Tasks filtered to Data Provider role
    - Verify they can see "Enter Results" action for cycles in DATA_COLLECTION

27. **Data Provider Permissions Check**
    - Attempt to access admin-only features (e.g., create new plan)
    - Screenshot: Permission denied or hidden admin controls
    - Verify Data Provider CAN enter results but CANNOT approve cycles

28. **Return to Admin**
    - Logout and login back as admin@example.com
    - Screenshot: Confirm admin access restored

### Phase 9: User Task Views - Admin (3 screenshots)
29. **My Monitoring Tasks Page (Admin)**
    - Navigate to "My Monitoring" or "My Monitoring Tasks"
    - View task list showing all assigned tasks
    - Screenshot: My Monitoring Tasks overview (admin view)
    - Screenshot: Task cards with status indicators

30. **Admin Overview Dashboard**
    - View admin monitoring overview
    - Check summary cards (overdue, pending, in-progress)
    - Screenshot: Admin governance dashboard with statistics

### Phase 10: Analytics, Visualizations & Reporting (7 screenshots)
31. **Metric Trend Analysis**
    - Open a plan with historical data (after creating 2+ cycles)
    - Click on metric to view trend
    - Screenshot: Trend chart modal showing historical values across cycles

32. **Bullet Chart Threshold Visualization**
    - Navigate to plan Metrics tab
    - View bullet chart showing threshold ranges
    - Screenshot: Metric list with bullet charts (GREEN/YELLOW/RED zones)
    - Screenshot: Metric detail with threshold visualization

33. **Results Grid Color Coding**
    - View cycle results grid
    - Verify GREEN/YELLOW/RED color coding matches thresholds
    - Screenshot: Results grid with color-coded outcomes (all three colors visible)

34. **Performance Summary Dashboard**
    - View plan dashboard tab
    - Check summary metrics and charts
    - Screenshot: Plan performance summary with aggregated stats

35. **Export Capabilities**
    - Export plan version as CSV
    - Export cycle results as CSV
    - Screenshot: Export options/buttons

### Phase 11: Edge Cases & Validation (5 screenshots)
36. **Threshold Validation**
    - Test invalid thresholds based on metric direction:
      - **For KS Statistic** (higher is better, uses red_min/yellow_min):
        Try setting `yellow_min ≤ red_min` (e.g., yellow_min=0.30, red_min=0.35)
      - **OR for PSI** (lower is better, uses yellow_max/red_max):
        Try setting `yellow_max ≥ red_max` (e.g., yellow_max=0.20, red_max=0.15)
    - Verify error message prevents save
    - Screenshot: Validation error message showing threshold constraint

37. **Active Cycle Warning**
    - Try to modify metrics on plan with active cycle
    - Verify warning message about impact
    - Screenshot: Active cycle warning dialog

38. **Cancel Cycle**
    - Create a test cycle (Cycle 4)
    - Cancel it with reason: "Test cancellation"
    - Screenshot: Cancel confirmation dialog
    - Screenshot: Cancelled cycle showing CANCELLED status

---

## Screenshot Naming Convention
Screenshots will be named sequentially:
- `01_login_page.png`
- `02_dashboard_after_login.png`
- `03_monitoring_plans_overview.png`
- etc.

## Expected Outcomes
- All workflows execute without errors
- UI matches documented behavior in USER_GUIDE
- Status transitions follow documented state machine (with evidence captured)
- Approval workflow completes correctly
- **Exception Automation:**
  - Type 1 exception triggers for RED result WITHOUT linked recommendation
  - NO exception for RED result WITH linked recommendation (PSI test)
  - Persistent RED exception triggers after 2 consecutive APPROVED cycles
- **CSV Import:**
  - Validation catches invalid metric codes/data types
  - Error messages clearly identify problematic rows
  - Valid data imports successfully
- **Role-Based Access:**
  - Data Provider can view tasks and enter results
  - Data Provider CANNOT access admin features (plan creation, approvals)
  - Admin has full access to all features
- **Read-Only States:**
  - Results locked in PENDING_APPROVAL status
  - Edit controls disabled/blocked appropriately
- **Visualizations render correctly:**
  - Bullet charts show threshold ranges (GREEN/YELLOW/RED zones)
  - Results grid has proper GREEN/YELLOW/RED color coding
  - Trend charts display historical data across cycles
  - Admin dashboard shows summary statistics

## Test Data Created During UAT
All data will be created from scratch:
1. **Models** (from existing seed or created):
   - Model A: For GREEN results testing
   - Model B: For YELLOW results testing
   - Model C: For RED results and exception testing
2. **Monitoring Team**: "Credit Risk Monitoring Team" with 2+ members
3. **Monitoring Plan**: "Credit Scorecard Monitoring Q4 2025"
   - Frequency: Quarterly
   - Models: 3 models (A, B, C)
   - Data Provider: Assign `user@example.com` for role-based testing
   - Metrics: 2+ quantitative metrics:
     - KS Statistic (with yellow/red thresholds)
     - PSI (Population Stability Index)
4. **Monitoring Cycles**:
   - Cycle 1: APPROVED with mixed results (for Exception Scenario A)
   - Cycle 2: APPROVED with persistent RED (for Exception Scenario B)
   - Cycle 3: For CSV import testing
   - Cycle 4: For cancel testing
5. **Results Matrix for Exception Testing**:
   | Cycle | Model | KS Statistic | PSI | Recommendation |
   |-------|-------|-------------|-----|----------------|
   | 1 | A | GREEN (0.45) | - | N/A |
   | 1 | B | YELLOW (0.33) | - | N/A |
   | 1 | C | RED (0.25) | RED (0.30) | PSI only (not KS) |
   | 2 | A | GREEN (0.42) | - | N/A |
   | 2 | B | GREEN (0.36) | - | N/A |
   | 2 | C | RED (0.28) | GREEN (0.08) | None |
6. **Recommendations**: 1 linked to PSI metric on Cycle 1 (plan_metric_id populated)
7. **Exceptions Expected**:
   - After Cycle 1: UNMITIGATED_PERFORMANCE for Model C / KS Statistic
   - After Cycle 2: PERSISTENT_RED for Model C / KS Statistic (2 consecutive approved cycles)

## Execution Notes
- Use headless mode for Puppeteer: `{ headless: true }`
- Save screenshots to NAS: `/Volumes/Content/MCPScreenShots/`
- Wait for page loads and API responses before taking screenshots
- Verify elements are visible before interacting
- Document any bugs or deviations from expected behavior
- For visualization tests, ensure data is loaded before capturing
