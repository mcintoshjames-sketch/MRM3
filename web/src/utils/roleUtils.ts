export type RoleCode =
    | 'ADMIN'
    | 'USER'
    | 'VALIDATOR'
    | 'GLOBAL_APPROVER'
    | 'REGIONAL_APPROVER';

export const ROLE_CODE_TO_DISPLAY: Record<RoleCode, string> = {
    ADMIN: 'Admin',
    USER: 'User',
    VALIDATOR: 'Validator',
    GLOBAL_APPROVER: 'Global Approver',
    REGIONAL_APPROVER: 'Regional Approver'
};

const ROLE_DISPLAY_TO_CODE: Record<string, RoleCode> = {
    admin: 'ADMIN',
    administrator: 'ADMIN',
    user: 'USER',
    validator: 'VALIDATOR',
    'global approver': 'GLOBAL_APPROVER',
    global_approver: 'GLOBAL_APPROVER',
    'regional approver': 'REGIONAL_APPROVER',
    regional_approver: 'REGIONAL_APPROVER'
};

export type UserLike = {
    role_code?: string | null;
    role?: string | null;
    capabilities?: Record<string, boolean> | null;
};

const hasCapability = (
    user: UserLike | null | undefined,
    capability: string,
    fallback?: () => boolean
): boolean => {
    const value = user?.capabilities?.[capability];
    if (value !== undefined) {
        return value;
    }
    return fallback ? fallback() : false;
};

export const normalizeRoleCode = (value?: string | null): RoleCode | null => {
    if (!value) return null;
    const trimmed = value.trim();
    if (!trimmed) return null;
    const upper = trimmed.toUpperCase().replace(/ /g, '_');
    if (upper in ROLE_CODE_TO_DISPLAY) {
        return upper as RoleCode;
    }
    return ROLE_DISPLAY_TO_CODE[trimmed.toLowerCase()] ?? null;
};

export const getUserRoleCode = (user?: UserLike | null): RoleCode | null => {
    if (!user) return null;
    return normalizeRoleCode(user.role_code) ?? normalizeRoleCode(user.role);
};

export const isAdmin = (user?: UserLike | null): boolean => {
    if (user?.capabilities?.is_admin !== undefined) {
        return user.capabilities.is_admin;
    }
    return getUserRoleCode(user) === 'ADMIN';
};

export const isValidator = (user?: UserLike | null): boolean => {
    if (user?.capabilities?.is_validator !== undefined) {
        return user.capabilities.is_validator;
    }
    return getUserRoleCode(user) === 'VALIDATOR';
};

export const isGlobalApprover = (user?: UserLike | null): boolean => {
    if (user?.capabilities?.is_global_approver !== undefined) {
        return user.capabilities.is_global_approver;
    }
    return getUserRoleCode(user) === 'GLOBAL_APPROVER';
};

export const isRegionalApprover = (user?: UserLike | null): boolean => {
    if (user?.capabilities?.is_regional_approver !== undefined) {
        return user.capabilities.is_regional_approver;
    }
    return getUserRoleCode(user) === 'REGIONAL_APPROVER';
};

export const isApprover = (user?: UserLike | null): boolean =>
    isGlobalApprover(user) || isRegionalApprover(user);

export const isAdminOrValidator = (user?: UserLike | null): boolean =>
    isAdmin(user) || isValidator(user);

export const canViewAdminDashboard = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_view_admin_dashboard', () => isAdmin(user));

export const canViewValidatorDashboard = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_view_validator_dashboard', () => isValidator(user));

export const canViewApproverDashboard = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_view_approver_dashboard', () => isAdmin(user) || isApprover(user));

export const canViewAuditLogs = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_view_audit_logs', () => isAdminOrValidator(user));

export const canViewValidationAlerts = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_view_validation_alerts', () => isAdmin(user));

export const canManageUsers = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_manage_users', () => isAdmin(user));

export const canManageTaxonomy = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_manage_taxonomy', () => isAdminOrValidator(user));

export const canManageRegions = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_manage_regions', () => isAdmin(user));

export const canManageWorkflowConfig = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_manage_workflow_config', () => isAdmin(user));

export const canManageDelegates = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_manage_delegates', () => isAdmin(user));

export const canManageValidationPolicies = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_manage_validation_policies', () => isAdmin(user));

export const canManageMrsaReviewPolicies = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_manage_mrsa_review_policies', () => isAdmin(user));

export const canManageApproverRoles = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_manage_approver_roles', () => isAdmin(user));

export const canManageConditionalApprovals = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_manage_conditional_approvals', () => isAdmin(user));

export const canManageMonitoringPlans = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_manage_monitoring_plans', () => isAdmin(user));

export const canEditMonitoringPlan = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_edit_monitoring_plan', () => isAdmin(user));

export const canManageAttestations = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_manage_attestations', () => isAdmin(user));

export const canManageIrps = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_manage_irps', () => isAdmin(user));

export const canManageModels = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_manage_models', () => isAdmin(user));

export const canManageModelRelationships = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_manage_model_relationships', () => isAdmin(user));

export const canManageLob = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_manage_lob', () => isAdmin(user));

export const canManageValidations = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_manage_validations', () => isAdminOrValidator(user));

export const canManageRecommendations = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_manage_recommendations', () => isAdminOrValidator(user));

export const canManageDecommissioning = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_manage_decommissioning', () => isAdminOrValidator(user));

export const canApproveModel = (user?: UserLike | null): boolean =>
    hasCapability(user, 'can_approve_model', () => isAdmin(user));

export const getRoleDisplay = (user?: UserLike | null): string => {
    const roleCode = getUserRoleCode(user);
    if (roleCode && ROLE_CODE_TO_DISPLAY[roleCode]) {
        return ROLE_CODE_TO_DISPLAY[roleCode];
    }
    return user?.role || 'User';
};
