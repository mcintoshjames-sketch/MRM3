import { Link } from 'react-router-dom';
import PublicLayout from '../components/public/PublicLayout';

function GuideLink({ to, title, body }: { to: string; title: string; body: string }) {
    return (
        <Link to={to} className="block bg-white border border-gray-200 rounded-lg p-5 hover:border-gray-300 hover:shadow-sm transition">
            <div className="text-base font-semibold text-gray-900">{title}</div>
            <div className="mt-2 text-sm text-gray-700">{body}</div>
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
                            These guides describe typical workflows at a high level. Detailed screens and data are available after login.
                        </p>
                    </header>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <GuideLink
                            to="/guides/getting-started"
                            title="Getting Started"
                            body="Sign in, understand navigation, and find the right dashboard for your role."
                        />
                        <GuideLink
                            to="/guides/model-owners"
                            title="Model Owners & Contributors"
                            body="Maintain model records, respond to recommendations, and complete attestations."
                        />
                        <GuideLink
                            to="/guides/validators"
                            title="Validators"
                            body="Manage validation workflow steps, outcomes, and review queues."
                        />
                        <GuideLink
                            to="/guides/approvers"
                            title="Approvers"
                            body="Review items awaiting approval and track decisions."
                        />
                        <GuideLink
                            to="/guides/admins"
                            title="Admins"
                            body="Configure reference data, manage users, and oversee operational reporting."
                        />
                    </div>

                    <div className="text-sm text-gray-600">
                        Need access? Use the <Link className="text-blue-700 font-medium" to="/login">Login</Link> link.
                    </div>
                </div>
            </div>
        </PublicLayout>
    );
}
