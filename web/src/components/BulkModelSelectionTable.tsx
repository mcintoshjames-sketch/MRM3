import { Link } from 'react-router-dom';
import { BulkAttestationModel } from '../hooks/useBulkAttestation';

interface Props {
    models: BulkAttestationModel[];
    selectedModelIds: Set<number>;
    onToggleModel: (modelId: number) => void;
    onSelectAll: () => void;
    onDeselectAll: () => void;
    disabled?: boolean;
}

export default function BulkModelSelectionTable({
    models,
    selectedModelIds,
    onToggleModel,
    onSelectAll,
    onDeselectAll,
    disabled = false
}: Props) {
    // Only show PENDING models for selection
    const pendingModels = models.filter(m => m.attestation_status === 'PENDING');
    const allSelected = pendingModels.length > 0 && pendingModels.every(m => selectedModelIds.has(m.model_id));
    const noneSelected = pendingModels.every(m => !selectedModelIds.has(m.model_id));

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '-';
        return dateStr.split('T')[0];
    };

    const getStatusBadge = (status: string, isExcluded: boolean) => {
        if (isExcluded) {
            return (
                <span className="px-2 py-1 text-xs font-medium rounded-full bg-orange-100 text-orange-800">
                    Excluded
                </span>
            );
        }

        switch (status) {
            case 'SUBMITTED':
                return (
                    <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                        Submitted
                    </span>
                );
            case 'ACCEPTED':
                return (
                    <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                        Accepted
                    </span>
                );
            case 'REJECTED':
                return (
                    <span className="px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800">
                        Rejected
                    </span>
                );
            default:
                return (
                    <span className="px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800">
                        Pending
                    </span>
                );
        }
    };

    if (pendingModels.length === 0) {
        return (
            <div className="bg-gray-50 rounded-lg p-6 text-center text-gray-600">
                No pending models available for bulk attestation.
            </div>
        );
    }

    return (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
            {/* Header with Select All/None controls */}
            <div className="bg-gray-50 px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <button
                        type="button"
                        onClick={onSelectAll}
                        disabled={disabled || allSelected}
                        className={`text-sm font-medium ${
                            disabled || allSelected
                                ? 'text-gray-400 cursor-not-allowed'
                                : 'text-blue-600 hover:text-blue-800'
                        }`}
                    >
                        Select All ({pendingModels.length})
                    </button>
                    <span className="text-gray-300">|</span>
                    <button
                        type="button"
                        onClick={onDeselectAll}
                        disabled={disabled || noneSelected}
                        className={`text-sm font-medium ${
                            disabled || noneSelected
                                ? 'text-gray-400 cursor-not-allowed'
                                : 'text-blue-600 hover:text-blue-800'
                        }`}
                    >
                        Deselect All
                    </button>
                </div>
                <div className="text-sm text-gray-600">
                    {selectedModelIds.size} of {pendingModels.length} selected
                </div>
            </div>

            {/* Table */}
            <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                    <tr>
                        <th className="w-12 px-4 py-3">
                            <span className="sr-only">Select</span>
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            Model Name
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            Risk Tier
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            Status
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            Last Attested
                        </th>
                    </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                    {pendingModels.map((model) => {
                        const isSelected = selectedModelIds.has(model.model_id);
                        const isExcludedFromBulk = !isSelected;

                        return (
                            <tr
                                key={model.model_id}
                                className={`hover:bg-gray-50 cursor-pointer ${
                                    isExcludedFromBulk ? 'bg-orange-50' : ''
                                }`}
                                onClick={() => !disabled && onToggleModel(model.model_id)}
                            >
                                <td className="px-4 py-3">
                                    <input
                                        type="checkbox"
                                        checked={isSelected}
                                        onChange={() => onToggleModel(model.model_id)}
                                        disabled={disabled}
                                        className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                        onClick={(e) => e.stopPropagation()}
                                    />
                                </td>
                                <td className="px-4 py-3">
                                    <Link
                                        to={`/models/${model.model_id}`}
                                        className="text-blue-600 hover:text-blue-800 font-medium"
                                        onClick={(e) => e.stopPropagation()}
                                    >
                                        {model.model_name}
                                    </Link>
                                </td>
                                <td className="px-4 py-3 text-sm text-gray-600">
                                    {model.risk_tier_label || model.risk_tier_code || '-'}
                                </td>
                                <td className="px-4 py-3">
                                    {getStatusBadge(model.attestation_status, isExcludedFromBulk)}
                                </td>
                                <td className="px-4 py-3 text-sm text-gray-600">
                                    {formatDate(model.last_attested_date)}
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>

            {/* Summary Footer */}
            <div className="bg-gray-50 px-4 py-3 border-t border-gray-200">
                <div className="flex items-center gap-6 text-sm">
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 bg-blue-100 border border-blue-300 rounded"></div>
                        <span className="text-gray-600">
                            {selectedModelIds.size} selected for bulk attestation
                        </span>
                    </div>
                    {pendingModels.length - selectedModelIds.size > 0 && (
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 bg-orange-100 border border-orange-300 rounded"></div>
                            <span className="text-gray-600">
                                {pendingModels.length - selectedModelIds.size} excluded (require individual attestation)
                            </span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
