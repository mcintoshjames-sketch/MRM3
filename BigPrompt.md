**Next Objective:** Implement intelligent model grouping suggestions, regional scope detection, and model change tracking with version management that automatically triggers appropriate validations.

### Core Requirements:

#### 1. Model Grouping Memory (Most Recent Only)
- Track which models were validated together in the most recent validation
- When creating a new validation for a model, check if it was part of a group last time
- If yes, suggest: "This model was last validated with [other models]. Include these?"
- Don't look back beyond the most recent validation

#### 2. Regional Scope Intelligence (Union Approach)  
- When models are selected for validation, find ALL regions across ALL selected models
- Present the union of regions as the default suggestion (all checked)
- Allow users to uncheck regions to narrow scope
- Example: Model A (US, UK) + Model B (US, EU) → Suggest all three: US, UK, EU

#### 3. Model Change & Version Management
**Model changes** should be tracked as separate records that:
- Create new model versions
- Automatically trigger validation requests for review
- Track which regions are affected by the change

**Production version tracking** needs:
- Default assumption: All regions use the same model version
- Regional overrides: Specific regions can be on different versions
- When a regional change occurs, only that region's version gets updated

#### 4. Smart Approver Assignment
Automatically determine required approvers based on scope:
- Global validations → Global approver
- Regional validations → Regional approvers for selected regions  
- Mixed scope → Both global and regional approvers

### Implementation Approach:

First, analyze the existing schema to understand:
- How model versions are currently stored
- How validation requests track multiple models
- How regions are linked to models
- The current approver assignment logic

Then design new tables/columns to support:
- Tracking the last validation grouping for each model
- Storing production version per model per region
- Recording model changes as first-class entities
- Linking model changes to triggered validations

### Key Behaviors:

1. **Version Management**:
   - New models start at v1.0 for all regions
   - Global changes update all regions to the new version
   - Regional changes update only specified regions
   - UI shows global version unless regional override exists

2. **Automatic Validation Triggers**:
   - Model changes create validation requests automatically
   - Validation scope matches the change's affected regions
   - Required approvers determined by regional scope

3. **Grouping Suggestions**:
   - Store the model group after each multi-model validation
   - Only remember the most recent grouping per model
   - No suggestion if model was validated alone last time

### API Design Needs:

Create endpoints for:
- Getting validation suggestions for a model (last grouping + applicable regions)
- Recording model changes and triggering validations
- Querying production versions (global and per-region)
- Updating regional version deployments

### UI Enhancements Needed:

1. **Validation Creation**: 
   - Show grouping suggestions when applicable
   - Display region checkboxes based on union of model regions
   
2. **Model Change Recording**:
   - New interface for recording changes
   - Region selector for change scope
   - Automatic validation creation confirmation

3. **Model Details**:
   - Display current production versions by region
   - Show version deployment history

### Non-Breaking Implementation:
- Make all new fields nullable/optional
- Existing single-model validations continue to work
- Assume existing models are v1.0 globally if no version data exists
- Gracefully handle models without previous validation groupings

**Start by:**
1. Examining the current database schema for models, versions, validations, and regions
2. Proposing the schema changes needed (as SQLAlchemy models, not raw SQL)
3. Designing the API endpoints with request/response examples
4. Planning the UI components and state management

