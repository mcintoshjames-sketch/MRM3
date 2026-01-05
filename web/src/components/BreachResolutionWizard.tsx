import React, { useState, useEffect } from 'react';

// Types
export interface BreachItem {
    result_id: number;
    metric_name: string;
    model_name: string;
    numeric_value: number | null;
}

export interface BreachResolution {
    result_id: number;
    narrative: string;
}

export interface BreachResolutionWizardProps {
    breaches: BreachItem[];
    onComplete: (resolutions: BreachResolution[]) => Promise<void>;
    onCancel: () => void;
    isLoading?: boolean;
}

const BreachResolutionWizard: React.FC<BreachResolutionWizardProps> = ({
    breaches,
    onComplete,
    onCancel,
    isLoading = false,
}) => {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [resolutions, setResolutions] = useState<Record<number, string>>({});
    const [error, setError] = useState<string | null>(null);

    // Initialize resolutions with empty strings
    useEffect(() => {
        const initial: Record<number, string> = {};
        breaches.forEach(b => {
            initial[b.result_id] = '';
        });
        setResolutions(initial);
    }, [breaches]);

    const currentBreach = breaches[currentIndex];
    const progress = ((currentIndex + 1) / breaches.length) * 100;

    const allResolved = Object.values(resolutions).every(n => n.trim().length > 0);
    const currentResolved = resolutions[currentBreach?.result_id]?.trim().length > 0;

    const handleNarrativeChange = (value: string) => {
        setResolutions(prev => ({
            ...prev,
            [currentBreach.result_id]: value
        }));
        setError(null);
    };

    const handleNext = () => {
        if (!currentResolved) {
            setError('Please provide a justification narrative for this breach');
            return;
        }
        if (currentIndex < breaches.length - 1) {
            setCurrentIndex(prev => prev + 1);
        }
    };

    const handlePrevious = () => {
        if (currentIndex > 0) {
            setCurrentIndex(prev => prev - 1);
        }
    };

    const handleComplete = async () => {
        if (!allResolved) {
            setError('Please provide narratives for all breaches before completing');
            return;
        }

        const resolutionArray: BreachResolution[] = breaches.map(b => ({
            result_id: b.result_id,
            narrative: resolutions[b.result_id]
        }));

        await onComplete(resolutionArray);
    };

    if (!currentBreach) {
        return null;
    }

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
                {/* Header */}
                <div className="bg-red-600 text-white px-4 py-2">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                            <h2 className="text-lg font-semibold">Breach Resolution Required</h2>
                        </div>
                        <button
                            onClick={onCancel}
                            className="text-white/80 hover:text-white"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                    {/* Progress bar */}
                    <div className="mt-4">
                        <div className="flex justify-between text-sm mb-1">
                            <span>Breach {currentIndex + 1} of {breaches.length}</span>
                            <span>{Math.round(progress)}% Complete</span>
                        </div>
                        <div className="w-full bg-red-800 rounded-full h-2">
                            <div
                                className="bg-white rounded-full h-2 transition-all"
                                style={{ width: `${progress}%` }}
                            />
                        </div>
                    </div>
                </div>

                {/* Content */}
                <div className="p-6">
                    {/* Breach Info Card */}
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                        <div className="flex items-start gap-4">
                            <div className="flex-shrink-0 w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                                <span className="text-2xl font-bold text-red-600">!</span>
                            </div>
                            <div className="flex-1">
                                <h3 className="font-semibold text-red-800">{currentBreach.metric_name}</h3>
                                <p className="text-sm text-red-600 mt-1">
                                    {currentBreach.model_name !== 'Plan-level' && (
                                        <span className="font-medium">Model: </span>
                                    )}
                                    {currentBreach.model_name}
                                </p>
                                {currentBreach.numeric_value !== null && (
                                    <p className="text-sm text-red-700 mt-2">
                                        <span className="font-medium">Recorded Value: </span>
                                        <span className="font-mono bg-red-100 px-2 py-0.5 rounded">
                                            {currentBreach.numeric_value}
                                        </span>
                                    </p>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Narrative Input */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Breach Justification Narrative <span className="text-red-600">*</span>
                        </label>
                        <p className="text-sm text-gray-500 mb-3">
                            Provide an explanation for this breach, including root cause analysis,
                            remediation actions taken or planned, and any mitigating factors.
                        </p>
                        <textarea
                            value={resolutions[currentBreach.result_id] || ''}
                            onChange={(e) => handleNarrativeChange(e.target.value)}
                            rows={5}
                            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 ${
                                error ? 'border-red-500' : 'border-gray-300'
                            }`}
                            placeholder="Enter justification for this breach..."
                            disabled={isLoading}
                        />
                        {error && (
                            <p className="mt-2 text-sm text-red-600">{error}</p>
                        )}
                        <p className="mt-2 text-sm text-gray-500">
                            {resolutions[currentBreach.result_id]?.length || 0} characters
                        </p>
                    </div>

                    {/* Quick navigation dots */}
                    {breaches.length > 1 && (
                        <div className="flex justify-center gap-2 mt-6">
                            {breaches.map((_, idx) => (
                                <button
                                    key={idx}
                                    onClick={() => setCurrentIndex(idx)}
                                    className={`w-3 h-3 rounded-full transition-all ${
                                        idx === currentIndex
                                            ? 'bg-red-600 scale-110'
                                            : resolutions[breaches[idx].result_id]?.trim().length > 0
                                                ? 'bg-green-500'
                                                : 'bg-gray-300 hover:bg-gray-400'
                                    }`}
                                    title={`Breach ${idx + 1}: ${breaches[idx].metric_name}`}
                                />
                            ))}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="bg-gray-50 px-4 py-2 flex justify-between items-center border-t">
                    <button
                        onClick={handlePrevious}
                        disabled={currentIndex === 0 || isLoading}
                        className="px-4 py-2 text-gray-600 hover:text-gray-800 disabled:text-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                        Previous
                    </button>

                    <div className="flex items-center gap-3">
                        <button
                            onClick={onCancel}
                            disabled={isLoading}
                            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 disabled:opacity-50"
                        >
                            Cancel
                        </button>

                        {currentIndex < breaches.length - 1 ? (
                            <button
                                onClick={handleNext}
                                disabled={isLoading}
                                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 flex items-center gap-2"
                            >
                                Next
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                </svg>
                            </button>
                        ) : (
                            <button
                                onClick={handleComplete}
                                disabled={!allResolved || isLoading}
                                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                                {isLoading ? (
                                    <>
                                        <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                        </svg>
                                        Saving...
                                    </>
                                ) : (
                                    <>
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                        </svg>
                                        Complete & Request Approval
                                    </>
                                )}
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default BreachResolutionWizard;
