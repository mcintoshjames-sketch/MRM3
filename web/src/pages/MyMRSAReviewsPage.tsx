import Layout from '../components/Layout';
import MRSAReviewDashboardWidget from '../components/MRSAReviewDashboardWidget';

export default function MyMRSAReviewsPage() {
    return (
        <Layout>
            <div className="mb-6">
                <h1 className="text-3xl font-bold text-gray-900">My MRSA Reviews</h1>
                <p className="mt-2 text-gray-600">
                    Track review status for MRSAs you own, develop, or support as a delegate.
                </p>
                <p className="mt-1 text-sm text-gray-500">
                    Focus on items that need attention and upcoming review deadlines.
                </p>
            </div>

            <MRSAReviewDashboardWidget
                title="MRSA Review Status"
                description="Review obligations and due dates for your MRSAs."
            />
        </Layout>
    );
}
