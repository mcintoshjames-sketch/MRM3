import { useState, useEffect } from 'react';
import { Link, useSearchParams, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';

interface User {
    user_id: number;
    email: string;
    full_name: string;
    role: string;
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

interface Validation {
    validation_id: number;
    model_id: number;
    model_name: string;
    validation_date: string;
    validator_name: string;
    validation_type: string;
    outcome: string;
    scope: string;
    created_at: string;
}

export default function ValidationsPage() {
    const { user } = useAuth();
    const [searchParams] = useSearchParams();
    const location = useLocation();
    const [validations, setValidations] = useState<Validation[]>([]);
    const [models, setModels] = useState<Model[]>([]);
    const [users, setUsers] = useState<User[]>([]);
    const [validationTypes, setValidationTypes] = useState<TaxonomyValue[]>([]);
    const [outcomes, setOutcomes] = useState<TaxonomyValue[]>([]);
    const [scopes, setScopes] = useState<TaxonomyValue[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(location.pathname === '/validations/new');

    const preselectedModelId = searchParams.get('model_id');

    const [formData, setFormData] = useState({
        model_id: preselectedModelId ? parseInt(preselectedModelId) : 0,
        validation_date: new Date().toISOString().split('T')[0],
        validator_id: user?.user_id || 0,
        validation_type_id: 0,
        outcome_id: 0,
        scope_id: 0,
        findings_summary: '',
        report_reference: ''
    });

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [validationsRes, modelsRes, usersRes, taxonomiesRes] = await Promise.all([
                api.get('/validations/'),
                api.get('/models/'),
                api.get('/auth/users'),
                api.get('/taxonomies/')
            ]);

            console.log('Models fetched:', modelsRes.data);
            console.log('Users fetched:', usersRes.data);
            console.log('Taxonomies fetched:', taxonomiesRes.data);

            setValidations(validationsRes.data);
            setModels(modelsRes.data);
            setUsers(usersRes.data);

            // Fetch full taxonomy details to get values - this is separate so it doesn't break models/users
            try {
                const taxonomyList = taxonomiesRes.data;
                const taxDetails = await Promise.all(
                    taxonomyList.map((t: any) => api.get(`/taxonomies/${t.taxonomy_id}`))
                );
                const taxonomies = taxDetails.map((r: any) => r.data);

                // Extract taxonomy values
                const validationType = taxonomies.find((t: any) => t.name === 'Validation Type');
                const outcome = taxonomies.find((t: any) => t.name === 'Validation Outcome');
                const scope = taxonomies.find((t: any) => t.name === 'Targeted Scope');

                if (validationType) {
                    console.log('Validation Type values:', validationType.values);
                    setValidationTypes(validationType.values || []);
                }
                if (outcome) {
                    console.log('Outcome values:', outcome.values);
                    setOutcomes(outcome.values || []);
                }
                if (scope) {
                    console.log('Scope values:', scope.values);
                    setScopes(scope.values || []);
                }

                // Set defaults if available
                if (validationType?.values?.length > 0) {
                    setFormData(prev => ({ ...prev, validation_type_id: 0 }));
                }
                if (outcome?.values?.length > 0) {
                    setFormData(prev => ({ ...prev, outcome_id: 0 }));
                }
                if (scope?.values?.length > 0) {
                    setFormData(prev => ({ ...prev, scope_id: 0 }));
                }
            } catch (taxonomyError) {
                console.error('Failed to fetch taxonomy values:', taxonomyError);
                // Continue without taxonomy values - models and users are still available
            }
        } catch (error) {
            console.error('Failed to fetch data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            // Only include scope_id if validation type is TARGETED
            const selectedValidationType = validationTypes.find(t => t.value_id === formData.validation_type_id);
            const isTargeted = selectedValidationType?.code === 'TARGETED';

            const submissionData = {
                ...formData,
                scope_id: isTargeted ? formData.scope_id : null
            };

            await api.post('/validations/', submissionData);
            setShowForm(false);
            setFormData({
                model_id: 0,
                validation_date: new Date().toISOString().split('T')[0],
                validator_id: user?.user_id || 0,
                validation_type_id: validationTypes[0]?.value_id || 0,
                outcome_id: outcomes[0]?.value_id || 0,
                scope_id: scopes[0]?.value_id || 0,
                findings_summary: '',
                report_reference: ''
            });
            fetchData();
        } catch (error: any) {
            console.error('Failed to create validation:', error);
            alert(error.response?.data?.detail || 'Failed to create validation');
        }
    };

    const canCreateValidation = user?.role === 'Admin' || user?.role === 'Validator';

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
                <h2 className="text-2xl font-bold">Validations</h2>
                {canCreateValidation && (
                    <button onClick={() => setShowForm(true)} className="btn-primary">
                        + New Validation
                    </button>
                )}
            </div>

            {showForm && (
                <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                    <h3 className="text-lg font-bold mb-4">Create New Validation</h3>
                    <form onSubmit={handleSubmit}>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="mb-4">
                                <label htmlFor="model_id" className="block text-sm font-medium mb-2">
                                    Model (Required)
                                </label>
                                <select
                                    id="model_id"
                                    className="input-field"
                                    value={formData.model_id ? String(formData.model_id) : ''}
                                    onChange={(e) => setFormData({ ...formData, model_id: e.target.value ? parseInt(e.target.value) : 0 })}
                                    required
                                >
                                    <option value="">Select Model</option>
                                    {models.map(m => (
                                        <option key={m.model_id} value={String(m.model_id)}>{m.model_name}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="mb-4">
                                <label htmlFor="validation_date" className="block text-sm font-medium mb-2">
                                    Validation Date
                                </label>
                                <input
                                    id="validation_date"
                                    type="date"
                                    className="input-field"
                                    value={formData.validation_date}
                                    onChange={(e) => setFormData({ ...formData, validation_date: e.target.value })}
                                    required
                                />
                            </div>

                            <div className="mb-4">
                                <label htmlFor="validator_id" className="block text-sm font-medium mb-2">
                                    Validator
                                </label>
                                <select
                                    id="validator_id"
                                    className="input-field"
                                    value={formData.validator_id}
                                    onChange={(e) => setFormData({ ...formData, validator_id: parseInt(e.target.value) })}
                                    required
                                >
                                    <option value="">Select Validator</option>
                                    {users.filter(u => u.role === 'Validator' || u.role === 'Admin').map(u => (
                                        <option key={u.user_id} value={u.user_id}>{u.full_name} ({u.role})</option>
                                    ))}
                                </select>
                            </div>

                            <div className="mb-4">
                                <label htmlFor="validation_type_id" className="block text-sm font-medium mb-2">
                                    Validation Type
                                </label>
                                <select
                                    id="validation_type_id"
                                    className="input-field"
                                    value={formData.validation_type_id}
                                    onChange={(e) => setFormData({ ...formData, validation_type_id: parseInt(e.target.value) })}
                                    required
                                >
                                    <option value="0">Select Type</option>
                                    {validationTypes.map(t => (
                                        <option key={t.value_id} value={t.value_id}>{t.label}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="mb-4">
                                <label htmlFor="outcome_id" className="block text-sm font-medium mb-2">
                                    Outcome
                                </label>
                                <select
                                    id="outcome_id"
                                    className="input-field"
                                    value={formData.outcome_id}
                                    onChange={(e) => setFormData({ ...formData, outcome_id: parseInt(e.target.value) })}
                                    required
                                >
                                    <option value="0">Select Outcome</option>
                                    {outcomes.map(o => (
                                        <option key={o.value_id} value={o.value_id}>{o.label}</option>
                                    ))}
                                </select>
                            </div>

                            {/* Only show Targeted Scope when Targeted Review is selected */}
                            {validationTypes.find(t => t.value_id === formData.validation_type_id)?.code === 'TARGETED' && (
                                <div className="mb-4">
                                    <label htmlFor="scope_id" className="block text-sm font-medium mb-2">
                                        Targeted Scope
                                    </label>
                                    <select
                                        id="scope_id"
                                        className="input-field"
                                        value={formData.scope_id}
                                        onChange={(e) => setFormData({ ...formData, scope_id: parseInt(e.target.value) })}
                                        required
                                    >
                                        <option value="0">Select Scope</option>
                                        {scopes.map(s => (
                                            <option key={s.value_id} value={s.value_id}>{s.label}</option>
                                        ))}
                                    </select>
                                </div>
                            )}
                        </div>

                        <div className="mb-4">
                            <label htmlFor="findings_summary" className="block text-sm font-medium mb-2">
                                Findings Summary
                            </label>
                            <textarea
                                id="findings_summary"
                                className="input-field"
                                rows={4}
                                value={formData.findings_summary}
                                onChange={(e) => setFormData({ ...formData, findings_summary: e.target.value })}
                                placeholder="Summarize key findings from the validation..."
                            />
                        </div>

                        <div className="mb-4">
                            <label htmlFor="report_reference" className="block text-sm font-medium mb-2">
                                Report Reference
                            </label>
                            <input
                                id="report_reference"
                                type="text"
                                className="input-field"
                                value={formData.report_reference}
                                onChange={(e) => setFormData({ ...formData, report_reference: e.target.value })}
                                placeholder="Link to full validation report document..."
                            />
                        </div>

                        <div className="flex gap-2">
                            <button type="submit" className="btn-primary">Create</button>
                            <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">
                                Cancel
                            </button>
                        </div>
                    </form>
                </div >
            )
            }

            <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Validator</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Outcome</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Scope</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {validations.length === 0 ? (
                            <tr>
                                <td colSpan={7} className="px-6 py-4 text-center text-gray-500">
                                    No validations recorded yet.
                                </td>
                            </tr>
                        ) : (
                            validations.map((validation) => (
                                <tr key={validation.validation_id} className="hover:bg-gray-50">
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <Link
                                            to={`/models/${validation.model_id}`}
                                            className="font-medium text-blue-600 hover:text-blue-800"
                                        >
                                            {validation.model_name}
                                        </Link>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        {validation.validation_date}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        {validation.validator_name}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">
                                            {validation.validation_type}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`px-2 py-1 text-xs rounded ${validation.outcome === 'Pass'
                                            ? 'bg-green-100 text-green-800'
                                            : validation.outcome === 'Pass with Findings'
                                                ? 'bg-orange-100 text-orange-800'
                                                : 'bg-red-100 text-red-800'
                                            }`}>
                                            {validation.outcome}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className="px-2 py-1 text-xs rounded bg-purple-100 text-purple-800">
                                            {validation.scope}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <Link
                                            to={`/validations/${validation.validation_id}`}
                                            className="text-blue-600 hover:text-blue-800 text-sm"
                                        >
                                            View
                                        </Link>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </Layout >
    );
}
