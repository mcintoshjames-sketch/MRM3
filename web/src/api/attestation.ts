import api from './client';

export type AttestationChangeType = 'MODEL_EDIT' | 'NEW_MODEL' | 'DECOMMISSION';

export interface AttestationChangeLinkCreate {
    change_type: AttestationChangeType;
    model_id?: number;
    pending_edit_id?: number;
    decommissioning_request_id?: number;
}

export interface AttestationContext {
    attestation_id: number;
    model_id?: number;
}

const ATTESTATION_CONTEXT_KEY = 'attestation_context';

/**
 * Create a change link for an attestation
 */
export const createAttestationChangeLink = async (
    attestationId: number,
    data: AttestationChangeLinkCreate
): Promise<void> => {
    await api.post(`/attestations/records/${attestationId}/link-change`, data);
};

/**
 * Get attestation context from sessionStorage if present
 */
export const getAttestationContext = (): AttestationContext | null => {
    const contextStr = sessionStorage.getItem(ATTESTATION_CONTEXT_KEY);
    if (!contextStr) return null;

    try {
        return JSON.parse(contextStr) as AttestationContext;
    } catch {
        return null;
    }
};

/**
 * Clear attestation context from sessionStorage
 */
export const clearAttestationContext = (): void => {
    sessionStorage.removeItem(ATTESTATION_CONTEXT_KEY);
};

/**
 * Helper to create an attestation link if context is present and then clear it.
 * Silently handles errors (logs to console but doesn't throw).
 *
 * @param changeType - The type of change being linked
 * @param options - Additional options based on change type
 *   - model_id: Required for MODEL_EDIT and NEW_MODEL
 *   - pending_edit_id: Optional for MODEL_EDIT
 *   - decommissioning_request_id: Required for DECOMMISSION
 */
export const linkChangeToAttestationIfPresent = async (
    changeType: AttestationChangeType,
    options: {
        model_id?: number;
        pending_edit_id?: number;
        decommissioning_request_id?: number;
    }
): Promise<void> => {
    const context = getAttestationContext();
    if (!context) return;

    try {
        await createAttestationChangeLink(context.attestation_id, {
            change_type: changeType,
            model_id: options.model_id,
            pending_edit_id: options.pending_edit_id,
            decommissioning_request_id: options.decommissioning_request_id,
        });
        console.log(`Successfully linked ${changeType} to attestation ${context.attestation_id}`);
    } catch (error) {
        // Log error but don't fail the main operation
        console.error('Failed to link change to attestation:', error);
    } finally {
        // Always clear the context after attempting to create link
        clearAttestationContext();
    }
};

export const attestationApi = {
    createChangeLink: createAttestationChangeLink,
    getContext: getAttestationContext,
    clearContext: clearAttestationContext,
    linkChangeIfPresent: linkChangeToAttestationIfPresent,
};

export default attestationApi;
