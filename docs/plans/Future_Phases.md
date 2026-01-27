# Future Development Phases

This document outlines planned enhancements for the Model Risk Management system, organized by implementation phase.

---

## Phase 2: Validation Request Detail View

**Priority**: High
**Estimated Effort**: 2-3 days

### Frontend Components
- **Validation Request Detail Page** (`/validation-workflow/:id`)
  - Tabbed interface with:
    - **Overview Tab**: Request summary, current status, timeline visualization
    - **Assignments Tab**: Manage validator assignments, track hours, attestations
    - **Work Components Tab**: Update component status (Not Started → In Progress → Completed), add notes
    - **Outcome Tab**: Create/view outcome (only enabled when all components completed)
    - **Approvals Tab**: View/submit approval status for each required approver
    - **History Tab**: Complete timeline of status changes with reasons

### Backend Enhancements
- Add `GET /validation-workflow/requests/{id}/timeline` endpoint for visual timeline data
- Add validation rules for concurrent editing conflicts
- Add notification hooks (placeholder for Phase 4)

### Testing
- Frontend component tests for detail page
- Integration tests for full workflow scenarios

---

## Phase 3: Findings and Issues Management Module

**Priority**: High
**Estimated Effort**: 5-7 days

### Core Concept
Track detailed findings discovered during validation work, with severity classification, recommendations, and management responses.

### Database Schema

```sql
-- Individual findings discovered during validation
validation_findings (
  finding_id PK,
  request_id FK,
  component_id FK (nullable - which work component discovered this),
  finding_number VARCHAR (auto-generated: VF-2024-0001),
  title VARCHAR,
  description TEXT,
  severity_id FK (taxonomy: Critical, High, Medium, Low),
  category_id FK (taxonomy: Data Quality, Methodology, Implementation, Documentation, Governance),
  identified_date DATE,
  identified_by_id FK (user),
  status_id FK (taxonomy: Open, In Progress, Remediated, Closed, Risk Accepted),
  due_date DATE,
  created_at, updated_at
)

-- Recommendations for addressing findings
finding_recommendations (
  recommendation_id PK,
  finding_id FK,
  recommendation_text TEXT,
  priority_id FK,
  owner_id FK (user responsible),
  target_date DATE,
  status VARCHAR (Pending, In Progress, Completed, Overdue),
  completion_date DATE (nullable),
  created_at, updated_at
)

-- Management responses to findings
finding_management_responses (
  response_id PK,
  finding_id FK,
  responder_id FK,
  response_text TEXT,
  response_date DATE,
  accepts_finding BOOLEAN,
  proposed_action TEXT,
  created_at
)

-- Track conditions/limitations on model use
model_use_conditions (
  condition_id PK,
  outcome_id FK (links to validation outcome),
  condition_type VARCHAR (Limitation, Condition, Constraint),
  description TEXT,
  effective_date DATE,
  expiration_date DATE (nullable),
  is_active BOOLEAN,
  created_at
)
```

### API Endpoints
- `GET /validations/findings/` - List all findings with filters
- `POST /validations/findings/` - Create finding during validation work
- `GET /validations/findings/{id}` - Get finding details with recommendations and responses
- `PATCH /validations/findings/{id}` - Update finding status
- `POST /validations/findings/{id}/recommendations` - Add recommendation
- `POST /validations/findings/{id}/responses` - Add management response
- `GET /validations/dashboard/findings-aging` - Open findings aging report
- `GET /validations/dashboard/findings-by-severity` - Finding severity distribution
- `GET /models/{id}/conditions` - Active conditions/limitations on a model

### Frontend Pages
- Findings list with severity and status filtering
- Finding detail page with recommendations and responses timeline
- Integration with validation workflow (findings appear on work components)
- Model detail page shows active conditions/limitations

### Business Rules
- Critical and High severity findings may result in "Not Fit for Purpose" rating
- Findings must be addressed (remediated or risk accepted) before validation can be approved
- Track finding aging for compliance reporting
- Auto-generate finding numbers for traceability

---

## Phase 4: Notifications and Reminders

**Priority**: Medium
**Estimated Effort**: 3-4 days

### Email Notification Triggers
- Validation request created (to validation team)
- Validator assigned (to assigned validator)
- Status changed (to requestor, validators, stakeholders)
- Approval requested (to approver)
- Approval submitted (to validators)
- Request overdue (to validators and management)
- Finding created (to model owner)
- Finding recommendation assigned (to owner)

### Technical Implementation
- Background task queue (Celery or similar)
- Email template system
- Notification preferences per user
- In-app notification center
- Daily digest option

### Database Additions
```sql
notification_preferences (
  preference_id PK,
  user_id FK,
  notification_type VARCHAR,
  email_enabled BOOLEAN,
  in_app_enabled BOOLEAN,
  digest_frequency VARCHAR (Immediate, Daily, Weekly)
)

notifications (
  notification_id PK,
  user_id FK,
  title VARCHAR,
  message TEXT,
  link_url VARCHAR,
  is_read BOOLEAN,
  created_at
)
```

---

## Phase 5: Advanced Workflow Features

**Priority**: Medium
**Estimated Effort**: 4-5 days

### Kanban Board View
- Drag-and-drop status management
- Visual workflow pipeline
- Column customization
- Quick filters by priority, model, validator

### Bulk Operations
- Schedule multiple periodic validations
- Bulk status updates
- Bulk assignment of validators
- Template-based request creation

### Workflow Templates
- Pre-configured validation templates by model type
- Auto-populate work components based on template
- Default approver matrix by model tier
- Standard timelines by validation type

### SLA Management
- Define SLA by priority and validation type
- Auto-calculate target dates
- SLA breach alerts
- SLA performance reporting

---

## Phase 6: Reporting and Analytics

**Priority**: Medium
**Estimated Effort**: 3-4 days

### Dashboard Enhancements
- Validation coverage metrics (% of models validated in period)
- Average cycle time by status
- Validator productivity metrics
- Finding severity trends over time
- Model risk distribution charts

### Standard Reports
- Validation pipeline report (all active requests)
- Overdue validations report
- Validator workload and utilization
- Finding aging and remediation status
- Model validation history
- Compliance summary for regulators

### Export Capabilities
- Report scheduling and auto-delivery
- PDF generation for formal reports
- Excel exports with pivot tables
- API access for BI tool integration

---

## Phase 7: Enhanced Access Control

**Priority**: Low
**Estimated Effort**: 2-3 days

### Role Refinements
- **Validation Manager**: Assign validators, manage workload, configure policies
- **Senior Validator**: Can approve other validators' work
- **Junior Validator**: Can perform work but not approve outcomes
- **Model Risk Committee**: View-only access to outcomes and findings
- **Auditor**: Read-only access with enhanced search

### Permission Matrix
- Per-request permissions (who can view/edit specific requests)
- Model-level permissions (access to specific model data)
- Field-level security (sensitive fields restricted)
- Time-based access (temporary elevated permissions)

---

## Phase 8: Integration Capabilities

**Priority**: Low
**Estimated Effort**: 5-7 days

### External System Integration
- Model execution environment monitoring
- Version control system (Git) integration for model code
- Document management system for validation reports
- Risk management platform data sync
- Regulatory reporting system feeds

### API Enhancements
- Webhook support for event notifications
- GraphQL endpoint for flexible queries
- Rate limiting and API keys for external access
- Batch operations API

### Data Import/Export
- Bulk import from Excel for migration
- Standard export formats (XML, JSON, CSV)
- Regulatory submission formats (SR 11-7 compliance reports)

---

## Testing Debt (Ongoing)

### Backend Tests Completed ✅
- [x] ValidationRequest CRUD operations (12 tests)
- [x] Status transition validation (6 tests)
- [x] Validator independence checks (4 tests)
- [x] Work component completion rules (3 tests)
- [x] Outcome creation validation (2 tests)
- [x] Approval workflow (4 tests)
- [x] Dashboard endpoints (3 tests)
- [x] Audit log verification (2 tests)

**Total: 36 new validation workflow tests (165 total backend tests)**

### Frontend Tests Needed
- [ ] ValidationWorkflowPage component tests (~15 tests)
- [ ] ValidationRequestDetailPage component tests (~25 tests)
  - [ ] Overview tab rendering with request details
  - [ ] Assignments tab with validator management
  - [ ] Work components tab with status updates
  - [ ] Outcome tab creation and display
  - [ ] Approvals tab with decision submission
  - [ ] History tab with audit trail
  - [ ] Tab navigation and switching
  - [ ] Modal dialogs (status update, add assignment, create outcome, submit approval)
  - [ ] Error handling and validation
  - [ ] Loading states
- [ ] Form validation and submission (~10 tests)
- [ ] Status color coding (~5 tests)
- [ ] Priority display (~5 tests)
- [ ] Navigation integration (~5 tests)
- [ ] Error handling (~10 tests)

### Integration Tests
- [ ] Full workflow scenario (request → outcome → approval)
- [ ] Multi-user collaboration scenarios
- [ ] Permission enforcement across roles
- [ ] API contract verification

---

## Technical Debt

### Code Quality
- Add comprehensive type hints to all API endpoints
- Implement request/response logging middleware
- Add OpenAPI documentation comments
- Database query optimization (N+1 prevention audit)
- Add database indexes for common query patterns

### Infrastructure
- Database connection pooling optimization
- Add Redis caching layer for taxonomy lookups
- Implement API response caching
- Set up monitoring and alerting (Prometheus/Grafana)
- Add health check endpoints

### Security
- Implement API rate limiting
- Add request signing for sensitive operations
- Audit log encryption for sensitive data
- Session management improvements
- CORS policy tightening for production

---

## Migration Considerations

### Legacy Data Migration
When ready to deprecate the old `/validations` endpoints:

1. Create migration script to convert old `Validation` records to `ValidationRequest` records
2. Map old outcomes to new workflow:
   - Set status to "Approved"
   - Create `ValidationOutcome` from old outcome_id
   - Create `ValidationAssignment` from validator_id
   - Mark all work components as "Completed"
3. Preserve original timestamps
4. Add migration flag for identification
5. Run data integrity checks post-migration
6. Update all frontend references to use new endpoints
7. Deprecate old endpoints with 301 redirects
8. Eventually remove old table and code

---

## Prioritized Roadmap

### Immediate (Next 2 weeks)
1. Phase 2: Validation Request Detail View
2. Complete test coverage for current implementation

### Short-term (1-2 months)
3. Phase 3: Findings and Issues Management
4. Phase 4: Notifications and Reminders

### Medium-term (3-6 months)
5. Phase 5: Advanced Workflow Features
6. Phase 6: Reporting and Analytics
7. Legacy data migration and endpoint deprecation

### Long-term (6+ months)
8. Phase 7: Enhanced Access Control
9. Phase 8: Integration Capabilities
10. Performance optimization and scaling

---

*Last Updated: November 2025*
