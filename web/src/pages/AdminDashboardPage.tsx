import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';

interface OverdueModel {
    model_id: number;
    model_name: string;
    risk_tier: string | null;
    owner_name: string;
    last_validation_date: string | null;
    next_due_date: string | null;
    days_overdue: number | null;
    status: string;
}

interface PassWithFindingsValidation {
    validation_id: number;
    model_id: number;
    model_name: string;
    validation_date: string;
    validator_name: string;
    findings_summary: string | null;
    has_recommendations: boolean;
}

export default function AdminDashboardPage() {
    const { user } = useAuth();
    const [overdueModels, setOverdueModels] = useState<OverdueModel[]>([]);
    const [passWithFindings, setPassWithFindings] = useState<PassWithFindingsValidation[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchDashboardData();
    }, []);

    const fetchDashboardData = async () => {
        try {
            const [overdueRes, findingsRes] = await Promise.all([
                api.get('/validations/dashboard/overdue'),
                api.get('/validations/dashboard/pass-with-findings')
            ]);
            setOverdueModels(overdueRes.data);
            setPassWithFindings(findingsRes.data);
        } catch (error) {
            console.error('Failed to fetch dashboard data:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-full">Loading...</div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="mb-6">
                <h2 className="text-2xl font-bold">Admin Dashboard</h2>
                <p className="text-gray-600 mt-1">Welcome back, {user?.full_name}</p>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-white p-6 rounded-lg shadow-md">
                    <h3 className="text-sm font-medium text-gray-500 uppercase">Overdue Validations</h3>
                    <p className="text-3xl font-bold text-red-600 mt-2">{overdueModels.length}</p>
                    <p className="text-sm text-gray-600 mt-1">Models requiring validation</p>
                </div>
                <div className="bg-white p-6 rounded-lg shadow-md">
                    <h3 className="text-sm font-medium text-gray-500 uppercase">Pass with Findings</h3>
                    <p className="text-3xl font-bold text-orange-600 mt-2">
                        {passWithFindings.filter(v => !v.has_recommendations).length}
                    </p>
                    <p className="text-sm text-gray-600 mt-1">Validations needing recommendations</p>
                </div>
                <div className="bg-white p-6 rounded-lg shadow-md">
                    <h3 className="text-sm font-medium text-gray-500 uppercase">Quick Actions</h3>
                    <div className="mt-2 space-y-2">
                        <Link to="/validations" className="block text-blue-600 hover:text-blue-800 text-sm">
                            View All Validations &rarr;
                        </Link>
                        <Link to="/validation-policy" className="block text-blue-600 hover:text-blue-800 text-sm">
                            Configure Validation Policy &rarr;
                        </Link>
                    </div>
                </div>
            </div>

            {/* Overdue Validations Table */}
            <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                <h3 className="text-lg font-bold mb-4">
                    Models Overdue for Validation ({overdueModels.length})
                </h3>
                {overdueModels.length === 0 ? (
                    <p className="text-gray-500">No models are currently overdue for validation.</p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Model Name
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Risk Tier
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Owner
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Last Validation
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Status
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Actions
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {overdueModels.map((model) => (
                                    <tr key={model.model_id}>
                                        <td className="px-4 py-3 whitespace-nowrap font-medium">
                                            <Link
                                                to={`/models/${model.model_id}`}
                                                className="text-blue-600 hover:text-blue-800"
                                            >
                                                {model.model_name}
                                            </Link>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            {model.risk_tier ? (
                                                <span className="px-2 py-1 text-xs rounded bg-orange-100 text-orange-800">
                                                    {model.risk_tier}
                                                </span>
                                            ) : (
                                                <span className="text-gray-400">-</span>
                                            )}
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">
                                            {model.owner_name}
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">
                                            {model.last_validation_date || 'Never'}
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs rounded ${
                                                model.status === 'Never Validated'
                                                    ? 'bg-red-100 text-red-800'
                                                    : 'bg-orange-100 text-orange-800'
                                            }`}>
                                                {model.status}
                                                {model.days_overdue && ` (${model.days_overdue} days)`}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <Link
                                                to={`/validations/new?model_id=${model.model_id}`}
                                                className="text-blue-600 hover:text-blue-800 text-sm"
                                            >
                                                Create Validation
                                            </Link>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Pass with Findings Table */}
            <div className="bg-white p-6 rounded-lg shadow-md">
                <h3 className="text-lg font-bold mb-4">
                    Validations with Findings ({passWithFindings.length})
                </h3>
                {passWithFindings.length === 0 ? (
                    <p className="text-gray-500">No validations with findings requiring attention.</p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Model
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Validation Date
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Validator
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Findings Summary
                                    </th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                        Recommendations
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {passWithFindings.map((validation) => (
                                    <tr key={validation.validation_id}>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            <Link
                                                to={`/models/${validation.model_id}`}
                                                className="text-blue-600 hover:text-blue-800 font-medium"
                                            >
                                                {validation.model_name}
                                            </Link>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">
                                            {validation.validation_date}
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap text-sm">
                                            {validation.validator_name}
                                        </td>
                                        <td className="px-4 py-3 text-sm max-w-md">
                                            <div className="truncate">
                                                {validation.findings_summary || 'No summary provided'}
                                            </div>
                                        </td>
                                        <td className="px-4 py-3 whitespace-nowrap">
                                            {validation.has_recommendations ? (
                                                <span className="px-2 py-1 text-xs rounded bg-green-100 text-green-800">
                                                    Has Recommendations
                                                </span>
                                            ) : (
                                                <span className="px-2 py-1 text-xs rounded bg-red-100 text-red-800">
                                                    No Recommendations
                                                </span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </Layout>
    );
}
