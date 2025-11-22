import React, { useState, useEffect, useImperativeHandle, forwardRef } from 'react';
import api from '../api/client';

interface ValidationComponentDefinition {
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

interface ValidationPlanComponent {
    plan_component_id?: number;
    component_id: number;
    default_expectation: string;
    planned_treatment: string;
    is_deviation: boolean;
    rationale?: string;
    additional_notes?: string;
    component_definition: ValidationComponentDefinition;
}

interface ValidationPlan {
    plan_id?: number;
    request_id: number;
    overall_scope_summary?: string;
    material_deviation_from_standard: boolean;
    overall_deviation_rationale?: string;
    components: ValidationPlanComponent[];
    model_id?: number;
    model_name?: string;
    risk_tier?: string;
    validation_approach?: string;
    locked_at?: string | null;
}

interface TemplateSuggestion {
    source_request_id: number;
    source_plan_id: number;
    validation_type: string;
    model_names: string[];
    completion_date: string | null;
    validator_name: string | null;
    component_count: number;
    deviations_count: number;
    config_id: number | null;
    config_name: string | null;
    is_different_config: boolean;
}

export interface ValidationPlanFormHandle {
    saveForm: () => Promise<boolean>;
    hasUnsavedChanges: () => boolean;
}

interface Props {
    requestId: number;
    modelName?: string;
    riskTier?: string;
    onSave?: () => void;
}

const ValidationPlanForm = forwardRef<ValidationPlanFormHandle, Props>(({ requestId, modelName, riskTier, onSave }, ref) => {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [plan, setPlan] = useState<ValidationPlan | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
    const [saveSuccess, setSaveSuccess] = useState(false);

    // Template suggestion state
    const [templateSuggestions, setTemplateSuggestions] = useState<TemplateSuggestion[]>([]);
    const [showTemplateModal, setShowTemplateModal] = useState(false);
    const [selectedTemplate, setSelectedTemplate] = useState<number | null>(null);

    const [formData, setFormData] = useState<ValidationPlan>({
        request_id: requestId,
        overall_scope_summary: '',
        material_deviation_from_standard: false,
        overall_deviation_rationale: '',
        components: [],
        model_name: modelName,
        risk_tier: riskTier
    });

    useEffect(() => {
        fetchValidationPlan();
    }, [requestId]);

    // Expose methods to parent via ref
    useImperativeHandle(ref, () => ({
        saveForm: async () => {
            return await handleSaveInternal();
        },
        hasUnsavedChanges: () => hasUnsavedChanges
    }));

    // Block navigation when there are unsaved changes
    useEffect(() => {
        const handleBeforeUnload = (e: BeforeUnloadEvent) => {
            if (hasUnsavedChanges) {
                e.preventDefault();
                e.returnValue = ''; // Chrome requires returnValue to be set
            }
        };

        window.addEventListener('beforeunload', handleBeforeUnload);
        return () => window.removeEventListener('beforeunload', handleBeforeUnload);
    }, [hasUnsavedChanges]);

    const fetchValidationPlan = async () => {
        setLoading(true);
        setError(null);

        try {
            // Try to fetch existing plan
            const response = await api.get(`/validation-workflow/requests/${requestId}/plan`);
            setPlan(response.data);
            setFormData(response.data);
            setHasUnsavedChanges(false); // Reset dirty flag on load
        } catch (err: any) {
            if (err.response?.status === 404) {
                // Plan doesn't exist yet - that's okay, we'll create one
                setPlan(null);
                // Fetch template suggestions if no plan exists
                fetchTemplateSuggestions();
            } else {
                setError('Failed to load validation plan');
                console.error('Error loading validation plan:', err);
            }
        } finally {
            setLoading(false);
        }
    };

    const fetchTemplateSuggestions = async () => {
        try {
            const response = await api.get(`/validation-workflow/requests/${requestId}/plan/template-suggestions`);
            if (response.data.has_suggestions && response.data.suggestions.length > 0) {
                setTemplateSuggestions(response.data.suggestions);
                setShowTemplateModal(true);
            }
        } catch (err: any) {
            console.error('Error fetching template suggestions:', err);
            // Don't show error to user - templating is optional
        }
    };

    const handleCreatePlan = async (templatePlanId?: number) => {
        setSaving(true);
        setError(null);

        try {
            const payload: any = {
                overall_scope_summary: formData.overall_scope_summary || '',
                material_deviation_from_standard: false,
                overall_deviation_rationale: '',
                components: []
            };

            // If template was selected, include it
            if (templatePlanId) {
                payload.template_plan_id = templatePlanId;
            }

            const response = await api.post(`/validation-workflow/requests/${requestId}/plan`, payload);

            setPlan(response.data);
            setFormData(response.data);

            if (onSave) onSave();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to create validation plan');
            console.error('Error creating validation plan:', err);
        } finally {
            setSaving(false);
        }
    };

    const handleUseTemplate = (templatePlanId: number) => {
        setShowTemplateModal(false);
        handleCreatePlan(templatePlanId);
    };

    const handleCreateFromScratch = () => {
        setShowTemplateModal(false);
        handleCreatePlan();
    };

    const handleExportPDF = async () => {
        try {
            // Call backend PDF export endpoint
            const response = await api.get(`/validation-workflow/requests/${requestId}/plan/pdf`, {
                responseType: 'blob'
            });

            // Create download link
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;

            // Extract filename from Content-Disposition header or use default
            const contentDisposition = response.headers['content-disposition'];
            let filename = `validation_plan_request_${requestId}.pdf`;
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
                if (filenameMatch && filenameMatch[1]) {
                    filename = filenameMatch[1];
                }
            }

            link.setAttribute('download', filename);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (err: any) {
            console.error('Error exporting PDF:', err);
            setError('Failed to export PDF');
        }
    };

    const handleDeletePlan = async () => {
        if (!window.confirm('Are you sure you want to delete this validation plan? This action cannot be undone.')) {
            return;
        }

        setSaving(true);
        setError(null);

        try {
            await api.delete(`/validation-workflow/requests/${requestId}/plan`);

            // Reset to no plan state
            setPlan(null);
            setFormData({
                request_id: requestId,
                overall_scope_summary: '',
                material_deviation_from_standard: false,
                overall_deviation_rationale: '',
                components: [],
                model_name: modelName,
                risk_tier: riskTier
            });

            if (onSave) onSave();
        } catch (err: any) {
            const errorMessage = err.response?.data?.detail || 'Failed to delete validation plan';
            setError(errorMessage);
            console.error('Error deleting validation plan:', err);
        } finally {
            setSaving(false);
        }
    };

    // Internal save function that returns success boolean
    const handleSaveInternal = async (): Promise<boolean> => {
        setSaving(true);
        setError(null);
        setSaveSuccess(false);

        try {
            // Validate deviations have rationale
            for (const comp of formData.components) {
                if (comp.is_deviation && !comp.rationale?.trim()) {
                    const compDef = comp.component_definition;
                    throw new Error(`Rationale required for ${compDef.component_code} (${compDef.component_title}) because it deviates from the bank standard`);
                }
            }

            // Validate material deviation rationale
            if (formData.material_deviation_from_standard && !formData.overall_deviation_rationale?.trim()) {
                throw new Error('Overall deviation rationale is required when there is a material deviation from standard');
            }

            const updatePayload = {
                overall_scope_summary: formData.overall_scope_summary,
                material_deviation_from_standard: formData.material_deviation_from_standard,
                overall_deviation_rationale: formData.overall_deviation_rationale,
                components: formData.components.map(comp => ({
                    component_id: comp.component_id,
                    planned_treatment: comp.planned_treatment,
                    rationale: comp.rationale,
                    additional_notes: comp.additional_notes
                }))
            };

            const response = await api.patch(`/validation-workflow/requests/${requestId}/plan`, updatePayload);
            setPlan(response.data);
            setFormData(response.data);
            setHasUnsavedChanges(false); // Clear dirty flag on successful save
            setSaveSuccess(true);

            // Clear success message after 3 seconds
            setTimeout(() => setSaveSuccess(false), 3000);

            if (onSave) onSave();
            return true; // Success
        } catch (err: any) {
            if (err.message) {
                setError(err.message);
            } else {
                setError(err.response?.data?.detail || 'Failed to save validation plan');
            }
            console.error('Error saving validation plan:', err);
            return false; // Failure
        } finally {
            setSaving(false);
        }
    };

    const handleSave = async () => {
        await handleSaveInternal();
    };

    const handleComponentChange = (componentId: number, field: string, value: string) => {
        setHasUnsavedChanges(true);
        setSaveSuccess(false);
        setFormData(prev => ({
            ...prev,
            components: prev.components.map(comp => {
                if (comp.component_id === componentId) {
                    const updated = { ...comp, [field]: value };

                    // Recalculate deviation if planned_treatment changed
                    if (field === 'planned_treatment') {
                        updated.is_deviation = calculateIsDeviation(comp.default_expectation, value);
                    }

                    return updated;
                }
                return comp;
            })
        }));
    };

    const calculateIsDeviation = (defaultExpectation: string, plannedTreatment: string): boolean => {
        if (defaultExpectation === 'Required' && (plannedTreatment === 'NotPlanned' || plannedTreatment === 'NotApplicable')) {
            return true;
        }
        if (defaultExpectation === 'NotExpected' && plannedTreatment === 'Planned') {
            return true;
        }
        return false;
    };

    // Group components by section
    const groupedComponents = formData.components.reduce((acc, comp) => {
        const sectionKey = `${comp.component_definition.section_number}|${comp.component_definition.section_title}`;
        if (!acc[sectionKey]) {
            acc[sectionKey] = [];
        }
        acc[sectionKey].push(comp);
        return acc;
    }, {} as Record<string, ValidationPlanComponent[]>);

    const sections = Object.keys(groupedComponents).sort((a, b) => {
        const aNum = parseInt(a.split('|')[0]);
        const bNum = parseInt(b.split('|')[0]);
        return aNum - bNum;
    });

    if (loading) {
        return <div className="text-gray-600">Loading validation plan...</div>;
    }

    if (!plan) {
        return (
            <>
                {/* Template Selection Modal */}
                {showTemplateModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                            <div className="p-6">
                                <h2 className="text-2xl font-bold mb-4">Use Previous Validation Plan as Template?</h2>
                                <p className="text-gray-600 mb-6">
                                    We found {templateSuggestions.length} previous validation plan{templateSuggestions.length > 1 ? 's' : ''} that could be used as a starting point for this validation.
                                </p>

                                {/* Template Suggestions */}
                                <div className="space-y-4 mb-6">
                                    {templateSuggestions.map((suggestion) => (
                                        <div
                                            key={suggestion.source_plan_id}
                                            className={`border rounded-lg p-4 cursor-pointer transition ${
                                                selectedTemplate === suggestion.source_plan_id
                                                    ? 'border-blue-500 bg-blue-50'
                                                    : 'border-gray-300 hover:border-blue-300'
                                            }`}
                                            onClick={() => setSelectedTemplate(suggestion.source_plan_id)}
                                        >
                                            {/* Configuration Warning */}
                                            {suggestion.is_different_config && (
                                                <div className="mb-3 p-3 bg-yellow-50 border border-yellow-200 rounded">
                                                    <div className="flex items-start gap-2">
                                                        <span className="text-yellow-600 text-xl">⚠️</span>
                                                        <div className="text-sm text-yellow-800">
                                                            <div className="font-semibold mb-1">Requirements Version Changed</div>
                                                            <div>
                                                                This template uses a different validation requirements configuration ({suggestion.config_name || 'Unknown'}).
                                                                We'll automatically recalculate expectations using the current requirements, but review carefully.
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            )}

                                            <div className="grid grid-cols-2 gap-4">
                                                <div>
                                                    <div className="text-sm text-gray-500">Validation Request</div>
                                                    <div className="font-semibold">#{suggestion.source_request_id}</div>
                                                </div>
                                                <div>
                                                    <div className="text-sm text-gray-500">Validation Type</div>
                                                    <div className="font-semibold">{suggestion.validation_type}</div>
                                                </div>
                                                <div>
                                                    <div className="text-sm text-gray-500">Models</div>
                                                    <div className="font-semibold">{suggestion.model_names.join(', ')}</div>
                                                </div>
                                                <div>
                                                    <div className="text-sm text-gray-500">Completed</div>
                                                    <div className="font-semibold">
                                                        {suggestion.completion_date ? suggestion.completion_date.split('T')[0] : 'N/A'}
                                                    </div>
                                                </div>
                                                <div>
                                                    <div className="text-sm text-gray-500">Validator</div>
                                                    <div className="font-semibold">{suggestion.validator_name || 'N/A'}</div>
                                                </div>
                                                <div>
                                                    <div className="text-sm text-gray-500">Components / Deviations</div>
                                                    <div className="font-semibold">
                                                        {suggestion.component_count} components, {suggestion.deviations_count} deviations
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                {/* Action Buttons */}
                                <div className="flex justify-end gap-3">
                                    <button
                                        onClick={handleCreateFromScratch}
                                        className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
                                        disabled={saving}
                                    >
                                        Create from Scratch
                                    </button>
                                    <button
                                        onClick={() => selectedTemplate && handleUseTemplate(selectedTemplate)}
                                        disabled={!selectedTemplate || saving}
                                        className="btn-primary"
                                    >
                                        {saving ? 'Creating...' : 'Use Selected Template'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                <div className="bg-white rounded-lg shadow-md p-6">
                    <h2 className="text-xl font-bold mb-4">Validation Plan</h2>
                    <p className="text-gray-600 mb-4">
                        No validation plan exists for this request yet. Create a plan to document which validation components will be performed.
                    </p>

                    <div className="flex gap-3">
                        <button
                            onClick={() => handleCreatePlan()}
                            disabled={saving}
                            className="btn-primary"
                        >
                            {saving ? 'Creating...' : 'Create Validation Plan'}
                        </button>

                        {templateSuggestions.length > 0 && (
                            <button
                                onClick={() => setShowTemplateModal(true)}
                                disabled={saving}
                                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
                            >
                                Use Template from Previous Validation
                            </button>
                        )}
                    </div>
                </div>
            </>
        );
    }

    return (
        <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold">
                    Validation Plan
                    {hasUnsavedChanges && <span className="text-orange-600 ml-2">*</span>}
                </h2>
                <div className="text-sm">
                    {hasUnsavedChanges && (
                        <span className="text-orange-600 font-medium">Unsaved changes</span>
                    )}
                    {saveSuccess && (
                        <span className="text-green-600 font-medium">✓ Saved successfully</span>
                    )}
                </div>
            </div>

            {error && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded text-red-800">
                    {error}
                </div>
            )}

            {/* Header Info */}
            <div className="mb-6 p-4 bg-gray-50 rounded">
                <div className="grid grid-cols-3 gap-4">
                    <div>
                        <div className="text-sm font-medium text-gray-500">Model</div>
                        <div className="text-base font-semibold">{formData.model_name || 'N/A'}</div>
                    </div>
                    <div>
                        <div className="text-sm font-medium text-gray-500">Risk Tier</div>
                        <div className="text-base font-semibold">{formData.risk_tier || 'N/A'}</div>
                    </div>
                    <div>
                        <div className="text-sm font-medium text-gray-500">Validation Approach</div>
                        <div className="text-base font-semibold">{formData.validation_approach || 'N/A'}</div>
                    </div>
                </div>
            </div>

            {/* Overall Scope Summary */}
            <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Overall Scope Summary
                </label>
                <textarea
                    className="w-full border border-gray-300 rounded p-2 h-24"
                    placeholder="Describe the high-level scope of this validation..."
                    value={formData.overall_scope_summary || ''}
                    onChange={(e) => {
                        setHasUnsavedChanges(true);
                        setSaveSuccess(false);
                        setFormData({ ...formData, overall_scope_summary: e.target.value });
                    }}
                />
            </div>

            {/* Material Deviation */}
            <div className="mb-6 p-4 border border-gray-300 rounded">
                <label className="flex items-center mb-2">
                    <input
                        type="checkbox"
                        checked={formData.material_deviation_from_standard}
                        onChange={(e) => {
                            setHasUnsavedChanges(true);
                            setSaveSuccess(false);
                            setFormData({ ...formData, material_deviation_from_standard: e.target.checked });
                        }}
                        className="mr-2"
                    />
                    <span className="font-medium">Material Deviation from Standard</span>
                </label>
                {formData.material_deviation_from_standard && (
                    <div className="mt-2">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Overall Deviation Rationale <span className="text-red-500">*</span>
                        </label>
                        <textarea
                            className="w-full border border-gray-300 rounded p-2 h-20"
                            placeholder="Explain why this validation deviates materially from the standard approach..."
                            value={formData.overall_deviation_rationale || ''}
                            onChange={(e) => {
                                setHasUnsavedChanges(true);
                                setSaveSuccess(false);
                                setFormData({ ...formData, overall_deviation_rationale: e.target.value });
                            }}
                        />
                    </div>
                )}
            </div>

            {/* Components Table */}
            <div className="mb-6">
                <h3 className="text-lg font-semibold mb-4">Validation Components</h3>

                {sections.map(sectionKey => {
                    const [sectionNum, sectionTitle] = sectionKey.split('|');
                    const components = groupedComponents[sectionKey];

                    return (
                        <div key={sectionKey} className="mb-6">
                            <h4 className="font-semibold text-gray-800 mb-2 bg-gray-100 px-3 py-2 rounded">
                                Section {sectionNum} – {sectionTitle}
                            </h4>

                            <table className="min-w-full border border-gray-300 table-fixed">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="border border-gray-300 px-3 py-2 text-left text-xs font-medium w-1/4">
                                            Component
                                        </th>
                                        <th className="border border-gray-300 px-3 py-2 text-left text-xs font-medium w-36">
                                            Bank Expectation
                                        </th>
                                        <th className="border border-gray-300 px-3 py-2 text-left text-xs font-medium w-40">
                                            Planned Status
                                        </th>
                                        <th className="border border-gray-300 px-3 py-2 text-left text-xs font-medium">
                                            Rationale
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {components.map(comp => (
                                        <tr
                                            key={comp.component_id}
                                            className={comp.is_deviation ? 'bg-yellow-50' : ''}
                                        >
                                            <td className="border border-gray-300 px-3 py-2 text-sm">
                                                <div className="flex items-center gap-2">
                                                    {comp.is_deviation && (
                                                        <span className="text-yellow-600" title="Deviation from bank standard">
                                                            ⚠️
                                                        </span>
                                                    )}
                                                    <div>
                                                        <div className="font-medium">{comp.component_definition.component_code}</div>
                                                        <div className="text-gray-600">{comp.component_definition.component_title}</div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="border border-gray-300 px-3 py-2 text-sm">
                                                <span className={`px-2 py-1 rounded text-xs font-medium ${
                                                    comp.default_expectation === 'Required' ? 'bg-blue-100 text-blue-800' :
                                                    comp.default_expectation === 'IfApplicable' ? 'bg-gray-100 text-gray-800' :
                                                    'bg-red-100 text-red-800'
                                                }`}>
                                                    {comp.default_expectation}
                                                </span>
                                            </td>
                                            <td className="border border-gray-300 px-3 py-2">
                                                <select
                                                    className="border border-gray-300 rounded px-2 py-1 text-sm w-full"
                                                    value={comp.planned_treatment}
                                                    onChange={(e) => handleComponentChange(comp.component_id, 'planned_treatment', e.target.value)}
                                                >
                                                    <option value="Planned">Planned</option>
                                                    <option value="NotPlanned">Not Planned</option>
                                                    <option value="NotApplicable">Not Applicable</option>
                                                </select>
                                            </td>
                                            <td className="border border-gray-300 px-3 py-2">
                                                {comp.is_deviation ? (
                                                    <textarea
                                                        className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                                                        placeholder="Required: Explain deviation from standard..."
                                                        rows={2}
                                                        value={comp.rationale || ''}
                                                        onChange={(e) => handleComponentChange(comp.component_id, 'rationale', e.target.value)}
                                                    />
                                                ) : (
                                                    <textarea
                                                        className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                                                        placeholder="Optional notes..."
                                                        rows={2}
                                                        value={comp.rationale || ''}
                                                        onChange={(e) => handleComponentChange(comp.component_id, 'rationale', e.target.value)}
                                                    />
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    );
                })}
            </div>

            {/* Action Buttons */}
            <div className="flex justify-between">
                <div>
                    {plan && !plan.locked_at && (
                        <button
                            onClick={handleDeletePlan}
                            disabled={saving}
                            className="px-4 py-2 border border-red-600 text-red-600 rounded hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            Delete Plan
                        </button>
                    )}
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={handleExportPDF}
                        className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
                    >
                        Export PDF
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="btn-primary"
                    >
                        {saving ? 'Saving...' : 'Save Validation Plan'}
                    </button>
                </div>
            </div>
        </div>
    );
});

ValidationPlanForm.displayName = 'ValidationPlanForm';

export default ValidationPlanForm;
