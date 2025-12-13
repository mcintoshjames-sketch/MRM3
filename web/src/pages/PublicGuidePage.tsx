import { Link, useParams } from 'react-router-dom';
import PublicLayout from '../components/public/PublicLayout';

type GuideContent = {
    title: string;
    summary: string;
    sections: Array<{ heading: string; bullets: string[] }>;
};

const GUIDES: Record<string, GuideContent> = {
    'getting-started': {
        title: 'Getting Started',
        summary: 'A quick orientation for first-time users.',
        sections: [
            {
                heading: 'Sign In',
                bullets: [
                    'Use your assigned account to sign in.',
                    'If you do not have access, contact your system administrator.',
                ],
            },
            {
                heading: 'Navigation',
                bullets: [
                    'Use the main navigation to access dashboards, workflows, and reports.',
                    'Your available pages depend on your role (admin, validator, owner, approver).',
                ],
            },
            {
                heading: 'Common Tasks',
                bullets: [
                    'Find and update model records you own or contribute to.',
                    'Track validation requests and recommendations relevant to you.',
                    'Complete required attestations when cycles are open.',
                ],
            },
        ],
    },
    'model-owners': {
        title: 'Model Owners & Contributors',
        summary: 'Maintain model records and respond to governance actions.',
        sections: [
            {
                heading: 'Model Record Maintenance',
                bullets: [
                    'Keep model metadata current (ownership, status, key attributes).',
                    'Update relationships and supporting information as required by policy.',
                ],
            },
            {
                heading: 'Recommendations & Action Plans',
                bullets: [
                    'Review recommendations assigned to your models.',
                    'Provide responses and complete action plans as applicable.',
                ],
            },
            {
                heading: 'Attestations',
                bullets: [
                    'Complete attestations within the open window.',
                    'Provide required evidence when requested.',
                ],
            },
        ],
    },
    validators: {
        title: 'Validators',
        summary: 'Execute validation workflow steps and manage validation outcomes.',
        sections: [
            {
                heading: 'Workflow Execution',
                bullets: [
                    'Review incoming requests and required artifacts.',
                    'Record outcomes and manage status progression.',
                ],
            },
            {
                heading: 'Oversight',
                bullets: [
                    'Monitor queues and timelines using dashboards and reports.',
                    'Escalate exceptions according to governance processes.',
                ],
            },
        ],
    },
    approvers: {
        title: 'Approvers',
        summary: 'Review items awaiting approval and record decisions.',
        sections: [
            {
                heading: 'Approvals',
                bullets: [
                    'Review approval requests relevant to your remit.',
                    'Approve, reject, or request follow-up as permitted.',
                ],
            },
            {
                heading: 'Traceability',
                bullets: [
                    'Use built-in history and audit views to understand context.',
                ],
            },
        ],
    },
    admins: {
        title: 'Admins',
        summary: 'Configure reference data and oversee operational management.',
        sections: [
            {
                heading: 'Configuration',
                bullets: [
                    'Manage reference data and system configuration according to governance.',
                    'Maintain user access and roles as needed.',
                ],
            },
            {
                heading: 'Operations',
                bullets: [
                    'Monitor logs and operational reports.',
                    'Coordinate changes with appropriate review and testing.',
                ],
            },
        ],
    },
};

export default function PublicGuidePage() {
    const { slug } = useParams();

    const guide = (slug && GUIDES[slug]) || null;

    return (
        <PublicLayout>
            <div className="max-w-5xl mx-auto px-4 py-10">
                {!guide ? (
                    <div className="bg-white border border-gray-200 rounded-lg p-6">
                        <div className="text-lg font-semibold text-gray-900">Guide not found</div>
                        <div className="mt-2 text-sm text-gray-700">
                            Return to <Link className="text-blue-700 font-medium" to="/guides">User Guides</Link>.
                        </div>
                    </div>
                ) : (
                    <div className="flex flex-col gap-6">
                        <header className="flex flex-col gap-2">
                            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">{guide.title}</h1>
                            <p className="text-gray-700 max-w-3xl">{guide.summary}</p>
                        </header>

                        <div className="bg-white border border-gray-200 rounded-lg p-6">
                            <div className="flex flex-col gap-5">
                                {guide.sections.map((section) => (
                                    <section key={section.heading}>
                                        <div className="text-base font-semibold text-gray-900">{section.heading}</div>
                                        <ul className="mt-2 list-disc pl-5 space-y-1 text-sm text-gray-700">
                                            {section.bullets.map((b) => (
                                                <li key={b}>{b}</li>
                                            ))}
                                        </ul>
                                    </section>
                                ))}
                            </div>
                        </div>

                        <div className="text-sm text-gray-600">
                            Back to <Link className="text-blue-700 font-medium" to="/guides">User Guides</Link>.
                        </div>
                    </div>
                )}
            </div>
        </PublicLayout>
    );
}
