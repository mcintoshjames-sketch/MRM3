import PublicLayout from '../components/public/PublicLayout';
import { ReactNode } from 'react';

function Section({ title, children, icon }: { title: string; children: ReactNode; icon?: string }) {
    return (
        <section className="bg-white border border-gray-200 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                {icon && <span>{icon}</span>}
                {title}
            </h2>
            <div className="mt-3 text-sm text-gray-700 leading-6">{children}</div>
        </section>
    );
}

function FeatureCard({ title, description, icon }: { title: string; description: string; icon: string }) {
    return (
        <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
            <div className="flex items-start gap-3">
                <span className="text-2xl">{icon}</span>
                <div>
                    <h4 className="font-medium text-gray-900">{title}</h4>
                    <p className="text-sm text-gray-600 mt-1">{description}</p>
                </div>
            </div>
        </div>
    );
}

function WorkflowStep({ step, title, description }: { step: number; title: string; description: string }) {
    return (
        <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-bold">
                {step}
            </div>
            <div>
                <h4 className="font-medium text-gray-900">{title}</h4>
                <p className="text-sm text-gray-600">{description}</p>
            </div>
        </div>
    );
}

function RoleCard({ role, icon, capabilities }: { role: string; icon: string; capabilities: string[] }) {
    return (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">{icon}</span>
                <h4 className="font-semibold text-gray-900">{role}</h4>
            </div>
            <ul className="text-sm text-gray-600 space-y-1">
                {capabilities.map((cap, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                        <span className="text-green-500 mt-0.5">&#10003;</span>
                        <span>{cap}</span>
                    </li>
                ))}
            </ul>
        </div>
    );
}

export default function PublicOverviewPage() {
    return (
        <PublicLayout>
            <div className="max-w-6xl mx-auto px-4 py-10">
                <div className="flex flex-col gap-8">
                    {/* Header */}
                    <header className="text-center">
                        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900">
                            QMIS System Overview
                        </h1>
                        <p className="text-lg text-gray-600 mt-3 max-w-3xl mx-auto">
                            Quantitative Methods Information System - A comprehensive Model Risk Management platform
                            supporting the full lifecycle of models and non-models across the organization.
                        </p>
                    </header>

                    {/* Value Proposition */}
                    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-100">
                        <h2 className="text-xl font-semibold text-gray-900 mb-4">Key Value Proposition</h2>
                        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
                            <div className="text-center">
                                <div className="text-2xl mb-2">&#9989;</div>
                                <h4 className="font-medium text-gray-900">Regulatory Compliance</h4>
                                <p className="text-xs text-gray-600">Complete audit trail, configurable policies, KPI reporting</p>
                            </div>
                            <div className="text-center">
                                <div className="text-2xl mb-2">&#128202;</div>
                                <h4 className="font-medium text-gray-900">Risk Oversight</h4>
                                <p className="text-xs text-gray-600">Multi-level risk assessment with inherent and residual risk tracking</p>
                            </div>
                            <div className="text-center">
                                <div className="text-2xl mb-2">&#9889;</div>
                                <h4 className="font-medium text-gray-900">Operational Efficiency</h4>
                                <p className="text-xs text-gray-600">Automated workflows, task queues, SLA tracking</p>
                            </div>
                            <div className="text-center">
                                <div className="text-2xl mb-2">&#128065;</div>
                                <h4 className="font-medium text-gray-900">Transparency</h4>
                                <p className="text-xs text-gray-600">Role-based dashboards, cross-functional visibility</p>
                            </div>
                            <div className="text-center">
                                <div className="text-2xl mb-2">&#128737;</div>
                                <h4 className="font-medium text-gray-900">Governance</h4>
                                <p className="text-xs text-gray-600">Multi-stakeholder approval chains, independence controls</p>
                            </div>
                        </div>
                    </div>

                    {/* Core Capabilities */}
                    <Section title="Core Capabilities" icon="&#128640;">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
                            <FeatureCard
                                icon="&#128451;"
                                title="Model Inventory"
                                description="Central repository for all quantitative models with classification, metadata, ownership, and regional deployment tracking."
                            />
                            <FeatureCard
                                icon="&#9989;"
                                title="Validation Workflow"
                                description="End-to-end validation lifecycle from intake to approval with multi-stage workflow, scorecard ratings, and independence controls."
                            />
                            <FeatureCard
                                icon="&#128200;"
                                title="Performance Monitoring"
                                description="Ongoing model health tracking with configurable metrics, thresholds, and automated alerting for Red/Yellow status."
                            />
                            <FeatureCard
                                icon="&#128221;"
                                title="Recommendations"
                                description="Findings and issues management with action plans, rebuttals, and multi-stakeholder closure workflow."
                            />
                            <FeatureCard
                                icon="&#128203;"
                                title="Risk Attestation"
                                description="Periodic compliance attestation for model owners affirming adherence to Model Risk and Validation Policy."
                            />
                            <FeatureCard
                                icon="&#128202;"
                                title="Compliance Reporting"
                                description="KPI dashboards, overdue tracking, regulatory reports, and drill-down capability to underlying data."
                            />
                            <FeatureCard
                                icon="&#128465;"
                                title="Decommissioning"
                                description="Controlled retirement process with approval gates, replacement documentation, and downstream impact verification."
                            />
                            <FeatureCard
                                icon="&#128203;"
                                title="MRSA & IRP Governance"
                                description="Independent Review Process coverage for Model Risk-Sensitive Applications with certification tracking."
                            />
                        </div>
                    </Section>

                    {/* Validation Workflow Detail */}
                    <Section title="Validation Workflow" icon="&#128260;">
                        <p className="mb-4">
                            QMIS provides comprehensive end-to-end validation lifecycle management with enforced
                            governance controls, independence requirements, and regulatory compliance.
                        </p>

                        {/* Workflow Diagram */}
                        <div className="bg-gray-50 rounded-lg p-4 mb-4 overflow-x-auto">
                            <div className="flex items-center gap-2 min-w-max text-sm">
                                <div className="px-3 py-2 bg-blue-100 text-blue-800 rounded font-medium">INTAKE</div>
                                <span className="text-gray-400">&#8594;</span>
                                <div className="px-3 py-2 bg-blue-100 text-blue-800 rounded font-medium">PLANNING</div>
                                <span className="text-gray-400">&#8594;</span>
                                <div className="px-3 py-2 bg-yellow-100 text-yellow-800 rounded font-medium">IN PROGRESS</div>
                                <span className="text-gray-400">&#8594;</span>
                                <div className="px-3 py-2 bg-purple-100 text-purple-800 rounded font-medium">REVIEW</div>
                                <span className="text-gray-400">&#8594;</span>
                                <div className="px-3 py-2 bg-orange-100 text-orange-800 rounded font-medium">PENDING APPROVAL</div>
                                <span className="text-gray-400">&#8594;</span>
                                <div className="px-3 py-2 bg-green-100 text-green-800 rounded font-medium">APPROVED</div>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <h4 className="font-medium text-gray-900 mb-2">Validation Types</h4>
                                <ul className="space-y-2 text-sm">
                                    <li><span className="font-medium">Initial:</span> First-time validation for new models</li>
                                    <li><span className="font-medium">Comprehensive:</span> Periodic revalidation (annual/biennial)</li>
                                    <li><span className="font-medium">Targeted Review:</span> Focused review of specific areas</li>
                                    <li><span className="font-medium">Interim:</span> Bridge validation pending full review</li>
                                </ul>
                            </div>
                            <div>
                                <h4 className="font-medium text-gray-900 mb-2">Key Features</h4>
                                <ul className="space-y-2 text-sm">
                                    <li>&#9642; Multi-model validation requests with priority assignment</li>
                                    <li>&#9642; Validator independence verification</li>
                                    <li>&#9642; 14-component validation plan with deviation tracking</li>
                                    <li>&#9642; Multi-criterion scorecard (Green/Yellow/Red scale)</li>
                                    <li>&#9642; Multi-stakeholder approvals (Global + Regional)</li>
                                </ul>
                            </div>
                        </div>
                    </Section>

                    {/* Model Inventory Features */}
                    <Section title="Model Inventory Management" icon="&#128451;">
                        <p className="mb-4">
                            The Model Inventory serves as the authoritative source for all quantitative models,
                            capturing essential metadata, ownership, classification, and deployment information.
                        </p>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="bg-gray-50 rounded p-4">
                                <h4 className="font-medium text-gray-900 mb-2">Registration & Classification</h4>
                                <ul className="text-sm text-gray-600 space-y-1">
                                    <li>&#8226; Unique model identification</li>
                                    <li>&#8226; In-House vs. Third-Party/Vendor</li>
                                    <li>&#8226; AI/ML methodology assignment</li>
                                    <li>&#8226; Usage frequency tracking</li>
                                    <li>&#8226; Model naming history</li>
                                </ul>
                            </div>
                            <div className="bg-gray-50 rounded p-4">
                                <h4 className="font-medium text-gray-900 mb-2">Ownership & Accountability</h4>
                                <ul className="text-sm text-gray-600 space-y-1">
                                    <li>&#8226; Primary owner (required)</li>
                                    <li>&#8226; Developer designation</li>
                                    <li>&#8226; Shared ownership support</li>
                                    <li>&#8226; Monitoring manager assignment</li>
                                    <li>&#8226; Delegate capabilities</li>
                                </ul>
                            </div>
                            <div className="bg-gray-50 rounded p-4">
                                <h4 className="font-medium text-gray-900 mb-2">Risk Classification</h4>
                                <ul className="text-sm text-gray-600 space-y-1">
                                    <li>&#8226; 4-tier inherent risk (High to Very Low)</li>
                                    <li>&#8226; Quantitative & qualitative assessment</li>
                                    <li>&#8226; Override capability with justification</li>
                                    <li>&#8226; Residual risk computation</li>
                                    <li>&#8226; Multi-region deployment tracking</li>
                                </ul>
                            </div>
                        </div>

                        <div className="mt-4 bg-blue-50 rounded-lg p-4 border border-blue-100">
                            <h4 className="font-medium text-gray-900 mb-2">Model Approval Status</h4>
                            <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-sm">
                                <div className="bg-green-100 text-green-800 px-2 py-1 rounded text-center">APPROVED</div>
                                <div className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-center">INTERIM_APPROVED</div>
                                <div className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-center">VALIDATION_IN_PROGRESS</div>
                                <div className="bg-red-100 text-red-800 px-2 py-1 rounded text-center">EXPIRED</div>
                                <div className="bg-gray-100 text-gray-800 px-2 py-1 rounded text-center">NEVER_VALIDATED</div>
                            </div>
                        </div>
                    </Section>

                    {/* Performance Monitoring */}
                    <Section title="Performance Monitoring" icon="&#128200;">
                        <p className="mb-4">
                            Comprehensive ongoing monitoring framework for tracking model performance after validation
                            with configurable metrics, thresholds, and automated alerting.
                        </p>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <h4 className="font-medium text-gray-900 mb-3">Monitoring Cycle Workflow</h4>
                                <div className="flex flex-wrap items-center gap-2 text-sm mb-4">
                                    <span className="px-2 py-1 bg-gray-100 rounded">PENDING</span>
                                    <span>&#8594;</span>
                                    <span className="px-2 py-1 bg-blue-100 rounded">DATA_COLLECTION</span>
                                    <span>&#8594;</span>
                                    <span className="px-2 py-1 bg-purple-100 rounded">UNDER_REVIEW</span>
                                    <span>&#8594;</span>
                                    <span className="px-2 py-1 bg-orange-100 rounded">PENDING_APPROVAL</span>
                                    <span>&#8594;</span>
                                    <span className="px-2 py-1 bg-green-100 rounded">APPROVED</span>
                                </div>

                                <h4 className="font-medium text-gray-900 mb-2">Threshold Configuration</h4>
                                <div className="flex gap-3 text-sm">
                                    <div className="flex items-center gap-1">
                                        <span className="w-3 h-3 bg-green-500 rounded-full"></span>
                                        <span>Green: Acceptable</span>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <span className="w-3 h-3 bg-yellow-500 rounded-full"></span>
                                        <span>Yellow: Warning</span>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <span className="w-3 h-3 bg-red-500 rounded-full"></span>
                                        <span>Red: Critical</span>
                                    </div>
                                </div>
                            </div>
                            <div>
                                <h4 className="font-medium text-gray-900 mb-2">Key Performance Metrics (KPM)</h4>
                                <ul className="text-sm text-gray-600 space-y-1">
                                    <li>&#8226; Library of 47 pre-defined metrics across 13 categories</li>
                                    <li>&#8226; <span className="font-medium">Quantitative:</span> Numerical values with automated threshold checking</li>
                                    <li>&#8226; <span className="font-medium">Qualitative:</span> SME judgment with guidance</li>
                                    <li>&#8226; <span className="font-medium">Outcome Only:</span> Direct Red/Yellow/Green selection</li>
                                    <li>&#8226; Version-controlled metric configurations</li>
                                    <li>&#8226; Performance trend analysis over time</li>
                                </ul>
                            </div>
                        </div>
                    </Section>

                    {/* Recommendations Workflow */}
                    <Section title="Recommendations & Issues Tracking" icon="&#128221;">
                        <p className="mb-4">
                            Findings discovered during validation or monitoring are tracked as Recommendations
                            with full lifecycle management including action plans, rebuttals, and closure workflows.
                        </p>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <h4 className="font-medium text-gray-900 mb-2">Priority Levels</h4>
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2">
                                        <span className="px-2 py-1 bg-red-100 text-red-800 rounded text-sm font-medium">High</span>
                                        <span className="text-sm text-gray-600">Critical findings requiring immediate attention</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="px-2 py-1 bg-orange-100 text-orange-800 rounded text-sm font-medium">Medium</span>
                                        <span className="text-sm text-gray-600">Significant findings with moderate urgency</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-sm font-medium">Low</span>
                                        <span className="text-sm text-gray-600">Minor findings for tracking</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm font-medium">Consideration</span>
                                        <span className="text-sm text-gray-600">Advisory observations</span>
                                    </div>
                                </div>
                            </div>
                            <div>
                                <h4 className="font-medium text-gray-900 mb-2">Key Features</h4>
                                <ul className="text-sm text-gray-600 space-y-1">
                                    <li>&#8226; Task-based action plans with owners and target dates</li>
                                    <li>&#8226; Progress tracking per task</li>
                                    <li>&#8226; Rebuttal process with validator review</li>
                                    <li>&#8226; Evidence submission requirements</li>
                                    <li>&#8226; Multi-stakeholder approval for closure</li>
                                    <li>&#8226; Regional configuration overrides</li>
                                </ul>
                            </div>
                        </div>
                    </Section>

                    {/* Compliance Reporting */}
                    <Section title="Compliance Reporting & KPIs" icon="&#128202;">
                        <p className="mb-4">
                            Centralized Reports section with pre-built regulatory and operational reports
                            featuring drill-down capability to underlying data.
                        </p>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="bg-gray-50 rounded p-4">
                                <h4 className="font-medium text-gray-900 mb-2">Available Reports</h4>
                                <ul className="text-sm text-gray-600 space-y-1">
                                    <li>&#128202; KPI Report (21 metrics)</li>
                                    <li>&#127758; Regional Compliance</li>
                                    <li>&#128337; Overdue Revalidation</li>
                                    <li>&#128200; Deviation Trends</li>
                                    <li>&#9888; Critical Limitations</li>
                                    <li>&#128221; Name Changes</li>
                                </ul>
                            </div>
                            <div className="bg-gray-50 rounded p-4">
                                <h4 className="font-medium text-gray-900 mb-2">KPI Categories</h4>
                                <ul className="text-sm text-gray-600 space-y-1">
                                    <li>&#8226; Model Inventory (4.1-4.5)</li>
                                    <li>&#8226; Validation (4.6-4.9)</li>
                                    <li>&#8226; Key Risk Indicators (4.7, 4.27)</li>
                                    <li>&#8226; Monitoring (4.10-4.12)</li>
                                    <li>&#8226; Recommendations (4.18-4.21)</li>
                                    <li>&#8226; Governance (4.22-4.24)</li>
                                </ul>
                            </div>
                            <div className="bg-gray-50 rounded p-4">
                                <h4 className="font-medium text-gray-900 mb-2">Export Capabilities</h4>
                                <ul className="text-sm text-gray-600 space-y-1">
                                    <li>&#8226; CSV export on all list pages</li>
                                    <li>&#8226; PDF report generation</li>
                                    <li>&#8226; Current view export (filters applied)</li>
                                    <li>&#8226; Standardized ISO date formatting</li>
                                    <li>&#8226; Drill-down to underlying data</li>
                                </ul>
                            </div>
                        </div>
                    </Section>

                    {/* User Roles */}
                    <Section title="User Roles & Dashboards" icon="&#128101;">
                        <p className="mb-4">
                            Role-based access control with specialized dashboards tailored to each user type.
                        </p>

                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            <RoleCard
                                role="Admin"
                                icon="&#128736;"
                                capabilities={[
                                    "Full system access",
                                    "Policy configuration",
                                    "User management",
                                    "Taxonomy administration"
                                ]}
                            />
                            <RoleCard
                                role="Validator"
                                icon="&#9989;"
                                capabilities={[
                                    "Validation execution",
                                    "Findings creation",
                                    "Scorecard ratings",
                                    "Reviews and sign-offs"
                                ]}
                            />
                            <RoleCard
                                role="Approver"
                                icon="&#128203;"
                                capabilities={[
                                    "Global/Regional approvals",
                                    "Approval tracking",
                                    "Evidence review",
                                    "Quick approval links"
                                ]}
                            />
                            <RoleCard
                                role="Model Owner"
                                icon="&#128100;"
                                capabilities={[
                                    "Model submission",
                                    "Attestation completion",
                                    "Response to findings",
                                    "Portfolio management"
                                ]}
                            />
                            <RoleCard
                                role="Monitoring User"
                                icon="&#128200;"
                                capabilities={[
                                    "Data collection entry",
                                    "Metric result submission",
                                    "Cycle review workflow",
                                    "Performance tracking"
                                ]}
                            />
                            <RoleCard
                                role="Standard User"
                                icon="&#128065;"
                                capabilities={[
                                    "Read-only model access",
                                    "View reports",
                                    "Search inventory",
                                    "Dashboard widgets"
                                ]}
                            />
                        </div>
                    </Section>

                    {/* Getting Started */}
                    <Section title="Quick Navigation Guide" icon="&#127919;">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-4">
                                <WorkflowStep
                                    step={1}
                                    title="Dashboard"
                                    description="Start here to see pending tasks, alerts, and your work queue"
                                />
                                <WorkflowStep
                                    step={2}
                                    title="Models"
                                    description="Browse the model inventory, click any model for details and tabs"
                                />
                                <WorkflowStep
                                    step={3}
                                    title="Validation Workflow"
                                    description="View and manage validation requests through workflow stages"
                                />
                                <WorkflowStep
                                    step={4}
                                    title="Monitoring Plans"
                                    description="Track ongoing performance monitoring cycles and results"
                                />
                            </div>
                            <div className="space-y-4">
                                <WorkflowStep
                                    step={5}
                                    title="Recommendations"
                                    description="Track findings, action plans, and closure workflows"
                                />
                                <WorkflowStep
                                    step={6}
                                    title="IRPs"
                                    description="Manage Independent Review Processes for high-risk MRSAs"
                                />
                                <WorkflowStep
                                    step={7}
                                    title="Reports"
                                    description="Access KPI reports, compliance reports, and drill-down analytics"
                                />
                                <WorkflowStep
                                    step={8}
                                    title="Taxonomy (Admin)"
                                    description="Configure system values, risk factors, and workflow settings"
                                />
                            </div>
                        </div>
                    </Section>

                    {/* Security & Access */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Section title="Security & Access" icon="&#128274;">
                            <ul className="space-y-2">
                                <li className="flex items-start gap-2">
                                    <span className="text-green-500">&#10003;</span>
                                    <span><span className="font-medium">Authentication:</span> JWT-based with configurable token expiry</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-green-500">&#10003;</span>
                                    <span><span className="font-medium">Authorization:</span> Role-based access control (RBAC)</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-green-500">&#10003;</span>
                                    <span><span className="font-medium">Independence:</span> Enforced separation of duties</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-green-500">&#10003;</span>
                                    <span><span className="font-medium">Audit Logging:</span> Complete action attribution</span>
                                </li>
                            </ul>
                            <p className="mt-3 text-gray-500 text-xs">
                                Public pages contain only general information. All system data, workflows, and exports
                                require authentication.
                            </p>
                        </Section>

                        <Section title="Support & Access" icon="&#128172;">
                            <p className="mb-3">
                                After signing in, use in-app navigation to find workflow pages, dashboards, and reports.
                            </p>
                            <div className="bg-blue-50 border border-blue-100 rounded-lg p-3">
                                <p className="text-sm">
                                    <span className="font-medium">Need access?</span> Contact your system administrator
                                    to request appropriate role assignment based on your responsibilities.
                                </p>
                            </div>
                            <div className="mt-3 text-sm text-gray-600">
                                <p className="font-medium">Key Workflows to Explore:</p>
                                <ul className="mt-1 space-y-1">
                                    <li>&#8226; View a Model: Models &#8594; Click any model &#8594; Explore tabs</li>
                                    <li>&#8226; Validation Request: Workflow &#8594; View request &#8594; See stages</li>
                                    <li>&#8226; KPI Report: Reports &#8594; KPI Report &#8594; Drill-down</li>
                                </ul>
                            </div>
                        </Section>
                    </div>

                    {/* Footer */}
                    <div className="text-center text-sm text-gray-500 border-t border-gray-200 pt-6">
                        <p>
                            QMIS provides a comprehensive Model Risk Management solution addressing the complete model lifecycle—from
                            registration through validation, monitoring, and decommissioning—with rigorous governance,
                            compliance assurance, and operational efficiency.
                        </p>
                    </div>
                </div>
            </div>
        </PublicLayout>
    );
}
