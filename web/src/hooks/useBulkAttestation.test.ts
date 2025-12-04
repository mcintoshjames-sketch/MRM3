import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useBulkAttestation, BulkAttestationStateResponse } from './useBulkAttestation';

// Mock the API client
const mockGet = vi.fn();
const mockPost = vi.fn();
const mockDelete = vi.fn();

vi.mock('../api/client', () => ({
    default: {
        get: (...args: unknown[]) => mockGet(...args),
        post: (...args: unknown[]) => mockPost(...args),
        delete: (...args: unknown[]) => mockDelete(...args),
    },
}));

// Sample test data
const sampleCycle = {
    cycle_id: 1,
    cycle_name: 'Q4 2024 Attestation',
    submission_due_date: '2024-12-31',
    status: 'ACTIVE',
    days_until_due: 30,
};

const sampleQuestions = [
    {
        value_id: 101,
        code: 'ATT_Q1',
        label: 'Model performs as expected',
        description: 'Confirm the model continues to perform within acceptable parameters',
        requires_comment_if_no: true,
        sort_order: 1,
    },
    {
        value_id: 102,
        code: 'ATT_Q2',
        label: 'Documentation is current',
        description: 'Confirm all model documentation is up to date',
        requires_comment_if_no: false,
        sort_order: 2,
    },
];

const sampleModelsWithExclusions = [
    {
        attestation_id: 1,
        model_id: 10,
        model_name: 'Credit Risk Model',
        risk_tier_code: 'T1',
        risk_tier_label: 'Tier 1',
        model_status: 'Active',
        last_attested_date: '2024-06-15',
        attestation_status: 'PENDING' as const,
        is_excluded: false,
    },
    {
        attestation_id: 2,
        model_id: 20,
        model_name: 'Fraud Detection Model',
        risk_tier_code: 'T1',
        risk_tier_label: 'Tier 1',
        model_status: 'Active',
        last_attested_date: '2024-06-15',
        attestation_status: 'PENDING' as const,
        is_excluded: true, // This model is excluded
    },
    {
        attestation_id: 3,
        model_id: 30,
        model_name: 'Pricing Model',
        risk_tier_code: 'T2',
        risk_tier_label: 'Tier 2',
        model_status: 'Active',
        last_attested_date: null,
        attestation_status: 'PENDING' as const,
        is_excluded: false,
    },
];

const sampleSummary = {
    total_models: 3,
    pending_count: 3,
    excluded_count: 1,
    submitted_count: 0,
    accepted_count: 0,
    rejected_count: 0,
};

const createMockResponse = (overrides: Partial<BulkAttestationStateResponse> = {}): BulkAttestationStateResponse => ({
    cycle: sampleCycle,
    models: sampleModelsWithExclusions,
    questions: sampleQuestions,
    draft: {
        exists: false,
        bulk_submission_id: null,
        selected_model_ids: [],
        excluded_model_ids: [],
        responses: [],
        comment: null,
        last_saved: null,
    },
    summary: sampleSummary,
    ...overrides,
});

describe('useBulkAttestation', () => {
    beforeEach(() => {
        mockGet.mockReset();
        mockPost.mockReset();
        mockDelete.mockReset();
    });

    describe('initialization', () => {
        it('loads data on mount', async () => {
            mockGet.mockResolvedValueOnce({ data: createMockResponse() });

            const { result } = renderHook(() => useBulkAttestation(1));

            expect(result.current.isLoading).toBe(true);

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(mockGet).toHaveBeenCalledWith('/attestations/bulk/1');
            expect(result.current.cycle).toEqual(sampleCycle);
            expect(result.current.models).toEqual(sampleModelsWithExclusions);
            expect(result.current.questions).toEqual(sampleQuestions);
        });

        it('respects is_excluded flag from API when initializing selection', async () => {
            // This is the key test for Finding 1: Backend exclusion flags must be respected
            mockGet.mockResolvedValueOnce({ data: createMockResponse() });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // Model 10 (is_excluded: false) should be selected
            expect(result.current.selectedModelIds.has(10)).toBe(true);

            // Model 20 (is_excluded: true) should NOT be selected
            expect(result.current.selectedModelIds.has(20)).toBe(false);
            expect(result.current.excludedModelIds.has(20)).toBe(true);

            // Model 30 (is_excluded: false) should be selected
            expect(result.current.selectedModelIds.has(30)).toBe(true);

            // Verify counts
            expect(result.current.selectedCount).toBe(2);
            expect(result.current.excludedCount).toBe(1);
        });

        it('initializes all pending models as selected when none are excluded', async () => {
            const modelsWithoutExclusions = sampleModelsWithExclusions.map(m => ({
                ...m,
                is_excluded: false,
            }));

            mockGet.mockResolvedValueOnce({
                data: createMockResponse({ models: modelsWithoutExclusions }),
            });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // All pending models should be selected
            expect(result.current.selectedModelIds.size).toBe(3);
            expect(result.current.excludedModelIds.size).toBe(0);
        });

        it('handles API error gracefully', async () => {
            mockGet.mockRejectedValueOnce({
                response: { data: { detail: 'Cycle not found' } },
            });

            const { result } = renderHook(() => useBulkAttestation(999));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.error).toBe('Cycle not found');
            expect(result.current.cycle).toBeNull();
        });
    });

    describe('draft restoration', () => {
        it('restores selection state from existing draft', async () => {
            const draftResponse = createMockResponse({
                draft: {
                    exists: true,
                    bulk_submission_id: 42,
                    selected_model_ids: [10], // Only model 10 selected in draft
                    excluded_model_ids: [20, 30], // Models 20, 30 excluded in draft
                    responses: [
                        { question_id: 101, answer: true, comment: null },
                    ],
                    comment: 'Draft comment',
                    last_saved: '2024-12-01T10:00:00Z',
                },
            });

            mockGet.mockResolvedValueOnce({ data: draftResponse });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // Draft selection should override API's is_excluded flags
            expect(result.current.draftExists).toBe(true);
            expect(result.current.bulkSubmissionId).toBe(42);
            expect(result.current.selectedModelIds.has(10)).toBe(true);
            expect(result.current.selectedModelIds.has(20)).toBe(false);
            expect(result.current.selectedModelIds.has(30)).toBe(false);
            expect(result.current.excludedModelIds.has(20)).toBe(true);
            expect(result.current.excludedModelIds.has(30)).toBe(true);
            expect(result.current.decisionComment).toBe('Draft comment');
        });

        it('restores question responses from draft', async () => {
            const draftResponse = createMockResponse({
                draft: {
                    exists: true,
                    bulk_submission_id: 42,
                    selected_model_ids: [10, 30],
                    excluded_model_ids: [20],
                    responses: [
                        { question_id: 101, answer: true, comment: null },
                        { question_id: 102, answer: false, comment: 'Needs update' },
                    ],
                    comment: null,
                    last_saved: '2024-12-01T10:00:00Z',
                },
            });

            mockGet.mockResolvedValueOnce({ data: draftResponse });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            const response101 = result.current.responses.get(101);
            const response102 = result.current.responses.get(102);

            expect(response101?.answer).toBe(true);
            expect(response101?.comment).toBe('');
            expect(response102?.answer).toBe(false);
            expect(response102?.comment).toBe('Needs update');
        });
    });

    describe('model selection actions', () => {
        it('toggleModel adds model to selected and removes from excluded', async () => {
            mockGet.mockResolvedValueOnce({ data: createMockResponse() });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // Model 20 starts excluded
            expect(result.current.selectedModelIds.has(20)).toBe(false);
            expect(result.current.excludedModelIds.has(20)).toBe(true);

            // Toggle model 20 to select it
            act(() => {
                result.current.toggleModel(20);
            });

            expect(result.current.selectedModelIds.has(20)).toBe(true);
            expect(result.current.excludedModelIds.has(20)).toBe(false);
            expect(result.current.isDirty).toBe(true);
        });

        it('toggleModel removes model from selected and adds to excluded', async () => {
            mockGet.mockResolvedValueOnce({ data: createMockResponse() });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // Model 10 starts selected
            expect(result.current.selectedModelIds.has(10)).toBe(true);

            // Toggle model 10 to exclude it
            act(() => {
                result.current.toggleModel(10);
            });

            expect(result.current.selectedModelIds.has(10)).toBe(false);
            expect(result.current.excludedModelIds.has(10)).toBe(true);
            expect(result.current.isDirty).toBe(true);
        });

        it('selectAll selects all pending models', async () => {
            mockGet.mockResolvedValueOnce({ data: createMockResponse() });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            act(() => {
                result.current.selectAll();
            });

            expect(result.current.selectedModelIds.size).toBe(3);
            expect(result.current.excludedModelIds.size).toBe(0);
            expect(result.current.selectedModelIds.has(10)).toBe(true);
            expect(result.current.selectedModelIds.has(20)).toBe(true);
            expect(result.current.selectedModelIds.has(30)).toBe(true);
        });

        it('deselectAll moves all pending models to excluded', async () => {
            mockGet.mockResolvedValueOnce({ data: createMockResponse() });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            act(() => {
                result.current.deselectAll();
            });

            expect(result.current.selectedModelIds.size).toBe(0);
            expect(result.current.excludedModelIds.size).toBe(3);
        });
    });

    describe('form responses', () => {
        it('setResponse updates answer for question', async () => {
            mockGet.mockResolvedValueOnce({ data: createMockResponse() });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            act(() => {
                result.current.setResponse(101, true);
            });

            const response = result.current.responses.get(101);
            expect(response?.answer).toBe(true);
            expect(result.current.isDirty).toBe(true);
        });

        it('setResponseComment updates comment for question', async () => {
            mockGet.mockResolvedValueOnce({ data: createMockResponse() });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            act(() => {
                result.current.setResponse(101, false);
                result.current.setResponseComment(101, 'Model needs recalibration');
            });

            const response = result.current.responses.get(101);
            expect(response?.answer).toBe(false);
            expect(response?.comment).toBe('Model needs recalibration');
        });

        it('setDecisionComment updates the overall comment', async () => {
            mockGet.mockResolvedValueOnce({ data: createMockResponse() });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            act(() => {
                result.current.setDecisionComment('Reviewed all models carefully');
            });

            expect(result.current.decisionComment).toBe('Reviewed all models carefully');
            expect(result.current.isDirty).toBe(true);
        });
    });

    describe('validation', () => {
        it('validates at least one model must be selected', async () => {
            mockGet.mockResolvedValueOnce({ data: createMockResponse() });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // Deselect all models
            act(() => {
                result.current.deselectAll();
            });

            expect(result.current.validationErrors).toContain('At least one model must be selected');
            expect(result.current.canSubmit).toBe(false);
        });

        it('validates all questions must be answered', async () => {
            mockGet.mockResolvedValueOnce({ data: createMockResponse() });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // Questions not answered
            expect(result.current.validationErrors).toContain('Question "ATT_Q1" must be answered');
            expect(result.current.validationErrors).toContain('Question "ATT_Q2" must be answered');
            expect(result.current.canSubmit).toBe(false);
        });

        it('validates comment required when question answered No', async () => {
            mockGet.mockResolvedValueOnce({ data: createMockResponse() });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // Answer Q1 with No (requires comment)
            act(() => {
                result.current.setResponse(101, false); // ATT_Q1 requires comment if no
                result.current.setResponse(102, true); // ATT_Q2 does not require comment
            });

            expect(result.current.validationErrors).toContain(
                'Question "ATT_Q1" requires a comment when answered "No"'
            );
            expect(result.current.canSubmit).toBe(false);
        });

        it('allows submission when all validations pass', async () => {
            mockGet.mockResolvedValueOnce({ data: createMockResponse() });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // Answer all questions
            act(() => {
                result.current.setResponse(101, true);
                result.current.setResponse(102, true);
            });

            expect(result.current.validationErrors).toHaveLength(0);
            expect(result.current.canSubmit).toBe(true);
        });
    });

    describe('draft persistence', () => {
        it('saveDraft sends correct payload', async () => {
            mockGet.mockResolvedValueOnce({ data: createMockResponse() });
            mockPost.mockResolvedValueOnce({
                data: {
                    bulk_submission_id: 42,
                    last_saved: '2024-12-01T12:00:00Z',
                },
            });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // Set some responses
            act(() => {
                result.current.setResponse(101, true);
                result.current.setDecisionComment('Test comment');
            });

            await act(async () => {
                await result.current.saveDraft();
            });

            expect(mockPost).toHaveBeenCalledWith('/attestations/bulk/1/draft', {
                selected_model_ids: [10, 30], // Models not excluded
                excluded_model_ids: [20], // Model excluded from API
                responses: expect.arrayContaining([
                    expect.objectContaining({ question_id: 101, answer: true }),
                    expect.objectContaining({ question_id: 102, answer: null }),
                ]),
                comment: 'Test comment',
            });

            expect(result.current.draftExists).toBe(true);
            expect(result.current.bulkSubmissionId).toBe(42);
            expect(result.current.isDirty).toBe(false);
        });

        it('discardDraft resets to initial state', async () => {
            const draftResponse = createMockResponse({
                draft: {
                    exists: true,
                    bulk_submission_id: 42,
                    selected_model_ids: [10],
                    excluded_model_ids: [20, 30],
                    responses: [{ question_id: 101, answer: true, comment: null }],
                    comment: 'Draft comment',
                    last_saved: '2024-12-01T10:00:00Z',
                },
            });

            mockGet.mockResolvedValueOnce({ data: draftResponse });
            mockDelete.mockResolvedValueOnce({});

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.draftExists).toBe(true);
            expect(result.current.selectedModelIds.size).toBe(1);

            await act(async () => {
                await result.current.discardDraft();
            });

            expect(mockDelete).toHaveBeenCalledWith('/attestations/bulk/1/draft');
            expect(result.current.draftExists).toBe(false);
            expect(result.current.bulkSubmissionId).toBeNull();
            expect(result.current.selectedModelIds.size).toBe(3); // All pending models selected
            expect(result.current.decisionComment).toBe('');
            expect(result.current.successMessage).toBe('Draft discarded');
        });
    });

    describe('submission', () => {
        it('submit sends correct payload and reloads data', async () => {
            mockGet.mockResolvedValueOnce({ data: createMockResponse() });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // Answer all questions
            act(() => {
                result.current.setResponse(101, true);
                result.current.setResponse(102, true);
            });

            mockPost.mockResolvedValueOnce({
                data: { message: 'Successfully submitted 2 attestations' },
            });

            // Mock the reload call
            mockGet.mockResolvedValueOnce({
                data: createMockResponse({
                    models: sampleModelsWithExclusions.map(m => ({
                        ...m,
                        attestation_status: m.model_id !== 20 ? 'SUBMITTED' : 'PENDING',
                    })),
                    summary: { ...sampleSummary, pending_count: 1, submitted_count: 2 },
                }),
            });

            let success = false;
            await act(async () => {
                success = await result.current.submit();
            });

            expect(success).toBe(true);
            expect(mockPost).toHaveBeenCalledWith('/attestations/bulk/1/submit', {
                selected_model_ids: [10, 30],
                responses: expect.arrayContaining([
                    expect.objectContaining({ question_id: 101, answer: true }),
                    expect.objectContaining({ question_id: 102, answer: true }),
                ]),
                decision_comment: null,
            });
            expect(result.current.successMessage).toBe('Successfully submitted 2 attestations');
        });

        it('submit returns false when canSubmit is false', async () => {
            mockGet.mockResolvedValueOnce({ data: createMockResponse() });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // Don't answer questions - canSubmit should be false
            expect(result.current.canSubmit).toBe(false);

            let success = true;
            await act(async () => {
                success = await result.current.submit();
            });

            expect(success).toBe(false);
            expect(mockPost).not.toHaveBeenCalledWith(
                expect.stringContaining('/submit'),
                expect.anything()
            );
        });

        it('handles submission error', async () => {
            mockGet.mockResolvedValueOnce({ data: createMockResponse() });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // Answer all questions
            act(() => {
                result.current.setResponse(101, true);
                result.current.setResponse(102, true);
            });

            mockPost.mockRejectedValueOnce({
                response: { data: { detail: 'Submission failed - cycle closed' } },
            });

            let success = true;
            await act(async () => {
                success = await result.current.submit();
            });

            expect(success).toBe(false);
            expect(result.current.error).toBe('Submission failed - cycle closed');
        });
    });

    describe('computed values', () => {
        it('pendingModelIds only includes PENDING status models', async () => {
            const mixedStatusModels = [
                ...sampleModelsWithExclusions,
                {
                    attestation_id: 4,
                    model_id: 40,
                    model_name: 'Already Submitted',
                    risk_tier_code: 'T2',
                    risk_tier_label: 'Tier 2',
                    model_status: 'Active',
                    last_attested_date: null,
                    attestation_status: 'SUBMITTED' as const,
                    is_excluded: false,
                },
            ];

            mockGet.mockResolvedValueOnce({
                data: createMockResponse({ models: mixedStatusModels }),
            });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // Only the 3 PENDING models should be in pendingModelIds
            expect(result.current.pendingModelIds).toHaveLength(3);
            expect(result.current.pendingModelIds).toContain(10);
            expect(result.current.pendingModelIds).toContain(20);
            expect(result.current.pendingModelIds).toContain(30);
            expect(result.current.pendingModelIds).not.toContain(40);
        });
    });

    describe('error and success message handling', () => {
        it('clearError clears error message', async () => {
            mockGet.mockRejectedValueOnce({
                response: { data: { detail: 'Test error' } },
            });

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.error).toBe('Test error');
            });

            act(() => {
                result.current.clearError();
            });

            expect(result.current.error).toBeNull();
        });

        it('clearSuccess clears success message', async () => {
            const draftResponse = createMockResponse({
                draft: {
                    exists: true,
                    bulk_submission_id: 42,
                    selected_model_ids: [10, 30],
                    excluded_model_ids: [20],
                    responses: [],
                    comment: null,
                    last_saved: null,
                },
            });

            mockGet.mockResolvedValueOnce({ data: draftResponse });
            mockDelete.mockResolvedValueOnce({});

            const { result } = renderHook(() => useBulkAttestation(1));

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            await act(async () => {
                await result.current.discardDraft();
            });

            expect(result.current.successMessage).toBe('Draft discarded');

            act(() => {
                result.current.clearSuccess();
            });

            expect(result.current.successMessage).toBeNull();
        });
    });
});
