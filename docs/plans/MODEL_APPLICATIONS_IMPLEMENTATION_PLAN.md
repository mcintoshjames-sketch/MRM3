# Model-Application Relationship Implementation Plan

## Overview

This feature enables tracking of applications that support a model's end-to-end process. Models can be linked to one or more applications from the organization's application inventory system (MAP - Managed Application Portfolio), with metadata describing the nature of each relationship.

## Design Decisions (Confirmed)

1. **Permissions**: Admin, Validator, AND model owners/developers can manage application links
2. **Data flow direction**: Not needed - relationship type is sufficient
3. **Historical tracking**: Soft delete with `end_date` field
4. **Multiple relationships**: One relationship type per model-application pair
5. **Criticality**: Not tracked on the relationship
6. **System name**: MAP = "Managed Application Portfolio"

## Business Context

Financial services models rarely operate in isolation. They depend on:
- **Data sources** that feed input data
- **Execution platforms** that run the model code
- **Output consumers** that use model results
- **Monitoring systems** that track performance
- **Reporting dashboards** that display results

Tracking these relationships is critical for:
- Impact analysis when applications change
- Audit and compliance documentation
- Operational risk management
- Change management coordination

---

## Database Design

### 1. MAP Applications Table (Mock Application Inventory)

Similar to `entra_users` (mock directory) and `vendors` tables, this simulates integration with the organization's application inventory system.

```sql
CREATE TABLE map_applications (
    application_id SERIAL PRIMARY KEY,
    application_code VARCHAR(50) UNIQUE NOT NULL,  -- MAP system identifier (e.g., "APP-12345")
    application_name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_name VARCHAR(255),                       -- Application owner/steward
    owner_email VARCHAR(255),
    department VARCHAR(100),
    technology_stack VARCHAR(255),                 -- e.g., "Python/AWS Lambda", "Java/On-Prem"
    criticality_tier VARCHAR(20),                  -- Critical, High, Medium, Low
    status VARCHAR(50) DEFAULT 'Active',           -- Active, Decommissioned, In Development
    external_url VARCHAR(500),                     -- Link to MAP system record
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 2. Model-Application Junction Table

Stores the many-to-many relationship with metadata about the nature of each link.

```sql
CREATE TABLE model_applications (
    model_id INTEGER NOT NULL REFERENCES models(model_id) ON DELETE CASCADE,
    application_id INTEGER NOT NULL REFERENCES map_applications(application_id) ON DELETE CASCADE,
    relationship_type_id INTEGER NOT NULL REFERENCES taxonomy_values(value_id),
    description TEXT,                              -- Notes about this specific relationship
    effective_date DATE,
    end_date DATE,                                 -- NULL if currently active (soft delete)
    created_at TIMESTAMP DEFAULT NOW(),
    created_by_user_id INTEGER REFERENCES users(user_id),
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (model_id, application_id)
);
```

### 3. New Taxonomy: Application Relationship Type

Add to seed data:

| Code | Label | Description |
|------|-------|-------------|
| DATA_SOURCE | Data Source | Application provides input data to the model |
| EXECUTION | Execution Platform | Application runs or hosts the model |
| OUTPUT_CONSUMER | Output Consumer | Application consumes model outputs/scores |
| MONITORING | Monitoring/Alerting | Application monitors model performance |
| REPORTING | Reporting/Dashboard | Application displays model results |
| DATA_STORAGE | Data Storage | Application stores model data or results |
| ORCHESTRATION | Workflow/Orchestration | Application orchestrates model execution |
| VALIDATION | Validation Support | Application supports model validation process |
| OTHER | Other | Other relationship type |

---

## Seed Data: Mock MAP Applications

Example applications typical of a financial services organization:

| Code | Name | Department | Technology | Criticality |
|------|------|------------|------------|-------------|
| APP-EDW-001 | Enterprise Data Warehouse | Data Engineering | Snowflake/AWS | Critical |
| APP-RAP-001 | Risk Analytics Platform | Model Risk | Python/Kubernetes | Critical |
| APP-BBG-001 | Bloomberg Data Feed | Market Data | Bloomberg API | Critical |
| APP-MRD-001 | Model Results Dashboard | Business Intelligence | Tableau/React | High |
| APP-AMS-001 | Alert Management System | Operations | ServiceNow | High |
| APP-PMS-001 | Portfolio Management System | Trading | Java/On-Prem | Critical |
| APP-TES-001 | Trade Execution System | Trading | C++/Low-Latency | Critical |
| APP-RRP-001 | Regulatory Reporting Platform | Compliance | Python/SQL Server | Critical |
| APP-DQM-001 | Data Quality Monitor | Data Governance | Great Expectations | Medium |
| APP-MSO-001 | Model Scheduler/Orchestrator | Model Operations | Airflow/AWS | High |
| APP-CRM-001 | Credit Risk Manager | Credit Risk | SAS/Oracle | Critical |
| APP-FVS-001 | Fair Value System | Accounting | Python/PostgreSQL | High |
| APP-STR-001 | Stress Testing Runner | Risk Management | Python/Grid Computing | Critical |
| APP-LMS-001 | Limit Management System | Risk Management | Java/Oracle | High |
| APP-RDL-001 | Reference Data Library | Data Management | MDM/SQL Server | High |

---

## API Design

### MAP Application Endpoints (Read-Only - Simulating External System)

```
GET  /map/applications
     Query params: search, department, status, criticality_tier, skip, limit
     Returns: List of applications from MAP inventory

GET  /map/applications/{application_id}
     Returns: Single application details
```

### Model-Application Relationship Endpoints

```
GET  /models/{model_id}/applications
     Query params: include_inactive (boolean, default false)
     Returns: List of applications linked to this model with relationship details

POST /models/{model_id}/applications
     Body: { application_id, relationship_type_id, description?, effective_date? }
     Returns: Created relationship

PATCH /models/{model_id}/applications/{application_id}
      Body: { relationship_type_id?, description?, end_date? }
      Returns: Updated relationship

DELETE /models/{model_id}/applications/{application_id}
       Soft delete: Sets end_date to today
       Returns: 204 No Content
```

### Response Schema: ModelApplicationResponse

```json
{
  "model_id": 1,
  "application_id": 5,
  "application": {
    "application_id": 5,
    "application_code": "APP-EDW-001",
    "application_name": "Enterprise Data Warehouse",
    "owner_name": "Jane Smith",
    "department": "Data Engineering",
    "criticality_tier": "Critical",
    "status": "Active"
  },
  "relationship_type": {
    "value_id": 150,
    "code": "DATA_SOURCE",
    "label": "Data Source"
  },
  "description": "Provides daily market data feed for pricing models",
  "effective_date": "2024-01-15",
  "end_date": null,
  "created_at": "2024-01-15T10:30:00Z",
  "created_by_user": {
    "user_id": 1,
    "full_name": "Admin User"
  }
}
```

---

## Frontend Design

### Model Details Page - New "Applications" Tab

Located alongside existing tabs: Details | Versions | Delegates | Validations | Hierarchy | Dependencies | **Applications** | Lineage | Activity

#### Tab Content Layout

```
+------------------------------------------------------------------+
| Supporting Applications                           [+ Add Application] |
+------------------------------------------------------------------+
| Filter: [All Types ▼]  [Critical Only ☐]  [Include Inactive ☐]    |
+------------------------------------------------------------------+
| APPLICATION          | RELATIONSHIP  | DIRECTION | CRITICAL | ... |
|---------------------|---------------|-----------|----------|-----|
| Enterprise Data     | Data Source   | Inbound   | ✓        | ... |
| Warehouse (APP-EDW) |               |           |          |     |
|---------------------|---------------|-----------|----------|-----|
| Risk Analytics      | Execution     | --        | ✓        | ... |
| Platform (APP-RAP)  | Platform      |           |          |     |
+------------------------------------------------------------------+
```

### Add Application Modal

```
+------------------------------------------+
| Add Supporting Application               |
+------------------------------------------+
| Search MAP Inventory:                    |
| [________________________] [Search]      |
|                                          |
| Results:                                 |
| ○ APP-EDW-001 - Enterprise Data Warehouse|
|   Data Engineering | Critical | Active   |
| ○ APP-RAP-001 - Risk Analytics Platform  |
|   Model Risk | Critical | Active         |
|                                          |
| Relationship Details:                    |
| Type: [Data Source        ▼]             |
| Direction: [Inbound ▼]                   |
| Critical? [✓]                            |
| Description:                             |
| [________________________________]       |
| [________________________________]       |
| Effective Date: [2024-01-15]             |
|                                          |
|              [Cancel]  [Add Application] |
+------------------------------------------+
```

### Application Detail View (Expandable Row or Side Panel)

Shows full relationship details:
- Application info (name, code, owner, department, technology)
- Relationship metadata (type, direction, criticality)
- Description/notes
- Dates (effective, end if applicable)
- Created by / created at
- Edit / Remove actions (Admin only)

---

## Implementation Phases

### Phase 1: Database & Backend Foundation
- [ ] Create Alembic migration for `map_applications` table
- [ ] Create Alembic migration for `model_applications` table
- [ ] Add "Application Relationship Type" taxonomy to seed data
- [ ] Create SQLAlchemy models: `MapApplication`, `ModelApplication`
- [ ] Add mock MAP applications to seed data (15 applications)
- [ ] Create Pydantic schemas for request/response

### Phase 2: API Endpoints
- [ ] Implement `GET /map/applications` with search/filter
- [ ] Implement `GET /map/applications/{id}`
- [ ] Implement `GET /models/{id}/applications`
- [ ] Implement `POST /models/{id}/applications`
- [ ] Implement `PATCH /models/{id}/applications/{app_id}`
- [ ] Implement `DELETE /models/{id}/applications/{app_id}`
- [ ] Add audit logging for relationship changes
- [ ] Write pytest tests for all endpoints

### Phase 3: Frontend - Read Views
- [ ] Add "Applications" tab to ModelDetailsPage
- [ ] Create `ModelApplicationsSection` component
- [ ] Display linked applications in table format
- [ ] Add filters (relationship type, critical only, include inactive)
- [ ] Add expandable row for full details

### Phase 4: Frontend - Write Operations
- [ ] Create `AddApplicationModal` component
- [ ] Implement MAP search functionality
- [ ] Create relationship form (type, direction, criticality, description)
- [ ] Create `EditApplicationModal` for updating relationships
- [ ] Add remove functionality with confirmation
- [ ] Restrict write operations to Admin role

### Phase 5: Enhancements (Future)
- [ ] Add applications to model CSV export
- [ ] Create "Application Impact Report" in Reports section
- [ ] Add application relationships to Lineage visualization
- [ ] Bulk import/link applications
- [ ] Notifications when linked applications change status

---

## File Structure

```
api/
├── alembic/versions/
│   └── xxxx_add_map_applications.py
├── app/
│   ├── models/
│   │   ├── map_application.py
│   │   └── model_application.py
│   ├── schemas/
│   │   ├── map_application.py
│   │   └── model_application.py
│   └── api/
│       ├── map_applications.py
│       └── model_applications.py
└── tests/
    └── test_model_applications.py

web/src/
├── api/
│   └── mapApplications.ts
├── components/
│   ├── ModelApplicationsSection.tsx
│   ├── AddApplicationModal.tsx
│   └── EditApplicationModal.tsx
└── pages/
    └── ModelDetailsPage.tsx (add tab)
```

---

## Security & Permissions

| Action | Admin | Validator | Owner/Developer | Other User |
|--------|-------|-----------|-----------------|------------|
| View model applications | ✓ | ✓ | ✓ | ✓ (if model visible) |
| Search MAP inventory | ✓ | ✓ | ✓ | ✓ |
| Add application link | ✓ | ✓ | ✓ | ✗ |
| Edit relationship | ✓ | ✓ | ✓ | ✗ |
| Remove application link | ✓ | ✓ | ✓ | ✗ |

Note: Uses same permission logic as `can_modify_model` from RLS - owners, developers, and delegates with `can_submit_changes` can manage application links for their models.

---

## Testing Strategy

### Backend Tests
1. CRUD operations for model-application relationships
2. Search/filter MAP applications
3. Duplicate relationship prevention
4. Cascade delete when model deleted
5. Date validation (end_date >= effective_date)
6. Permission checks for write operations

### Frontend Tests
1. Applications tab renders correctly
2. Search modal finds applications
3. Add application flow works
4. Edit relationship updates correctly
5. Remove with confirmation works
6. Filters work correctly

---

## Questions to Consider

1. **Should we track historical relationships?** Current design uses `end_date` for soft-delete, preserving history. Alternative: hard delete with audit log only.

2. **Integration pattern for production?** In production, the `map_applications` table could be:
   - Synced periodically from real MAP system
   - Replaced with direct API calls to MAP
   - Federated query to MAP database

3. **Should applications appear in lineage visualization?** Could extend the lineage viewer to show applications as nodes, differentiated from models.

4. **Notification requirements?** Should model owners be notified when a linked application's status changes (e.g., decommissioned)?

---

## Approval

Please review this implementation plan and confirm:
- [ ] Database schema looks correct
- [ ] API design meets requirements
- [ ] UI design is appropriate
- [ ] Phased approach is acceptable
- [ ] Any modifications needed before implementation
