import { Link } from 'react-router-dom';
import PublicLayout from '../components/public/PublicLayout';

function Card({ title, body, to }: { title: string; body: string; to: string }) {
    return (
        <Link
            to={to}
            className="block bg-white border border-gray-200 rounded-lg p-5 hover:border-gray-300 hover:shadow-sm transition"
        >
            <div className="text-base font-semibold text-gray-900">{title}</div>
            <div className="mt-2 text-sm text-gray-600">{body}</div>
            <div className="mt-3 text-sm font-medium text-blue-700">Learn more →</div>
        </Link>
    );
}

export default function PublicLandingPage() {
    return (
        <PublicLayout>
            <div className="bg-white">
                <div className="max-w-5xl mx-auto px-4 py-12">
                    <div className="flex flex-col gap-6">
                        <div className="flex flex-col gap-3">
                            <h1 className="text-3xl sm:text-4xl font-bold text-gray-900">
                                Model inventory and governance — in one place
                            </h1>
                            <p className="text-lg text-gray-700 max-w-3xl">
                                QMIS supports model inventory management, workflow-based validation tracking, attestations,
                                approvals, and reporting. This public landing page provides a high-level overview and
                                role-based user guides. All operational data is available only after login.
                            </p>
                        </div>

                        <div className="flex flex-col sm:flex-row gap-3">
                            <Link to="/login" className="btn-primary w-full sm:w-auto text-center">
                                Login to QMIS
                            </Link>
                            <Link to="/overview" className="btn-secondary w-full sm:w-auto text-center">
                                System Overview
                            </Link>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4">
                            <Card
                                title="System Overview"
                                body="What QMIS is, what it does, and how the components fit together."
                                to="/overview"
                            />
                            <Card
                                title="User Guides"
                                body="Role-based guides for admins, validators, model owners, and approvers."
                                to="/guides"
                            />
                            <Card
                                title="Getting Started"
                                body="Basic navigation, common tasks, and where to find help once signed in."
                                to="/guides/getting-started"
                            />
                        </div>

                        <div className="mt-6 bg-gray-50 border border-gray-200 rounded-lg p-5">
                            <div className="text-sm font-semibold text-gray-900">Privacy note</div>
                            <div className="mt-2 text-sm text-gray-700">
                                This page intentionally avoids sensitive or proprietary details. If you have access,
                                use the Login button to sign in and view internal content.
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </PublicLayout>
    );
}
