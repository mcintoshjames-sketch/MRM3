# Performance Monitoring Business Process Flow

## Complete Monitoring Cycle Workflow

```mermaid
---
config:
  layout: fixed
---
flowchart TD
 subgraph SETUP["Plan Configuration (One-Time Setup)"]
        S1["Create Monitoring Plan"]
        S2["Add models to scope"]
        S3["Configure metrics and thresholds"]
        S4["Publish Plan Version"]
  end
 subgraph TEAM["Monitoring Team (Risk Function)"]
        T1["Create new monitoring cycle"]
        T2["Start cycle (locks to active version)"]
        T3["Review submitted results"]
        T4{"All results complete and accurate?"}
        T5["Return to Data Provider with feedback"]
        T6{"All RED outcomes have justification?"}
        T7["Request breach justifications"]
        T8["Request management approval with report URL"]
  end
 subgraph DP["Data Provider (1st Line)"]
        P1["Access cycle in Data Collection status"]
        P2["Enter metric results (manual or CSV import)"]
        P3{"Any RED outcomes?"}
        P4["Add justification narrative for breaches"]
        P5["Submit cycle for review"]
        P6["Address feedback and resubmit"]
  end
 subgraph APPROVE["Approvers (Management)"]
        A1["Review monitoring results and report"]
        A2{"Global Approver: Accept results?"}
        A3["Global Approval granted"]
        A4["Reject with comments"]
        A5{"Regional approval required?"}
        A6["Regional Approver reviews"]
        A7{"Regional Approver: Accept results?"}
        A8["Regional Approval granted"]
        A9["Reject with comments"]
        A10{"All required approvals granted?"}
  end

    %% Setup Flow
    S1 --> S2
    S2 --> S3
    S3 --> S4
    S4 --> T1

    %% Cycle Initiation
    T1 --> T2
    T2 --> P1

    %% Data Entry Flow
    P1 --> P2
    P2 --> P3
    P3 -- Yes --> P4
    P4 --> P5
    P3 -- No --> P5

    %% Review Flow
    P5 --> T3
    T3 --> T4
    T4 -- No --> T5
    T5 --> P6
    P6 --> P5
    T4 -- Yes --> T6
    T6 -- No --> T7
    T7 --> P6
    T6 -- Yes --> T8

    %% Approval Flow
    T8 --> A1
    A1 --> A2
    A2 -- Reject --> A4
    A4 --> T5
    A2 -- Approve --> A3
    A3 --> A5
    A5 -- No --> A10
    A5 -- Yes --> A6
    A6 --> A7
    A7 -- Reject --> A9
    A9 --> T5
    A7 -- Approve --> A8
    A8 --> A10
    A10 -- No, awaiting more --> A6
    A10 -- Yes, all complete --> DONE

    DONE["Cycle Approved & Closed"]:::endstate

    classDef endstate fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20
```

---

## Simplified Cycle Status Flow

```mermaid
---
config:
  layout: fixed
---
flowchart LR
 subgraph STATUS["Monitoring Cycle Lifecycle"]
        PENDING["PENDING"]
        DC["DATA COLLECTION"]
        UR["UNDER REVIEW"]
        PA["PENDING APPROVAL"]
        APP["APPROVED"]:::endstate
        CAN["CANCELLED"]:::cancelstate
  end

    PENDING -- "Team: Start Cycle" --> DC
    DC -- "Provider: Submit" --> UR
    UR -- "Team: Request Approval" --> PA
    PA -- "All Approvers: Approve" --> APP

    PENDING -- "Team: Cancel" --> CAN
    DC -- "Team: Cancel" --> CAN
    UR -- "Team: Cancel" --> CAN

    classDef endstate fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20
    classDef cancelstate fill:#ffebee,stroke:#c62828,color:#b71c1c
```

---

## Data Entry Decision Flow

```mermaid
---
config:
  layout: fixed
---
flowchart TD
 subgraph ENTRY["Result Entry Process"]
        E1["Select metric to enter"]
        E2{"Metric type?"}
        E3["Enter numeric value"]
        E4["System calculates outcome from thresholds"]
        E5["Select outcome: GREEN / YELLOW / RED"]
        E6["Enter narrative explanation"]
        E7{"Outcome is RED?"}
        E8["Add breach justification (required)"]
        E9["Save result"]
        E10{"More metrics to enter?"}
  end

    E1 --> E2
    E2 -- Quantitative --> E3
    E3 --> E4
    E4 --> E7
    E2 -- Qualitative --> E5
    E5 --> E6
    E6 --> E7
    E7 -- Yes --> E8
    E8 --> E9
    E7 -- No --> E9
    E9 --> E10
    E10 -- Yes --> E1
    E10 -- No --> SUBMIT["Submit Cycle"]:::endstate

    classDef endstate fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20
```

---

## Plan Version Management Flow

```mermaid
---
config:
  layout: fixed
---
flowchart TD
 subgraph VERSION["Plan Versioning Process"]
        V1["Plan created with initial configuration"]
        V2["Publish Version 1"]
        V3["Version 1 Active"]
        V4["Cycle started - locks to Version 1"]
        V5["Team modifies metrics or models"]
        V6["Plan shows 'Unpublished Changes'"]
        V7{"Ready to apply changes?"}
        V8["Publish Version 2"]
        V9["Version 2 Active, Version 1 Inactive"]
        V10["New cycles use Version 2"]
        V11["Existing cycle still uses Version 1"]
  end

    V1 --> V2
    V2 --> V3
    V3 --> V4
    V3 --> V5
    V5 --> V6
    V6 --> V7
    V7 -- No --> V5
    V7 -- Yes --> V8
    V8 --> V9
    V9 --> V10
    V4 --> V11
    V11 --> COMPLETE["Cycle completes with V1 thresholds"]:::endstate
    V10 --> NEW["New cycle uses V2 thresholds"]:::endstate

    classDef endstate fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20
```

---

## Approval Workflow Detail

```mermaid
---
config:
  layout: fixed
---
flowchart TD
 subgraph APPROVALS["Approval Process"]
        R1["Team requests approval with report URL"]
        R2["System creates approval requirements"]
        G1["Global Approval Required"]
        G2["Global Approver reviews"]
        G3{"Decision?"}
        G4["Approved with comments"]
        G5["Rejected - return to team"]
        RG1{"Models in regions requiring approval?"}
        RG2["Regional Approval Required per region"]
        RG3["Regional Approver reviews"]
        RG4{"Decision?"}
        RG5["Approved with comments"]
        RG6["Rejected - return to team"]
        CHECK{"All required approvals complete?"}
  end
 subgraph ADMIN["Admin Override (if needed)"]
        AD1["Admin reviews pending approval"]
        AD2["Admin approves on behalf"]
        AD3["Provide approval evidence"]
  end

    R1 --> R2
    R2 --> G1
    R2 --> RG1

    G1 --> G2
    G2 --> G3
    G3 -- Approve --> G4
    G3 -- Reject --> G5
    G5 --> REWORK["Return for rework"]:::warnstate

    RG1 -- Yes --> RG2
    RG1 -- No --> CHECK
    RG2 --> RG3
    RG3 --> RG4
    RG4 -- Approve --> RG5
    RG4 -- Reject --> RG6
    RG6 --> REWORK

    G4 --> CHECK
    RG5 --> CHECK
    CHECK -- No --> WAIT["Awaiting remaining approvals"]
    WAIT --> G2
    WAIT --> RG3
    CHECK -- Yes --> DONE["Cycle Approved"]:::endstate

    %% Admin path
    WAIT -.-> AD1
    AD1 --> AD2
    AD2 --> AD3
    AD3 -.-> G4
    AD3 -.-> RG5

    classDef endstate fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20
    classDef warnstate fill:#fff3e0,stroke:#ef6c00,color:#e65100
```

---

## Role Permissions Summary

```mermaid
---
config:
  layout: fixed
---
flowchart LR
 subgraph ROLES["Who Can Do What"]
    direction TB
        subgraph ADMIN_ROLE["Administrator"]
            A_ALL["All actions"]
            A_PROXY["Approve on behalf"]
            A_VOID["Void approvals"]
        end
        subgraph TEAM_ROLE["Monitoring Team Member"]
            T_CONFIG["Configure plans"]
            T_START["Start cycles"]
            T_REVIEW["Review & request approval"]
            T_CANCEL["Cancel cycles"]
        end
        subgraph DP_ROLE["Data Provider"]
            D_ENTER["Enter results"]
            D_SUBMIT["Submit cycle"]
            D_NO["Cannot: Start, Request Approval, Cancel"]:::restricted
        end
        subgraph APP_ROLE["Approver"]
            AP_GLOBAL["Approve (Global scope)"]
            AP_REGION["Approve (Regional scope)"]
            AP_REJECT["Reject with comments"]
        end
  end

    classDef restricted fill:#ffebee,stroke:#c62828,color:#b71c1c
```

---

## End-to-End Timeline Example

```mermaid
---
config:
  layout: fixed
---
flowchart LR
 subgraph TIMELINE["Q1 2025 Monitoring Cycle Timeline"]
        T1["Jan 1\nPeriod Start"]
        T2["Mar 31\nPeriod End"]
        T3["Apr 15\nSubmission Due"]
        T4["May 15\nReport Due"]
  end
 subgraph ACTIONS["Key Actions"]
        A1["Team starts cycle\n(locks version)"]
        A2["Data Provider\nenters results"]
        A3["Data Provider\nsubmits cycle"]
        A4["Team reviews\nand requests approval"]
        A5["Approvers\nsign off"]
        A6["Cycle\nApproved"]:::endstate
  end

    T1 --> A1
    A1 --> A2
    T2 --> A2
    A2 --> A3
    T3 --> A3
    A3 --> A4
    A4 --> A5
    T4 --> A5
    A5 --> A6

    classDef endstate fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20
```
