/**
 * ValidationScorecardTab Component
 *
 * A comprehensive scorecard entry form for validation requests.
 * Scorecard can be completed before the final outcome determination.
 * Features:
 * - Summary card at top showing overall + section ratings
 * - Progress indicator for rated/unrated criteria
 * - Collapsible sections
 * - Rating dropdowns with explicit N/A selection
 * - Auto-save on rating change
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import {
    getScorecard,
    updateSingleRating,
    updateOverallNarrative,
    exportScorecardPDF,
    ScorecardFullResponse,
    ScorecardRating,
    RATING_OPTIONS,
    getRatingColorClass,
    getScoreColorClass,
} from '../api/scorecard';

interface Props {
    requestId: number;
    canEdit: boolean;
    onScorecardChange?: () => void;
}

// ============================================================================
// Sub-components
// ============================================================================

interface RatingBadgeProps {
    rating: string | null;
    score?: number;
    size?: 'sm' | 'md' | 'lg';
}

function RatingBadge({ rating, score, size = 'md' }: RatingBadgeProps) {
    const sizeClasses = {
        sm: 'px-2 py-0.5 text-xs',
        md: 'px-3 py-1 text-sm',
        lg: 'px-4 py-2 text-base font-medium',
    };

    if (!rating) {
        return (
            <span className={`${sizeClasses[size]} rounded bg-gray-100 text-gray-500`}>
                Unrated
            </span>
        );
    }

    return (
        <span className={`${sizeClasses[size]} rounded ${getRatingColorClass(rating)}`}>
            {rating} {score !== undefined && `(${score})`}
        </span>
    );
}

interface ProgressBarProps {
    rated: number;
    total: number;
}

function ProgressBar({ rated, total }: ProgressBarProps) {
    const percentage = total > 0 ? Math.round((rated / total) * 100) : 0;
    const bgColor = percentage === 100 ? 'bg-green-500' : percentage > 50 ? 'bg-yellow-500' : 'bg-gray-300';

    return (
        <div className="w-full">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>{rated} of {total} rated</span>
                <span>{percentage}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                    className={`${bgColor} h-2 rounded-full transition-all duration-300`}
                    style={{ width: `${percentage}%` }}
                />
            </div>
        </div>
    );
}

// ============================================================================
// Main Component
// ============================================================================

export default function ValidationScorecardTab({ requestId, canEdit, onScorecardChange }: Props) {
    // State - scorecard now includes config_sections (historical snapshot or current config)
    const [scorecard, setScorecard] = useState<ScorecardFullResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [savingCriterion, setSavingCriterion] = useState<string | null>(null);
    const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

    // Local state for criterion fields (descriptions and comments)
    const [criterionFields, setCriterionFields] = useState<Record<string, { description: string; comments: string }>>({});

    // Overall assessment narrative state
    const [overallNarrative, setOverallNarrative] = useState<string>('');
    const [savingNarrative, setSavingNarrative] = useState(false);

    // PDF export state
    const [exporting, setExporting] = useState(false);

    // Load scorecard data (includes config_sections from historical snapshot or current config)
    useEffect(() => {
        async function loadData() {
            try {
                setLoading(true);
                setError(null);

                const scorecardData = await getScorecard(requestId);
                setScorecard(scorecardData);

                // Expand all sections by default (using config from scorecard response)
                const allSectionCodes = new Set(scorecardData.config_sections.map(s => s.code));
                setExpandedSections(allSectionCodes);

                // Initialize local fields from scorecard data
                const fields: Record<string, { description: string; comments: string }> = {};
                scorecardData.criteria_details.forEach(detail => {
                    fields[detail.criterion_code] = {
                        description: detail.description || '',
                        comments: detail.comments || '',
                    };
                });
                setCriterionFields(fields);

                // Initialize overall narrative from scorecard data
                setOverallNarrative(scorecardData.overall_assessment.overall_assessment_narrative || '');

            } catch (err: unknown) {
                console.error('Error loading scorecard:', err);
                setError(err instanceof Error ? err.message : 'Failed to load scorecard');
            } finally {
                setLoading(false);
            }
        }

        loadData();
    }, [requestId]);

    // Toggle section expansion
    const toggleSection = useCallback((code: string) => {
        setExpandedSections(prev => {
            const next = new Set(prev);
            if (next.has(code)) {
                next.delete(code);
            } else {
                next.add(code);
            }
            return next;
        });
    }, []);

    // Handle rating change - preserve scroll position during update
    const handleRatingChange = useCallback(async (criterionCode: string, rating: ScorecardRating) => {
        if (!canEdit) return;

        // Capture scroll position before any state changes
        const scrollTop = window.scrollY;

        // Function to restore scroll after React render and browser paint
        const restoreScroll = () => {
            // Double requestAnimationFrame ensures we run after React's render AND browser paint
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    window.scrollTo(0, scrollTop);
                });
            });
        };

        try {
            setSavingCriterion(criterionCode);

            const updated = await updateSingleRating(requestId, criterionCode, {
                rating,
                description: criterionFields[criterionCode]?.description || null,
                comments: criterionFields[criterionCode]?.comments || null,
            });

            setScorecard(updated);
            onScorecardChange?.();

        } catch (err: unknown) {
            console.error('Error updating rating:', err);
            setError(err instanceof Error ? err.message : 'Failed to save rating');
        } finally {
            setSavingCriterion(null);
            restoreScroll();
        }
    }, [requestId, canEdit, criterionFields, onScorecardChange]);

    // Handle field blur (save description/comments)
    const handleFieldBlur = useCallback(async (criterionCode: string, field: 'description' | 'comments') => {
        if (!canEdit) return;

        // Get current rating from scorecard
        const currentDetail = scorecard?.criteria_details.find(d => d.criterion_code === criterionCode);
        if (!currentDetail) return;

        // Only save if field has changed
        const currentValue = field === 'description' ? currentDetail.description : currentDetail.comments;
        const newValue = criterionFields[criterionCode]?.[field] || '';
        if (currentValue === newValue || (!currentValue && !newValue)) return;

        try {
            setSavingCriterion(criterionCode);

            const updated = await updateSingleRating(requestId, criterionCode, {
                [field]: newValue || null,
            });

            setScorecard(updated);

        } catch (err: unknown) {
            console.error(`Error updating ${field}:`, err);
        } finally {
            setSavingCriterion(null);
        }
    }, [requestId, canEdit, scorecard, criterionFields]);

    // Update local field state
    const handleFieldChange = useCallback((criterionCode: string, field: 'description' | 'comments', value: string) => {
        setCriterionFields(prev => ({
            ...prev,
            [criterionCode]: {
                ...prev[criterionCode],
                [field]: value,
            },
        }));
    }, []);

    // Handle overall narrative blur (auto-save)
    const handleNarrativeBlur = useCallback(async () => {
        if (!canEdit) return;

        // Only save if narrative has changed
        const currentNarrative = scorecard?.overall_assessment.overall_assessment_narrative || '';
        if (currentNarrative === overallNarrative) return;

        try {
            setSavingNarrative(true);
            const updated = await updateOverallNarrative(requestId, overallNarrative || null);
            setScorecard(updated);
            onScorecardChange?.();
        } catch (err: unknown) {
            console.error('Error updating overall narrative:', err);
            setError(err instanceof Error ? err.message : 'Failed to save narrative');
        } finally {
            setSavingNarrative(false);
        }
    }, [requestId, canEdit, scorecard, overallNarrative, onScorecardChange]);

    // Get criterion detail by code
    const getCriterionDetail = useCallback((code: string) => {
        return scorecard?.criteria_details.find(d => d.criterion_code === code);
    }, [scorecard]);

    // Get section summary by code
    const getSectionSummary = useCallback((code: string) => {
        return scorecard?.section_summaries.find(s => s.section_code === code);
    }, [scorecard]);

    // Calculate total progress
    const progress = useMemo(() => {
        if (!scorecard) return { rated: 0, total: 0 };

        const total = scorecard.criteria_details.length;
        const rated = scorecard.criteria_details.filter(d =>
            d.rating !== null && d.rating !== undefined
        ).length;

        return { rated, total };
    }, [scorecard]);

    // Handle PDF export
    const handleExportPDF = useCallback(async () => {
        try {
            setExporting(true);

            const blob = await exportScorecardPDF(requestId);

            // Create download link and trigger download
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `validation-scorecard-${requestId}-${new Date().toISOString().split('T')[0]}.pdf`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);

        } catch (err: unknown) {
            console.error('Error exporting PDF:', err);
            setError(err instanceof Error ? err.message : 'Failed to export PDF');
        } finally {
            setExporting(false);
        }
    }, [requestId]);

    // ========================================================================
    // Render
    // ========================================================================

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-3 text-gray-600">Loading scorecard...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
                <strong>Error:</strong> {error}
            </div>
        );
    }

    if (!scorecard) {
        return (
            <div className="text-gray-500 text-center py-8">
                No scorecard data available.
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Summary Card */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
                    {/* Overall Assessment */}
                    <div className="text-center md:text-left">
                        <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
                            Overall Assessment
                        </h3>
                        <div className="flex items-center gap-3">
                            <RatingBadge
                                rating={scorecard.overall_assessment.rating}
                                score={scorecard.overall_assessment.numeric_score}
                                size="lg"
                            />
                            <span className={`text-2xl font-bold ${getScoreColorClass(scorecard.overall_assessment.numeric_score)}`}>
                                {scorecard.overall_assessment.numeric_score}/6
                            </span>
                        </div>
                    </div>

                    {/* Section Summaries */}
                    <div className="flex-1">
                        <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
                            Section Ratings
                        </h3>
                        <div className="flex flex-wrap gap-2">
                            {scorecard.section_summaries.map(section => (
                                <div
                                    key={section.section_code}
                                    className="flex items-center gap-2 bg-white rounded px-3 py-1 border"
                                >
                                    <span className="text-xs text-gray-500">S{section.section_code}:</span>
                                    <RatingBadge rating={section.rating} score={section.numeric_score} size="sm" />
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Progress */}
                    <div className="w-full md:w-48">
                        <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
                            Progress
                        </h3>
                        <ProgressBar rated={progress.rated} total={progress.total} />
                    </div>
                </div>

                {/* Overall Assessment Narrative */}
                <div className="mt-4 pt-4 border-t border-blue-200">
                    <div className="flex items-center justify-between mb-2">
                        <label className="text-sm font-medium text-gray-700">
                            Overall Assessment Narrative
                        </label>
                        {savingNarrative && (
                            <span className="text-xs text-blue-600 flex items-center gap-1">
                                <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                </svg>
                                Saving...
                            </span>
                        )}
                    </div>
                    <textarea
                        value={overallNarrative}
                        onChange={(e) => setOverallNarrative(e.target.value)}
                        onBlur={handleNarrativeBlur}
                        disabled={!canEdit}
                        placeholder="Summarize key findings, areas of concern, and overall assessment rationale..."
                        className={`w-full h-24 px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 resize-y ${
                            !canEdit ? 'bg-gray-50 text-gray-500 cursor-not-allowed' : 'bg-white'
                        }`}
                    />
                    <p className="mt-1 text-xs text-gray-500">
                        Provide a summary of the overall validation assessment. Changes are saved automatically.
                    </p>
                </div>

                {/* Last updated and Export */}
                <div className="mt-4 pt-4 border-t border-blue-200 flex items-center justify-between">
                    <span className="text-xs text-gray-500">
                        Last computed: {scorecard.computed_at.split('T')[0]} at {scorecard.computed_at.split('T')[1]?.slice(0, 8)}
                    </span>
                    <button
                        onClick={handleExportPDF}
                        disabled={exporting}
                        className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                            exporting
                                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                : 'bg-blue-600 text-white hover:bg-blue-700'
                        }`}
                    >
                        {exporting ? (
                            <>
                                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                </svg>
                                Exporting...
                            </>
                        ) : (
                            <>
                                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                                Export PDF
                            </>
                        )}
                    </button>
                </div>
            </div>

            {/* Sections - rendered from historical config snapshot */}
            {scorecard.config_sections.map((section) => {
                const summary = getSectionSummary(section.code);
                const isExpanded = expandedSections.has(section.code);

                return (
                    <div key={section.code} className="border border-gray-200 rounded-lg overflow-hidden">
                        {/* Section Header */}
                        <button
                            onClick={() => toggleSection(section.code)}
                            className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors"
                        >
                            <div className="flex items-center gap-3">
                                <span className="font-bold text-gray-700">
                                    Section {section.code}: {section.name}
                                </span>
                                {summary && (
                                    <RatingBadge rating={summary.rating} score={summary.numeric_score} size="sm" />
                                )}
                            </div>
                            <div className="flex items-center gap-4">
                                {summary && (
                                    <span className="text-sm text-gray-500">
                                        {summary.rated_count}/{summary.criteria_count} rated
                                    </span>
                                )}
                                <svg
                                    className={`w-5 h-5 text-gray-400 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                            </div>
                        </button>

                        {/* Section Content */}
                        {isExpanded && (
                            <div className="divide-y divide-gray-100">
                                {section.criteria.map((criterion) => {
                                    const detail = getCriterionDetail(criterion.code);
                                    const fields = criterionFields[criterion.code] || { description: '', comments: '' };
                                    const isSaving = savingCriterion === criterion.code;

                                    return (
                                        <div key={criterion.code} className="p-4 hover:bg-gray-50">
                                            <div className="flex items-start gap-4">
                                                {/* Criterion Info */}
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-2">
                                                        <span className="font-mono text-sm bg-gray-100 px-2 py-0.5 rounded">
                                                            {criterion.code}
                                                        </span>
                                                        <h4 className="font-medium text-gray-900">{criterion.name}</h4>
                                                        {isSaving && (
                                                            <span className="text-xs text-blue-600 animate-pulse">Saving...</span>
                                                        )}
                                                    </div>

                                                    {/* Description Field */}
                                                    {criterion.description_prompt && (
                                                        <div className="mb-3">
                                                            <label className="block text-sm text-gray-600 mb-1">
                                                                {criterion.description_prompt}
                                                            </label>
                                                            <textarea
                                                                value={fields.description}
                                                                onChange={(e) => handleFieldChange(criterion.code, 'description', e.target.value)}
                                                                onBlur={() => handleFieldBlur(criterion.code, 'description')}
                                                                disabled={!canEdit}
                                                                rows={2}
                                                                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                                                                placeholder="Enter description..."
                                                            />
                                                        </div>
                                                    )}

                                                    {/* Comments Field */}
                                                    {criterion.comments_prompt && (
                                                        <div>
                                                            <label className="block text-sm text-gray-600 mb-1">
                                                                {criterion.comments_prompt}
                                                            </label>
                                                            <textarea
                                                                value={fields.comments}
                                                                onChange={(e) => handleFieldChange(criterion.code, 'comments', e.target.value)}
                                                                onBlur={() => handleFieldBlur(criterion.code, 'comments')}
                                                                disabled={!canEdit}
                                                                rows={2}
                                                                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                                                                placeholder="Enter rationale."
                                                            />
                                                        </div>
                                                    )}
                                                </div>

                                                {/* Rating Dropdown */}
                                                <div className="flex-shrink-0 w-40">
                                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                                        Rating
                                                    </label>
                                                    <select
                                                        value={detail?.rating || ''}
                                                        onChange={(e) => {
                                                            const value = e.target.value as ScorecardRating;
                                                            handleRatingChange(criterion.code, value || null);
                                                        }}
                                                        disabled={!canEdit || isSaving}
                                                        className={`w-full px-3 py-2 border rounded-md text-sm focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 ${
                                                            detail?.rating ? getRatingColorClass(detail.rating) : 'border-gray-300'
                                                        }`}
                                                    >
                                                        {RATING_OPTIONS.map((opt) => (
                                                            <option key={opt.value || 'unrated'} value={opt.value || ''}>
                                                                {opt.label}
                                                            </option>
                                                        ))}
                                                    </select>
                                                    {detail?.numeric_score !== undefined && detail.numeric_score > 0 && (
                                                        <div className="mt-1 text-center">
                                                            <span className={`text-sm font-medium ${getScoreColorClass(detail.numeric_score)}`}>
                                                                Score: {detail.numeric_score}
                                                            </span>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                );
            })}

            {/* Help Text */}
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-600">
                <h4 className="font-medium text-gray-700 mb-2">Rating Scale</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    <div><span className="font-medium text-green-700">Green (6)</span>: Excellent</div>
                    <div><span className="font-medium text-green-600">Green- (5)</span>: Good</div>
                    <div><span className="font-medium text-yellow-700">Yellow+ (4)</span>: Satisfactory</div>
                    <div><span className="font-medium text-yellow-600">Yellow (3)</span>: Adequate</div>
                    <div><span className="font-medium text-yellow-500">Yellow- (2)</span>: Marginal</div>
                    <div><span className="font-medium text-red-600">Red (1)</span>: Unsatisfactory</div>
                    <div><span className="font-medium text-gray-500">N/A (0)</span>: Not Applicable</div>
                </div>
            </div>
        </div>
    );
}
