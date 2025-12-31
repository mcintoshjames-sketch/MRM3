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

export const getRoleDisplay = (user?: UserLike | null): string => {
    const roleCode = getUserRoleCode(user);
    if (roleCode && ROLE_CODE_TO_DISPLAY[roleCode]) {
        return ROLE_CODE_TO_DISPLAY[roleCode];
    }
    return user?.role || 'User';
};
