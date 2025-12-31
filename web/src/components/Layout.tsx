import { Link, useLocation, useMatch, useNavigate, useResolvedPath } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useState, useEffect } from 'react';
import api from '../api/client';

interface LayoutProps {
    children: React.ReactNode;
}

interface CollapsedSections {
    myTasks: boolean;
    monitoring: boolean;
    reportsAudit: boolean;
    configuration: boolean;
}

// Icons as simple SVG components
const ChevronDown = ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
);

const ChevronRight = ({ className = "w-4 h-4" }: { className?: string }) => (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
);

const requiresMonitoringAction = (task: { status?: string; user_role?: string }) => {
    switch (task.user_role) {
        case 'data_provider':
            return task.status === 'DATA_COLLECTION';
        case 'assignee':
            return ['PENDING', 'DATA_COLLECTION', 'UNDER_REVIEW'].includes(task.status ?? '');
        case 'team_member':
            return ['UNDER_REVIEW', 'PENDING_APPROVAL'].includes(task.status ?? '');
        default:
            return false;
    }
};

export default function Layout({ children }: LayoutProps) {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [pendingCounts, setPendingCounts] = useState({
        submissions: 0,
        deployments: 0,
        decommissioning: 0,
        monitoring: 0,
        attestations: 0,
        approvals: 0,
        recommendations: 0,
        irpAttention: 0,
        mrsaAttention: 0
    });

    // Load collapsed state from localStorage
    const [collapsed, setCollapsed] = useState<CollapsedSections>(() => {
        const saved = localStorage.getItem('nav-collapsed');
        if (saved) {
            try {
                return JSON.parse(saved);
            } catch {
                return { myTasks: false, monitoring: false, reportsAudit: false, configuration: true };
            }
        }
        return { myTasks: false, monitoring: false, reportsAudit: false, configuration: true };
    });

    // Persist collapsed state
    useEffect(() => {
        localStorage.setItem('nav-collapsed', JSON.stringify(collapsed));
    }, [collapsed]);

    const toggleSection = (section: keyof CollapsedSections) => {
        setCollapsed(prev => ({ ...prev, [section]: !prev[section] }));
    };

    useEffect(() => {
        const fetchPendingCounts = async () => {
            try {
                // Fetch pending submissions count
                const submissionsRes = await api.get('/validation-workflow/my-pending-submissions');
                const urgentSubmissions = submissionsRes.data.filter((s: any) =>
                    s.urgency === 'overdue' || s.urgency === 'in_grace_period' || s.urgency === 'due_soon'
                ).length;

                // Fetch pending deployment tasks count
                const deploymentsRes = await api.get('/deployment-tasks/my-tasks');
                const pendingDeployments = deploymentsRes.data.filter((t: any) =>
                    t.status === 'PENDING' && (t.days_until_due < 0 || t.days_until_due <= 7)
                ).length;

                // Fetch pending decommissioning requests
                let pendingDecommissioning = 0;
                if (user?.role === 'Admin' || user?.role === 'Validator') {
                    try {
                        const decomRes = await api.get('/decommissioning/pending-validator-review');
                        pendingDecommissioning = decomRes.data.length;
                    } catch {
                        // User may not have permission
                    }
                } else {
                    try {
                        const ownerReviewRes = await api.get('/decommissioning/my-pending-owner-reviews');
                        pendingDecommissioning = ownerReviewRes.data.length;
                    } catch {
                        // Silently fail
                    }
                }

                // Fetch monitoring tasks count
                let pendingMonitoring = 0;
                try {
                    const monitoringRes = await api.get('/monitoring/my-tasks');
                    pendingMonitoring = monitoringRes.data.filter((task: any) =>
                        requiresMonitoringAction(task)
                    ).length;
                } catch {
                    // Silently fail
                }

                // Fetch attestations count
                let pendingAttestations = 0;
                try {
                    const attestationsRes = await api.get('/attestations/my-upcoming');
                    pendingAttestations = attestationsRes.data.pending_count || 0;
                } catch {
                    // Silently fail - attestations may not be set up yet
                }

                // Fetch pending approvals count (for approvers)
                let pendingApprovals = 0;
                try {
                    const approvalsRes = await api.get('/validation-workflow/my-pending-approvals');
                    pendingApprovals = approvalsRes.data.length;
                } catch {
                    // Silently fail - user may not be an approver
                }

                // Fetch recommendation tasks count
                let pendingRecommendations = 0;
                try {
                    const recRes = await api.get('/recommendations/my-tasks');
                    pendingRecommendations = recRes.data.total_tasks || 0;
                } catch {
                    // Silently fail
                }

                // Fetch MRSA reviews needing attention (Admin only - matches nav visibility)
                let irpAttention = 0;
                if (user?.role === 'Admin') {
                    try {
                        const mrsaRes = await api.get('/dashboard/mrsa-reviews/summary');
                        irpAttention = (mrsaRes.data.overdue_count || 0) + (mrsaRes.data.no_irp_count || 0);
                    } catch {
                        // Silent fail - badge just won't show
                    }
                }

                // Fetch MRSA reviews needing attention for model owners/delegates
                let mrsaAttention = 0;
                if (user?.role !== 'Admin' && user?.role !== 'Validator') {
                    try {
                        const mrsaRes = await api.get('/dashboard/mrsa-reviews/summary');
                        mrsaAttention = (mrsaRes.data.overdue_count || 0)
                            + (mrsaRes.data.no_irp_count || 0)
                            + (mrsaRes.data.never_reviewed_count || 0);
                    } catch {
                        // Silent fail - badge just won't show
                    }
                }

                setPendingCounts({
                    submissions: urgentSubmissions,
                    deployments: pendingDeployments,
                    decommissioning: pendingDecommissioning,
                    monitoring: pendingMonitoring,
                    attestations: pendingAttestations,
                    approvals: pendingApprovals,
                    recommendations: pendingRecommendations,
                    irpAttention: irpAttention,
                    mrsaAttention: mrsaAttention
                });
            } catch (error) {
                console.error('Failed to fetch pending counts:', error);
            }
        };

        if (user) {
            fetchPendingCounts();
            const interval = setInterval(fetchPendingCounts, 5 * 60 * 1000);
            return () => clearInterval(interval);
        }
    }, [user]);

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    // Calculate total tasks badge
    const totalTasksBadge = pendingCounts.submissions + pendingCounts.deployments +
        pendingCounts.decommissioning + (user?.role !== 'Admin' ? pendingCounts.attestations : 0) +
        pendingCounts.approvals + pendingCounts.recommendations +
        (user?.role !== 'Admin' && user?.role !== 'Validator' ? pendingCounts.mrsaAttention : 0);
    const isApproverDashboard = location.pathname === '/approver-dashboard';
    const isApproverQueue = isApproverDashboard && location.hash === '#approval-queue';

    // Reusable nav link component
    const NavItem = ({ to, children, badge, badgeColor = 'red', end = false, isActiveOverride }: {
        to: string;
        children: React.ReactNode;
        badge?: number;
        badgeColor?: 'red' | 'purple' | 'green' | 'orange';
        end?: boolean;
        isActiveOverride?: boolean;
    }) => {
        const resolved = useResolvedPath(to);
        const match = useMatch({ path: resolved.pathname, end });
        const isActive = typeof isActiveOverride === 'boolean' ? isActiveOverride : Boolean(match);
        const colorClasses = {
            red: 'bg-red-500',
            purple: 'bg-purple-500',
            green: 'bg-green-500',
            orange: 'bg-orange-500'
        };

        return (
            <li>
                <Link
                    to={to}
                    aria-current={isActive ? 'page' : undefined}
                    className={`block px-4 py-2 rounded transition-colors ${
                        isActive ? 'bg-blue-600 text-white' : 'text-gray-700 hover:bg-gray-100'
                    }`}
                >
                    <div className="flex items-center justify-between">
                        <span>{children}</span>
                        {badge !== undefined && badge > 0 && (
                            <span className={`ml-2 px-2 py-0.5 text-xs font-bold rounded-full ${
                                isActive ? 'bg-white text-blue-600' : `${colorClasses[badgeColor]} text-white`
                            }`}>
                                {badge}
                            </span>
                        )}
                    </div>
                </Link>
            </li>
        );
    };

    // Section header component
    const SectionHeader = ({
        title,
        isCollapsed,
        onToggle,
        badge
    }: {
        title: string;
        isCollapsed: boolean;
        onToggle: () => void;
        badge?: number;
    }) => (
        <li className="pt-4 pb-1">
            <button
                onClick={onToggle}
                className="w-full flex items-center justify-between px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider hover:text-gray-600 transition-colors"
            >
                <div className="flex items-center gap-2">
                    {isCollapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    <span>{title}</span>
                </div>
                {badge !== undefined && badge > 0 && isCollapsed && (
                    <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-red-500 text-white">
                        {badge}
                    </span>
                )}
            </button>
        </li>
    );

    // Subsection divider for configuration
    const SubsectionLabel = ({ label }: { label: string }) => (
        <li className="px-4 pt-3 pb-1">
            <span className="text-xs text-gray-400">{label}</span>
        </li>
    );

    return (
        <div className="min-h-screen bg-gray-100 flex">
            {/* Side Panel */}
            <aside className="w-64 bg-white shadow-lg flex flex-col flex-shrink-0">
                <div className="p-4 border-b">
                    <h1 className="text-xl font-bold text-blue-600">QMIS v0.1</h1>
                </div>
                <nav className="flex-1 p-4 overflow-y-auto">
                    <ul className="space-y-1">
                        {/* ══════════════════════════════════════════════════════════
                            MAIN SECTION - Always visible
                        ══════════════════════════════════════════════════════════ */}

                        {/* Dashboard - role-specific */}
                        {(user?.role === 'Admin' || user?.role === 'Validator') && (
                            <NavItem to={user?.role === 'Admin' ? '/dashboard' : '/validator-dashboard'}>
                                Dashboard
                            </NavItem>
                        )}
                        {(user?.role === 'Global Approver' || user?.role === 'Regional Approver') && (
                            <NavItem
                                to="/approver-dashboard"
                                isActiveOverride={isApproverDashboard && !isApproverQueue}
                            >
                                Approver Dashboard
                            </NavItem>
                        )}
                        {(user?.role !== 'Admin' && user?.role !== 'Validator' && user?.role !== 'Global Approver' && user?.role !== 'Regional Approver') && (
                            <NavItem to="/my-dashboard">My Dashboard</NavItem>
                        )}

                        {/* Core entity views */}
                        <NavItem to={pendingCounts.recommendations > 0 ? "/recommendations?my_tasks=true" : "/recommendations"} badge={pendingCounts.recommendations} badgeColor="purple">Recommendations</NavItem>
                        <NavItem to="/models">Models</NavItem>
                        <NavItem to="/validation-workflow">Validations</NavItem>
                        {user?.role === 'Admin' && (
                            <NavItem to="/attestations">Attestation Management</NavItem>
                        )}
                        {user?.role === 'Admin' && (
                            <NavItem to="/irps" badge={pendingCounts.irpAttention} badgeColor="red">IRP Management</NavItem>
                        )}
                        {(user?.role === 'Admin' || user?.role === 'Validator') && (
                            <NavItem to="/reports/exceptions">Model Exceptions</NavItem>
                        )}

                        {/* ══════════════════════════════════════════════════════════
                            MY TASKS SECTION - Personal action items with badges
                        ══════════════════════════════════════════════════════════ */}
                        <SectionHeader
                            title="My Tasks"
                            isCollapsed={collapsed.myTasks}
                            onToggle={() => toggleSection('myTasks')}
                            badge={totalTasksBadge}
                        />

                        {!collapsed.myTasks && (
                            <>
                                <NavItem to="/my-pending-submissions" badge={pendingCounts.submissions} badgeColor="red">
                                    Pending Submissions
                                </NavItem>
                                <NavItem to="/my-deployment-tasks" badge={pendingCounts.deployments} badgeColor="red">
                                    Pending Deployments
                                </NavItem>
                                <NavItem to="/pending-decommissioning" badge={pendingCounts.decommissioning} badgeColor="purple">
                                    Pending Decommissioning
                                </NavItem>
                                {(user?.role === 'Admin' || user?.role === 'Global Approver' || user?.role === 'Regional Approver') && (
                                    <NavItem
                                        to="/approver-dashboard#approval-queue"
                                        badge={pendingCounts.approvals}
                                        badgeColor="orange"
                                        isActiveOverride={isApproverQueue}
                                    >
                                        Pending Approvals
                                    </NavItem>
                                )}
                                {user?.role !== 'Admin' && (
                                    <NavItem to="/my-attestations" badge={pendingCounts.attestations} badgeColor="orange">
                                        My Attestations
                                    </NavItem>
                                )}
                                {user?.role !== 'Admin' && user?.role !== 'Validator' && (
                                    <NavItem to="/my-mrsa-reviews" badge={pendingCounts.mrsaAttention} badgeColor="red">
                                        My MRSA Reviews
                                    </NavItem>
                                )}
                            </>
                        )}

                        {/* ══════════════════════════════════════════════════════════
                            MONITORING SECTION
                        ══════════════════════════════════════════════════════════ */}
                        <SectionHeader
                            title="Monitoring"
                            isCollapsed={collapsed.monitoring}
                            onToggle={() => toggleSection('monitoring')}
                            badge={user?.role !== 'Admin' ? pendingCounts.monitoring : undefined}
                        />

                        {!collapsed.monitoring && (
                            <>
                                {user?.role === 'Admin' && (
                                    <NavItem to="/monitoring-plans">Performance Monitoring</NavItem>
                                )}
                                {user?.role !== 'Admin' && (
                                    <NavItem to="/my-monitoring-tasks" badge={pendingCounts.monitoring} badgeColor="green">
                                        My Monitoring Tasks
                                    </NavItem>
                                )}
                            </>
                        )}

                        {/* ══════════════════════════════════════════════════════════
                            REPORTS & AUDIT SECTION
                        ══════════════════════════════════════════════════════════ */}
                        <SectionHeader
                            title="Reports & Audit"
                            isCollapsed={collapsed.reportsAudit}
                            onToggle={() => toggleSection('reportsAudit')}
                        />

                        {!collapsed.reportsAudit && (
                            <>
                                <NavItem to="/reports" end>Reports</NavItem>
                                {user?.role === 'Admin' && (
                                    <NavItem to="/analytics">Advanced Analytics</NavItem>
                                )}
                                {(user?.role === 'Admin' || user?.role === 'Validator') && (
                                    <NavItem to="/audit">Audit Logs</NavItem>
                                )}
                            </>
                        )}

                        {/* ══════════════════════════════════════════════════════════
                            CONFIGURATION SECTION - Admin only
                        ══════════════════════════════════════════════════════════ */}
                        {user?.role === 'Admin' && (
                            <>
                                <SectionHeader
                                    title="Configuration"
                                    isCollapsed={collapsed.configuration}
                                    onToggle={() => toggleSection('configuration')}
                                />

                                {!collapsed.configuration && (
                                    <>
                                        {/* Reference Data subsection */}
                                        <SubsectionLabel label="Reference Data" />
                                    <NavItem to="/reference-data">Reference Data</NavItem>
                                    <NavItem
                                        to="/taxonomy"
                                        isActiveOverride={location.pathname === '/taxonomy'
                                            && new URLSearchParams(location.search).get('tab') !== 'component-definitions'}
                                    >
                                        Taxonomy
                                    </NavItem>

                                        {/* Workflow & Policies subsection */}
                                        <SubsectionLabel label="Workflow & Policies" />
                                        <NavItem to="/workflow-config">Workflow Config</NavItem>
                                        <NavItem to="/validation-policies">Validation Policies</NavItem>
                                        <NavItem to="/mrsa-review-policies">MRSA Review Policies</NavItem>
                                        <NavItem to="/approver-roles">Approver Roles</NavItem>
                                        <NavItem to="/additional-approval-rules">Additional Approvals</NavItem>

                                        {/* Governance subsection */}
                                        <SubsectionLabel label="Governance" />
                                        <NavItem to="/regions">Regions</NavItem>
                                        <NavItem to="/batch-delegates">Batch Delegates</NavItem>

                                        {/* Components subsection */}
                                        <SubsectionLabel label="Validation Components" />
                                    <NavItem
                                        to="/taxonomy?tab=component-definitions"
                                        isActiveOverride={location.pathname === '/taxonomy'
                                            && new URLSearchParams(location.search).get('tab') === 'component-definitions'}
                                    >
                                        Component Definitions
                                    </NavItem>
                                    </>
                                )}
                            </>
                        )}

                        {/* Validator-specific: Reference Data & Taxonomy access */}
                        {user?.role === 'Validator' && (
                            <>
                                <SectionHeader
                                    title="Reference"
                                    isCollapsed={collapsed.configuration}
                                    onToggle={() => toggleSection('configuration')}
                                />
                                {!collapsed.configuration && (
                                    <>
                                        <NavItem to="/reference-data">Reference Data</NavItem>
                                        <NavItem to="/taxonomy">Taxonomy</NavItem>
                                    </>
                                )}
                            </>
                        )}
                    </ul>
                </nav>
                <div className="p-4 border-t">
                    <div className="text-sm text-gray-700 mb-2">
                        {user?.full_name}
                        <br />
                        <span className="text-xs text-gray-500">({user?.role})</span>
                    </div>
                    <button
                        onClick={handleLogout}
                        className="btn-secondary text-sm w-full"
                    >
                        Logout
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 p-6 overflow-x-hidden">
                {children}
            </main>
        </div>
    );
}
