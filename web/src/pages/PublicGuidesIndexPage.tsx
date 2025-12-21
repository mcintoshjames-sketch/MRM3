import { Link } from 'react-router-dom';
import PublicLayout from '../components/public/PublicLayout';

interface Guide {
    slug: string;
    title: string;
    description: string;
    filename: string;
}

const GUIDES: Guide[] = [
    {
        slug: 'model-inventory',
        title: 'Model Inventory',
        description: 'Submit model records, understand model details, risk assessment, versions, relationships, limitations, and decommissioning.',
        filename: 'USER_GUIDE_MODEL_INVENTORY.md',
    },
    {
        slug: 'model-validation',
        title: 'Model Validation',
        description: 'Complete guide to the validation workflow including intake, planning, execution, review, and approval processes.',
        filename: 'USER_GUIDE_MODEL_VALIDATION.md',
    },
    {
        slug: 'model-changes',
        title: 'Model Changes & Version Management',
        description: 'Manage model versions, track changes, deployment workflows, and version activation procedures.',
        filename: 'USER_GUIDE_MODEL_CHANGES.md',
    },
    {
        slug: 'recommendations',
        title: 'Model Recommendations',
        description: 'Track and resolve validation findings including action plans, rebuttals, and approval workflows.',
        filename: 'USER_GUIDE_RECOMMENDATIONS.md',
    },
    {
        slug: 'model-exceptions',
        title: 'Model Exceptions',
        description: 'Document and manage model exceptions, compensating controls, and exception approval workflows.',
        filename: 'USER_GUIDE_MODEL_EXCEPTIONS.md',
    },
    {
        slug: 'attestation',
        title: 'Model Risk Attestation',
        description: 'Conduct periodic attestations, coverage targets, scheduling rules, and attestation cycle management.',
        filename: 'USER_GUIDE_ATTESTATION.md',
    },
    {
        slug: 'performance-monitoring',
        title: 'Performance Monitoring',
        description: 'Configure monitoring plans, define KPMs, record metrics, track thresholds, and manage monitoring cycles.',
        filename: 'USER_GUIDE_PERFORMANCE_MONITORING.md',
    },
    {
        slug: 'mrsa-irp',
        title: 'MRSA and IRP Management',
        description: 'Manage Model Risk Self-Assessments (MRSAs) and Identified Risk Profiles (IRPs) for non-model quantitative methods.',
        filename: 'USER_GUIDE_MRSA_IRP.md',
    },
];

function GuideLink({ guide }: { guide: Guide }) {
    return (
        <Link
            to={`/guides/${guide.slug}`}
            className="block bg-white border border-gray-200 rounded-lg p-5 hover:border-blue-300 hover:shadow-md transition group"
        >
            <div className="text-base font-semibold text-gray-900 group-hover:text-blue-700">{guide.title}</div>
            <div className="mt-2 text-sm text-gray-600">{guide.description}</div>
        </Link>
    );
}

export default function PublicGuidesIndexPage() {
    return (
        <PublicLayout>
            <div className="max-w-5xl mx-auto px-4 py-10">
                <div className="flex flex-col gap-6">
                    <header className="flex flex-col gap-2">
                        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">User Guides</h1>
                        <p className="text-gray-700 max-w-3xl">
                            Comprehensive documentation for managing models, validations, and risk governance workflows in the Quantitative Methods Information System (QMIS).
                        </p>
                    </header>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {GUIDES.map((guide) => (
                            <GuideLink key={guide.slug} guide={guide} />
                        ))}
                    </div>

                    <div className="text-sm text-gray-600">
                        Need access to the application? Use the <Link className="text-blue-700 font-medium hover:underline" to="/login">Login</Link> link.
                    </div>
                </div>
            </div>
        </PublicLayout>
    );
}

// Export GUIDES for use in PublicGuidePage
export { GUIDES };
export type { Guide };
