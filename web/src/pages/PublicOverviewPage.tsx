import PublicLayout from '../components/public/PublicLayout';

import { ReactNode } from 'react';

function Section({ title, children }: { title: string; children: ReactNode }) {
    return (
        <section className="bg-white border border-gray-200 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
            <div className="mt-3 text-sm text-gray-700 leading-6">{children}</div>
        </section>
    );
}

export default function PublicOverviewPage() {
    return (
        <PublicLayout>
            <div className="max-w-5xl mx-auto px-4 py-10">
                <div className="flex flex-col gap-6">
                    <header className="flex flex-col gap-2">
                        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">System Overview</h1>
                        <p className="text-gray-700 max-w-3xl">
                            QMIS is a web application for managing a model inventory and supporting governance workflows.
                            This overview describes the system at a high level without exposing internal data.
                        </p>
                    </header>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Section title="Core Capabilities">
                            <ul className="list-disc pl-5 space-y-1">
                                <li>Model inventory management and ownership tracking</li>
                                <li>Workflow-based validation and recommendation tracking</li>
                                <li>Attestation cycles, submissions, and review flows</li>
                                <li>Role-based access controls and auditability</li>
                                <li>Operational reporting for oversight and planning</li>
                            </ul>
                        </Section>

                        <Section title="Who Uses It">
                            <ul className="list-disc pl-5 space-y-1">
                                <li><span className="font-medium">Admins</span>: configure reference data and oversee operations</li>
                                <li><span className="font-medium">Validators</span>: run workflow steps and manage outcomes</li>
                                <li><span className="font-medium">Model owners/contributors</span>: maintain records and respond to actions</li>
                                <li><span className="font-medium">Approvers</span>: review and approve region/global decisions (as applicable)</li>
                            </ul>
                        </Section>

                        <Section title="Security & Access">
                            <p>
                                Public pages contain only general information. All system data, workflows, and exports
                                require authentication.
                            </p>
                        </Section>

                        <Section title="Support">
                            <p>
                                After signing in, use in-app navigation to find workflow pages, dashboards, and reports.
                                If you need access, contact your system administrator.
                            </p>
                        </Section>
                    </div>
                </div>
            </div>
        </PublicLayout>
    );
}
