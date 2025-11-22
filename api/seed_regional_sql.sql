-- Regional Compliance Report Demo Data
-- Directly insert minimal test data

BEGIN;

-- Get user IDs
\set admin_id '(SELECT user_id FROM users WHERE email = ''admin@example.com'')'
\set validator_id '(SELECT user_id FROM users WHERE email = ''validator@example.com'')'
\set us_approver_id '(SELECT user_id FROM users WHERE email = ''usapprover@example.com'')'
\set eu_approver_id '(SELECT user_id FROM users WHERE email = ''euapprover@example.com'')'

-- Get region IDs
\set us_region_id '(SELECT region_id FROM regions WHERE code = ''US'')'
\set eu_region_id '(SELECT region_id FROM regions WHERE code = ''EU'')'
\set uk_region_id '(SELECT region_id FROM regions WHERE code = ''UK'')'

-- Get taxonomy value IDs
\set val_type_initial_id '(SELECT value_id FROM taxonomy_values WHERE code = ''INITIAL'')'
\set priority_high_id '(SELECT value_id FROM taxonomy_values WHERE code = ''HIGH'')'
\set status_approved_id '(SELECT value_id FROM taxonomy_values WHERE code = ''APPROVED'')'
\set status_pending_id '(SELECT value_id FROM taxonomy_values WHERE code = ''PENDING_APPROVAL'')'

-- ============================================================================
-- SCENARIO 1: Credit Risk Model - Deployed to US and EU (Both Approved)
-- ============================================================================

-- Create model
INSERT INTO models (model_name, description, development_type, owner_id, developer_id, created_at, updated_at)
VALUES ('Credit Risk Scorecard v3', 'Consumer credit risk scoring model', 'In-House', 
        :admin_id, :validator_id, NOW() - INTERVAL '180 days', NOW())
ON CONFLICT DO NOTHING
RETURNING model_id \gset model1_id

-- Create validation request
INSERT INTO validation_requests (
    request_date, requestor_id, validation_type_id, priority_id,
    target_completion_date, current_status_id, trigger_reason, created_at, updated_at
)
VALUES (
    CURRENT_DATE - 60, :admin_id, :val_type_initial_id, :priority_high_id,
    CURRENT_DATE - 30, :status_approved_id, 'Annual validation',
    NOW() - INTERVAL '60 days', NOW() - INTERVAL '45 days'
)
RETURNING request_id \gset val1_id

-- Link validation to model
INSERT INTO validation_request_models (request_id, model_id)
VALUES (:val1_id, :model1_id);

-- Add regions to validation
INSERT INTO validation_request_regions (request_id, region_id)
VALUES (:val1_id, :us_region_id), (:val1_id, :eu_region_id);

-- Create model version
INSERT INTO model_versions (
    model_id, version_number, change_type, created_at, status, validation_request_id
)
VALUES (
    :model1_id, '2.1.0', 'MAJOR', NOW() - INTERVAL '60 days', 'APPROVED', :val1_id
)
RETURNING version_id \gset version1_id

-- US Regional Approval - APPROVED
INSERT INTO validation_approvals (
    request_id, approver_id, approver_role, approval_type, region_id,
    approval_status, approved_at, comments, created_at
)
VALUES (
    :val1_id, :us_approver_id, 'Regional Validator', 'Regional', :us_region_id,
    'Approved', NOW() - INTERVAL '45 days', 'Approved for US deployment', NOW() - INTERVAL '45 days'
);

-- EU Regional Approval - APPROVED
INSERT INTO validation_approvals (
    request_id, approver_id, approver_role, approval_type, region_id,
    approval_status, approved_at, comments, created_at
)
VALUES (
    :val1_id, :eu_approver_id, 'Regional Validator', 'Regional', :eu_region_id,
    'Approved', NOW() - INTERVAL '44 days', 'Approved for EU deployment', NOW() - INTERVAL '44 days'
);

-- Deploy to US
INSERT INTO model_regions (model_id, region_id, version_id, deployed_at, deployment_notes)
VALUES (:model1_id, :us_region_id, :version1_id, NOW() - INTERVAL '40 days', 'Production deployment to US')
ON CONFLICT (model_id, region_id) DO UPDATE SET
    version_id = EXCLUDED.version_id,
    deployed_at = EXCLUDED.deployed_at,
    deployment_notes = EXCLUDED.deployment_notes;

-- Deploy to EU
INSERT INTO model_regions (model_id, region_id, version_id, deployed_at, deployment_notes)
VALUES (:model1_id, :eu_region_id, :version1_id, NOW() - INTERVAL '38 days', 'Production deployment to EU')
ON CONFLICT (model_id, region_id) DO UPDATE SET
    version_id = EXCLUDED.version_id,
    deployed_at = EXCLUDED.deployed_at,
    deployment_notes = EXCLUDED.deployment_notes;

SELECT 'Scenario 1 Complete: Credit Risk Model deployed to US and EU' AS status;

COMMIT;

SELECT 'Demo data created successfully' AS result;
SELECT 'Test at: /regional-compliance-report/?region_code=US' AS test_url;
