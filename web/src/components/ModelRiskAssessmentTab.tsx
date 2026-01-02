/**
 * Model Risk Assessment Tab Component
 *
 * Displays and manages risk assessments for a model including:
 * - Qualitative assessment (4 weighted factors)
 * - Quantitative assessment
 * - Inherent risk matrix
 * - Override controls
 * - Final tier calculation
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
    listAssessments,
    createAssessment,
    updateAssessment,
    deleteAssessment,
    getAssessmentHistory,
    checkOpenValidationsForModel,
    RiskAssessmentResponse,
    RiskAssessmentHistoryItem,
    FactorRatingInput,
    OpenValidationsCheckResponse,
    RATING_COLORS,
    lookupInherentRisk,
    TIER_LABELS,
    TIER_MAP,
    downloadAssessmentPdf,
} from '../api/riskAssessment';
import { listFactors, FactorResponse } from '../api/qualitativeFactors';
import { useAuth } from '../contexts/AuthContext';
import { canManageModels } from '../utils/roleUtils';

interface Props {
    modelId: number;
    regions?: { region_id: number; code: string; name: string }[];
}

type Rating = 'HIGH' | 'MEDIUM' | 'LOW' | null;
type InherentRating = 'HIGH' | 'MEDIUM' | 'LOW' | 'VERY_LOW' | null;

const RATINGS: ('HIGH' | 'MEDIUM' | 'LOW')[] = ['HIGH', 'MEDIUM', 'LOW'];
const INHERENT_RATINGS: ('HIGH' | 'MEDIUM' | 'LOW' | 'VERY_LOW')[] = ['HIGH', 'MEDIUM', 'LOW', 'VERY_LOW'];

const ModelRiskAssessmentTab: React.FC<Props> = ({ modelId, regions = [] }) => {
    const { user } = useAuth();
    const canManageModelsFlag = canManageModels(user);

    // State
    const [assessments, setAssessments] = useState<RiskAssessmentResponse[]>([]);
    const [factors, setFactors] = useState<FactorResponse[]>([]);
    const [history, setHistory] = useState<RiskAssessmentHistoryItem[]>([]);
    const [showHistory, setShowHistory] = useState(false);
    const [selectedRegionId, setSelectedRegionId] = useState<number | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Form state
    const [factorRatings, setFactorRatings] = useState<Record<number, { rating: Rating; comment: string }>>({});
    const [quantitativeRating, setQuantitativeRating] = useState<Rating>(null);
    const [quantitativeComment, setQuantitativeComment] = useState('');
    const [quantitativeOverride, setQuantitativeOverride] = useState<Rating>(null);
    const [quantitativeOverrideComment, setQuantitativeOverrideComment] = useState('');
    const [qualitativeOverride, setQualitativeOverride] = useState<Rating>(null);
    const [qualitativeOverrideComment, setQualitativeOverrideComment] = useState('');
    const [derivedOverride, setDerivedOverride] = useState<InherentRating>(null);
    const [derivedOverrideComment, setDerivedOverrideComment] = useState('');

    // Risk tier change warning modal state
    const [showTierChangeWarning, setShowTierChangeWarning] = useState(false);
    const [tierChangeImpact, setTierChangeImpact] = useState<OpenValidationsCheckResponse | null>(null);
    const [pendingSaveAction, setPendingSaveAction] = useState<(() => Promise<void>) | null>(null);
    const [showCopyFromGlobalModal, setShowCopyFromGlobalModal] = useState(false);
    const [showRegionChangeWarning, setShowRegionChangeWarning] = useState(false);
    const [pendingRegionId, setPendingRegionId] = useState<number | null | undefined>(undefined);

    // Current assessment for selected region
    const currentAssessment = assessments.find(a =>
        selectedRegionId === null ? a.region === null : a.region?.region_id === selectedRegionId
    );
    const globalAssessment = assessments.find(a => a.region === null);
    const hasFormData = quantitativeRating !== null
        || quantitativeComment.trim() !== ''
        || Object.values(factorRatings).some(f => f.rating !== null || (f.comment ?? '').trim() !== '')
        || quantitativeOverride !== null
        || quantitativeOverrideComment.trim() !== ''
        || qualitativeOverride !== null
        || qualitativeOverrideComment.trim() !== ''
        || derivedOverride !== null
        || derivedOverrideComment.trim() !== '';
    const canCopyFromGlobal = selectedRegionId !== null
        && !currentAssessment
        && globalAssessment?.is_complete === true
        && canManageModelsFlag;
    const formHasUnsavedChanges = (() => {
        const normalize = (value: string | null | undefined) => value ?? '';

        if (currentAssessment) {
            if (quantitativeRating !== currentAssessment.quantitative_rating) return true;
            if (normalize(quantitativeComment) !== normalize(currentAssessment.quantitative_comment)) return true;
            if (quantitativeOverride !== currentAssessment.quantitative_override) return true;
            if (normalize(quantitativeOverrideComment) !== normalize(currentAssessment.quantitative_override_comment)) return true;
            if (qualitativeOverride !== currentAssessment.qualitative_override) return true;
            if (normalize(qualitativeOverrideComment) !== normalize(currentAssessment.qualitative_override_comment)) return true;
            if (derivedOverride !== currentAssessment.derived_risk_tier_override) return true;
            if (normalize(derivedOverrideComment) !== normalize(currentAssessment.derived_risk_tier_override_comment)) return true;

            const factorMap = new Map<number, { rating: Rating | null; comment: string | null }>();
            currentAssessment.qualitative_factors.forEach(factor => {
                factorMap.set(factor.factor_id, { rating: factor.rating, comment: factor.comment });
            });

            for (const factor of factors) {
                const current = factorRatings[factor.factor_id];
                const baseline = factorMap.get(factor.factor_id);
                const currentRating = current?.rating ?? null;
                const currentComment = normalize(current?.comment);
                const baselineRating = baseline?.rating ?? null;
                const baselineComment = normalize(baseline?.comment);
                if (currentRating !== baselineRating || currentComment !== baselineComment) {
                    return true;
                }
            }
            return false;
        }

        if (quantitativeRating !== null) return true;
        if (normalize(quantitativeComment) !== '') return true;
        if (quantitativeOverride !== null) return true;
        if (normalize(quantitativeOverrideComment) !== '') return true;
        if (qualitativeOverride !== null) return true;
        if (normalize(qualitativeOverrideComment) !== '') return true;
        if (derivedOverride !== null) return true;
        if (normalize(derivedOverrideComment) !== '') return true;

        for (const factor of factors) {
            const current = factorRatings[factor.factor_id];
            if (current?.rating !== null && current?.rating !== undefined) return true;
            if (normalize(current?.comment) !== '') return true;
        }
        return false;
    })();

    // Load data
    const loadData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const [assessmentsData, factorsData, historyData] = await Promise.all([
                listAssessments(modelId),
                listFactors(),
                getAssessmentHistory(modelId)
            ]);
            setAssessments(assessmentsData);
            setFactors(factorsData);
            setHistory(historyData);
        } catch (err) {
            setError('Failed to load risk assessment data');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [modelId]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    // Populate form when assessment changes
    useEffect(() => {
        if (currentAssessment) {
            // Populate factor ratings from assessment
            const ratings: Record<number, { rating: Rating; comment: string }> = {};
            currentAssessment.qualitative_factors.forEach(f => {
                ratings[f.factor_id] = {
                    rating: f.rating,
                    comment: f.comment || ''
                };
            });
            setFactorRatings(ratings);
            setQuantitativeRating(currentAssessment.quantitative_rating);
            setQuantitativeComment(currentAssessment.quantitative_comment || '');
            setQuantitativeOverride(currentAssessment.quantitative_override);
            setQuantitativeOverrideComment(currentAssessment.quantitative_override_comment || '');
            setQualitativeOverride(currentAssessment.qualitative_override);
            setQualitativeOverrideComment(currentAssessment.qualitative_override_comment || '');
            setDerivedOverride(currentAssessment.derived_risk_tier_override);
            setDerivedOverrideComment(currentAssessment.derived_risk_tier_override_comment || '');
        } else {
            // Reset form for new assessment
            const ratings: Record<number, { rating: Rating; comment: string }> = {};
            factors.forEach(f => {
                ratings[f.factor_id] = { rating: null, comment: '' };
            });
            setFactorRatings(ratings);
            setQuantitativeRating(null);
            setQuantitativeComment('');
            setQuantitativeOverride(null);
            setQuantitativeOverrideComment('');
            setQualitativeOverride(null);
            setQualitativeOverrideComment('');
            setDerivedOverride(null);
            setDerivedOverrideComment('');
        }
    }, [currentAssessment, factors, selectedRegionId]);

    const handleCopyFromGlobal = () => {
        if (!globalAssessment) return;

        setQuantitativeRating(globalAssessment.quantitative_rating);
        setQuantitativeComment(globalAssessment.quantitative_comment || '');

        const newFactorRatings: Record<number, { rating: Rating; comment: string }> = {};
        factors.forEach(factor => {
            const globalFactorRating = globalAssessment.qualitative_factors?.find(
                fr => fr.factor_id === factor.factor_id
            );
            newFactorRatings[factor.factor_id] = {
                rating: globalFactorRating?.rating ?? null,
                comment: globalFactorRating?.comment || ''
            };
        });
        setFactorRatings(newFactorRatings);

        setQuantitativeOverride(globalAssessment.quantitative_override);
        setQuantitativeOverrideComment(globalAssessment.quantitative_override_comment || '');
        setQualitativeOverride(globalAssessment.qualitative_override);
        setQualitativeOverrideComment(globalAssessment.qualitative_override_comment || '');
        setDerivedOverride(globalAssessment.derived_risk_tier_override);
        setDerivedOverrideComment(globalAssessment.derived_risk_tier_override_comment || '');

        setShowCopyFromGlobalModal(false);
    };

    // Calculate qualitative score
    const calculateQualitativeScore = (): { score: number | null; level: Rating } => {
        const SCORES: Record<string, number> = { HIGH: 3, MEDIUM: 2, LOW: 1 };
        let totalWeightedScore = 0;
        let totalWeight = 0;

        factors.forEach(factor => {
            const rating = factorRatings[factor.factor_id]?.rating;
            if (rating) {
                totalWeightedScore += factor.weight * SCORES[rating];
                totalWeight += factor.weight;
            }
        });

        if (totalWeight === 0) return { score: null, level: null };

        const score = totalWeightedScore / totalWeight;
        let level: Rating = null;
        if (score >= 2.1) level = 'HIGH';
        else if (score >= 1.6) level = 'MEDIUM';
        else level = 'LOW';

        return { score, level };
    };

    // Get effective values
    const { score: qualitativeScore, level: qualitativeLevel } = calculateQualitativeScore();
    const effectiveQualitative = qualitativeOverride || qualitativeLevel;
    const effectiveQuantitative = quantitativeOverride || quantitativeRating;

    // Calculate derived tier
    let derivedTier: InherentRating = null;
    if (effectiveQuantitative && effectiveQualitative) {
        derivedTier = lookupInherentRisk(effectiveQuantitative, effectiveQualitative);
    }
    const effectiveTier = derivedOverride || derivedTier;

    // Perform the actual save operation
    const performSave = async () => {
        setSaving(true);
        setError(null);

        const factorRatingsInput: FactorRatingInput[] = factors.map(f => ({
            factor_id: f.factor_id,
            rating: factorRatings[f.factor_id]?.rating || null,
            comment: factorRatings[f.factor_id]?.comment || undefined
        }));

        try {
            if (currentAssessment) {
                // Update existing
                await updateAssessment(modelId, currentAssessment.assessment_id, {
                    quantitative_rating: quantitativeRating || undefined,
                    quantitative_comment: quantitativeComment || undefined,
                    quantitative_override: quantitativeOverride || undefined,
                    quantitative_override_comment: quantitativeOverrideComment || undefined,
                    qualitative_override: qualitativeOverride || undefined,
                    qualitative_override_comment: qualitativeOverrideComment || undefined,
                    derived_risk_tier_override: derivedOverride || undefined,
                    derived_risk_tier_override_comment: derivedOverrideComment || undefined,
                    factor_ratings: factorRatingsInput,
                });
            } else {
                // Create new
                await createAssessment(modelId, {
                    region_id: selectedRegionId,
                    quantitative_rating: quantitativeRating || undefined,
                    quantitative_comment: quantitativeComment || undefined,
                    quantitative_override: quantitativeOverride || undefined,
                    quantitative_override_comment: quantitativeOverrideComment || undefined,
                    qualitative_override: qualitativeOverride || undefined,
                    qualitative_override_comment: qualitativeOverrideComment || undefined,
                    derived_risk_tier_override: derivedOverride || undefined,
                    derived_risk_tier_override_comment: derivedOverrideComment || undefined,
                    factor_ratings: factorRatingsInput,
                });
            }
            await loadData();
        } catch (err) {
            setError('Failed to save assessment');
            console.error(err);
        } finally {
            setSaving(false);
        }
    };

    // Handle save with tier change warning check
    const handleSave = async () => {
        if (!canManageModelsFlag) return;

        // Validate overrides: must change the value and have justification
        const overrideErrors: string[] = [];

        // Quantitative override validation
        if (quantitativeOverride !== null) {
            if (quantitativeOverride === quantitativeRating) {
                overrideErrors.push('Quantitative Override must differ from the base rating');
            } else if (!quantitativeOverrideComment.trim()) {
                overrideErrors.push('Quantitative Override requires justification');
            }
        }

        // Qualitative override validation
        if (qualitativeOverride !== null) {
            if (qualitativeOverride === qualitativeLevel) {
                overrideErrors.push('Qualitative Override must differ from the calculated level');
            } else if (!qualitativeOverrideComment.trim()) {
                overrideErrors.push('Qualitative Override requires justification');
            }
        }

        // Final tier override validation
        if (derivedOverride !== null) {
            if (derivedOverride === derivedTier) {
                overrideErrors.push('Final Tier Override must differ from the derived tier');
            } else if (!derivedOverrideComment.trim()) {
                overrideErrors.push('Final Tier Override requires justification');
            }
        }

        if (overrideErrors.length > 0) {
            setError(overrideErrors.join('. '));
            return;
        }

        // Check if this is a Global assessment (region_id is null)
        const isGlobalAssessment = selectedRegionId === null;

        // For Global assessments, check with backend if tier change will affect open validations
        // The backend compares the model's current tier with the proposed tier
        if (isGlobalAssessment && effectiveTier) {
            try {
                // Convert effectiveTier (e.g., "MEDIUM") to code format (e.g., "TIER_2")
                const proposedTierCode = TIER_MAP[effectiveTier];
                // Check for open validations that would be affected by a tier change
                const impact = await checkOpenValidationsForModel(modelId, proposedTierCode);

                if (impact.has_open_validations) {
                    // Show warning modal and store the save action
                    setTierChangeImpact(impact);
                    setPendingSaveAction(() => performSave);
                    setShowTierChangeWarning(true);
                    return;
                }
            } catch (err) {
                console.error('Failed to check for open validations:', err);
                // Continue with save even if check fails
            }
        }

        // No tier change or no open validations - proceed with save
        await performSave();
    };

    // Handle confirmation of tier change warning
    const handleConfirmTierChange = async () => {
        setShowTierChangeWarning(false);
        if (pendingSaveAction) {
            await pendingSaveAction();
        }
        setPendingSaveAction(null);
        setTierChangeImpact(null);
    };

    // Handle cancellation of tier change warning
    const handleCancelTierChange = () => {
        setShowTierChangeWarning(false);
        setPendingSaveAction(null);
        setTierChangeImpact(null);
    };

    const handleRegionChange = (nextRegionId: number | null) => {
        if (nextRegionId === selectedRegionId) return;
        if (formHasUnsavedChanges) {
            setPendingRegionId(nextRegionId);
            setShowRegionChangeWarning(true);
            return;
        }
        setSelectedRegionId(nextRegionId);
    };

    const handleConfirmRegionChange = () => {
        setShowRegionChangeWarning(false);
        if (pendingRegionId !== undefined) {
            setSelectedRegionId(pendingRegionId);
        }
        setPendingRegionId(undefined);
    };

    const handleCancelRegionChange = () => {
        setShowRegionChangeWarning(false);
        setPendingRegionId(undefined);
    };

    // Handle delete
    const handleDelete = async () => {
        if (!canManageModelsFlag || !currentAssessment) return;
        if (!window.confirm('Are you sure you want to delete this assessment?')) return;

        setSaving(true);
        setError(null);
        try {
            await deleteAssessment(modelId, currentAssessment.assessment_id);
            await loadData();
        } catch (err) {
            setError('Failed to delete assessment');
            console.error(err);
        } finally {
            setSaving(false);
        }
    };

    // Render rating badge
    const RatingBadge: React.FC<{ rating: string | null }> = ({ rating }) => {
        if (!rating) return <span className="text-gray-400 text-sm">Not set</span>;
        const colors = RATING_COLORS[rating] || { bg: 'bg-gray-100', text: 'text-gray-800' };
        return (
            <span className={`px-3 py-1.5 text-sm font-semibold rounded-md ${colors.bg} ${colors.text}`}>
                {rating}
            </span>
        );
    };

    // Render select dropdown
    const RatingSelect: React.FC<{
        value: Rating;
        onChange: (v: Rating) => void;
        disabled?: boolean;
        includeEmpty?: boolean;
    }> = ({ value, onChange, disabled, includeEmpty = true }) => (
        <select
            value={value || ''}
            onChange={e => onChange(e.target.value as Rating || null)}
            disabled={disabled}
            className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm disabled:bg-gray-100"
        >
            {includeEmpty && <option value="">-- Select --</option>}
            {RATINGS.map(r => (
                <option key={r} value={r}>{r}</option>
            ))}
        </select>
    );

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Risk Tier Change Warning Modal */}
            {showTierChangeWarning && tierChangeImpact && (
                <div className="fixed inset-0 z-50 overflow-y-auto">
                    <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
                        <div className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75" onClick={handleCancelTierChange}></div>
                        <div className="inline-block overflow-hidden text-left align-bottom transition-all transform bg-white rounded-lg shadow-xl sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
                            <div className="px-4 pt-5 pb-4 bg-white sm:p-6 sm:pb-4">
                                <div className="sm:flex sm:items-start">
                                    <div className="flex items-center justify-center flex-shrink-0 w-12 h-12 mx-auto bg-yellow-100 rounded-full sm:mx-0 sm:h-10 sm:w-10">
                                        <svg className="w-6 h-6 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                        </svg>
                                    </div>
                                    <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                                        <h3 className="text-lg font-medium leading-6 text-gray-900">
                                            Risk Tier Change Warning
                                        </h3>
                                        <div className="mt-2">
                                            <p className="text-sm text-gray-500 mb-3">
                                                {tierChangeImpact.warning_message}
                                            </p>
                                            <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3 mb-3">
                                                <p className="text-sm font-medium text-yellow-800 mb-2">
                                                    Affected Validation Requests:
                                                </p>
                                                <ul className="text-sm text-yellow-700 space-y-1">
                                                    {tierChangeImpact.open_validations.map(v => (
                                                        <li key={v.request_id} className="flex items-center">
                                                            <span className="w-2 h-2 bg-yellow-400 rounded-full mr-2"></span>
                                                            Request #{v.request_id} - {v.validation_type} ({v.current_status})
                                                            {v.primary_validator && <span className="ml-1 text-gray-500">- {v.primary_validator}</span>}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                            <p className="text-sm text-gray-500">
                                                Are you sure you want to continue?
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div className="px-4 py-3 bg-gray-50 sm:px-6 sm:flex sm:flex-row-reverse">
                                <button
                                    type="button"
                                    onClick={handleConfirmTierChange}
                                    className="inline-flex justify-center w-full px-4 py-2 text-base font-medium text-white bg-yellow-600 border border-transparent rounded-md shadow-sm hover:bg-yellow-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500 sm:ml-3 sm:w-auto sm:text-sm"
                                >
                                    Yes, Proceed with Change
                                </button>
                                <button
                                    type="button"
                                    onClick={handleCancelTierChange}
                                    className="inline-flex justify-center w-full px-4 py-2 mt-3 text-base font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {showCopyFromGlobalModal && (
                <div className="fixed inset-0 z-50 overflow-y-auto">
                    <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
                        <div className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75" onClick={() => setShowCopyFromGlobalModal(false)}></div>
                        <div className="inline-block overflow-hidden text-left align-bottom transition-all transform bg-white rounded-lg shadow-xl sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
                            <div className="px-4 pt-5 pb-4 bg-white sm:p-6 sm:pb-4">
                                <div className="sm:flex sm:items-start">
                                    <div className="flex items-center justify-center flex-shrink-0 w-12 h-12 mx-auto bg-blue-100 rounded-full sm:mx-0 sm:h-10 sm:w-10">
                                        <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7h16M4 12h16M4 17h16" />
                                        </svg>
                                    </div>
                                    <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                                        <h3 className="text-lg font-medium leading-6 text-gray-900">
                                            Copy from Global Assessment?
                                        </h3>
                                        <div className="mt-2">
                                            <p className="text-sm text-gray-500">
                                                This will overwrite your current regional assessment data with values from the
                                                Global assessment. Any unsaved changes will be lost.
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div className="px-4 py-3 bg-gray-50 sm:px-6 sm:flex sm:flex-row-reverse">
                                <button
                                    type="button"
                                    onClick={handleCopyFromGlobal}
                                    className="inline-flex justify-center w-full px-4 py-2 text-base font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm"
                                >
                                    Copy Data
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setShowCopyFromGlobalModal(false)}
                                    className="inline-flex justify-center w-full px-4 py-2 mt-3 text-base font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {showRegionChangeWarning && (
                <div className="fixed inset-0 z-50 overflow-y-auto">
                    <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
                        <div className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75" onClick={handleCancelRegionChange}></div>
                        <div className="inline-block overflow-hidden text-left align-bottom transition-all transform bg-white rounded-lg shadow-xl sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
                            <div className="px-4 pt-5 pb-4 bg-white sm:p-6 sm:pb-4">
                                <div className="sm:flex sm:items-start">
                                    <div className="flex items-center justify-center flex-shrink-0 w-12 h-12 mx-auto bg-yellow-100 rounded-full sm:mx-0 sm:h-10 sm:w-10">
                                        <svg className="w-6 h-6 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                        </svg>
                                    </div>
                                    <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                                        <h3 className="text-lg font-medium leading-6 text-gray-900">
                                            Discard unsaved changes?
                                        </h3>
                                        <div className="mt-2">
                                            <p className="text-sm text-gray-500">
                                                You have unsaved changes for this region. Switching regions will discard them.
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div className="px-4 py-3 bg-gray-50 sm:px-6 sm:flex sm:flex-row-reverse">
                                <button
                                    type="button"
                                    onClick={handleConfirmRegionChange}
                                    className="inline-flex justify-center w-full px-4 py-2 text-base font-medium text-white bg-yellow-600 border border-transparent rounded-md shadow-sm hover:bg-yellow-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500 sm:ml-3 sm:w-auto sm:text-sm"
                                >
                                    Discard and Switch
                                </button>
                                <button
                                    type="button"
                                    onClick={handleCancelRegionChange}
                                    className="inline-flex justify-center w-full px-4 py-2 mt-3 text-base font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                                >
                                    Stay Here
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h3 className="text-lg font-medium text-gray-900">Risk Assessment</h3>
                    <p className="text-sm text-gray-500">
                        Calculate inherent model risk based on qualitative and quantitative factors
                    </p>
                </div>
                <div className="flex items-center space-x-4">
                    {currentAssessment && (
                        <button
                            onClick={() => downloadAssessmentPdf(modelId, currentAssessment.assessment_id)}
                            className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                        >
                            <svg className="-ml-0.5 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            Export PDF
                        </button>
                    )}
                    <label className="text-sm font-medium text-gray-700">Region:</label>
                    <select
                        value={selectedRegionId === null ? '' : selectedRegionId}
                        onChange={e => handleRegionChange(e.target.value ? parseInt(e.target.value) : null)}
                        className="block w-48 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    >
                        <option value="">Global</option>
                        {regions.map(r => (
                            <option key={r.region_id} value={r.region_id}>{r.name}</option>
                        ))}
                    </select>
                    {canCopyFromGlobal && (
                        <button
                            onClick={() => hasFormData ? setShowCopyFromGlobalModal(true) : handleCopyFromGlobal()}
                            className="px-3 py-2 text-sm font-medium text-blue-700 bg-blue-100 border border-blue-200 rounded-md hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                        >
                            Copy from Global
                        </button>
                    )}
                </div>
            </div>

            {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                    {error}
                </div>
            )}

            {/* Quantitative Assessment Section */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h4 className="text-md font-medium text-gray-900 mb-4">Quantitative Assessment</h4>

                <div className="grid grid-cols-2 gap-6">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Rating</label>
                        <RatingSelect
                            value={quantitativeRating}
                            onChange={setQuantitativeRating}
                            disabled={!canManageModelsFlag}
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Comment</label>
                        <textarea
                            value={quantitativeComment}
                            onChange={e => setQuantitativeComment(e.target.value)}
                            disabled={!canManageModelsFlag}
                            rows={2}
                            className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm disabled:bg-gray-100 resize-y"
                            placeholder="Optional comment"
                        />
                    </div>
                </div>

                <div className="mt-4 pt-4 border-t border-gray-200">
                    <div className="flex items-center justify-between mb-3">
                        <div>
                            <span className="text-sm text-gray-500">Rating: </span>
                            <RatingBadge rating={quantitativeRating} />
                        </div>
                        <div>
                            <span className="text-sm text-gray-500">Effective: </span>
                            <RatingBadge rating={effectiveQuantitative} />
                        </div>
                    </div>

                    {/* Override Panel */}
                    <div className={`rounded-lg border-2 p-3 transition-colors ${quantitativeOverride !== null
                            ? 'bg-amber-50 border-amber-300'
                            : 'bg-gray-50 border-dashed border-gray-300 hover:border-amber-300 hover:bg-amber-50/50'
                        }`}>
                        <div className="flex items-center gap-4">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={quantitativeOverride !== null}
                                    onChange={e => {
                                        if (e.target.checked) {
                                            setQuantitativeOverride(quantitativeRating || 'HIGH');
                                        } else {
                                            setQuantitativeOverride(null);
                                            setQuantitativeOverrideComment('');
                                        }
                                    }}
                                    disabled={!canManageModelsFlag}
                                    className="w-4 h-4 rounded border-gray-300 text-amber-600 focus:ring-amber-500"
                                />
                                <span className={`text-sm font-medium ${quantitativeOverride !== null ? 'text-amber-800' : 'text-gray-600'}`}>
                                    Manual Override
                                </span>
                            </label>
                            {quantitativeOverride !== null && (
                                <>
                                    <div className="w-28">
                                        <RatingSelect
                                            value={quantitativeOverride}
                                            onChange={setQuantitativeOverride}
                                            disabled={!canManageModelsFlag}
                                            includeEmpty={false}
                                        />
                                    </div>
                                    <textarea
                                        value={quantitativeOverrideComment}
                                        onChange={e => setQuantitativeOverrideComment(e.target.value)}
                                        disabled={!canManageModelsFlag}
                                        rows={1}
                                        className="flex-1 px-3 py-2 border border-amber-300 rounded-md shadow-sm focus:outline-none focus:ring-amber-500 focus:border-amber-500 sm:text-sm bg-white resize-y"
                                        placeholder="Justification required"
                                    />
                                </>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Qualitative Assessment Section */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h4 className="text-md font-medium text-gray-900 mb-4">Qualitative Assessment</h4>

                <table className="min-w-full divide-y divide-gray-200 table-fixed">
                    <thead>
                        <tr>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase" style={{ width: '330px', minWidth: '330px', maxWidth: '330px' }}>Factor</th>
                            <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase" style={{ width: '60px' }}>Weight</th>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase" style={{ width: '120px' }}>Rating</th>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Comment</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                        {factors.map(factor => (
                            <tr key={factor.factor_id}>
                                <td className="px-4 py-3" style={{ width: '330px', minWidth: '330px', maxWidth: '330px' }}>
                                    <div className="font-medium text-gray-900">{factor.name}</div>
                                    {factor.description && (
                                        <div className="text-xs text-gray-500 whitespace-normal">{factor.description}</div>
                                    )}
                                </td>
                                <td className="px-4 py-3 text-center text-sm text-gray-500" style={{ width: '60px' }}>
                                    {(factor.weight * 100).toFixed(0)}%
                                </td>
                                <td className="px-4 py-3">
                                    <RatingSelect
                                        value={factorRatings[factor.factor_id]?.rating || null}
                                        onChange={v => setFactorRatings(prev => ({
                                            ...prev,
                                            [factor.factor_id]: { ...prev[factor.factor_id], rating: v }
                                        }))}
                                        disabled={!canManageModelsFlag}
                                    />
                                </td>
                                <td className="px-4 py-3">
                                    <textarea
                                        value={factorRatings[factor.factor_id]?.comment || ''}
                                        onChange={e => setFactorRatings(prev => ({
                                            ...prev,
                                            [factor.factor_id]: { ...prev[factor.factor_id], comment: e.target.value }
                                        }))}
                                        disabled={!canManageModelsFlag}
                                        rows={1}
                                        className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm disabled:bg-gray-100 resize-y"
                                        placeholder="Optional comment"
                                    />
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>

                <div className="mt-4 pt-4 border-t border-gray-200">
                    <div className="flex items-center justify-between mb-3">
                        <div>
                            <span className="text-sm text-gray-500">Calculated Score: </span>
                            <span className="font-medium">
                                {qualitativeScore !== null ? qualitativeScore.toFixed(2) : '--'}
                            </span>
                            <span className="mx-2">→</span>
                            <RatingBadge rating={qualitativeLevel} />
                        </div>
                        <div>
                            <span className="text-sm text-gray-500">Effective: </span>
                            <RatingBadge rating={effectiveQualitative} />
                        </div>
                    </div>

                    {/* Override Panel */}
                    <div className={`rounded-lg border-2 p-3 transition-colors ${qualitativeOverride !== null
                            ? 'bg-amber-50 border-amber-300'
                            : 'bg-gray-50 border-dashed border-gray-300 hover:border-amber-300 hover:bg-amber-50/50'
                        }`}>
                        <div className="flex items-center gap-4">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={qualitativeOverride !== null}
                                    onChange={e => {
                                        if (e.target.checked) {
                                            setQualitativeOverride(qualitativeLevel || 'HIGH');
                                        } else {
                                            setQualitativeOverride(null);
                                            setQualitativeOverrideComment('');
                                        }
                                    }}
                                    disabled={!canManageModelsFlag}
                                    className="w-4 h-4 rounded border-gray-300 text-amber-600 focus:ring-amber-500"
                                />
                                <span className={`text-sm font-medium ${qualitativeOverride !== null ? 'text-amber-800' : 'text-gray-600'}`}>
                                    Manual Override
                                </span>
                            </label>
                            {qualitativeOverride !== null && (
                                <>
                                    <div className="w-28">
                                        <RatingSelect
                                            value={qualitativeOverride}
                                            onChange={setQualitativeOverride}
                                            disabled={!canManageModelsFlag}
                                            includeEmpty={false}
                                        />
                                    </div>
                                    <textarea
                                        value={qualitativeOverrideComment}
                                        onChange={e => setQualitativeOverrideComment(e.target.value)}
                                        disabled={!canManageModelsFlag}
                                        rows={1}
                                        className="flex-1 px-3 py-2 border border-amber-300 rounded-md shadow-sm focus:outline-none focus:ring-amber-500 focus:border-amber-500 sm:text-sm bg-white resize-y"
                                        placeholder="Justification required"
                                    />
                                </>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Inherent Risk Matrix */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h4 className="text-md font-medium text-gray-900 mb-4">Inherent Risk Matrix</h4>

                <div className="overflow-x-auto">
                    <table className="border-collapse">
                        <thead>
                            <tr>
                                <th className="border p-2 bg-gray-50"></th>
                                <th className="border p-2 bg-gray-50 text-center text-sm font-medium">Qual: HIGH</th>
                                <th className="border p-2 bg-gray-50 text-center text-sm font-medium">Qual: MEDIUM</th>
                                <th className="border p-2 bg-gray-50 text-center text-sm font-medium">Qual: LOW</th>
                            </tr>
                        </thead>
                        <tbody>
                            {(['HIGH', 'MEDIUM', 'LOW'] as const).map(quant => (
                                <tr key={quant}>
                                    <td className="border p-2 bg-gray-50 text-sm font-medium">Quant: {quant}</td>
                                    {(['HIGH', 'MEDIUM', 'LOW'] as const).map(qual => {
                                        const result = lookupInherentRisk(quant, qual);
                                        const isSelected = effectiveQuantitative === quant && effectiveQualitative === qual;
                                        const colors = RATING_COLORS[result];
                                        return (
                                            <td
                                                key={qual}
                                                className={`border p-3 text-center ${colors.bg} ${colors.text} ${isSelected ? 'ring-2 ring-blue-500 ring-inset font-bold' : ''
                                                    }`}
                                            >
                                                {result}
                                            </td>
                                        );
                                    })}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                <div className="mt-4 pt-4 border-t border-gray-200">
                    <div className="flex items-center justify-between mb-3">
                        <div>
                            <span className="text-sm text-gray-500">Derived Tier: </span>
                            <RatingBadge rating={derivedTier} />
                        </div>
                        <div>
                            <span className="text-sm text-gray-500">Effective Tier: </span>
                            <RatingBadge rating={effectiveTier} />
                        </div>
                    </div>

                    {/* Override Panel */}
                    <div className={`rounded-lg border-2 p-3 transition-colors ${derivedOverride !== null
                            ? 'bg-amber-50 border-amber-300'
                            : 'bg-gray-50 border-dashed border-gray-300 hover:border-amber-300 hover:bg-amber-50/50'
                        }`}>
                        <div className="flex items-center gap-4">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={derivedOverride !== null}
                                    onChange={e => {
                                        if (e.target.checked) {
                                            setDerivedOverride(derivedTier || 'HIGH');
                                        } else {
                                            setDerivedOverride(null);
                                            setDerivedOverrideComment('');
                                        }
                                    }}
                                    disabled={!canManageModelsFlag}
                                    className="w-4 h-4 rounded border-gray-300 text-amber-600 focus:ring-amber-500"
                                />
                                <span className={`text-sm font-medium ${derivedOverride !== null ? 'text-amber-800' : 'text-gray-600'}`}>
                                    Manual Override
                                </span>
                            </label>
                            {derivedOverride !== null && (
                                <>
                                    <div className="w-28">
                                        <select
                                            value={derivedOverride || ''}
                                            onChange={e => setDerivedOverride(e.target.value as InherentRating)}
                                            disabled={!canManageModelsFlag}
                                            className="block w-full px-3 py-2 border border-amber-300 rounded-md shadow-sm focus:outline-none focus:ring-amber-500 focus:border-amber-500 sm:text-sm bg-white"
                                        >
                                            {INHERENT_RATINGS.map(r => (
                                                <option key={r} value={r}>{r}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <textarea
                                        value={derivedOverrideComment}
                                        onChange={e => setDerivedOverrideComment(e.target.value)}
                                        disabled={!canManageModelsFlag}
                                        rows={1}
                                        className="flex-1 px-3 py-2 border border-amber-300 rounded-md shadow-sm focus:outline-none focus:ring-amber-500 focus:border-amber-500 sm:text-sm bg-white resize-y"
                                        placeholder="Justification required"
                                    />
                                </>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Final Tier Display */}
            <div className={`border-2 rounded-lg p-6 text-center ${effectiveTier ? RATING_COLORS[effectiveTier].border : 'border-gray-300'
                } ${effectiveTier ? RATING_COLORS[effectiveTier].bg : 'bg-gray-50'}`}>
                <div className="text-sm text-gray-600 mb-2">FINAL MODEL TIER</div>
                <div className={`text-2xl font-bold ${effectiveTier ? RATING_COLORS[effectiveTier].text : 'text-gray-400'
                    }`}>
                    {effectiveTier ? TIER_LABELS[`TIER_${effectiveTier === 'VERY_LOW' ? '4' : effectiveTier === 'HIGH' ? '1' : effectiveTier === 'MEDIUM' ? '2' : '3'}`] : 'Not Calculated'}
                </div>
                {currentAssessment?.assessed_by && currentAssessment?.assessed_at && (
                    <div className="mt-2 text-sm text-gray-500">
                        Last assessed by {currentAssessment.assessed_by.full_name} on{' '}
                        {currentAssessment.assessed_at.split('T')[0]}
                    </div>
                )}
            </div>

            {/* Action Buttons */}
            {canManageModelsFlag && (
                <div className="flex justify-end space-x-4">
                    {currentAssessment && (
                        <button
                            onClick={handleDelete}
                            disabled={saving}
                            className="px-4 py-2 text-sm font-medium text-red-700 bg-red-100 border border-red-300 rounded-md hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
                        >
                            Delete Assessment
                        </button>
                    )}
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                    >
                        {saving ? 'Saving...' : currentAssessment ? 'Update Assessment' : 'Save Assessment'}
                    </button>
                </div>
            )}

            {/* Assessment History Section (Collapsible) */}
            {history.length > 0 && (
                <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                    <button
                        onClick={() => setShowHistory(!showHistory)}
                        className="flex items-center justify-between w-full text-left"
                    >
                        <h4 className="text-sm font-medium text-gray-700 flex items-center gap-2">
                            <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            Risk Assessment History ({history.length} change{history.length !== 1 ? 's' : ''})
                        </h4>
                        <svg
                            className={`w-5 h-5 text-gray-500 transform transition-transform ${showHistory ? 'rotate-180' : ''}`}
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                    </button>
                    {showHistory && (
                        <div className="mt-3 overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-100">
                                    <tr>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Region</th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Changes</th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {history.map(item => (
                                        <tr key={item.log_id}>
                                            <td className="px-4 py-2 text-sm text-gray-900 whitespace-nowrap">
                                                {item.timestamp.split('T')[0]}
                                            </td>
                                            <td className="px-4 py-2 text-sm whitespace-nowrap">
                                                <span className={`px-2 py-1 rounded text-xs font-medium ${item.action === 'CREATE' ? 'bg-green-100 text-green-800' :
                                                        item.action === 'UPDATE' ? 'bg-blue-100 text-blue-800' :
                                                            item.action === 'DELETE' ? 'bg-red-100 text-red-800' :
                                                                'bg-gray-100 text-gray-800'
                                                    }`}>
                                                    {item.action}
                                                </span>
                                            </td>
                                            <td className="px-4 py-2 text-sm text-gray-500 whitespace-nowrap">
                                                {item.region_name || 'Global'}
                                            </td>
                                            <td className="px-4 py-2 text-sm text-gray-500 whitespace-nowrap">
                                                {item.user_name || 'Unknown'}
                                            </td>
                                            <td className="px-4 py-2 text-sm text-gray-500">
                                                {item.changes_summary}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default ModelRiskAssessmentTab;
