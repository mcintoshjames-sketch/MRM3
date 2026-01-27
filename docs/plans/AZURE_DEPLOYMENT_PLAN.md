# Azure Hardening & Deployment Illustrative Plan

## Overview
This document outlines the comprehensive work plan to transform the current local Docker Compose-based MRM solution into a bank-grade, secure Azure PaaS deployment. This plan prioritizes Zero Trust security, operational resilience, and strict compliance with banking standards.

## Feasibility Study Summary
**Verdict: Highly Feasible**
The current application architecture (FastAPI, React, SQLAlchemy, Docker) is "cloud-native ready" and aligns perfectly with Azure PaaS patterns. The migration is primarily an integration exercise rather than a re-platforming one.

**Core Assumptions & Prerequisites:**
*   **Network:** Existence of a shared Hub VNet (Firewall, ExpressRoute to on-prem, DDoS Protection) and approved Landing Zone.
*   **Identity:** Entra ID tenant available with group-based RBAC and support for App Registrations/Managed Identities.
*   **Tooling:** Azure DevOps or GitHub Enterprise available with OIDC support for CI/CD.

**Technical Validation:**
*   **Compute & DB:** AKS (Private Cluster) or Container Apps are fully supported. Postgres Flexible Server supports Zone Redundancy (ZRS) and Private Access in primary US regions.
*   **Security:** Architecture supports full "Zero Trust" implementation: Private Endpoints for all PaaS (ACR, KV, Storage, DB), egress filtering via Azure Firewall, and WAF (App Gateway) for ingress.
*   **Operations:** Native support for ZRS, soft-delete, and automated backups meets DR requirements.

**Key Risks:**
*   **Process Delays:** InfoSec reviews, Firewall rule approvals, and Private DNS coordination often cause significant lead times in banking environments.
*   **Technical:** Long-running synchronous tasks (e.g., PDF generation) may hit Azure Load Balancer timeouts, potentially requiring a future move to async background workers.

## Resource Assumptions
- **Team:** 2 Senior Engineers (1 Cloud/DevOps, 1 Full Stack), 1 QA Engineer.
- **Prerequisites:** Access to Azure Subscription, Entra ID Tenant, and existing Hub VNet (Firewall/ExpressRoute) connectivity.

## Cost Estimate (Chicago Market Rates)
Estimates based on typical fully-loaded contractor rates for Senior roles in Chicago, IL (2025).

| Role | Rate (Hourly) | Allocation | Duration | Total Cost |
| :--- | :--- | :--- | :--- | :--- |
| **Sr. Cloud/DevOps Engineer** | $145/hr | 100% (40hrs/wk) | 28 Weeks | $162,400 |
| **Sr. Full Stack Engineer** | $135/hr | 100% (40hrs/wk) | 28 Weeks | $151,200 |
| **QA Engineer** | $95/hr | 50% (20hrs/wk) | 28 Weeks | $53,200 |
| **Project Manager / Scrum Master** | $110/hr | 25% (10hrs/wk) | 28 Weeks | $30,800 |
| **Total Labor Cost** | | | | **$397,600** |

### Estimated Monthly Infrastructure Costs (Production)
*Estimates for a Zone-Redundant (ZRS) deployment in US East/Central.*

| Service | Configuration | Est. Monthly Cost |
| :--- | :--- | :--- |
| **Azure Postgres Flex** | General Purpose (D4ds_v5), HA (Zone Redundant), 512GB | ~$680 |
| **Compute (AKS/ACA)** | 3x Nodes (Standard_DS3_v2), ZRS | ~$450 |
| **App Gateway (WAF)** | WAF v2, Medium Instance Count | ~$350 |
| **Observability** | Log Analytics (Ingestion + Retention) | ~$300 |
| **Security & Networking** | ACR Premium, Key Vault, Private Endpoints | ~$150 |
| **Storage** | Blob Storage (ZRS), Backups | ~$100 |
| **Total Monthly Run-Rate** | | **~$2,030** |

*Note: Excludes external penetration testing fees ($15k-$30k).*

## Timeline Summary
**Total Estimated Duration:** 28 Weeks (~7 Months)
*Adjustment: Added 2 weeks to account for DR planning/drills, WAF tuning, and Governance implementation.*

| Phase | Focus | Duration |
| :--- | :--- | :--- |
| **1** | Architecture & Security Design | 5 Weeks |
| **2** | Application Hardening (Code) | 6 Weeks |
| **3** | Infrastructure Implementation (IaC) | 7 Weeks |
| **4** | DevSecOps & Observability | 4 Weeks |
| **5** | Security Review & Go-Live | 6 Weeks |

---

## Detailed Work Plan

### Phase 1: Architecture & Security Design
**Goal:** Define the target state and secure approval from InfoSec Architecture Board.

*   **Week 1-2: Network & Resource Design**
    *   Design Hub & Spoke VNet topology (Subnets for AKS/ACA, Data, Gateway).
    *   **Network Hardening:** Define Private DNS Zones for all Private Endpoints. Plan Azure Firewall Policies (FQDN allowlisting) for egress.
    *   **Resilience:** Define RPO/RTO targets. Select Zone Redundant storage/compute SKUs.
*   **Week 3-4: Threat Modeling & Governance**
    *   Conduct Threat Modeling session (STRIDE methodology).
    *   **Governance:** Define Azure Policy guardrails (Allowed Locations, Deny Public IP). Define Tagging Strategy.
    *   **Identity:** Define Workload Identity Federation (OIDC) for CI/CD (no long-lived secrets).
*   **Week 5: InfoSec Review Gate**
    *   Present architecture to InfoSec.
    *   Address initial feedback and architectural constraints.
    *   **Milestone:** Architecture Sign-off.

### Phase 2: Application Hardening (Code Remediation)
**Goal:** Refactor application code to support cloud-native security patterns.

*   **Week 6-7: Authentication Refactor**
    *   Replace `api/app/api/auth.py` mock auth with **MSAL (Microsoft Authentication Library)**.
    *   Implement JWT validation against real Azure AD tenant keys.
    *   Map Azure AD Groups to internal application roles (Admin, Validator).
*   **Week 8-9: Secrets & Configuration**
    *   Remove `.env` file dependency for sensitive data.
    *   Integrate `azure-identity` and `azure-keyvault-secrets` SDKs.
    *   **Secret Ops:** Implement logic for handling secret rotation (e.g., DB credentials) without downtime.
*   **Week 10: Database & Storage**
    *   Update SQLAlchemy engine to support Entra ID token-based authentication (passwordless).
    *   Refactor file storage to use Azure Blob Storage SDK instead of local disk.
*   **Week 11: Containerization**
    *   Create production multi-stage `Dockerfile` for Frontend (Nginx serving static build).
    *   Optimize Backend `Dockerfile` (non-root user, minimal base image).
    *   **Milestone:** Application running locally connected to Dev Azure resources.

### Phase 3: Infrastructure Implementation (IaC)
**Goal:** Provision the secure environment using Infrastructure as Code (Terraform/Bicep).

*   **Week 12-14: Core Networking & Governance**
    *   **IaC Governance:** Setup Remote State with Locking (Azure Storage). Apply Azure Policies.
    *   Provision VNets, NSGs, and **Private DNS Zones**.
    *   Deploy Azure Firewall with logging enabled.
    *   Provision Key Vault (RBAC model) and ACR (Private Endpoint).
*   **Week 15-16: Compute & Database (Resilient)**
    *   Provision Azure Postgres Flexible Server (**Zone Redundant**, Geo-Backup enabled).
    *   Provision AKS/ACA (**Zone Redundant**).
    *   Configure Node Pools and Autoscaling settings.
*   **Week 17-18: Ingress & Security**
    *   Deploy Azure Application Gateway with WAF (OWASP 3.2).
    *   **TLS Lifecycle:** Configure Key Vault integration for auto-renewing certificates. Enforce TLS 1.2+.
    *   Set up Azure Firewall rules for egress filtering.
    *   **Milestone:** Infrastructure deployed in Dev/Test environment.

### Phase 4: DevSecOps & Observability
**Goal:** Automate secure delivery and ensure visibility.

*   **Week 19-20: CI/CD Pipelines**
    *   Configure **OIDC (Workload Identity)** for GitHub Actions/Azure DevOps.
    *   Build pipelines for CI (Build, Test, Scan).
    *   Release pipelines for CD (Terraform Apply, Helm/Container Deploy).
*   **Week 21: Security Scanning Integration**
    *   Integrate SAST tools (SonarQube/CodeQL) into build pipeline.
    *   Integrate Container Image Scanning (Trivy/Defender for Cloud).
*   **Week 22: Observability**
    *   Instrument Backend/Frontend with Application Insights (OpenTelemetry).
    *   Configure Log Analytics Workspace for centralized logging (App + Firewall + WAF logs).
    *   **Milestone:** Automated deployment to Test with full telemetry.

### Phase 5: Security Review & Go-Live
**Goal:** Validate security posture and launch.

*   **Week 23-24: Penetration Testing & WAF Tuning**
    *   Engage internal Red Team or external vendor for Pen Test.
    *   **WAF Tuning:** Analyze logs in Log Analytics, tune exclusion rules to eliminate false positives.
*   **Week 25-26: DR Drill & Remediation**
    *   **DR Drill:** Execute full failover/restore test to validate RPO/RTO targets.
    *   Fix critical/high findings from Pen Test.
*   **Week 27: Final Prep**
    *   Perform dry-run data migration.
    *   Final InfoSec Sign-off.
*   **Week 28: Go-Live**
    *   Production deployment.
    *   DNS Cutover.
    *   Post-deployment verification.
    *   **Milestone:** Production Go-Live.

## Risk Factors & Contingencies
1.  **InfoSec Delays:** Security reviews often take longer than expected. *Mitigation:* Engage InfoSec early in Phase 1.
2.  **Legacy Data Migration:** Complexity of mapping old data to new schema. *Mitigation:* Start data mapping analysis in Phase 2.
3.  **Azure AD Integration:** Complex group mapping logic. *Mitigation:* Prototype auth flow early in Phase 2.
