Here’s a combined reference you can drop straight into your requirements / CLAUDE.md.

---

# Model Taxonomy Reference

**Dimensions:** Regulatory Category vs. Model Type (Orthogonal)

This reference defines two distinct but related taxonomies:

* **Regulatory Category** – *“Which regulatory regime(s) does this model matter for?”*
* **Model Type** – *“What kind of model is this, functionally and economically?”*

A single model can have **one primary Model Type** and **one or more Regulatory Categories**.
Methodology (regression, GBM, NN, etc.) is **not** included here and will be handled via a separate **Methodology taxonomy**.

---

## 1. Regulatory Category Taxonomy

Regulatory Category captures the **regulatory or prudential context** in which a model is used. A model may have **multiple** regulatory categories (e.g., `{CCAR, CECL, Regulatory Reporting}`).

### 1.1 Capital & Stress Testing

**CCAR / DFAST Stress Testing**
Models used to produce projections and loss estimates for the Federal Reserve’s stress tests and internal CCAR-like processes.
Typical uses: FR Y-14 schedules, capital planning, enterprise stress testing.

**Basel Regulatory Capital – Credit Risk (RWA)**
Models that determine risk-weighted assets and capital requirements for credit risk under Basel rules (Standardized or Advanced).
Typical uses: IRB PD/LGD/EAD, internal rating–based capital engines.

**Market Risk Capital (VaR / FRTB / Stressed VaR / RNIV)**
Models supporting market risk capital calculations under Basel/FRB rules.
Typical uses: Trading book VaR/ES models, stressed VaR, risk-not-in-VaR, P&L attribution.

**Counterparty Credit Risk / CVA Capital**
Models to compute exposure at default, PFE, and CVA for counterparty credit risk capital.
Typical uses: Monte Carlo exposure engines, CVA pricing models, SA-CCR calculators.

**Internal Economic Capital / ICAAP**
Models used for internal capital (economic capital) and ICAAP beyond regulatory minima.
Typical uses: Economic capital by risk type, portfolio risk aggregation, capital allocation.

---

### 1.2 Accounting & Financial Reporting

**CECL / Allowance for Credit Losses (ACL)**
Models used for U.S. GAAP CECL expected credit loss and allowance calculations.
Typical uses: Lifetime PD/LGD/EAD, macro-linked loss forecasting, allowance allocation.

**IFRS 9 Expected Credit Loss**
Models used for IFRS 9 staging and ECL in non-U.S. entities within the group.
Typical uses: Stage 1/2/3 models, lifetime ECL, PD/LGD/EAD under IFRS rules.

**Fair Value / Valuation for Financial Reporting**
Models determining fair value of instruments and derivatives for accounting and disclosure (e.g., ASC 820).
Typical uses: Pricing Level 2/3 instruments, complex derivatives, CVA for GAAP P&L.

---

### 1.3 Liquidity, Interest Rate & Balance Sheet Risk

**Liquidity Risk & LCR / NSFR**
Models supporting liquidity risk metrics and regulatory liquidity ratios.
Typical uses: Cashflow forecasting, runoff and decay models, stress liquidity horizons.

**Interest Rate Risk in the Banking Book (IRRBB)**
Models for IRRBB metrics (EVE, NII) in the banking book.
Typical uses: Customer behaviour models, prepayment and deposit models for IRRBB.

**Asset/Liability Management (ALM) / FTP**
Models used for structural balance sheet risk and internal funds transfer pricing.
Typical uses: FTP curve construction, structural hedge models.

---

### 1.4 AML, Fraud, Conduct & Operational Risk

**AML / Sanctions / Transaction Monitoring**
Models and rule engines used for AML/BSA and sanctions monitoring.
Typical uses: Transaction scoring, customer risk scoring, sanctions matching.

**Fraud Detection**
Models that detect fraud across payment types and channels.
Typical uses: Card fraud, payments fraud, digital banking fraud detection.

**Conduct Risk / Fair Lending / UDAAP**
Models used for conduct, fair lending, and UDAAP risk monitoring.
Typical uses: Pricing and approval models subject to bias / fairness review.

**Operational Risk Capital / Scenario Models**
Models for operational risk capital and scenario-based loss estimation.
Typical uses: Loss distribution approaches, scenario aggregation.

---

### 1.5 Regulatory Reporting & Internal Risk Reporting

**Regulatory Reporting (FFIEC, FR Y-9C, FR Y-14, Call Reports, etc.)**
Models that directly feed or transform data for regulatory reports.
Typical uses: Allocation models, derivation of regulatory metrics, report-specific transformations.

**Internal Risk & Board Reporting**
Models used to produce Board/senior management risk dashboards and risk appetite metrics.
Typical uses: Composite risk indicators, enterprise risk dashboards.

---

### 1.6 Pricing, Margining & Collateral

**Pricing & Valuation – Internal / Customer**
Models used for pricing and valuation **not** directly labeled as capital or GAAP drivers.
Typical uses: Customer pricing, internal valuation engines, structured product pricing used primarily for business decisions.

**Margin & Collateral Models (IM / VM / Haircuts)**
Models that set margin levels, collateral eligibility, and haircuts.
Typical uses: Initial margin calculators, collateral valuation, securities financing haircuts.

---

### 1.7 Other / Cross-Cutting

**Model Risk Management / Meta-Models**
Models that quantify **model risk itself**, or aggregate model risk into scores/capital add-ons.
Typical uses: Model risk scoring engines, model risk capital add-on calculators.

**Non-Regulatory / Business Only**
Models with **no direct regulatory regime** link, but in scope due to material business impact.
Typical uses: Marketing, sales optimization, operational optimization models that affect decisions but are not explicitly referenced in regulations.

---

## 2. Model Type Taxonomy

Model Type describes **what the model does** in economic/risk terms. A model normally has **one primary type** (optionally a sub-type).

### 2.1 Credit Risk & Loss Models

**Retail PD Model**
Predicts probability of default for retail exposures (cards, mortgages, auto, consumer loans) over a horizon (point-in-time or lifetime).

**Wholesale PD Model**
Predicts probability of default for corporate, FI, sovereign, CRE or other wholesale obligors, often feeding internal rating systems.

**LGD Model (Loss Given Default)**
Estimates the percentage loss conditional on default, including collateral recoveries, workout costs, and cure rates.

**EAD / CCF Model (Exposure at Default / Credit Conversion Factor)**
Estimates exposure at the time of default, especially for revolving and off-balance sheet products.

**Application Scorecard**
Used at origination for accept/decline, limit assignment, and pricing decisions for new applicants.

**Behavioural Scorecard**
Scores existing customers based on recent behaviour for ongoing risk management and treatment decisions.

**Collections Scorecard**
Scores delinquent accounts to prioritize collections strategies, treatments, and resources.

**Internal Rating Model – Obligor / Facility**
Assigns obligor or facility ratings (grade scales) based on quantitative and qualitative factors; maps to PD or LGD bands.

**Transition / Migration / Roll-Rate Model**
Models transitions between states (e.g., current → 30/60/90 DPD → default → cure) or grade migrations over time.

**Prepayment / Early Termination Model**
Predicts early payoff, refinancing, or attrition of loans and lines; used in IRRBB, CECL lifetime, and ALM.

**Cure / Recovery Process Model**
Models the probability, timing, and amount of cure or recovery following default, including path-dependent workout behaviour.

---

### 2.2 Market Risk, Pricing & Valuation Models

**Pricing Model – Linear Instruments**
Values linear instruments (bonds, swaps, forwards, FX) using yield curves, spreads, and discounting.

**Pricing Model – Options & Exotics**
Values options and structured products (e.g. calls/puts, barriers, cliquets, structured notes) using stochastic models, trees, or simulation.

**Curve / Surface Construction Model**
Builds discount curves, credit curves, vol surfaces, and correlation structures from market quotes.

**VaR / Expected Shortfall (ES) Model**
Computes portfolio market risk (VaR/ES) at specified horizons and confidence levels using historical, simulation, or parametric methods.

**Sensitivity / Greeks Aggregation Model**
Calculates and aggregates sensitivities (delta, gamma, vega, etc.) across positions for risk management and hedging.

**XVA Model (CVA / DVA / FVA / MVA)**
Calculates valuation adjustments (credit, debt, funding, margin) on derivative portfolios.

**Risk Factor Simulation / Scenario Generator**
Simulates joint paths of risk factors (rates, FX, equity, commodities, spreads) for valuation, risk, and stress testing.

---

### 2.3 Liquidity, ALM & IRRBB Models

**Non-Maturity Deposit (NMD) Model**
Models stable vs non-stable deposit balances, behavioural life, and rate sensitivity for NMD products.

**Liquidity Runoff / Survival Horizon Model**
Projects cash inflows/outflows and survival horizons under stress assumptions.

**Balance Sheet Evolution / Dynamic Balance Sheet Model**
Simulates the evolution of the balance sheet (growth, run-off, prepayments, attrition) under macro and business scenarios.

**IRRBB Model (EVE / NII Simulation)**
Projects economic value and net interest income under rate shocks and scenarios for banking-book IRR.

**Funds Transfer Pricing (FTP) Model**
Allocates funding and liquidity costs to products/segments using internal transfer prices and curve constructs.

---

### 2.4 Accounting, Provisioning & Capital Aggregation Models

**Lifetime Loss / Expected Credit Loss (ECL) Engine**
Combines component models (PD, LGD, EAD, prepayment, macro links) to generate lifetime expected losses per exposure/segment.

**Provision / Reserve Allocation Model**
Allocates total allowance or provisions across portfolios, segments, and entities using ECL outputs and management overlays.

**Economic Capital / Unexpected Loss Model**
Computes unexpected loss and economic capital by risk type or portfolio using loss distributions and correlation assumptions.

**Stress Testing Projection Model (Top-Down / Bottom-Up)**
Generates stressed projections of key P&L and balance sheet metrics (PPNR, losses, RWA, capital ratios) under macro scenarios.

**Regulatory Metric Calculation Engine**
Calculates regulatory ratios and metrics (capital, leverage, liquidity, large exposure limits) from underlying risk and accounting data.

---

### 2.5 AML, Fraud, Compliance & Conduct Models

**Transaction Monitoring / Alert Generation Model (AML)**
Scores transactions, accounts, or relationships for suspicious activity and generates alerts.

**Customer Risk Rating (CRR) Model – AML/KYC**
Assigns inherent AML risk scores to customers based on geography, products, behaviour, and profile attributes.

**Sanctions Screening Matching Model**
Computes similarity/matching scores between customer/transaction data and sanctions lists.

**Fraud Detection Model**
Identifies potentially fraudulent transactions or accounts across products and channels.

**Fair Lending / Fairness Assessment Model**
Quantifies potential disparate impact or bias in credit approval, pricing, or collections decisions using fairness metrics.

---

### 2.6 Operational & Non-Financial Risk Models

**Operational Risk Capital Model (Loss Distribution Approach)**
Fits severity/frequency distributions to op-risk losses and computes capital at high confidence levels.

**Operational Risk Scenario Model**
Aggregates severe but plausible scenario losses into capital or risk measures.

**Conduct Risk / Complaints Scoring Model**
Scores complaints, events, or interactions for conduct risk severity and urgency.

**Vendor / Third-Party Risk Scoring Model**
Scores third-party relationships based on inherent risk and control environment.

---

### 2.7 Business, Customer & Revenue Analytics Models

**Propensity / Next-Best-Offer Model**
Predicts likelihood that a customer will accept a specific product or offer.

**Churn / Attrition Model**
Predicts likelihood that a customer will leave or significantly reduce activity.

**Pricing & Elasticity Model**
Estimates demand and/or margin sensitivity to price or fee changes.

**Segmentation / Clustering Model**
Groups customers or exposures into segments based on behaviours, value, or risk characteristics.

**Forecasting Model – Volumes / Revenues / KPIs**
Forecasts balances, transaction volumes, revenues, or other key performance indicators using time-series or panel methods.

---

### 2.8 Meta-Models & Utility Models

**Aggregation / Composite Index Model**
Combines multiple metrics into a composite index (e.g., risk appetite index, health scores).

**Mapping / Allocation Model**
Maps or allocates metrics from one dimension to another (e.g., group to legal entities, internal to regulatory categories).

**Model Risk Scoring / Model Tiering Model**
Scores models themselves to determine model risk tier, criticality, or validation intensity.

---

## 3. How These Dimensions Work Together in Governance & Reporting

### 3.1 Orthogonality

* **Model Type** describes the **function** of the model (PD vs LGD vs VaR vs pricing vs propensity).
* **Regulatory Category** describes the **regime / stakeholder** that cares about its outputs (CECL, CCAR, Basel capital, AML, etc.).
* The **same Model Type** can appear under multiple Regulatory Categories:

  * A **Retail PD Model** can be:

    * `{CECL, CCAR, Basel Capital}` in a large regulated bank.
    * `{Non-Regulatory / Business Only}` in a niche portfolio.
* This allows clean slicing:

  * “All **LGD models used for CECL**” → Type=`LGD`, RegCategory includes `CECL`.
  * “All **VaR models used for Market Risk Capital**” → Type=`VaR / ES`, RegCategory includes `Market Risk Capital`.

### 3.2 Implementation in the Inventory

In your model inventory / MRM database:

* **ModelType**: usually a **single FK** from `models.model_type_id` to a `model_types` lookup table (with `name` + `description` as above).
* **RegulatoryCategory**: typically a **many-to-many** via a link table:

  * `regulatory_categories` (id, name, description)
  * `model_regulatory_categories` (model_id, reg_category_id)

This structure supports:

* Governance rules keyed on **type + category** (e.g., “All CECL ECL engines must be validated comprehensively and approved by the Model Risk Committee”).
* Reporting slices that regulators and Board care about (e.g., “High-risk models tagged CCAR”, “All AML transaction monitoring models and their validation status”).

### 3.3 Governance & Reporting Use Cases

* **Risk Tiering & Validation Frequency**

  * Model Type shapes the **testing approach** (e.g., PD models get discrimination/calibration tests; VaR models get backtesting).
  * Regulatory Category shapes **validation intensity and frequency** (e.g., comprehensive for CCAR/CECL; targeted for internal business-only models).

* **Approval Routing & Policy Applicability**

  * Capital, CECL, and AML categories require **higher-level approvals** and additional stakeholders (Finance, Accounting, Compliance).
  * Non-regulatory types can follow lighter-weight approval paths.

* **Regulatory & Board Reporting**

  * Quickly extract inventory views such as:

    * “All CECL models with last validation date and open issues.”
    * “All Market Risk Capital models and their backtesting performance.”
    * “All fraud models and their monitoring metrics.”

* **Change Impact Assessment**

  * When a model changes, the combination of Model Type and Regulatory Category tells you:

    * Which **tests** must be re-run, and
    * Which **regulators / committees / reports** may be impacted.

This separation of **Type**, **Regulatory Category**, and (separately) **Methodology** gives you a clean, extensible taxonomy that works both for **data modeling** in your application and for **governance & reporting** in a large U.S. financial institution.
