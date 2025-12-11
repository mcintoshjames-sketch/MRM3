/**
 * KPIDefinitionModal - displays metric definition and calculation details.
 */
import React from 'react';
import { KPIMetric } from '../api/kpiReport';

interface KPIDefinitionModalProps {
    metric: KPIMetric | null;
    isOpen: boolean;
    onClose: () => void;
}

const KPIDefinitionModal: React.FC<KPIDefinitionModalProps> = ({ metric, isOpen, onClose }) => {
    if (!isOpen || !metric) {
        return null;
    }

    return (
        <div className="fixed inset-0 z-50 overflow-y-auto">
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="flex min-h-full items-center justify-center p-4">
                <div className="relative bg-white rounded-lg shadow-xl max-w-lg w-full">
                    {/* Header */}
                    <div className="flex items-start justify-between p-4 border-b border-gray-200">
                        <div className="flex items-center gap-3">
                            <span className="inline-flex items-center px-2.5 py-1 rounded text-sm font-medium bg-gray-100 text-gray-800">
                                {metric.metric_id}
                            </span>
                            {metric.is_kri && (
                                <span className="inline-flex items-center px-2.5 py-1 rounded text-sm font-medium bg-red-100 text-red-800">
                                    Key Risk Indicator
                                </span>
                            )}
                        </div>
                        <button
                            onClick={onClose}
                            className="text-gray-400 hover:text-gray-500 focus:outline-none"
                        >
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M6 18L18 6M6 6l12 12"
                                />
                            </svg>
                        </button>
                    </div>

                    {/* Content */}
                    <div className="p-4 space-y-4">
                        {/* Metric Name */}
                        <div>
                            <h3 className="text-lg font-semibold text-gray-900">
                                {metric.metric_name}
                            </h3>
                            <p className="text-sm text-gray-500 mt-1">
                                Category: {metric.category}
                            </p>
                        </div>

                        {/* Definition */}
                        <div>
                            <h4 className="text-sm font-medium text-gray-700 mb-1">Definition</h4>
                            <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded">
                                {metric.definition}
                            </p>
                        </div>

                        {/* Calculation */}
                        <div>
                            <h4 className="text-sm font-medium text-gray-700 mb-1">Calculation</h4>
                            <p className="text-sm text-gray-600 bg-blue-50 p-3 rounded font-mono">
                                {metric.calculation}
                            </p>
                        </div>

                        {/* Metric Type */}
                        <div className="flex items-center gap-4 text-sm">
                            <div>
                                <span className="text-gray-500">Type:</span>{' '}
                                <span className="font-medium text-gray-700 capitalize">
                                    {metric.metric_type}
                                </span>
                            </div>
                            {metric.is_kri && (
                                <div className="text-red-600">
                                    <span className="font-medium">This is a Key Risk Indicator (KRI)</span>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="flex justify-end p-4 border-t border-gray-200">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 font-medium text-sm"
                        >
                            Close
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default KPIDefinitionModal;
