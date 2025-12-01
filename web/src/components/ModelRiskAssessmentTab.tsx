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
    RiskAssessmentResponse,
    FactorRatingInput,
    RATING_COLORS,
    lookupInherentRisk,
    TIER_LABELS,
} from '../api/riskAssessment';
import { listFactors, FactorResponse } from '../api/qualitativeFactors';
import { useAuth } from '../contexts/AuthContext';

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
    const isAdminOrValidator = user?.role === 'Admin' || user?.role === 'Validator';

    // State
    const [assessments, setAssessments] = useState<RiskAssessmentResponse[]>([]);
    const [factors, setFactors] = useState<FactorResponse[]>([]);
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

    // Current assessment for selected region
    const currentAssessment = assessments.find(a =>
        selectedRegionId === null ? a.region === null : a.region?.region_id === selectedRegionId
    );

    // Load data
    const loadData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const [assessmentsData, factorsData] = await Promise.all([
                listAssessments(modelId),
                listFactors()
            ]);
            setAssessments(assessmentsData);
            setFactors(factorsData);
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
    }, [currentAssessment, factors]);

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

    // Handle save
    const handleSave = async () => {
        if (!isAdminOrValidator) return;

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

    // Handle delete
    const handleDelete = async () => {
        if (!isAdminOrValidator || !currentAssessment) return;
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
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h3 className="text-lg font-medium text-gray-900">Risk Assessment</h3>
                    <p className="text-sm text-gray-500">
                        Calculate inherent model risk based on qualitative and quantitative factors
                    </p>
                </div>
                <div className="flex items-center space-x-4">
                    <label className="text-sm font-medium text-gray-700">Region:</label>
                    <select
                        value={selectedRegionId === null ? '' : selectedRegionId}
                        onChange={e => setSelectedRegionId(e.target.value ? parseInt(e.target.value) : null)}
                        className="block w-48 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    >
                        <option value="">Global</option>
                        {regions.map(r => (
                            <option key={r.region_id} value={r.region_id}>{r.name}</option>
                        ))}
                    </select>
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
                            disabled={!isAdminOrValidator}
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Comment</label>
                        <textarea
                            value={quantitativeComment}
                            onChange={e => setQuantitativeComment(e.target.value)}
                            disabled={!isAdminOrValidator}
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
                    <div className={`rounded-lg border-2 p-3 transition-colors ${
                        quantitativeOverride !== null
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
                                    disabled={!isAdminOrValidator}
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
                                            disabled={!isAdminOrValidator}
                                            includeEmpty={false}
                                        />
                                    </div>
                                    <textarea
                                        value={quantitativeOverrideComment}
                                        onChange={e => setQuantitativeOverrideComment(e.target.value)}
                                        disabled={!isAdminOrValidator}
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
                                        disabled={!isAdminOrValidator}
                                    />
                                </td>
                                <td className="px-4 py-3">
                                    <textarea
                                        value={factorRatings[factor.factor_id]?.comment || ''}
                                        onChange={e => setFactorRatings(prev => ({
                                            ...prev,
                                            [factor.factor_id]: { ...prev[factor.factor_id], comment: e.target.value }
                                        }))}
                                        disabled={!isAdminOrValidator}
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
                    <div className={`rounded-lg border-2 p-3 transition-colors ${
                        qualitativeOverride !== null
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
                                    disabled={!isAdminOrValidator}
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
                                            disabled={!isAdminOrValidator}
                                            includeEmpty={false}
                                        />
                                    </div>
                                    <textarea
                                        value={qualitativeOverrideComment}
                                        onChange={e => setQualitativeOverrideComment(e.target.value)}
                                        disabled={!isAdminOrValidator}
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
                                                className={`border p-3 text-center ${colors.bg} ${colors.text} ${
                                                    isSelected ? 'ring-2 ring-blue-500 ring-inset font-bold' : ''
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
                    <div className={`rounded-lg border-2 p-3 transition-colors ${
                        derivedOverride !== null
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
                                    disabled={!isAdminOrValidator}
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
                                            disabled={!isAdminOrValidator}
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
                                        disabled={!isAdminOrValidator}
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
            <div className={`border-2 rounded-lg p-6 text-center ${
                effectiveTier ? RATING_COLORS[effectiveTier].border : 'border-gray-300'
            } ${effectiveTier ? RATING_COLORS[effectiveTier].bg : 'bg-gray-50'}`}>
                <div className="text-sm text-gray-600 mb-2">FINAL MODEL TIER</div>
                <div className={`text-2xl font-bold ${
                    effectiveTier ? RATING_COLORS[effectiveTier].text : 'text-gray-400'
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
            {isAdminOrValidator && (
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
        </div>
    );
};

export default ModelRiskAssessmentTab;
