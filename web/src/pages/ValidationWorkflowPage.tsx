import { useState, useEffect } from 'react';
import { Link, useSearchParams, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import { regionsApi, Region } from '../api/regions';
import Layout from '../components/Layout';

interface ValidationRequest {
    request_id: number;
    model_id: number;
    model_name: string;
    request_date: string;
    requestor_name: string;
    validation_type: string;
    priority: string;
    target_completion_date: string;
    current_status: string;
    days_in_status: number;
    primary_validator: string | null;
    region?: Region | null;
    created_at: string;
}

interface Model {
    model_id: number;
    model_name: string;
}

interface TaxonomyValue {
    value_id: number;
    code: string;
    label: string;
}

export default function ValidationWorkflowPage() {
    const { user } = useAuth();
    const [searchParams] = useSearchParams();
    const location = useLocation();
    const [requests, setRequests] = useState<ValidationRequest[]>([]);
    const [models, setModels] = useState<Model[]>([]);
    const [validationTypes, setValidationTypes] = useState<TaxonomyValue[]>([]);
    const [priorities, setPriorities] = useState<TaxonomyValue[]>([]);
    const [regions, setRegions] = useState<Region[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [formData, setFormData] = useState({
        model_id: 0,
        validation_type_id: 0,
        priority_id: 0,
        target_completion_date: '',
        trigger_reason: '',
        region_id: undefined as number | undefined
    });

    // Auto-open form and pre-populate model_id from query params
    useEffect(() => {
        if (location.pathname === '/validation-workflow/new') {
            setShowForm(true);
            const modelIdParam = searchParams.get('model_id');
            if (modelIdParam) {
                setFormData(prev => ({
                    ...prev,
                    model_id: parseInt(modelIdParam)
                }));
            }
        }
    }, [location.pathname, searchParams]);

    // Auto-select "Initial" validation type if model has no prior validations
    useEffect(() => {
        const checkAndSetInitialValidationType = async () => {
            if (formData.model_id && validationTypes.length > 0) {
                try {
                    // Check if model has any validation requests
                    const modelValidationsRes = await api.get('/validation-workflow/requests/');
                    const modelValidations = modelValidationsRes.data.filter(
                        (req: ValidationRequest) => req.model_id === formData.model_id
                    );

                    // If no prior validations, default to "Initial" validation type
                    if (modelValidations.length === 0) {
                        const initialType = validationTypes.find(
                            (type: TaxonomyValue) => type.code === 'INITIAL' || type.label.toLowerCase().includes('initial')
                        );
                        if (initialType && formData.validation_type_id === 0) {
                            setFormData(prev => ({
                                ...prev,
                                validation_type_id: initialType.value_id
                            }));
                        }
                    }
                } catch (err) {
                    console.error('Failed to check model validations:', err);
                }
            }
        };

        checkAndSetInitialValidationType();
    }, [formData.model_id, validationTypes]);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            setError(null);

            // Fetch validation requests
            const requestsRes = await api.get('/validation-workflow/requests/');
            setRequests(requestsRes.data);

            // Fetch models for form
            const modelsRes = await api.get('/models/');
            setModels(modelsRes.data);

            // Fetch taxonomies for form
            const taxonomiesRes = await api.get('/taxonomies/');
            const taxonomyList = taxonomiesRes.data;

            // Fetch taxonomy values
            const taxDetails = await Promise.all(
                taxonomyList.map((t: any) => api.get(`/taxonomies/${t.taxonomy_id}`))
            );
            const taxonomies = taxDetails.map((r: any) => r.data);

            const valType = taxonomies.find((t: any) => t.name === 'Validation Type');
            const priority = taxonomies.find((t: any) => t.name === 'Validation Priority');

            if (valType) {
                setValidationTypes(valType.values || []);
            }
            if (priority) {
                setPriorities(priority.values || []);
            }

            // Fetch regions
            const regionsData = await regionsApi.getRegions();
            setRegions(regionsData);
        } catch (err: any) {
            console.error('Failed to fetch data:', err);
            setError(err.response?.data?.detail || 'Failed to load validation requests');
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!formData.model_id || !formData.validation_type_id || !formData.priority_id) {
            setError('Please fill in all required fields');
            return;
        }

        try {
            // Only send region_id if it's set (not 0 or undefined)
            const payload = {
                ...formData,
                region_id: formData.region_id || undefined
            };
            await api.post('/validation-workflow/requests/', payload);
            setShowForm(false);
            setFormData({
                model_id: 0,
                validation_type_id: 0,
                priority_id: 0,
                target_completion_date: '',
                trigger_reason: '',
                region_id: undefined
            });
            fetchData();
        } catch (err: any) {
            console.error('Failed to create request:', err);
            setError(err.response?.data?.detail || 'Failed to create validation request');
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'Intake': return 'bg-gray-100 text-gray-800';
            case 'Planning': return 'bg-blue-100 text-blue-800';
            case 'In Progress': return 'bg-yellow-100 text-yellow-800';
            case 'Review': return 'bg-purple-100 text-purple-800';
            case 'Pending Approval': return 'bg-orange-100 text-orange-800';
            case 'Approved': return 'bg-green-100 text-green-800';
            case 'On Hold': return 'bg-red-100 text-red-800';
            case 'Cancelled': return 'bg-gray-400 text-white';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case 'Critical': return 'bg-red-100 text-red-800';
            case 'High': return 'bg-orange-100 text-orange-800';
            case 'Medium': return 'bg-yellow-100 text-yellow-800';
            case 'Low': return 'bg-green-100 text-green-800';
            default: return 'bg-gray-100 text-gray-800';
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
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-2xl font-bold">Validation Workflow</h2>
                    <p className="text-sm text-gray-600 mt-1">
                        Manage validation requests through their complete lifecycle
                    </p>
                </div>
                <button onClick={() => setShowForm(true)} className="btn-primary">
                    + New Validation Request
                </button>
            </div>

            {error && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                    {error}
                </div>
            )}

            {showForm && (
                <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                    <h3 className="text-lg font-bold mb-4">Create New Validation Request</h3>
                    <p className="text-sm text-gray-600 mb-4">
                        Submit a validation request. The outcome will be determined after the validation work is complete.
                    </p>
                    <form onSubmit={handleSubmit}>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="mb-4">
                                <label htmlFor="model_id" className="block text-sm font-medium mb-2">
                                    Model (Required)
                                </label>
                                <select
                                    id="model_id"
                                    className="input-field"
                                    value={formData.model_id || ''}
                                    onChange={(e) => setFormData({ ...formData, model_id: parseInt(e.target.value) || 0 })}
                                    required
                                >
                                    <option value="">Select Model</option>
                                    {models.map(m => (
                                        <option key={m.model_id} value={m.model_id}>{m.model_name}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="mb-4">
                                <label htmlFor="validation_type_id" className="block text-sm font-medium mb-2">
                                    Validation Type (Required)
                                </label>
                                <select
                                    id="validation_type_id"
                                    className="input-field"
                                    value={formData.validation_type_id || ''}
                                    onChange={(e) => setFormData({ ...formData, validation_type_id: parseInt(e.target.value) || 0 })}
                                    required
                                >
                                    <option value="">Select Type</option>
                                    {validationTypes.map(t => (
                                        <option key={t.value_id} value={t.value_id}>{t.label}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="mb-4">
                                <label htmlFor="priority_id" className="block text-sm font-medium mb-2">
                                    Priority (Required)
                                </label>
                                <select
                                    id="priority_id"
                                    className="input-field"
                                    value={formData.priority_id || ''}
                                    onChange={(e) => setFormData({ ...formData, priority_id: parseInt(e.target.value) || 0 })}
                                    required
                                >
                                    <option value="">Select Priority</option>
                                    {priorities.map(p => (
                                        <option key={p.value_id} value={p.value_id}>{p.label}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="mb-4">
                                <label htmlFor="target_completion_date" className="block text-sm font-medium mb-2">
                                    Target Completion Date (Required)
                                </label>
                                <input
                                    id="target_completion_date"
                                    type="date"
                                    className="input-field"
                                    value={formData.target_completion_date}
                                    onChange={(e) => setFormData({ ...formData, target_completion_date: e.target.value })}
                                    required
                                />
                            </div>

                            <div className="mb-4">
                                <label htmlFor="region_id" className="block text-sm font-medium mb-2">
                                    Region (Optional)
                                    <span className="text-xs text-gray-500 ml-2">Leave empty for global validation</span>
                                </label>
                                <select
                                    id="region_id"
                                    className="input-field"
                                    value={formData.region_id || ''}
                                    onChange={(e) => setFormData({ ...formData, region_id: e.target.value ? parseInt(e.target.value) : undefined })}
                                >
                                    <option value="">Global (No Region)</option>
                                    {regions.map(r => (
                                        <option key={r.region_id} value={r.region_id}>{r.name} ({r.code})</option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        <div className="mb-4">
                            <label htmlFor="trigger_reason" className="block text-sm font-medium mb-2">
                                Trigger Reason (Optional)
                            </label>
                            <input
                                id="trigger_reason"
                                type="text"
                                className="input-field"
                                value={formData.trigger_reason}
                                onChange={(e) => setFormData({ ...formData, trigger_reason: e.target.value })}
                                placeholder="What triggered this validation request?"
                            />
                        </div>

                        <div className="flex gap-2">
                            <button type="submit" className="btn-primary">Submit Request</button>
                            <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            )}

            <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Region</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Priority</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Days in Status</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Target Date</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Validator</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {requests.length === 0 ? (
                            <tr>
                                <td colSpan={10} className="px-6 py-4 text-center text-gray-500">
                                    No validation requests found. Click "New Validation Request" to create one.
                                </td>
                            </tr>
                        ) : (
                            requests.map((req) => (
                                <tr key={req.request_id} className="hover:bg-gray-50">
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono">
                                        #{req.request_id}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <Link
                                            to={`/models/${req.model_id}`}
                                            className="font-medium text-blue-600 hover:text-blue-800"
                                        >
                                            {req.model_name}
                                        </Link>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        {req.validation_type}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        {req.region ? (
                                            <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                                                {req.region.code}
                                            </span>
                                        ) : (
                                            <span className="text-gray-400 text-xs">Global</span>
                                        )}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`px-2 py-1 text-xs rounded ${getPriorityColor(req.priority)}`}>
                                            {req.priority}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`px-2 py-1 text-xs rounded ${getStatusColor(req.current_status)}`}>
                                            {req.current_status}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        <span className={req.days_in_status > 14 ? 'text-red-600 font-semibold' : ''}>
                                            {req.days_in_status} days
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        {req.target_completion_date}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        {req.primary_validator || <span className="text-gray-400">Unassigned</span>}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <Link
                                            to={`/validation-workflow/${req.request_id}`}
                                            className="text-blue-600 hover:text-blue-800 text-sm"
                                        >
                                            View Details
                                        </Link>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </Layout>
    );
}
