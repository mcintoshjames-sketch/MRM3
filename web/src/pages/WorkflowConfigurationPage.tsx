import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import Layout from '../components/Layout';
import api from '../api/client';

interface WorkflowSLA {
    sla_id: number;
    workflow_type: string;
    assignment_days: number;
    begin_work_days: number;
    approval_days: number;
    created_at: string;
    updated_at: string;
}

export default function WorkflowConfigurationPage() {
    const { user } = useAuth();
    const [sla, setSla] = useState<WorkflowSLA | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);

    const [formData, setFormData] = useState({
        assignment_days: 10,
        begin_work_days: 5,
        approval_days: 10
    });

    useEffect(() => {
        fetchSLA();
    }, []);

    const fetchSLA = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await api.get('/workflow-sla/validation');
            setSla(response.data);
            setFormData({
                assignment_days: response.data.assignment_days,
                begin_work_days: response.data.begin_work_days,
                approval_days: response.data.approval_days
            });
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load SLA configuration');
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setSuccess(null);
        setSaving(true);

        try {
            const response = await api.patch('/workflow-sla/validation', formData);
            setSla(response.data);
            setSuccess('Workflow SLA configuration updated successfully');
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update SLA configuration');
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex justify-center items-center h-64">
                    <div className="text-gray-500">Loading...</div>
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="max-w-4xl">
                <h1 className="text-2xl font-bold mb-6">Workflow Configuration</h1>

                {error && (
                    <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                        {error}
                    </div>
                )}

                {success && (
                    <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
                        {success}
                    </div>
                )}

                <div className="bg-white rounded-lg shadow-md p-6">
                    <div className="mb-6">
                        <h2 className="text-xl font-semibold mb-2">Validation Workflow SLA</h2>
                        <p className="text-sm text-gray-600">
                            Configure service level agreement timelines for the validation workflow.
                            These timelines are used to calculate time remaining and generate overdue alerts.
                        </p>
                    </div>

                    <form onSubmit={handleSubmit}>
                        <div className="space-y-6">
                            {/* Assignment SLA */}
                            <div className="border-b pb-4">
                                <label htmlFor="assignment_days" className="block text-sm font-medium mb-2">
                                    Assignment / Claim Period
                                </label>
                                <div className="flex items-start gap-4">
                                    <div className="flex-shrink-0">
                                        <input
                                            id="assignment_days"
                                            type="number"
                                            min="1"
                                            max="365"
                                            className="input-field w-24"
                                            value={formData.assignment_days}
                                            onChange={(e) => setFormData({ ...formData, assignment_days: parseInt(e.target.value) })}
                                            required
                                        />
                                        <span className="ml-2 text-sm text-gray-600">days</span>
                                    </div>
                                    <div className="flex-1">
                                        <p className="text-sm text-gray-600">
                                            Time allowed for a validation project to be assigned to a validator or claimed
                                            (from Intake status to having a primary validator assigned)
                                        </p>
                                    </div>
                                </div>
                            </div>

                            {/* Begin Work SLA */}
                            <div className="border-b pb-4">
                                <label htmlFor="begin_work_days" className="block text-sm font-medium mb-2">
                                    Begin Work Period
                                </label>
                                <div className="flex items-start gap-4">
                                    <div className="flex-shrink-0">
                                        <input
                                            id="begin_work_days"
                                            type="number"
                                            min="1"
                                            max="365"
                                            className="input-field w-24"
                                            value={formData.begin_work_days}
                                            onChange={(e) => setFormData({ ...formData, begin_work_days: parseInt(e.target.value) })}
                                            required
                                        />
                                        <span className="ml-2 text-sm text-gray-600">days</span>
                                    </div>
                                    <div className="flex-1">
                                        <p className="text-sm text-gray-600">
                                            Time allowed for assigned validators to begin work after assignment or claim
                                            (from Planning to In Progress status)
                                        </p>
                                    </div>
                                </div>
                            </div>

                            {/* Work Completion Lead Time - Info Only */}
                            <div className="border-b pb-4 bg-gray-50 -mx-6 px-6 py-4">
                                <div className="flex items-start gap-4">
                                    <div className="flex-shrink-0">
                                        <span className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-blue-100 text-blue-600">
                                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                            </svg>
                                        </span>
                                    </div>
                                    <div className="flex-1">
                                        <h4 className="text-sm font-medium text-gray-900 mb-1">
                                            Work Completion Lead Time
                                        </h4>
                                        <p className="text-sm text-gray-600">
                                            The work completion period is determined by each model's <strong>inherent risk tier</strong> and
                                            is configured in the <strong>Validation Policies</strong> section. Higher risk models have longer
                                            lead times to ensure thorough validation. This allows different completion expectations based on
                                            model complexity and risk exposure.
                                        </p>
                                        <p className="text-sm text-gray-500 mt-2">
                                            Navigate to <span className="font-medium">Admin → Validation Policies</span> to configure
                                            risk-tier-specific lead times.
                                        </p>
                                    </div>
                                </div>
                            </div>

                            {/* Approval SLA */}
                            <div className="pb-4">
                                <label htmlFor="approval_days" className="block text-sm font-medium mb-2">
                                    Approval Period
                                </label>
                                <div className="flex items-start gap-4">
                                    <div className="flex-shrink-0">
                                        <input
                                            id="approval_days"
                                            type="number"
                                            min="1"
                                            max="365"
                                            className="input-field w-24"
                                            value={formData.approval_days}
                                            onChange={(e) => setFormData({ ...formData, approval_days: parseInt(e.target.value) })}
                                            required
                                        />
                                        <span className="ml-2 text-sm text-gray-600">days</span>
                                    </div>
                                    <div className="flex-1">
                                        <p className="text-sm text-gray-600">
                                            Time allowed for approvals to be obtained after requesting approval
                                            (from Pending Approval to Approved status)
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="mt-6 flex gap-2">
                            <button
                                type="submit"
                                disabled={saving || user?.role !== 'Admin'}
                                className="btn-primary disabled:opacity-50"
                            >
                                {saving ? 'Saving...' : 'Save Configuration'}
                            </button>
                            {user?.role !== 'Admin' && (
                                <p className="text-sm text-gray-500 flex items-center">
                                    Only administrators can modify workflow configuration
                                </p>
                            )}
                        </div>
                    </form>

                    {sla && (
                        <div className="mt-6 pt-6 border-t">
                            <p className="text-xs text-gray-500">
                                Last updated: {new Date(sla.updated_at).toLocaleString()}
                            </p>
                        </div>
                    )}
                </div>

                <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h3 className="font-medium text-blue-900 mb-2">About Workflow SLA</h3>
                    <p className="text-sm text-blue-800">
                        These SLA timelines define the expected duration for each phase of the validation workflow.
                        They are used to:
                    </p>
                    <ul className="list-disc list-inside text-sm text-blue-800 mt-2 space-y-1">
                        <li>Calculate time remaining in each workflow phase</li>
                        <li>Generate overdue alerts for delayed validations</li>
                        <li>Track performance metrics and adherence to timelines</li>
                        <li>Provide visibility into validation process bottlenecks</li>
                    </ul>
                </div>
            </div>
        </Layout>
    );
}
