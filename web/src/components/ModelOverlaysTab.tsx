import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../api/client';
import {
    listModelOverlays,
    createModelOverlay,
    updateModelOverlay,
    retireModelOverlay,
    ModelOverlayListItem,
    ModelOverlayUpdate,
    OverlayKind,
} from '../api/modelOverlays';
import { canManageModels } from '../utils/roleUtils';
import { useTableSort } from '../hooks/useTableSort';

interface Region {
    region_id: number;
    code: string;
    name: string;
}

const overlayKindOptions: { value: OverlayKind; label: string }[] = [
    { value: 'OVERLAY', label: 'Overlay' },
    { value: 'MANAGEMENT_JUDGEMENT', label: 'Management Judgement' },
];

const formatDate = (value?: string | null) => (value ? value.split('T')[0] : '');

const ModelOverlaysTab: React.FC<{ modelId: number }> = ({ modelId }) => {
    const { user } = useAuth();
    const canEdit = canManageModels(user);

    const [overlays, setOverlays] = useState<ModelOverlayListItem[]>([]);
    const [regions, setRegions] = useState<Region[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [showRetired, setShowRetired] = useState(false);

    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showEditModal, setShowEditModal] = useState(false);
    const [showRetireModal, setShowRetireModal] = useState(false);
    const [selectedOverlay, setSelectedOverlay] = useState<ModelOverlayListItem | null>(null);

    const [createError, setCreateError] = useState<string | null>(null);
    const [editError, setEditError] = useState<string | null>(null);
    const [retireError, setRetireError] = useState<string | null>(null);

    const today = new Date().toISOString().split('T')[0];

    const [createForm, setCreateForm] = useState({
        overlay_kind: 'OVERLAY' as OverlayKind,
        is_underperformance_related: true,
        description: '',
        rationale: '',
        effective_from: today,
        effective_to: '',
        region_id: '',
        evidence_description: '',
        trigger_monitoring_result_id: '',
        trigger_monitoring_cycle_id: '',
        related_recommendation_id: '',
        related_limitation_id: '',
    });

    const [editForm, setEditForm] = useState({
        evidence_description: '',
        trigger_monitoring_result_id: '',
        trigger_monitoring_cycle_id: '',
        related_recommendation_id: '',
        related_limitation_id: '',
    });
    const [editInitial, setEditInitial] = useState(editForm);

    const [retirementReason, setRetirementReason] = useState('');

    const fetchRegions = async () => {
        try {
            const response = await api.get('/regions/');
            setRegions(response.data);
        } catch (err) {
            console.error('Failed to fetch regions:', err);
        }
    };

    const fetchOverlays = async () => {
        try {
            setLoading(true);
            setError(null);
            const params = showRetired ? { include_retired: true } : undefined;
            const data = await listModelOverlays(modelId, params);
            setOverlays(data);
        } catch (err) {
            console.error('Failed to fetch overlays:', err);
            setError('Failed to load overlays');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRegions();
    }, []);

    useEffect(() => {
        fetchOverlays();
    }, [modelId, showRetired]);

    const isInEffect = (overlay: ModelOverlayListItem) => {
        const starts = overlay.effective_from <= today;
        const ends = !overlay.effective_to || overlay.effective_to >= today;
        return !overlay.is_retired && starts && ends;
    };

    const displayOverlays = useMemo(() => {
        if (showRetired) return overlays;
        return overlays.filter(isInEffect);
    }, [overlays, showRetired]);

    const { sortedData, requestSort, getSortIcon } = useTableSort<ModelOverlayListItem>(
        displayOverlays,
        'effective_from',
        'desc'
    );

    const inEffectCount = overlays.filter(isInEffect).length;
    const retiredCount = overlays.filter(o => o.is_retired).length;

    const getStatusBadge = (overlay: ModelOverlayListItem) => {
        if (overlay.is_retired) {
            return <span className="px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-700">Retired</span>;
        }
        if (isInEffect(overlay)) {
            return <span className="px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-700">In Effect</span>;
        }
        if (overlay.effective_from > today) {
            return <span className="px-2 py-1 text-xs font-medium rounded bg-blue-100 text-blue-700">Scheduled</span>;
        }
        return <span className="px-2 py-1 text-xs font-medium rounded bg-yellow-100 text-yellow-700">Expired</span>;
    };

    const resetCreateForm = () => {
        setCreateForm({
            overlay_kind: 'OVERLAY',
            is_underperformance_related: true,
            description: '',
            rationale: '',
            effective_from: today,
            effective_to: '',
            region_id: '',
            evidence_description: '',
            trigger_monitoring_result_id: '',
            trigger_monitoring_cycle_id: '',
            related_recommendation_id: '',
            related_limitation_id: '',
        });
        setCreateError(null);
    };

    const openEditModal = (overlay: ModelOverlayListItem) => {
        setSelectedOverlay(overlay);
        const initial = {
            evidence_description: overlay.evidence_description || '',
            trigger_monitoring_result_id: overlay.trigger_monitoring_result_id?.toString() || '',
            trigger_monitoring_cycle_id: overlay.trigger_monitoring_cycle_id?.toString() || '',
            related_recommendation_id: overlay.related_recommendation_id?.toString() || '',
            related_limitation_id: overlay.related_limitation_id?.toString() || '',
        };
        setEditForm(initial);
        setEditInitial(initial);
        setEditError(null);
        setShowEditModal(true);
    };

    const openRetireModal = (overlay: ModelOverlayListItem) => {
        setSelectedOverlay(overlay);
        setRetirementReason('');
        setRetireError(null);
        setShowRetireModal(true);
    };

    const parseOptionalId = (value: string) => {
        const trimmed = value.trim();
        if (!trimmed) return null;
        const parsed = Number(trimmed);
        return Number.isNaN(parsed) ? null : parsed;
    };

    const handleCreate = async () => {
        setCreateError(null);
        if (!createForm.description.trim() || !createForm.rationale.trim() || !createForm.effective_from) {
            setCreateError('Description, rationale, and effective from date are required.');
            return;
        }

        const triggerResult = parseOptionalId(createForm.trigger_monitoring_result_id);
        const triggerCycle = parseOptionalId(createForm.trigger_monitoring_cycle_id);
        const relatedRec = parseOptionalId(createForm.related_recommendation_id);
        const relatedLimitation = parseOptionalId(createForm.related_limitation_id);

        if (
            (createForm.trigger_monitoring_result_id.trim() && triggerResult === null) ||
            (createForm.trigger_monitoring_cycle_id.trim() && triggerCycle === null) ||
            (createForm.related_recommendation_id.trim() && relatedRec === null) ||
            (createForm.related_limitation_id.trim() && relatedLimitation === null)
        ) {
            setCreateError('Linked IDs must be valid numbers.');
            return;
        }

        try {
            await createModelOverlay(modelId, {
                overlay_kind: createForm.overlay_kind,
                is_underperformance_related: createForm.is_underperformance_related,
                description: createForm.description.trim(),
                rationale: createForm.rationale.trim(),
                effective_from: createForm.effective_from,
                effective_to: createForm.effective_to || null,
                region_id: createForm.region_id ? Number(createForm.region_id) : null,
                evidence_description: createForm.evidence_description.trim() || null,
                trigger_monitoring_result_id: triggerResult,
                trigger_monitoring_cycle_id: triggerCycle,
                related_recommendation_id: relatedRec,
                related_limitation_id: relatedLimitation,
            });
            setShowCreateModal(false);
            resetCreateForm();
            fetchOverlays();
        } catch (err) {
            console.error('Failed to create overlay:', err);
            setCreateError('Failed to create overlay');
        }
    };

    const handleEdit = async () => {
        if (!selectedOverlay) return;
        setEditError(null);

        const next = {
            evidence_description: editForm.evidence_description.trim() || null,
            trigger_monitoring_result_id: parseOptionalId(editForm.trigger_monitoring_result_id),
            trigger_monitoring_cycle_id: parseOptionalId(editForm.trigger_monitoring_cycle_id),
            related_recommendation_id: parseOptionalId(editForm.related_recommendation_id),
            related_limitation_id: parseOptionalId(editForm.related_limitation_id),
        };

        if (
            (editForm.trigger_monitoring_result_id.trim() && next.trigger_monitoring_result_id === null) ||
            (editForm.trigger_monitoring_cycle_id.trim() && next.trigger_monitoring_cycle_id === null) ||
            (editForm.related_recommendation_id.trim() && next.related_recommendation_id === null) ||
            (editForm.related_limitation_id.trim() && next.related_limitation_id === null)
        ) {
            setEditError('Linked IDs must be valid numbers.');
            return;
        }

        const payload: Partial<ModelOverlayUpdate> = {};
        (Object.keys(next) as (keyof typeof next)[]).forEach((key) => {
            const initial = editInitial[key];
            const current = next[key];
            if ((initial || '') !== (current === null ? '' : current?.toString?.() || '')) {
                payload[key as keyof ModelOverlayUpdate] = current as ModelOverlayUpdate[keyof ModelOverlayUpdate];
            }
        });

        if (Object.keys(payload).length === 0) {
            setEditError('No changes to save.');
            return;
        }

        try {
            await updateModelOverlay(selectedOverlay.overlay_id, payload);
            setShowEditModal(false);
            setSelectedOverlay(null);
            fetchOverlays();
        } catch (err) {
            console.error('Failed to update overlay:', err);
            setEditError('Failed to update overlay');
        }
    };

    const handleRetire = async () => {
        if (!selectedOverlay) return;
        setRetireError(null);
        if (!retirementReason.trim()) {
            setRetireError('Retirement reason is required.');
            return;
        }

        try {
            await retireModelOverlay(selectedOverlay.overlay_id, { retirement_reason: retirementReason.trim() });
            setShowRetireModal(false);
            setSelectedOverlay(null);
            fetchOverlays();
        } catch (err) {
            console.error('Failed to retire overlay:', err);
            setRetireError('Failed to retire overlay');
        }
    };

    const exportToCSV = () => {
        if (sortedData.length === 0) return;
        const headers = [
            'Overlay ID',
            'Model ID',
            'Kind',
            'Underperformance Related',
            'Description',
            'Rationale',
            'Effective From',
            'Effective To',
            'Region',
            'Status',
            'Evidence',
            'Monitoring Result ID',
            'Monitoring Cycle ID',
            'Recommendation ID',
            'Limitation ID',
        ];

        const rows = sortedData.map((overlay) => [
            overlay.overlay_id,
            overlay.model_id,
            overlay.overlay_kind === 'OVERLAY' ? 'Overlay' : 'Management Judgement',
            overlay.is_underperformance_related ? 'Yes' : 'No',
            `"${overlay.description.replace(/"/g, '""')}"`,
            `"${overlay.rationale.replace(/"/g, '""')}"`,
            formatDate(overlay.effective_from),
            formatDate(overlay.effective_to),
            overlay.region?.name || 'Global',
            overlay.is_retired ? 'Retired' : (isInEffect(overlay) ? 'In Effect' : (overlay.effective_from > today ? 'Scheduled' : 'Expired')),
            `"${(overlay.evidence_description || '').replace(/"/g, '""')}"`,
            overlay.trigger_monitoring_result_id || '',
            overlay.trigger_monitoring_cycle_id || '',
            overlay.related_recommendation_id || '',
            overlay.related_limitation_id || '',
        ]);

        const csvContent = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `model_overlays_${today}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-3 text-gray-600">Loading overlays...</span>
            </div>
        );
    }

    return (
        <div>
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h3 className="text-xl font-bold">Overlays &amp; Judgements</h3>
                    <p className="text-sm text-gray-500 mt-1">
                        {inEffectCount > 0 && (
                            <span className="text-green-700 font-medium">{inEffectCount} In Effect</span>
                        )}
                        {inEffectCount > 0 && retiredCount > 0 && ' · '}
                        {retiredCount > 0 && (
                            <span>{retiredCount} Retired</span>
                        )}
                        {inEffectCount === 0 && retiredCount === 0 && 'No overlays recorded'}
                    </p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={exportToCSV}
                        disabled={sortedData.length === 0}
                        className="bg-gray-100 text-gray-700 px-4 py-2 rounded hover:bg-gray-200 text-sm disabled:opacity-50"
                    >
                        Export CSV
                    </button>
                    {canEdit && (
                        <button
                            onClick={() => setShowCreateModal(true)}
                            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm"
                        >
                            + Add Overlay
                        </button>
                    )}
                </div>
            </div>

            <div className="flex items-center gap-4 mb-4">
                <label className="flex items-center gap-2 text-sm text-gray-600">
                    <input
                        type="checkbox"
                        checked={showRetired}
                        onChange={(e) => setShowRetired(e.target.checked)}
                        className="rounded border-gray-300"
                    />
                    Include retired
                </label>
            </div>

            {error && (
                <div className="mb-4 p-3 bg-red-100 text-red-800 rounded">
                    {error}
                </div>
            )}

            {sortedData.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="mt-4 text-lg">No overlays recorded</p>
                    <p className="mt-2 text-sm">
                        {canEdit
                            ? 'Click "Add Overlay" to document an underperformance judgement.'
                            : 'Overlays will appear here when documented by validators.'}
                    </p>
                </div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th
                                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                    onClick={() => requestSort('overlay_kind')}
                                >
                                    <div className="flex items-center gap-2">
                                        Kind
                                        {getSortIcon('overlay_kind')}
                                    </div>
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Underperformance
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Description
                                </th>
                                <th
                                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                    onClick={() => requestSort('effective_from')}
                                >
                                    <div className="flex items-center gap-2">
                                        Effective Window
                                        {getSortIcon('effective_from')}
                                    </div>
                                </th>
                                <th
                                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                    onClick={() => requestSort('region.name')}
                                >
                                    <div className="flex items-center gap-2">
                                        Region
                                        {getSortIcon('region.name')}
                                    </div>
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Status
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Links
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                    Actions
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {sortedData.map((overlay) => (
                                <tr key={overlay.overlay_id} className={overlay.is_retired ? 'bg-gray-50 opacity-70' : ''}>
                                    <td className="px-4 py-4 text-sm text-gray-900">
                                        {overlay.overlay_kind === 'OVERLAY' ? 'Overlay' : 'Management Judgement'}
                                    </td>
                                    <td className="px-4 py-4 text-sm text-gray-900">
                                        {overlay.is_underperformance_related ? 'Yes' : 'No'}
                                    </td>
                                    <td className="px-4 py-4 text-sm text-gray-900">
                                        <div className="font-medium">{overlay.description}</div>
                                        <div className="text-xs text-gray-500 mt-1">Rationale: {overlay.rationale}</div>
                                        {overlay.evidence_description && (
                                            <div className="text-xs text-gray-500 mt-1">Evidence: {overlay.evidence_description}</div>
                                        )}
                                    </td>
                                    <td className="px-4 py-4 text-sm text-gray-900">
                                        <div>{formatDate(overlay.effective_from)}</div>
                                        <div className="text-xs text-gray-500">to {overlay.effective_to ? formatDate(overlay.effective_to) : 'Open-ended'}</div>
                                    </td>
                                    <td className="px-4 py-4 text-sm text-gray-900">
                                        {overlay.region?.name || 'Global'}
                                    </td>
                                    <td className="px-4 py-4 text-sm">
                                        {getStatusBadge(overlay)}
                                    </td>
                                    <td className="px-4 py-4 text-sm text-gray-700">
                                        <div className="flex flex-wrap gap-2">
                                            {overlay.trigger_monitoring_cycle_id && (
                                                <Link
                                                    to={`/monitoring/cycles/${overlay.trigger_monitoring_cycle_id}`}
                                                    className="text-blue-600 hover:text-blue-800 hover:underline text-xs"
                                                >
                                                    Cycle #{overlay.trigger_monitoring_cycle_id}
                                                </Link>
                                            )}
                                            {overlay.trigger_monitoring_result_id && (
                                                <span className="text-xs text-gray-600">Result #{overlay.trigger_monitoring_result_id}</span>
                                            )}
                                            {overlay.related_recommendation_id && (
                                                <Link
                                                    to={`/recommendations/${overlay.related_recommendation_id}`}
                                                    className="text-blue-600 hover:text-blue-800 hover:underline text-xs"
                                                >
                                                    Rec #{overlay.related_recommendation_id}
                                                </Link>
                                            )}
                                            {overlay.related_limitation_id && (
                                                <span className="text-xs text-gray-600">Limitation #{overlay.related_limitation_id}</span>
                                            )}
                                            {!overlay.trigger_monitoring_cycle_id &&
                                                !overlay.trigger_monitoring_result_id &&
                                                !overlay.related_recommendation_id &&
                                                !overlay.related_limitation_id && (
                                                    <span className="text-xs text-gray-400">None</span>
                                                )}
                                        </div>
                                    </td>
                                    <td className="px-4 py-4 text-sm text-gray-900">
                                        {canEdit ? (
                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={() => openEditModal(overlay)}
                                                    className="text-blue-600 hover:text-blue-800 text-xs"
                                                >
                                                    Edit
                                                </button>
                                                {!overlay.is_retired && (
                                                    <button
                                                        onClick={() => openRetireModal(overlay)}
                                                        className="text-red-600 hover:text-red-800 text-xs"
                                                    >
                                                        Retire
                                                    </button>
                                                )}
                                            </div>
                                        ) : (
                                            <span className="text-xs text-gray-400">-</span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {showCreateModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-lg w-full max-w-2xl p-6 max-h-[90vh] overflow-y-auto">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-semibold">Add Overlay / Judgement</h3>
                            <button onClick={() => { setShowCreateModal(false); resetCreateForm(); }} className="text-gray-500 hover:text-gray-700">x</button>
                        </div>

                        {createError && (
                            <div className="mb-4 p-3 bg-red-100 text-red-800 rounded">
                                {createError}
                            </div>
                        )}

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Kind</label>
                                <select
                                    value={createForm.overlay_kind}
                                    onChange={(e) => setCreateForm({ ...createForm, overlay_kind: e.target.value as OverlayKind })}
                                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                >
                                    {overlayKindOptions.map((opt) => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="flex items-center gap-2 mt-6">
                                <input
                                    type="checkbox"
                                    checked={createForm.is_underperformance_related}
                                    onChange={(e) => setCreateForm({ ...createForm, is_underperformance_related: e.target.checked })}
                                    className="rounded border-gray-300"
                                />
                                <span className="text-sm text-gray-700">Underperformance-related</span>
                            </div>
                            <div className="md:col-span-2">
                                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                                <textarea
                                    value={createForm.description}
                                    onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                    rows={3}
                                />
                            </div>
                            <div className="md:col-span-2">
                                <label className="block text-sm font-medium text-gray-700 mb-1">Rationale</label>
                                <textarea
                                    value={createForm.rationale}
                                    onChange={(e) => setCreateForm({ ...createForm, rationale: e.target.value })}
                                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                    rows={3}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Effective From</label>
                                <input
                                    type="date"
                                    value={createForm.effective_from}
                                    onChange={(e) => setCreateForm({ ...createForm, effective_from: e.target.value })}
                                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Effective To</label>
                                <input
                                    type="date"
                                    value={createForm.effective_to}
                                    onChange={(e) => setCreateForm({ ...createForm, effective_to: e.target.value })}
                                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Region</label>
                                <select
                                    value={createForm.region_id}
                                    onChange={(e) => setCreateForm({ ...createForm, region_id: e.target.value })}
                                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                >
                                    <option value="">Global</option>
                                    {regions.map((region) => (
                                        <option key={region.region_id} value={region.region_id}>
                                            {region.name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Evidence</label>
                                <input
                                    type="text"
                                    value={createForm.evidence_description}
                                    onChange={(e) => setCreateForm({ ...createForm, evidence_description: e.target.value })}
                                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                    placeholder="Optional evidence description"
                                />
                            </div>
                            <div className="md:col-span-2">
                                <p className="text-xs text-gray-500 mb-2">Optional links for traceability</p>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Monitoring Result ID</label>
                                <input
                                    type="text"
                                    value={createForm.trigger_monitoring_result_id}
                                    onChange={(e) => setCreateForm({ ...createForm, trigger_monitoring_result_id: e.target.value })}
                                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Monitoring Cycle ID</label>
                                <input
                                    type="text"
                                    value={createForm.trigger_monitoring_cycle_id}
                                    onChange={(e) => setCreateForm({ ...createForm, trigger_monitoring_cycle_id: e.target.value })}
                                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Recommendation ID</label>
                                <input
                                    type="text"
                                    value={createForm.related_recommendation_id}
                                    onChange={(e) => setCreateForm({ ...createForm, related_recommendation_id: e.target.value })}
                                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Limitation ID</label>
                                <input
                                    type="text"
                                    value={createForm.related_limitation_id}
                                    onChange={(e) => setCreateForm({ ...createForm, related_limitation_id: e.target.value })}
                                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                />
                            </div>
                        </div>

                        <div className="flex justify-end gap-3 mt-6">
                            <button
                                onClick={() => { setShowCreateModal(false); resetCreateForm(); }}
                                className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleCreate}
                                className="px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700"
                            >
                                Save Overlay
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {showEditModal && selectedOverlay && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-lg w-full max-w-lg p-6">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-semibold">Edit Evidence &amp; Links</h3>
                            <button onClick={() => setShowEditModal(false)} className="text-gray-500 hover:text-gray-700">x</button>
                        </div>

                        {editError && (
                            <div className="mb-4 p-3 bg-red-100 text-red-800 rounded">
                                {editError}
                            </div>
                        )}

                        <div className="grid grid-cols-1 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Evidence</label>
                                <input
                                    type="text"
                                    value={editForm.evidence_description}
                                    onChange={(e) => setEditForm({ ...editForm, evidence_description: e.target.value })}
                                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Monitoring Result ID</label>
                                <input
                                    type="text"
                                    value={editForm.trigger_monitoring_result_id}
                                    onChange={(e) => setEditForm({ ...editForm, trigger_monitoring_result_id: e.target.value })}
                                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Monitoring Cycle ID</label>
                                <input
                                    type="text"
                                    value={editForm.trigger_monitoring_cycle_id}
                                    onChange={(e) => setEditForm({ ...editForm, trigger_monitoring_cycle_id: e.target.value })}
                                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Recommendation ID</label>
                                <input
                                    type="text"
                                    value={editForm.related_recommendation_id}
                                    onChange={(e) => setEditForm({ ...editForm, related_recommendation_id: e.target.value })}
                                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Limitation ID</label>
                                <input
                                    type="text"
                                    value={editForm.related_limitation_id}
                                    onChange={(e) => setEditForm({ ...editForm, related_limitation_id: e.target.value })}
                                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                                />
                            </div>
                        </div>

                        <div className="flex justify-end gap-3 mt-6">
                            <button
                                onClick={() => setShowEditModal(false)}
                                className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleEdit}
                                className="px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700"
                            >
                                Save Changes
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {showRetireModal && selectedOverlay && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-lg w-full max-w-md p-6">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-semibold">Retire Overlay</h3>
                            <button onClick={() => setShowRetireModal(false)} className="text-gray-500 hover:text-gray-700">x</button>
                        </div>

                        {retireError && (
                            <div className="mb-4 p-3 bg-red-100 text-red-800 rounded">
                                {retireError}
                            </div>
                        )}

                        <label className="block text-sm font-medium text-gray-700 mb-1">Retirement Reason</label>
                        <textarea
                            value={retirementReason}
                            onChange={(e) => setRetirementReason(e.target.value)}
                            className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                            rows={3}
                        />

                        <div className="flex justify-end gap-3 mt-6">
                            <button
                                onClick={() => setShowRetireModal(false)}
                                className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded hover:bg-gray-200"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleRetire}
                                className="px-4 py-2 text-sm text-white bg-red-600 rounded hover:bg-red-700"
                            >
                                Retire Overlay
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ModelOverlaysTab;
