import React from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';

interface Report {
    id: string;
    name: string;
    description: string;
    path: string;
    icon: string;
    category: string;
}

const availableReports: Report[] = [
    {
        id: 'regional-compliance',
        name: 'Regional Deployment & Compliance Report',
        description: 'Shows all models deployed in each region with version numbers, validation status, and region-specific approval status. Answers the regulatory question: "Did the regional approver approve this specific deployment?"',
        path: '/reports/regional-compliance',
        icon: '🌍',
        category: 'Compliance'
    },
    {
        id: 'deviation-trends',
        name: 'Deviation Trends Report',
        description: 'Track validation component deviations across all validation projects. Shows deviation rates by component, risk tier, section, and trends over time.',
        path: '/reports/deviation-trends',
        icon: '📊',
        category: 'Compliance'
    },
    {
        id: 'overdue-revalidation',
        name: 'Overdue Revalidation Report',
        description: 'Comprehensive view of all overdue model revalidations including submission delays and validation delays. Tracks commentary status, responsible parties, and target dates for regulatory oversight.',
        path: '/reports/overdue-revalidation',
        icon: '⏰',
        category: 'Operations'
    },
];

const ReportsPage: React.FC = () => {
    // Group reports by category
    const reportsByCategory = availableReports.reduce((acc, report) => {
        if (!acc[report.category]) {
            acc[report.category] = [];
        }
        acc[report.category].push(report);
        return acc;
    }, {} as Record<string, Report[]>);

    return (
        <Layout>
            <div className="p-6">
                <div className="mb-6">
                    <h2 className="text-2xl font-bold text-gray-900">Reports</h2>
                    <p className="mt-2 text-sm text-gray-600">
                        Select a report to generate and export data for regulatory compliance and operational analysis.
                    </p>
                </div>

                {/* Reports Grid */}
                <div className="space-y-8">
                    {Object.entries(reportsByCategory).map(([category, reports]) => (
                        <div key={category}>
                            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                                <span className="mr-2">{category}</span>
                                <span className="text-xs font-normal text-gray-500">
                                    ({reports.length} {reports.length === 1 ? 'report' : 'reports'})
                                </span>
                            </h3>

                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {reports.map((report) => (
                                    <Link
                                        key={report.id}
                                        to={report.path}
                                        className="block bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow p-6 border border-gray-200 hover:border-blue-500"
                                    >
                                        <div className="flex items-start">
                                            <div className="text-4xl mr-4">{report.icon}</div>
                                            <div className="flex-1">
                                                <h4 className="text-lg font-semibold text-gray-900 mb-2">
                                                    {report.name}
                                                </h4>
                                                <p className="text-sm text-gray-600 mb-4">
                                                    {report.description}
                                                </p>
                                                <div className="flex items-center text-blue-600 text-sm font-medium">
                                                    <span>Generate Report</span>
                                                    <svg
                                                        className="w-4 h-4 ml-1"
                                                        fill="none"
                                                        stroke="currentColor"
                                                        viewBox="0 0 24 24"
                                                    >
                                                        <path
                                                            strokeLinecap="round"
                                                            strokeLinejoin="round"
                                                            strokeWidth={2}
                                                            d="M9 5l7 7-7 7"
                                                        />
                                                    </svg>
                                                </div>
                                            </div>
                                        </div>
                                    </Link>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Info Box */}
                <div className="mt-8 bg-blue-50 border-l-4 border-blue-400 p-4">
                    <div className="flex">
                        <div className="flex-shrink-0">
                            <svg
                                className="h-5 w-5 text-blue-400"
                                xmlns="http://www.w3.org/2000/svg"
                                viewBox="0 0 20 20"
                                fill="currentColor"
                            >
                                <path
                                    fillRule="evenodd"
                                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                                    clipRule="evenodd"
                                />
                            </svg>
                        </div>
                        <div className="ml-3">
                            <h3 className="text-sm font-medium text-blue-800">About Reports</h3>
                            <div className="mt-2 text-sm text-blue-700">
                                <p>
                                    All reports can be filtered, customized, and exported to CSV format.
                                    Reports are generated in real-time from the current database state.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Coming Soon Section */}
                <div className="mt-8 bg-gray-50 rounded-lg p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-3">Coming Soon</h3>
                    <ul className="space-y-2 text-sm text-gray-600">
                        <li className="flex items-center">
                            <svg className="w-4 h-4 mr-2 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                                <circle cx="10" cy="10" r="3" />
                            </svg>
                            Validation Aging Report - Track validation request lifecycle and SLA compliance
                        </li>
                        <li className="flex items-center">
                            <svg className="w-4 h-4 mr-2 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                                <circle cx="10" cy="10" r="3" />
                            </svg>
                            Model Inventory Report - Complete model inventory with ownership and status
                        </li>
                        <li className="flex items-center">
                            <svg className="w-4 h-4 mr-2 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                                <circle cx="10" cy="10" r="3" />
                            </svg>
                            Validation Findings Report - Summary of validation findings and recommendations
                        </li>
                        <li className="flex items-center">
                            <svg className="w-4 h-4 mr-2 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                                <circle cx="10" cy="10" r="3" />
                            </svg>
                            Audit Trail Report - Detailed audit log exports with filtering
                        </li>
                    </ul>
                </div>
            </div>
        </Layout>
    );
};

export default ReportsPage;
