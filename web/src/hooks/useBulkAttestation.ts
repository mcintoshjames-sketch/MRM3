import { useState, useEffect, useCallback, useMemo } from 'react';
import api from '../api/client';

// ============================================================================
// Helper: Extract error message from API response
// ============================================================================

function extractErrorMessage(err: any, fallback: string): string {
    const detail = err?.response?.data?.detail;
    if (!detail) return fallback;

    // If detail is a string, return it directly
    if (typeof detail === 'string') return detail;

    // If detail is an array (Pydantic validation errors), extract messages
    if (Array.isArray(detail)) {
        const messages = detail.map((e: any) => e.msg || e.message || JSON.stringify(e));
        return messages.join('; ');
    }

    // If detail is an object with a message property
    if (typeof detail === 'object' && detail.msg) return detail.msg;

    return fallback;
}

// ============================================================================
// Types
// ============================================================================

export interface BulkAttestationCycleInfo {
    cycle_id: number;
    cycle_name: string;
    submission_due_date: string;
    status: string;
    days_until_due: number;
}

export interface BulkAttestationModel {
    attestation_id: number;
    model_id: number;
    model_name: string;
    risk_tier_code: string | null;
    risk_tier_label: string | null;
    model_status: string | null;
    last_attested_date: string | null;
    attestation_status: 'PENDING' | 'SUBMITTED' | 'ACCEPTED' | 'REJECTED';
    is_excluded: boolean;
}

export interface AttestationQuestion {
    value_id: number;
    code: string;
    label: string;
    description: string | null;
    requires_comment_if_no: boolean;
    sort_order: number;
}

export interface BulkAttestationDraft {
    exists: boolean;
    bulk_submission_id: number | null;
    selected_model_ids: number[];
    excluded_model_ids: number[];
    responses: ResponseItem[];
    comment: string | null;
    last_saved: string | null;
}

export interface BulkAttestationSummary {
    total_models: number;
    pending_count: number;
    excluded_count: number;
    submitted_count: number;
    accepted_count: number;
    rejected_count: number;
}

export interface BulkAttestationStateResponse {
    cycle: BulkAttestationCycleInfo;
    models: BulkAttestationModel[];
    draft: BulkAttestationDraft;
    questions: AttestationQuestion[];
    summary: BulkAttestationSummary;
}

export interface ResponseItem {
    question_id: number;
    answer: boolean | null;
    comment: string | null;
}

// ============================================================================
// Hook State Interface
// ============================================================================

export interface BulkAttestationState {
    // Data from API
    cycle: BulkAttestationCycleInfo | null;
    models: BulkAttestationModel[];
    questions: AttestationQuestion[];
    summary: BulkAttestationSummary | null;

    // Selection state
    selectedModelIds: Set<number>;
    excludedModelIds: Set<number>;

    // Form state
    responses: Map<number, { answer: boolean | null; comment: string }>;
    decisionComment: string;

    // Draft state
    isDirty: boolean;
    lastSaved: Date | null;
    isSaving: boolean;
    draftExists: boolean;
    bulkSubmissionId: number | null;

    // Loading states
    isLoading: boolean;
    isSubmitting: boolean;
    error: string | null;
    successMessage: string | null;

    // Computed
    selectedCount: number;
    excludedCount: number;
    pendingModelIds: number[];
    canSubmit: boolean;
    validationErrors: string[];
}

export interface BulkAttestationActions {
    // Model selection
    toggleModel: (modelId: number) => void;
    selectAll: () => void;
    deselectAll: () => void;

    // Form
    setResponse: (questionId: number, answer: boolean, comment?: string) => void;
    setResponseComment: (questionId: number, comment: string) => void;
    setDecisionComment: (comment: string) => void;

    // Persistence
    saveDraft: () => Promise<void>;
    discardDraft: () => Promise<void>;
    submit: () => Promise<boolean>;

    // Lifecycle
    loadData: () => Promise<void>;
    clearError: () => void;
    clearSuccess: () => void;
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useBulkAttestation(cycleId: number): BulkAttestationState & BulkAttestationActions {
    // API data state
    const [cycle, setCycle] = useState<BulkAttestationCycleInfo | null>(null);
    const [models, setModels] = useState<BulkAttestationModel[]>([]);
    const [questions, setQuestions] = useState<AttestationQuestion[]>([]);
    const [summary, setSummary] = useState<BulkAttestationSummary | null>(null);

    // Selection state
    const [selectedModelIds, setSelectedModelIds] = useState<Set<number>>(new Set());
    const [excludedModelIds, setExcludedModelIds] = useState<Set<number>>(new Set());

    // Form state
    const [responses, setResponses] = useState<Map<number, { answer: boolean | null; comment: string }>>(new Map());
    const [decisionComment, setDecisionComment] = useState('');

    // Draft state
    const [isDirty, setIsDirty] = useState(false);
    const [lastSaved, setLastSaved] = useState<Date | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const [draftExists, setDraftExists] = useState(false);
    const [bulkSubmissionId, setBulkSubmissionId] = useState<number | null>(null);

    // Loading states
    const [isLoading, setIsLoading] = useState(true);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    // ========================================================================
    // Computed values
    // ========================================================================

    const pendingModelIds = useMemo(() => {
        return models
            .filter(m => m.attestation_status === 'PENDING')
            .map(m => m.model_id);
    }, [models]);

    const selectedCount = selectedModelIds.size;
    const excludedCount = excludedModelIds.size;

    const validationErrors = useMemo(() => {
        const errors: string[] = [];

        if (selectedCount === 0) {
            errors.push('At least one model must be selected');
        }

        // Check all questions are answered
        for (const q of questions) {
            const response = responses.get(q.value_id);
            if (!response || response.answer === null) {
                errors.push(`Question "${q.code}" must be answered`);
            } else if (response.answer === false && q.requires_comment_if_no && !response.comment?.trim()) {
                errors.push(`Question "${q.code}" requires a comment when answered "No"`);
            }
        }

        return errors;
    }, [selectedCount, questions, responses]);

    const canSubmit = validationErrors.length === 0 && !isSubmitting;

    // ========================================================================
    // Load data from API
    // ========================================================================

    const loadData = useCallback(async () => {
        setIsLoading(true);
        setError(null);

        try {
            const response = await api.get<BulkAttestationStateResponse>(`/attestations/bulk/${cycleId}`);
            const data = response.data;

            setCycle(data.cycle);
            setModels(data.models);
            setQuestions(data.questions);
            setSummary(data.summary);

            // Initialize from draft if exists
            if (data.draft.exists) {
                setDraftExists(true);
                setBulkSubmissionId(data.draft.bulk_submission_id);
                setSelectedModelIds(new Set(data.draft.selected_model_ids));
                setExcludedModelIds(new Set(data.draft.excluded_model_ids));
                setDecisionComment(data.draft.comment || '');

                // Initialize responses from draft
                const responseMap = new Map<number, { answer: boolean | null; comment: string }>();
                for (const r of data.draft.responses) {
                    responseMap.set(r.question_id, {
                        answer: r.answer,
                        comment: r.comment || ''
                    });
                }
                setResponses(responseMap);

                if (data.draft.last_saved) {
                    setLastSaved(new Date(data.draft.last_saved));
                }
            } else {
                // Initialize selection state from server's is_excluded flags
                // Respect any exclusions that were previously set
                const pendingModels = data.models.filter(m => m.attestation_status === 'PENDING');

                // Models not excluded on server are selected
                const selectedIds = pendingModels
                    .filter(m => !m.is_excluded)
                    .map(m => m.model_id);
                setSelectedModelIds(new Set(selectedIds));

                // Models excluded on server stay excluded
                const excludedIds = pendingModels
                    .filter(m => m.is_excluded)
                    .map(m => m.model_id);
                setExcludedModelIds(new Set(excludedIds));

                // Initialize empty responses for all questions
                const responseMap = new Map<number, { answer: boolean | null; comment: string }>();
                for (const q of data.questions) {
                    responseMap.set(q.value_id, { answer: null, comment: '' });
                }
                setResponses(responseMap);
            }

            setIsDirty(false);
        } catch (err: any) {
            setError(extractErrorMessage(err, 'Failed to load bulk attestation data'));
        } finally {
            setIsLoading(false);
        }
    }, [cycleId]);

    // Load on mount
    useEffect(() => {
        loadData();
    }, [loadData]);

    // ========================================================================
    // Model selection actions
    // ========================================================================

    const toggleModel = useCallback((modelId: number) => {
        setSelectedModelIds(prev => {
            const next = new Set(prev);
            if (next.has(modelId)) {
                next.delete(modelId);
                // Add to excluded
                setExcludedModelIds(excl => {
                    const nextExcl = new Set(excl);
                    nextExcl.add(modelId);
                    return nextExcl;
                });
            } else {
                next.add(modelId);
                // Remove from excluded
                setExcludedModelIds(excl => {
                    const nextExcl = new Set(excl);
                    nextExcl.delete(modelId);
                    return nextExcl;
                });
            }
            return next;
        });
        setIsDirty(true);
    }, []);

    const selectAll = useCallback(() => {
        setSelectedModelIds(new Set(pendingModelIds));
        setExcludedModelIds(new Set());
        setIsDirty(true);
    }, [pendingModelIds]);

    const deselectAll = useCallback(() => {
        setSelectedModelIds(new Set());
        setExcludedModelIds(new Set(pendingModelIds));
        setIsDirty(true);
    }, [pendingModelIds]);

    // ========================================================================
    // Form actions
    // ========================================================================

    const setResponse = useCallback((questionId: number, answer: boolean, comment?: string) => {
        setResponses(prev => {
            const next = new Map(prev);
            const existing = next.get(questionId);
            next.set(questionId, {
                answer,
                comment: comment ?? existing?.comment ?? ''
            });
            return next;
        });
        setIsDirty(true);
    }, []);

    const setResponseComment = useCallback((questionId: number, comment: string) => {
        setResponses(prev => {
            const next = new Map(prev);
            const existing = next.get(questionId);
            next.set(questionId, {
                answer: existing?.answer ?? null,
                comment
            });
            return next;
        });
        setIsDirty(true);
    }, []);

    const handleSetDecisionComment = useCallback((comment: string) => {
        setDecisionComment(comment);
        setIsDirty(true);
    }, []);

    // ========================================================================
    // Draft persistence
    // ========================================================================

    const saveDraft = useCallback(async () => {
        if (isSaving) return;

        setIsSaving(true);
        setError(null);

        try {
            const responsesArray: ResponseItem[] = [];
            responses.forEach((value, questionId) => {
                responsesArray.push({
                    question_id: questionId,
                    answer: value.answer,
                    comment: value.comment || null
                });
            });

            const response = await api.post(`/attestations/bulk/${cycleId}/draft`, {
                selected_model_ids: Array.from(selectedModelIds),
                excluded_model_ids: Array.from(excludedModelIds),
                responses: responsesArray,
                comment: decisionComment || null
            });

            setBulkSubmissionId(response.data.bulk_submission_id);
            setLastSaved(new Date(response.data.last_saved));
            setDraftExists(true);
            setIsDirty(false);
        } catch (err: any) {
            setError(extractErrorMessage(err, 'Failed to save draft'));
        } finally {
            setIsSaving(false);
        }
    }, [cycleId, selectedModelIds, excludedModelIds, responses, decisionComment, isSaving]);

    const discardDraft = useCallback(async () => {
        setError(null);

        try {
            await api.delete(`/attestations/bulk/${cycleId}/draft`);

            // Reset to initial state
            setDraftExists(false);
            setBulkSubmissionId(null);
            setSelectedModelIds(new Set(pendingModelIds));
            setExcludedModelIds(new Set());
            setDecisionComment('');

            // Reset responses
            const responseMap = new Map<number, { answer: boolean | null; comment: string }>();
            for (const q of questions) {
                responseMap.set(q.value_id, { answer: null, comment: '' });
            }
            setResponses(responseMap);

            setLastSaved(null);
            setIsDirty(false);
            setSuccessMessage('Draft discarded');
        } catch (err: any) {
            setError(extractErrorMessage(err, 'Failed to discard draft'));
        }
    }, [cycleId, pendingModelIds, questions]);

    // ========================================================================
    // Submit
    // ========================================================================

    const submit = useCallback(async (): Promise<boolean> => {
        if (!canSubmit) return false;

        setIsSubmitting(true);
        setError(null);

        try {
            const responsesArray: ResponseItem[] = [];
            responses.forEach((value, questionId) => {
                responsesArray.push({
                    question_id: questionId,
                    answer: value.answer,
                    comment: value.comment || null
                });
            });

            const response = await api.post(`/attestations/bulk/${cycleId}/submit`, {
                selected_model_ids: Array.from(selectedModelIds),
                responses: responsesArray,
                decision_comment: decisionComment || null
            });

            setSuccessMessage(response.data.message);
            setIsDirty(false);

            // Reload data to get updated state
            await loadData();

            return true;
        } catch (err: any) {
            setError(extractErrorMessage(err, 'Failed to submit attestations'));
            return false;
        } finally {
            setIsSubmitting(false);
        }
    }, [canSubmit, cycleId, selectedModelIds, responses, decisionComment, loadData]);

    // ========================================================================
    // Error/Success handling
    // ========================================================================

    const clearError = useCallback(() => setError(null), []);
    const clearSuccess = useCallback(() => setSuccessMessage(null), []);

    // ========================================================================
    // Auto-save (debounced)
    // ========================================================================

    useEffect(() => {
        if (!isDirty || isLoading) return;

        const timer = setTimeout(() => {
            saveDraft();
        }, 5000);

        return () => clearTimeout(timer);
    }, [isDirty, isLoading, saveDraft]);

    // ========================================================================
    // Return state and actions
    // ========================================================================

    return {
        // State
        cycle,
        models,
        questions,
        summary,
        selectedModelIds,
        excludedModelIds,
        responses,
        decisionComment,
        isDirty,
        lastSaved,
        isSaving,
        draftExists,
        bulkSubmissionId,
        isLoading,
        isSubmitting,
        error,
        successMessage,
        selectedCount,
        excludedCount,
        pendingModelIds,
        canSubmit,
        validationErrors,

        // Actions
        toggleModel,
        selectAll,
        deselectAll,
        setResponse,
        setResponseComment,
        setDecisionComment: handleSetDecisionComment,
        saveDraft,
        discardDraft,
        submit,
        loadData,
        clearError,
        clearSuccess
    };
}
