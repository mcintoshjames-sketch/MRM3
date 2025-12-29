import { useState, useEffect, useCallback } from 'react';
import api from '../api/client';
import { recommendationsApi, TaxonomyValue } from '../api/recommendations';
import ModelSearchSelect from './ModelSearchSelect';

interface Model {
    model_id: number;
    model_name: string;
}

interface TimeframeInfo {
    priority_code: string;
    risk_tier_code: string;
    usage_frequency_code: string;
    max_days: number;
    calculated_max_date: string;
    enforce_timeframes: boolean;
    enforced_by_region: string | null;
}

interface User {
    user_id: number;
    email: string;
    full_name: string;
}

interface ValidationRequest {
    request_id: number;
    model_ids: number[];
    model_names: string[];
    validation_type: string;
    current_status: string;
}

interface MonitoringCycle {
    cycle_id: number;
    period_start_date: string;
    period_end_date: string;
    plan_name?: string;
    status?: string;
}

interface RecommendationCreateModalProps {
    onClose: () => void;
    onCreated: () => void;
    models: Model[];
    users: User[];
    priorities: TaxonomyValue[];
    categories: TaxonomyValue[];
    preselectedModelId?: number;
    preselectedValidationRequestId?: number;
    preselectedMonitoringCycleId?: number;
    preselectedPlanMetricId?: number;
    preselectedTitle?: string;
    preselectedDescription?: string;
}

export default function RecommendationCreateModal({
    onClose,
    onCreated,
    models,
    users,
    priorities,
    categories,
    preselectedModelId,
    preselectedValidationRequestId,
    preselectedMonitoringCycleId,
    preselectedPlanMetricId,
    preselectedTitle,
    preselectedDescription
}: RecommendationCreateModalProps) {
    const [formData, setFormData] = useState({
        model_id: preselectedModelId || 0,
        validation_request_id: preselectedValidationRequestId || null as number | null,
        monitoring_cycle_id: preselectedMonitoringCycleId || null as number | null,
        plan_metric_id: preselectedPlanMetricId || null as number | null,
        title: preselectedTitle || '',
        description: preselectedDescription || '',
        priority_id: 0,
        category_id: null as number | null,
        assigned_to_id: 0,
        original_target_date: '',
        target_date_change_reason: ''
    });
    const [assignedUserSearch, setAssignedUserSearch] = useState('');
    const [showAssignedUserDropdown, setShowAssignedUserDropdown] = useState(false);

    const [validationRequests, setValidationRequests] = useState<ValidationRequest[]>([]);
    const [monitoringCycles, setMonitoringCycles] = useState<MonitoringCycle[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [timeframeInfo, setTimeframeInfo] = useState<TimeframeInfo | null>(null);
    const [timeframeLoading, setTimeframeLoading] = useState(false);

    // Fetch validation requests and monitoring cycles for selected model
    useEffect(() => {
        const fetchValidationRequests = async () => {
            if (formData.model_id) {
                try {
                    const response = await api.get('/validation-workflow/requests/', {
                        params: { model_id: formData.model_id }
                    });
                    setValidationRequests(response.data);
                } catch (err) {
                    console.error('Failed to fetch validation requests:', err);
                    setValidationRequests([]);
                }
            } else {
                setValidationRequests([]);
            }
        };

        const fetchMonitoringCycles = async () => {
            if (formData.model_id) {
                try {
                    // Fetch monitoring plans that include this model
                    const plansResponse = await api.get('/monitoring/plans', {
                        params: { model_id: formData.model_id }
                    });
                    // Extract cycles from all plans
                    const cycles: MonitoringCycle[] = [];
                    for (const plan of plansResponse.data) {
                        const cyclesResponse = await api.get(`/monitoring/plans/${plan.plan_id}/cycles`);
                        for (const cycle of cyclesResponse.data) {
                            cycles.push({
                                cycle_id: cycle.cycle_id,
                                period_start_date: cycle.period_start_date,
                                period_end_date: cycle.period_end_date,
                                plan_name: plan.name,
                                status: cycle.status
                            });
                        }
                    }
                    setMonitoringCycles(cycles);
                } catch (err) {
                    console.error('Failed to fetch monitoring cycles:', err);
                    setMonitoringCycles([]);
                }
            } else {
                setMonitoringCycles([]);
            }
        };

        fetchValidationRequests();
        fetchMonitoringCycles();
    }, [formData.model_id, models]);

    // Calculate timeframe when model and priority are selected
    const calculateTimeframe = useCallback(async (modelId: number, priorityId: number) => {
        if (!modelId || !priorityId) {
            setTimeframeInfo(null);
            return;
        }

        setTimeframeLoading(true);
        try {
            const response = await api.post('/recommendations/timeframe-config/calculate', {
                model_id: modelId,
                priority_id: priorityId
            });
            const info = response.data as TimeframeInfo;
            setTimeframeInfo(info);

            // Set default target date to calculated max date
            setFormData(prev => ({
                ...prev,
                original_target_date: info.calculated_max_date,
                target_date_change_reason: '' // Clear reason when switching to default
            }));
        } catch (err) {
            console.error('Failed to calculate timeframe:', err);
            setTimeframeInfo(null);
            // Fall back to default 30 days if calculation fails
            const defaultDate = new Date();
            defaultDate.setDate(defaultDate.getDate() + 30);
            setFormData(prev => ({
                ...prev,
                original_target_date: defaultDate.toISOString().split('T')[0]
            }));
        } finally {
            setTimeframeLoading(false);
        }
    }, []);

    // Trigger timeframe calculation when model or priority changes
    useEffect(() => {
        if (formData.model_id && formData.priority_id) {
            calculateTimeframe(formData.model_id, formData.priority_id);
        } else {
            setTimeframeInfo(null);
            // Set default 30 days if no model/priority yet
            const defaultDate = new Date();
            defaultDate.setDate(defaultDate.getDate() + 30);
            setFormData(prev => ({
                ...prev,
                original_target_date: defaultDate.toISOString().split('T')[0]
            }));
        }
    }, [formData.model_id, formData.priority_id, calculateTimeframe]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        // Validation
        if (!formData.model_id) {
            setError('Please select a model');
            return;
        }
        if (!formData.title.trim()) {
            setError('Please enter a title');
            return;
        }
        if (!formData.description.trim()) {
            setError('Please enter a description');
            return;
        }
        if (!formData.priority_id) {
            setError('Please select a priority');
            return;
        }
        if (!formData.assigned_to_id) {
            setError('Please select an assigned user');
            return;
        }
        if (!formData.original_target_date) {
            setError('Please set a target date');
            return;
        }

        try {
            setLoading(true);
            await recommendationsApi.create({
                model_id: formData.model_id,
                validation_request_id: formData.validation_request_id || undefined,
                monitoring_cycle_id: formData.monitoring_cycle_id || undefined,
                plan_metric_id: formData.plan_metric_id || undefined,
                title: formData.title.trim(),
                description: formData.description.trim(),
                priority_id: formData.priority_id,
                category_id: formData.category_id || undefined,
                assigned_to_id: formData.assigned_to_id,
                original_target_date: formData.original_target_date,
                target_date_change_reason: formData.target_date_change_reason?.trim() || undefined
            });
            onCreated();
        } catch (err: any) {
            console.error('Failed to create recommendation:', err);
            setError(err.response?.data?.detail || 'Failed to create recommendation');
        } finally {
            setLoading(false);
        }
    };

    const selectedAssignedUser = users.find((u) => u.user_id === formData.assigned_to_id);
    const normalizedAssignedUserSearch = assignedUserSearch.trim().toLowerCase();
    const filteredAssignedUsers = users.filter((u) => {
        if (!normalizedAssignedUserSearch) return true;
        return (
            u.full_name.toLowerCase().includes(normalizedAssignedUserSearch) ||
            u.email.toLowerCase().includes(normalizedAssignedUserSearch)
        );
    }).slice(0, 50);
    const selectedModel = models.find((m) => m.model_id === formData.model_id);

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                <div className="p-6">
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="text-lg font-bold">Create New Recommendation</h3>
                        <button
                            onClick={onClose}
                            className="text-gray-500 hover:text-gray-700"
                        >
                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    <p className="text-sm text-gray-600 mb-4">
                        Create a new recommendation to track a validation finding. The recommendation will start in Draft status
                        until finalized and sent to the assigned developer.
                    </p>

                    {error && (
                        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit}>
                        <div className="space-y-4">
                            {/* Model Selection */}
                            <div>
                                <label htmlFor="model_id" className="block text-sm font-medium text-gray-700 mb-1">
                                    Model <span className="text-red-500">*</span>
                                </label>
                                <ModelSearchSelect
                                    id="model_id"
                                    models={models}
                                    value={formData.model_id || null}
                                    onChange={(value) => {
                                        const nextId = typeof value === 'number' ? value : 0;
                                        setFormData({
                                            ...formData,
                                            model_id: nextId,
                                            validation_request_id: null,
                                            monitoring_cycle_id: null
                                        });
                                    }}
                                    placeholder="Type to search by model name or ID..."
                                    disabled={!!preselectedModelId}
                                    required
                                />
                                {formData.model_id > 0 && selectedModel && (
                                    <p className="mt-1 text-sm text-green-600">
                                        Selected: {selectedModel.model_name}
                                    </p>
                                )}
                            </div>

                            {/* Validation Request (Optional) */}
                            {formData.model_id > 0 && validationRequests.length > 0 && (
                                <div>
                                    <label htmlFor="validation_request_id" className="block text-sm font-medium text-gray-700 mb-1">
                                        Related Validation Project (Optional)
                                    </label>
                                    <select
                                        id="validation_request_id"
                                        className="input-field"
                                        value={formData.validation_request_id || ''}
                                        onChange={(e) => setFormData({
                                            ...formData,
                                            validation_request_id: e.target.value ? parseInt(e.target.value) : null
                                        })}
                                        disabled={!!preselectedValidationRequestId}
                                    >
                                        <option value="">No specific validation...</option>
                                        {validationRequests.map(vr => (
                                            <option key={vr.request_id} value={vr.request_id}>
                                                #{vr.request_id} - {vr.validation_type} ({vr.current_status})
                                            </option>
                                        ))}
                                    </select>
                                    <p className="text-xs text-gray-500 mt-1">
                                        Link this recommendation to a specific validation project
                                    </p>
                                </div>
                            )}

                            {/* Monitoring Cycle (Optional) */}
                            {formData.model_id > 0 && monitoringCycles.length > 0 && (
                                <div>
                                    <label htmlFor="monitoring_cycle_id" className="block text-sm font-medium text-gray-700 mb-1">
                                        Related Monitoring Cycle (Optional)
                                    </label>
                                    <select
                                        id="monitoring_cycle_id"
                                        className="input-field"
                                        value={formData.monitoring_cycle_id || ''}
                                        onChange={(e) => setFormData({
                                            ...formData,
                                            monitoring_cycle_id: e.target.value ? parseInt(e.target.value) : null
                                        })}
                                    >
                                        <option value="">No specific monitoring cycle...</option>
                                        {monitoringCycles.map(mc => (
                                            <option key={mc.cycle_id} value={mc.cycle_id}>
                                                {mc.plan_name ? `${mc.plan_name}: ` : ''}{mc.period_start_date} to {mc.period_end_date} ({mc.status})
                                            </option>
                                        ))}
                                    </select>
                                    <p className="text-xs text-gray-500 mt-1">
                                        Link this recommendation to a specific monitoring cycle
                                    </p>
                                </div>
                            )}

                            {/* Title */}
                            <div>
                                <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">
                                    Title <span className="text-red-500">*</span>
                                </label>
                                <input
                                    id="title"
                                    type="text"
                                    className="input-field"
                                    value={formData.title}
                                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                                    placeholder="Brief summary of the issue..."
                                    required
                                    maxLength={500}
                                />
                            </div>

                            {/* Description */}
                            <div>
                                <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
                                    Description <span className="text-red-500">*</span>
                                </label>
                                <textarea
                                    id="description"
                                    className="input-field"
                                    rows={4}
                                    value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    placeholder="Detailed description of the finding..."
                                    required
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                {/* Priority */}
                                <div>
                                    <label htmlFor="priority_id" className="block text-sm font-medium text-gray-700 mb-1">
                                        Priority <span className="text-red-500">*</span>
                                    </label>
                                    <select
                                        id="priority_id"
                                        className="input-field"
                                        value={formData.priority_id || ''}
                                        onChange={(e) => setFormData({ ...formData, priority_id: parseInt(e.target.value) || 0 })}
                                        required
                                    >
                                        <option value="">Select priority...</option>
                                        {priorities.map(p => (
                                            <option key={p.value_id} value={p.value_id}>{p.label}</option>
                                        ))}
                                    </select>
                                </div>

                                {/* Category */}
                                <div>
                                    <label htmlFor="category_id" className="block text-sm font-medium text-gray-700 mb-1">
                                        Category
                                    </label>
                                    <select
                                        id="category_id"
                                        className="input-field"
                                        value={formData.category_id || ''}
                                        onChange={(e) => setFormData({ ...formData, category_id: e.target.value ? parseInt(e.target.value) : null })}
                                    >
                                        <option value="">Select category...</option>
                                        {categories.map(c => (
                                            <option key={c.value_id} value={c.value_id}>{c.label}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                {/* Assigned To */}
                                <div>
                                    <label htmlFor="assigned_to_id" className="block text-sm font-medium text-gray-700 mb-1">
                                        Assigned To <span className="text-red-500">*</span>
                                    </label>
                                    <div className="relative">
                                        <input
                                            id="assigned_to_id"
                                            type="text"
                                            placeholder="Type to search users..."
                                            value={assignedUserSearch}
                                            onChange={(e) => {
                                                const value = e.target.value;
                                                setAssignedUserSearch(value);
                                                setShowAssignedUserDropdown(true);
                                                if (formData.assigned_to_id && selectedAssignedUser) {
                                                    if (value !== selectedAssignedUser.full_name && value !== selectedAssignedUser.email) {
                                                        setFormData({ ...formData, assigned_to_id: 0 });
                                                    }
                                                }
                                            }}
                                            onFocus={() => setShowAssignedUserDropdown(true)}
                                            className="input-field"
                                            required
                                        />
                                        {showAssignedUserDropdown && (
                                            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                                                {filteredAssignedUsers.map((u) => (
                                                    <div
                                                        key={u.user_id}
                                                        className="px-4 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                                                        onClick={() => {
                                                            setFormData({ ...formData, assigned_to_id: u.user_id });
                                                            setAssignedUserSearch(u.full_name);
                                                            setShowAssignedUserDropdown(false);
                                                        }}
                                                    >
                                                        <div className="font-medium">{u.full_name}</div>
                                                        <div className="text-xs text-gray-500">{u.email}</div>
                                                    </div>
                                                ))}
                                                {filteredAssignedUsers.length === 0 && (
                                                    <div className="px-4 py-2 text-sm text-gray-500">No users found</div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                    {formData.assigned_to_id > 0 && selectedAssignedUser && (
                                        <p className="mt-1 text-sm text-green-600">
                                            Selected: {selectedAssignedUser.full_name}
                                        </p>
                                    )}
                                    <p className="text-xs text-gray-500 mt-1">
                                        The developer responsible for remediation
                                    </p>
                                </div>

                                {/* Target Date */}
                                <div>
                                    <label htmlFor="target_date" className="block text-sm font-medium text-gray-700 mb-1">
                                        Target Date <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        id="target_date"
                                        type="date"
                                        className="input-field"
                                        value={formData.original_target_date}
                                        onChange={(e) => setFormData({ ...formData, original_target_date: e.target.value })}
                                        required
                                        min={new Date().toISOString().split('T')[0]}
                                        max={timeframeInfo?.enforce_timeframes ? timeframeInfo.calculated_max_date : undefined}
                                    />
                                    {timeframeLoading && (
                                        <p className="text-xs text-gray-500 mt-1">
                                            Calculating timeframe...
                                        </p>
                                    )}
                                    {timeframeInfo && !timeframeLoading && (
                                        <div className="mt-2 space-y-1">
                                            <p className="text-xs text-gray-600">
                                                <span className="font-medium">Max allowed:</span> {timeframeInfo.calculated_max_date}
                                                {' '}({timeframeInfo.max_days} days from creation)
                                            </p>
                                            {timeframeInfo.enforce_timeframes ? (
                                                <p className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded">
                                                    ⚠️ Timeframe enforced
                                                    {timeframeInfo.enforced_by_region && ` by ${timeframeInfo.enforced_by_region}`}
                                                    — target date cannot exceed {timeframeInfo.calculated_max_date}
                                                </p>
                                            ) : (
                                                <p className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">
                                                    ℹ️ Suggested deadline based on priority, risk tier, and usage frequency
                                                </p>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Target Date Change Reason (required when date differs from calculated max) */}
                            {timeframeInfo && formData.original_target_date &&
                             formData.original_target_date !== timeframeInfo.calculated_max_date && (
                                <div>
                                    <label htmlFor="target_date_reason" className="block text-sm font-medium text-gray-700 mb-1">
                                        Reason for Target Date <span className="text-red-500">*</span>
                                    </label>
                                    <textarea
                                        id="target_date_reason"
                                        className="input-field"
                                        rows={2}
                                        value={formData.target_date_change_reason}
                                        onChange={(e) => setFormData({ ...formData, target_date_change_reason: e.target.value })}
                                        placeholder="Explain why this target date differs from the calculated maximum..."
                                        required
                                    />
                                    <p className="text-xs text-gray-500 mt-1">
                                        Required because target date ({formData.original_target_date}) differs from calculated max ({timeframeInfo.calculated_max_date})
                                    </p>
                                </div>
                            )}
                        </div>

                        {/* Actions */}
                        <div className="flex justify-end gap-3 mt-6 pt-4 border-t">
                            <button
                                type="button"
                                onClick={onClose}
                                className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                                disabled={loading}
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                className="btn-primary"
                                disabled={loading}
                            >
                                {loading ? 'Creating...' : 'Create Recommendation'}
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}
