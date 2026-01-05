import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import client from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { canManageWorkflowConfig } from '../utils/roleUtils';

interface ComponentDefinition {
    component_id: number;
    section_number: string;
    section_title: string;
    component_code: string;
    component_title: string;
    is_test_or_analysis: boolean;
    expectation_high: string;
    expectation_medium: string;
    expectation_low: string;
    expectation_very_low: string;
    sort_order: number;
    is_active: boolean;
}

interface Configuration {
    config_id: number;
    config_name: string;
    description: string;
    effective_date: string;
    created_by_user_id: number;
    created_at: string;
    is_active: boolean;
}

const ComponentDefinitionsPage: React.FC = () => {
    const { user } = useAuth();
    const canManageWorkflowConfigFlag = canManageWorkflowConfig(user);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [components, setComponents] = useState<ComponentDefinition[]>([]);
    const [activeConfig, setActiveConfig] = useState<Configuration | null>(null);
    const [editingComponent, setEditingComponent] = useState<number | null>(null);
    const [editForm, setEditForm] = useState<Partial<ComponentDefinition>>({});
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);
    const [showPublishModal, setShowPublishModal] = useState(false);
    const [publishForm, setPublishForm] = useState({
        config_name: '',
        description: '',
        effective_date: new Date().toISOString().split('T')[0]
    });

    useEffect(() => {
        if (user && !canManageWorkflowConfigFlag) {
            setError('Only administrators can access this page');
            setLoading(false);
            return;
        }
        fetchData();
    }, [user, canManageWorkflowConfigFlag]);

    const fetchData = async () => {
        setLoading(true);
        setError(null);

        try {
            // Fetch component definitions
            const componentsRes = await client.get('/validation-workflow/component-definitions');
            setComponents(componentsRes.data);

            // Fetch configurations to get active one
            const configsRes = await client.get('/validation-workflow/configurations');
            const activeConf = configsRes.data.find((c: Configuration) => c.is_active);
            setActiveConfig(activeConf || null);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load component definitions');
            console.error('Error loading data:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleEditClick = (component: ComponentDefinition) => {
        setEditingComponent(component.component_id);
        setEditForm({
            expectation_high: component.expectation_high,
            expectation_medium: component.expectation_medium,
            expectation_low: component.expectation_low,
            expectation_very_low: component.expectation_very_low
        });
    };

    const handleCancelEdit = () => {
        setEditingComponent(null);
        setEditForm({});
    };

    const handleSaveEdit = async (componentId: number) => {
        setSaving(true);
        setError(null);
        setSuccessMessage(null);

        try {
            const response = await client.patch(
                `/validation-workflow/component-definitions/${componentId}`,
                editForm
            );

            // Update local state
            setComponents(components.map(c =>
                c.component_id === componentId ? response.data : c
            ));

            setEditingComponent(null);
            setEditForm({});
            setSuccessMessage('Component updated successfully. Changes will apply to new plans after publishing a new configuration.');
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to update component');
            console.error('Error updating component:', err);
        } finally {
            setSaving(false);
        }
    };

    const handlePublishConfiguration = async () => {
        setSaving(true);
        setError(null);
        setSuccessMessage(null);

        try {
            const response = await client.post('/validation-workflow/configurations/publish', publishForm);

            setActiveConfig(response.data);
            setShowPublishModal(false);
            setPublishForm({
                config_name: '',
                description: '',
                effective_date: new Date().toISOString().split('T')[0]
            });
            setSuccessMessage(`Configuration "${response.data.config_name}" published successfully. New validation plans will use this configuration.`);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to publish configuration');
            console.error('Error publishing configuration:', err);
        } finally {
            setSaving(false);
        }
    };

    const getExpectationBadge = (expectation: string) => {
        const colors: Record<string, string> = {
            'Required': 'bg-blue-100 text-blue-800',
            'IfApplicable': 'bg-gray-100 text-gray-800',
            'NotExpected': 'bg-red-100 text-red-800'
        };
        return colors[expectation] || 'bg-gray-100 text-gray-800';
    };

    // Group components by section
    const groupedComponents = components.reduce((acc, comp) => {
        const sectionKey = `${comp.section_number}|${comp.section_title}`;
        if (!acc[sectionKey]) {
            acc[sectionKey] = [];
        }
        acc[sectionKey].push(comp);
        return acc;
    }, {} as Record<string, ComponentDefinition[]>);

    const sections = Object.keys(groupedComponents).sort((a, b) => {
        const aNum = parseInt(a.split('|')[0]);
        const bNum = parseInt(b.split('|')[0]);
        return aNum - bNum;
    });

    if (loading) {
        return (
            <Layout>
                <div className="text-gray-600">Loading component definitions...</div>
            </Layout>
        );
    }

    if (user && !canManageWorkflowConfigFlag) {
        return (
            <Layout>
                <div className="bg-white rounded-lg shadow-md p-6">
                    <div className="text-red-600">
                        Only administrators can access this page.
                    </div>
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="space-y-6">
                {/* Header */}
                <div className="bg-white rounded-lg shadow-md p-6">
                    <div className="flex justify-between items-start mb-4">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">Component Definition Management</h1>
                            <p className="text-gray-600 mt-2">
                                Manage validation component expectations for different risk tiers. Changes require publishing a new component definition version.
                            </p>
                        </div>
                        <button
                            onClick={() => setShowPublishModal(true)}
                            className="btn-primary"
                        >
                            Publish New Version
                        </button>
                    </div>

                    {/* Active Configuration Info */}
                    {activeConfig && (
                        <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded">
                            <div className="flex items-start gap-2">
                                <span className="text-blue-600 text-lg">ℹ️</span>
                                <div className="text-sm text-blue-900">
                                    <div className="font-semibold">Active Configuration: {activeConfig.config_name}</div>
                                    <div className="mt-1">{activeConfig.description}</div>
                                    <div className="mt-1 text-xs">
                                        Effective Date: {activeConfig.effective_date} |
                                        Created: {new Date(activeConfig.created_at).toLocaleString()}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Messages */}
                {error && (
                    <div className="bg-red-50 border border-red-200 rounded p-4 text-red-800">
                        {error}
                    </div>
                )}

                {successMessage && (
                    <div className="bg-green-50 border border-green-200 rounded p-4 text-green-800">
                        {successMessage}
                    </div>
                )}

                {/* Component Definitions Table */}
                {sections.map(sectionKey => {
                    const [sectionNum, sectionTitle] = sectionKey.split('|');
                    const sectionComponents = groupedComponents[sectionKey];

                    return (
                        <div key={sectionKey} className="bg-white rounded-lg shadow-md overflow-hidden">
                            <div className="bg-gray-100 px-4 py-2 border-b">
                                <h2 className="font-semibold text-gray-800">
                                    Section {sectionNum} – {sectionTitle}
                                </h2>
                            </div>

                            <div className="overflow-x-auto">
                                <table className="min-w-full">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase w-1/4">
                                                Component
                                            </th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase w-1/6">
                                                Tier 1 (High)
                                            </th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase w-1/6">
                                                Tier 2 (Medium)
                                            </th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase w-1/6">
                                                Tier 3 (Low)
                                            </th>
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase w-1/6">
                                                Tier 4 (Very Low)
                                            </th>
                                            <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase w-24">
                                                Actions
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {sectionComponents.map(component => {
                                            const isEditing = editingComponent === component.component_id;

                                            return (
                                                <tr key={component.component_id}>
                                                    <td className="px-4 py-2">
                                                        <div className="text-sm font-medium text-gray-900">
                                                            {component.component_code}
                                                        </div>
                                                        <div className="text-sm text-gray-600">
                                                            {component.component_title}
                                                        </div>
                                                    </td>

                                                    {/* Expectation columns */}
                                                    {isEditing ? (
                                                        <>
                                                            <td className="px-4 py-2">
                                                                <select
                                                                    value={editForm.expectation_high}
                                                                    onChange={(e) => setEditForm({ ...editForm, expectation_high: e.target.value })}
                                                                    className="border border-gray-300 rounded px-2 py-1 text-sm w-full"
                                                                >
                                                                    <option value="Required">Required</option>
                                                                    <option value="IfApplicable">If Applicable</option>
                                                                    <option value="NotExpected">Not Expected</option>
                                                                </select>
                                                            </td>
                                                            <td className="px-4 py-2">
                                                                <select
                                                                    value={editForm.expectation_medium}
                                                                    onChange={(e) => setEditForm({ ...editForm, expectation_medium: e.target.value })}
                                                                    className="border border-gray-300 rounded px-2 py-1 text-sm w-full"
                                                                >
                                                                    <option value="Required">Required</option>
                                                                    <option value="IfApplicable">If Applicable</option>
                                                                    <option value="NotExpected">Not Expected</option>
                                                                </select>
                                                            </td>
                                                            <td className="px-4 py-2">
                                                                <select
                                                                    value={editForm.expectation_low}
                                                                    onChange={(e) => setEditForm({ ...editForm, expectation_low: e.target.value })}
                                                                    className="border border-gray-300 rounded px-2 py-1 text-sm w-full"
                                                                >
                                                                    <option value="Required">Required</option>
                                                                    <option value="IfApplicable">If Applicable</option>
                                                                    <option value="NotExpected">Not Expected</option>
                                                                </select>
                                                            </td>
                                                            <td className="px-4 py-2">
                                                                <select
                                                                    value={editForm.expectation_very_low}
                                                                    onChange={(e) => setEditForm({ ...editForm, expectation_very_low: e.target.value })}
                                                                    className="border border-gray-300 rounded px-2 py-1 text-sm w-full"
                                                                >
                                                                    <option value="Required">Required</option>
                                                                    <option value="IfApplicable">If Applicable</option>
                                                                    <option value="NotExpected">Not Expected</option>
                                                                </select>
                                                            </td>
                                                        </>
                                                    ) : (
                                                        <>
                                                            <td className="px-4 py-2">
                                                                <span className={`px-2 py-1 rounded text-xs font-medium ${getExpectationBadge(component.expectation_high)}`}>
                                                                    {component.expectation_high}
                                                                </span>
                                                            </td>
                                                            <td className="px-4 py-2">
                                                                <span className={`px-2 py-1 rounded text-xs font-medium ${getExpectationBadge(component.expectation_medium)}`}>
                                                                    {component.expectation_medium}
                                                                </span>
                                                            </td>
                                                            <td className="px-4 py-2">
                                                                <span className={`px-2 py-1 rounded text-xs font-medium ${getExpectationBadge(component.expectation_low)}`}>
                                                                    {component.expectation_low}
                                                                </span>
                                                            </td>
                                                            <td className="px-4 py-2">
                                                                <span className={`px-2 py-1 rounded text-xs font-medium ${getExpectationBadge(component.expectation_very_low)}`}>
                                                                    {component.expectation_very_low}
                                                                </span>
                                                            </td>
                                                        </>
                                                    )}

                                                    {/* Actions */}
                                                    <td className="px-4 py-2 text-right text-sm">
                                                        {isEditing ? (
                                                            <div className="flex gap-2 justify-end">
                                                                <button
                                                                    onClick={() => handleSaveEdit(component.component_id)}
                                                                    disabled={saving}
                                                                    className="text-blue-600 hover:text-blue-800"
                                                                >
                                                                    Save
                                                                </button>
                                                                <button
                                                                    onClick={handleCancelEdit}
                                                                    disabled={saving}
                                                                    className="text-gray-600 hover:text-gray-800"
                                                                >
                                                                    Cancel
                                                                </button>
                                                            </div>
                                                        ) : (
                                                            <button
                                                                onClick={() => handleEditClick(component)}
                                                                className="text-blue-600 hover:text-blue-800"
                                                            >
                                                                Edit
                                                            </button>
                                                        )}
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    );
                })}

                {/* Publish Configuration Modal */}
                {showPublishModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4">
                            <div className="p-6">
                                <h2 className="text-2xl font-bold mb-4">Publish New Component Definition Version</h2>
                                <p className="text-gray-600 mb-6">
                                    Publishing a new version will snapshot the current component definitions.
                                    New validation plans will use this version. Existing locked plans will remain linked to their original version.
                                </p>

                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Version Name <span className="text-red-500">*</span>
                                        </label>
                                        <input
                                            type="text"
                                            value={publishForm.config_name}
                                            onChange={(e) => setPublishForm({ ...publishForm, config_name: e.target.value })}
                                            placeholder="e.g., Q4 2025 Requirements Update"
                                            className="w-full border border-gray-300 rounded px-3 py-2"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Description
                                        </label>
                                        <textarea
                                            value={publishForm.description}
                                            onChange={(e) => setPublishForm({ ...publishForm, description: e.target.value })}
                                            placeholder="Describe what changed in this version..."
                                            rows={3}
                                            className="w-full border border-gray-300 rounded px-3 py-2"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Effective Date
                                        </label>
                                        <input
                                            type="date"
                                            value={publishForm.effective_date}
                                            onChange={(e) => setPublishForm({ ...publishForm, effective_date: e.target.value })}
                                            className="border border-gray-300 rounded px-3 py-2"
                                        />
                                    </div>
                                </div>

                                <div className="flex justify-end gap-3 mt-6">
                                    <button
                                        onClick={() => setShowPublishModal(false)}
                                        disabled={saving}
                                        className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handlePublishConfiguration}
                                        disabled={saving || !publishForm.config_name}
                                        className="btn-primary"
                                    >
                                        {saving ? 'Publishing...' : 'Publish Configuration'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </Layout>
    );
};

export default ComponentDefinitionsPage;
