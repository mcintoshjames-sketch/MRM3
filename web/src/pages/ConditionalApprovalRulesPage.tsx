import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import Layout from '../components/Layout';

interface ApproverRole {
    role_id: number;
    role_name: string;
    description: string | null;
    is_active: boolean;
}

interface TaxonomyValue {
    value_id: number;
    label: string;
    code: string;
}

interface Region {
    region_id: number;
    name: string;
    code: string;
}

interface ConditionalApprovalRule {
    rule_id: number;
    rule_name: string;
    description: string | null;
    is_active: boolean;
    conditions_summary: string;
    required_approver_names: string;
    created_at: string;
}

interface ConditionalApprovalRuleDetail {
    rule_id: number;
    rule_name: string;
    description: string | null;
    is_active: boolean;
    validation_type_ids: number[];
    risk_tier_ids: number[];
    governance_region_ids: number[];
    deployed_region_ids: number[];
    required_approver_roles: ApproverRole[];
    created_at: string;
    updated_at: string;
    rule_translation: string;
}

export default function ConditionalApprovalRulesPage() {
    const { user } = useAuth();
    const [rules, setRules] = useState<ConditionalApprovalRule[]>([]);
    const [approverRoles, setApproverRoles] = useState<ApproverRole[]>([]);
    const [validationTypes, setValidationTypes] = useState<TaxonomyValue[]>([]);
    const [riskTiers, setRiskTiers] = useState<TaxonomyValue[]>([]);
    const [regions, setRegions] = useState<Region[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [editingRule, setEditingRule] = useState<ConditionalApprovalRuleDetail | null>(null);
    const [showActiveOnly, setShowActiveOnly] = useState(true);
    const [formData, setFormData] = useState({
        rule_name: '',
        description: '',
        is_active: true,
        validation_type_ids: [] as number[],
        risk_tier_ids: [] as number[],
        governance_region_ids: [] as number[],
        deployed_region_ids: [] as number[],
        required_approver_role_ids: [] as number[]
    });
    const [previewTranslation, setPreviewTranslation] = useState<string>('');
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchData();
    }, [showActiveOnly]);

    useEffect(() => {
        // Update preview whenever form data changes
        if (showForm && formData.required_approver_role_ids.length > 0) {
            fetchPreview();
        } else {
            setPreviewTranslation('');
        }
    }, [formData, showForm]);

    const fetchData = async () => {
        try {
            const rulesUrl = showActiveOnly
                ? '/additional-approval-rules/?is_active=true'
                : '/additional-approval-rules/';
            const [rulesRes, rolesRes, regionsRes] = await Promise.all([
                api.get(rulesUrl),
                api.get('/approver-roles/?is_active=true'),
                api.get('/regions/')
            ]);

            setRules(rulesRes.data);
            setApproverRoles(rolesRes.data);
            setRegions(regionsRes.data);

            // Fetch taxonomies
            const taxonomiesRes = await api.get('/taxonomies/');
            const validationTypeTaxonomy = taxonomiesRes.data.find(
                (t: any) => t.name === 'Validation Type'
            );
            const riskTierTaxonomy = taxonomiesRes.data.find(
                (t: any) => t.name === 'Model Risk Tier'
            );

            if (validationTypeTaxonomy) {
                const taxRes = await api.get(`/taxonomies/${validationTypeTaxonomy.taxonomy_id}`);
                setValidationTypes(taxRes.data.values.filter((v: TaxonomyValue) => v.code !== null));
            }

            if (riskTierTaxonomy) {
                const taxRes = await api.get(`/taxonomies/${riskTierTaxonomy.taxonomy_id}`);
                setRiskTiers(taxRes.data.values.filter((v: TaxonomyValue) => v.code !== null));
            }
        } catch (error) {
            console.error('Failed to fetch data:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchRules = async () => {
        try {
            const url = showActiveOnly
                ? '/additional-approval-rules/?is_active=true'
                : '/additional-approval-rules/';
            const response = await api.get(url);
            setRules(response.data);
        } catch (error) {
            console.error('Failed to fetch rules:', error);
        }
    };

    const fetchPreview = async () => {
        try {
            const response = await api.post('/additional-approval-rules/preview', {
                validation_type_ids: formData.validation_type_ids.length > 0 ? formData.validation_type_ids : null,
                risk_tier_ids: formData.risk_tier_ids.length > 0 ? formData.risk_tier_ids : null,
                governance_region_ids: formData.governance_region_ids.length > 0 ? formData.governance_region_ids : null,
                deployed_region_ids: formData.deployed_region_ids.length > 0 ? formData.deployed_region_ids : null,
                required_approver_role_ids: formData.required_approver_role_ids
            });
            setPreviewTranslation(response.data.translation);
        } catch (error) {
            console.error('Failed to fetch preview:', error);
            setPreviewTranslation('');
        }
    };

    const resetForm = () => {
        setFormData({
            rule_name: '',
            description: '',
            is_active: true,
            validation_type_ids: [],
            risk_tier_ids: [],
            governance_region_ids: [],
            deployed_region_ids: [],
            required_approver_role_ids: []
        });
        setEditingRule(null);
        setShowForm(false);
        setError(null);
        setPreviewTranslation('');
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        // Validate at least one approver role selected
        if (formData.required_approver_role_ids.length === 0) {
            setError('At least one approver role must be selected');
            return;
        }

        try {
            if (editingRule) {
                await api.patch(`/additional-approval-rules/${editingRule.rule_id}`, formData);
            } else {
                await api.post('/additional-approval-rules/', formData);
            }
            resetForm();
            fetchRules();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save additional approval rule');
        }
    };

    const handleEdit = async (rule: ConditionalApprovalRule) => {
        try {
            // Fetch full rule details
            const response = await api.get(`/additional-approval-rules/${rule.rule_id}`);
            const ruleDetail: ConditionalApprovalRuleDetail = response.data;

            setEditingRule(ruleDetail);
            setFormData({
                rule_name: ruleDetail.rule_name,
                description: ruleDetail.description || '',
                is_active: ruleDetail.is_active,
                validation_type_ids: ruleDetail.validation_type_ids,
                risk_tier_ids: ruleDetail.risk_tier_ids,
                governance_region_ids: ruleDetail.governance_region_ids,
                deployed_region_ids: ruleDetail.deployed_region_ids,
                required_approver_role_ids: ruleDetail.required_approver_roles.map(r => r.role_id)
            });
            setShowForm(true);
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to load rule details');
        }
    };

    const handleDeactivate = async (ruleId: number) => {
        if (!confirm('Are you sure you want to deactivate this rule? It will no longer be evaluated for new validations.')) return;

        try {
            await api.delete(`/additional-approval-rules/${ruleId}`);
            fetchRules();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to deactivate rule');
        }
    };

    const handleReactivate = async (ruleId: number) => {
        if (!confirm('Are you sure you want to reactivate this rule? It will be evaluated for new validations.')) return;

        try {
            await api.patch(`/additional-approval-rules/${ruleId}`, { is_active: true });
            fetchRules();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to reactivate rule');
        }
    };

    const handleMultiSelectChange = (field: string, value: string) => {
        const numValue = parseInt(value);
        const currentValues = (formData as any)[field] as number[];

        if (currentValues.includes(numValue)) {
            // Remove
            setFormData({
                ...formData,
                [field]: currentValues.filter(v => v !== numValue)
            });
        } else {
            // Add
            setFormData({
                ...formData,
                [field]: [...currentValues, numValue]
            });
        }
    };

    // Only admins can access this page
    if (user?.role !== 'Admin') {
        return (
            <Layout>
                <div className="text-center py-12">
                    <h2 className="text-2xl font-bold text-gray-800">Access Denied</h2>
                    <p className="text-gray-600 mt-2">Only administrators can manage additional approval rules.</p>
                </div>
            </Layout>
        );
    }

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
                    <h2 className="text-2xl font-bold">Additional Approval Rules</h2>
                    <p className="text-gray-600 text-sm mt-1">
                        Define rules that determine when additional approvals are required for model use
                    </p>
                </div>
                <div className="flex items-center gap-4">
                    <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={showActiveOnly}
                            onChange={(e) => setShowActiveOnly(e.target.checked)}
                            className="rounded border-gray-300"
                        />
                        Show Active Only
                    </label>
                    <button onClick={() => setShowForm(true)} className="btn-primary">
                        + Add Rule
                    </button>
                </div>
            </div>

            {showForm && (
                <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                    <h3 className="text-lg font-bold mb-4">
                        {editingRule ? 'Edit Additional Approval Rule' : 'Create New Additional Approval Rule'}
                    </h3>

                    {error && (
                        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit}>
                        <div className="grid grid-cols-1 gap-6">
                            {/* Basic Info */}
                            <div>
                                <label htmlFor="rule_name" className="block text-sm font-medium mb-2">
                                    Rule Name *
                                </label>
                                <input
                                    id="rule_name"
                                    type="text"
                                    className="input-field"
                                    value={formData.rule_name}
                                    onChange={(e) => setFormData({ ...formData, rule_name: e.target.value })}
                                    placeholder="e.g., US High Risk Initial Validation Approval"
                                    maxLength={200}
                                    required
                                />
                            </div>

                            <div>
                                <label htmlFor="description" className="block text-sm font-medium mb-2">
                                    Description
                                </label>
                                <textarea
                                    id="description"
                                    className="input-field"
                                    rows={2}
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    placeholder="Optional description"
                                />
                            </div>

                            {/* Conditions */}
                            <div className="border-t pt-4">
                                <h4 className="font-semibold mb-3 text-gray-700">
                                    Conditions (Leave empty for ANY)
                                </h4>
                                <p className="text-sm text-gray-600 mb-4">
                                    The rule applies when ALL non-empty conditions match. Within each condition, ANY selected value will satisfy.
                                </p>

                                <div className="grid grid-cols-2 gap-4">
                                    {/* Validation Type */}
                                    <div>
                                        <label className="block text-sm font-medium mb-2">
                                            Validation Type(s)
                                        </label>
                                        <div className="border rounded p-2 bg-gray-50 max-h-40 overflow-y-auto">
                                            {validationTypes.map((vt) => (
                                                <label key={vt.value_id} className="flex items-center py-1">
                                                    <input
                                                        type="checkbox"
                                                        checked={formData.validation_type_ids.includes(vt.value_id)}
                                                        onChange={() => handleMultiSelectChange('validation_type_ids', vt.value_id.toString())}
                                                        className="mr-2"
                                                    />
                                                    <span className="text-sm">{vt.label}</span>
                                                </label>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Risk Tier */}
                                    <div>
                                        <label className="block text-sm font-medium mb-2">
                                            Model Risk Tier(s)
                                        </label>
                                        <div className="border rounded p-2 bg-gray-50 max-h-40 overflow-y-auto">
                                            {riskTiers.map((rt) => (
                                                <label key={rt.value_id} className="flex items-center py-1">
                                                    <input
                                                        type="checkbox"
                                                        checked={formData.risk_tier_ids.includes(rt.value_id)}
                                                        onChange={() => handleMultiSelectChange('risk_tier_ids', rt.value_id.toString())}
                                                        className="mr-2"
                                                    />
                                                    <span className="text-sm">{rt.label}</span>
                                                </label>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Governance Region */}
                                    <div>
                                        <label className="block text-sm font-medium mb-2">
                                            Governance Region(s)
                                        </label>
                                        <div className="border rounded p-2 bg-gray-50 max-h-40 overflow-y-auto">
                                            {regions.map((r) => (
                                                <label key={r.region_id} className="flex items-center py-1">
                                                    <input
                                                        type="checkbox"
                                                        checked={formData.governance_region_ids.includes(r.region_id)}
                                                        onChange={() => handleMultiSelectChange('governance_region_ids', r.region_id.toString())}
                                                        className="mr-2"
                                                    />
                                                    <span className="text-sm">{r.name}</span>
                                                </label>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Deployed Region */}
                                    <div>
                                        <label className="block text-sm font-medium mb-2">
                                            Deployed Region(s)
                                        </label>
                                        <div className="border rounded p-2 bg-gray-50 max-h-40 overflow-y-auto">
                                            {regions.map((r) => (
                                                <label key={r.region_id} className="flex items-center py-1">
                                                    <input
                                                        type="checkbox"
                                                        checked={formData.deployed_region_ids.includes(r.region_id)}
                                                        onChange={() => handleMultiSelectChange('deployed_region_ids', r.region_id.toString())}
                                                        className="mr-2"
                                                    />
                                                    <span className="text-sm">{r.name}</span>
                                                </label>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Required Approvers */}
                            <div className="border-t pt-4">
                                <label className="block text-sm font-medium mb-2">
                                    Required Approver Role(s) *
                                </label>
                                <div className="border rounded p-2 bg-gray-50 max-h-40 overflow-y-auto">
                                    {approverRoles.length === 0 ? (
                                        <p className="text-sm text-gray-500 p-2">
                                            No active approver roles available. Create approver roles first.
                                        </p>
                                    ) : (
                                        approverRoles.map((role) => (
                                            <label key={role.role_id} className="flex items-center py-1">
                                                <input
                                                    type="checkbox"
                                                    checked={formData.required_approver_role_ids.includes(role.role_id)}
                                                    onChange={() => handleMultiSelectChange('required_approver_role_ids', role.role_id.toString())}
                                                    className="mr-2"
                                                />
                                                <span className="text-sm">{role.role_name}</span>
                                            </label>
                                        ))
                                    )}
                                </div>
                            </div>

                            {/* Active Status */}
                            <div>
                                <label className="flex items-center">
                                    <input
                                        type="checkbox"
                                        checked={formData.is_active}
                                        onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                                        className="mr-2"
                                    />
                                    <span className="text-sm font-medium">Active</span>
                                </label>
                                <p className="text-xs text-gray-500 mt-1">
                                    Inactive rules are not evaluated for new validations
                                </p>
                            </div>

                            {/* Rule Translation Preview */}
                            {previewTranslation && (
                                <div className="border-t pt-4">
                                    <h4 className="font-semibold mb-2 text-gray-700">Rule Translation Preview</h4>
                                    <div className="bg-blue-50 border border-blue-200 rounded p-4">
                                        <pre className="text-sm text-gray-800 whitespace-pre-wrap font-sans">
                                            {previewTranslation}
                                        </pre>
                                    </div>
                                </div>
                            )}
                        </div>

                        <div className="flex gap-2 mt-6">
                            <button type="submit" className="btn-primary">
                                {editingRule ? 'Update Rule' : 'Create Rule'}
                            </button>
                            <button type="button" onClick={resetForm} className="btn-secondary">
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* Rules List */}
            <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Rule Name
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Conditions
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Required Approvers
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Status
                            </th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                                Actions
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {rules.length === 0 ? (
                            <tr>
                                <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                                    No additional approval rules defined. Click "Add Rule" to create one.
                                </td>
                            </tr>
                        ) : (
                            rules.map((rule) => (
                                <tr key={rule.rule_id} className="hover:bg-gray-50">
                                    <td className="px-6 py-4">
                                        <div className="text-sm font-medium text-gray-900">
                                            {rule.rule_name}
                                        </div>
                                        {rule.description && (
                                            <div className="text-xs text-gray-500 mt-1">
                                                {rule.description}
                                            </div>
                                        )}
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="text-sm text-gray-600">
                                            {rule.conditions_summary}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="text-sm text-gray-900">
                                            {rule.required_approver_names}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span
                                            className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                                rule.is_active
                                                    ? 'bg-green-100 text-green-800'
                                                    : 'bg-gray-100 text-gray-800'
                                            }`}
                                        >
                                            {rule.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-right text-sm font-medium">
                                        <button
                                            onClick={() => handleEdit(rule)}
                                            className="text-blue-600 hover:text-blue-800 mr-3"
                                        >
                                            Edit
                                        </button>
                                        {rule.is_active ? (
                                            <button
                                                onClick={() => handleDeactivate(rule.rule_id)}
                                                className="text-red-600 hover:text-red-800"
                                            >
                                                Deactivate
                                            </button>
                                        ) : (
                                            <button
                                                onClick={() => handleReactivate(rule.rule_id)}
                                                className="text-green-600 hover:text-green-800"
                                            >
                                                Reactivate
                                            </button>
                                        )}
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
