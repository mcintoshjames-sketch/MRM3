import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useState, useEffect } from 'react';
import api from '../api/client';

interface LayoutProps {
    children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [pendingCounts, setPendingCounts] = useState({
        submissions: 0,
        deployments: 0,
        decommissioning: 0,
        monitoring: 0
    });

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
                    // Admins/Validators see pending validator reviews
                    try {
                        const decomRes = await api.get('/decommissioning/pending-validator-review');
                        pendingDecommissioning = decomRes.data.length;
                    } catch {
                        // User may not have permission
                    }
                } else {
                    // Model owners see pending owner reviews for their models
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
                    // Count tasks that need action (overdue or have action needed)
                    pendingMonitoring = monitoringRes.data.filter((t: any) =>
                        t.is_overdue || t.action_needed.includes('Submit') || t.action_needed.includes('Review') || t.action_needed.includes('Approve')
                    ).length;
                } catch {
                    // Silently fail
                }

                setPendingCounts({
                    submissions: urgentSubmissions,
                    deployments: pendingDeployments,
                    decommissioning: pendingDecommissioning,
                    monitoring: pendingMonitoring
                });
            } catch (error) {
                // Silently fail - badges will just show 0
                console.error('Failed to fetch pending counts:', error);
            }
        };

        if (user) {
            fetchPendingCounts();
            // Refresh counts every 5 minutes
            const interval = setInterval(fetchPendingCounts, 5 * 60 * 1000);
            return () => clearInterval(interval);
        }
    }, [user]);

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    return (
        <div className="min-h-screen bg-gray-100 flex">
            {/* Side Panel */}
            <aside className="w-64 bg-white shadow-lg flex flex-col flex-shrink-0">
                <div className="p-4 border-b">
                    <h1 className="text-xl font-bold text-blue-600">MRM System v3</h1>
                </div>
                <nav className="flex-1 p-4">
                    <ul className="space-y-2">
                        {(user?.role === 'Admin' || user?.role === 'Validator') && (
                            <li>
                                <NavLink
                                    to={user?.role === 'Admin' ? '/dashboard' : '/validator-dashboard'}
                                    className={({ isActive }) =>
                                        `block px-4 py-2 rounded transition-colors ${isActive
                                            ? 'bg-blue-600 text-white'
                                            : 'text-gray-700 hover:bg-gray-100'
                                        }`
                                    }
                                >
                                    Dashboard
                                </NavLink>
                            </li>
                        )}
                        {(user?.role !== 'Admin' && user?.role !== 'Validator') && (
                            <li>
                                <NavLink
                                    to="/my-dashboard"
                                    className={({ isActive }) =>
                                        `block px-4 py-2 rounded transition-colors ${isActive
                                            ? 'bg-blue-600 text-white'
                                            : 'text-gray-700 hover:bg-gray-100'
                                        }`
                                    }
                                >
                                    My Dashboard
                                </NavLink>
                            </li>
                        )}
                        <li>
                            <NavLink
                                to="/models"
                                className={({ isActive }) =>
                                    `block px-4 py-2 rounded transition-colors ${isActive
                                        ? 'bg-blue-600 text-white'
                                        : 'text-gray-700 hover:bg-gray-100'
                                    }`
                                }
                            >
                                Models
                            </NavLink>
                        </li>
                        <li>
                            <NavLink
                                to="/validation-workflow"
                                className={({ isActive }) =>
                                    `block px-4 py-2 rounded transition-colors ${isActive
                                        ? 'bg-blue-600 text-white'
                                        : 'text-gray-700 hover:bg-gray-100'
                                    }`
                                }
                            >
                                Validations
                            </NavLink>
                        </li>
                        <li>
                            <NavLink
                                to="/recommendations"
                                className={({ isActive }) =>
                                    `block px-4 py-2 rounded transition-colors ${isActive
                                        ? 'bg-blue-600 text-white'
                                        : 'text-gray-700 hover:bg-gray-100'
                                    }`
                                }
                            >
                                Recommendations
                            </NavLink>
                        </li>
                        <li>
                            <NavLink
                                to="/my-pending-submissions"
                                className={({ isActive }) =>
                                    `block px-4 py-2 rounded transition-colors ${isActive
                                        ? 'bg-blue-600 text-white'
                                        : 'text-gray-700 hover:bg-gray-100'
                                    }`
                                }
                            >
                                {({ isActive }) => (
                                    <div className="flex items-center justify-between">
                                        <span>Pending Submissions</span>
                                        {pendingCounts.submissions > 0 && (
                                            <span className={`ml-2 px-2 py-0.5 text-xs font-bold rounded-full ${
                                                isActive ? 'bg-white text-blue-600' : 'bg-red-500 text-white'
                                            }`}>
                                                {pendingCounts.submissions}
                                            </span>
                                        )}
                                    </div>
                                )}
                            </NavLink>
                        </li>
                        <li>
                            <NavLink
                                to="/my-deployment-tasks"
                                className={({ isActive }) =>
                                    `block px-4 py-2 rounded transition-colors ${isActive
                                        ? 'bg-blue-600 text-white'
                                        : 'text-gray-700 hover:bg-gray-100'
                                    }`
                                }
                            >
                                {({ isActive }) => (
                                    <div className="flex items-center justify-between">
                                        <span>Pending Deployments</span>
                                        {pendingCounts.deployments > 0 && (
                                            <span className={`ml-2 px-2 py-0.5 text-xs font-bold rounded-full ${
                                                isActive ? 'bg-white text-blue-600' : 'bg-red-500 text-white'
                                            }`}>
                                                {pendingCounts.deployments}
                                            </span>
                                        )}
                                    </div>
                                )}
                            </NavLink>
                        </li>
                        <li>
                            <NavLink
                                to="/pending-decommissioning"
                                className={({ isActive }) =>
                                    `block px-4 py-2 rounded transition-colors ${isActive
                                        ? 'bg-blue-600 text-white'
                                        : 'text-gray-700 hover:bg-gray-100'
                                    }`
                                }
                            >
                                {({ isActive }) => (
                                    <div className="flex items-center justify-between">
                                        <span>Pending Decommissioning</span>
                                        {pendingCounts.decommissioning > 0 && (
                                            <span className={`ml-2 px-2 py-0.5 text-xs font-bold rounded-full ${
                                                isActive ? 'bg-white text-blue-600' : 'bg-purple-500 text-white'
                                            }`}>
                                                {pendingCounts.decommissioning}
                                            </span>
                                        )}
                                    </div>
                                )}
                            </NavLink>
                        </li>
                        {/* Monitoring Section */}
                        <li className="pt-4 pb-1">
                            <span className="px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                                Monitoring
                            </span>
                        </li>
                        <li>
                            <NavLink
                                to="/my-monitoring"
                                className={({ isActive }) =>
                                    `block px-4 py-2 rounded transition-colors ${isActive
                                        ? 'bg-blue-600 text-white'
                                        : 'text-gray-700 hover:bg-gray-100'
                                    }`
                                }
                            >
                                {({ isActive }) => (
                                    <div className="flex items-center justify-between">
                                        <span>My Monitoring Tasks</span>
                                        {pendingCounts.monitoring > 0 && (
                                            <span className={`ml-2 px-2 py-0.5 text-xs font-bold rounded-full ${
                                                isActive ? 'bg-white text-blue-600' : 'bg-green-500 text-white'
                                            }`}>
                                                {pendingCounts.monitoring}
                                            </span>
                                        )}
                                    </div>
                                )}
                            </NavLink>
                        </li>
                        {user?.role === 'Admin' && (
                            <li>
                                <NavLink
                                    to="/monitoring-plans"
                                    className={({ isActive }) =>
                                        `block px-4 py-2 rounded transition-colors ${isActive
                                            ? 'bg-blue-600 text-white'
                                            : 'text-gray-700 hover:bg-gray-100'
                                        }`
                                    }
                                >
                                    Monitoring Plans
                                </NavLink>
                            </li>
                        )}
                        {(user?.role === 'Admin' || user?.role === 'Validator') && (
                            <>
                                <li>
                                    <NavLink
                                        to="/vendors"
                                        className={({ isActive }) =>
                                            `block px-4 py-2 rounded transition-colors ${isActive
                                                ? 'bg-blue-600 text-white'
                                                : 'text-gray-700 hover:bg-gray-100'
                                            }`
                                        }
                                    >
                                        Vendors
                                    </NavLink>
                                </li>
                                <li>
                                    <NavLink
                                        to="/users"
                                        className={({ isActive }) =>
                                            `block px-4 py-2 rounded transition-colors ${isActive
                                                ? 'bg-blue-600 text-white'
                                                : 'text-gray-700 hover:bg-gray-100'
                                            }`
                                        }
                                    >
                                        Users
                                    </NavLink>
                                </li>
                                <li>
                                    <NavLink
                                        to="/taxonomy"
                                        className={({ isActive }) =>
                                            `block px-4 py-2 rounded transition-colors ${isActive
                                                ? 'bg-blue-600 text-white'
                                                : 'text-gray-700 hover:bg-gray-100'
                                            }`
                                        }
                                    >
                                        Taxonomy
                                    </NavLink>
                                </li>
                            </>
                        )}
                        <li>
                            <NavLink
                                to="/reports"
                                className={({ isActive }) =>
                                    `block px-4 py-2 rounded transition-colors ${isActive
                                        ? 'bg-blue-600 text-white'
                                        : 'text-gray-700 hover:bg-gray-100'
                                    }`
                                }
                            >
                                Reports
                            </NavLink>
                        </li>
                        {(user?.role === 'Admin' || user?.role === 'Validator') && (
                            <li>
                                <NavLink
                                    to="/audit"
                                    className={({ isActive }) =>
                                        `block px-4 py-2 rounded transition-colors ${isActive
                                            ? 'bg-blue-600 text-white'
                                            : 'text-gray-700 hover:bg-gray-100'
                                        }`
                                    }
                                >
                                    Audit Logs
                                </NavLink>
                            </li>
                        )}
                        {user?.role === 'Admin' && (
                            <>
                                <li>
                                    <NavLink
                                        to="/workflow-config"
                                        className={({ isActive }) =>
                                            `block px-4 py-2 rounded transition-colors ${isActive
                                                ? 'bg-blue-600 text-white'
                                                : 'text-gray-700 hover:bg-gray-100'
                                            }`
                                        }
                                    >
                                        Workflow Config
                                    </NavLink>
                                </li>
                                <li>
                                    <NavLink
                                        to="/batch-delegates"
                                        className={({ isActive }) =>
                                            `block px-4 py-2 rounded transition-colors ${isActive
                                                ? 'bg-blue-600 text-white'
                                                : 'text-gray-700 hover:bg-gray-100'
                                            }`
                                        }
                                    >
                                        Batch Delegates
                                    </NavLink>
                                </li>
                                <li>
                                    <NavLink
                                        to="/regions"
                                        className={({ isActive }) =>
                                            `block px-4 py-2 rounded transition-colors ${isActive
                                                ? 'bg-blue-600 text-white'
                                                : 'text-gray-700 hover:bg-gray-100'
                                            }`
                                        }
                                    >
                                        Regions
                                    </NavLink>
                                </li>
                                <li>
                                    <NavLink
                                        to="/validation-policies"
                                        className={({ isActive }) =>
                                            `block px-4 py-2 rounded transition-colors ${isActive
                                                ? 'bg-blue-600 text-white'
                                                : 'text-gray-700 hover:bg-gray-100'
                                            }`
                                        }
                                    >
                                        Validation Policies
                                    </NavLink>
                                </li>
                                <li>
                                    <NavLink
                                        to="/component-definitions"
                                        className={({ isActive }) =>
                                            `block px-4 py-2 rounded transition-colors ${isActive
                                                ? 'bg-blue-600 text-white'
                                                : 'text-gray-700 hover:bg-gray-100'
                                            }`
                                        }
                                    >
                                        Component Definitions
                                    </NavLink>
                                </li>
                                <li>
                                    <NavLink
                                        to="/configuration-history"
                                        className={({ isActive }) =>
                                            `block px-4 py-2 rounded transition-colors ${isActive
                                                ? 'bg-blue-600 text-white'
                                                : 'text-gray-700 hover:bg-gray-100'
                                            }`
                                        }
                                    >
                                        Configuration History
                                    </NavLink>
                                </li>
                                <li>
                                    <NavLink
                                        to="/approver-roles"
                                        className={({ isActive }) =>
                                            `block px-4 py-2 rounded transition-colors ${isActive
                                                ? 'bg-blue-600 text-white'
                                                : 'text-gray-700 hover:bg-gray-100'
                                            }`
                                        }
                                    >
                                        Approver Roles
                                    </NavLink>
                                </li>
                                <li>
                                    <NavLink
                                        to="/additional-approval-rules"
                                        className={({ isActive }) =>
                                            `block px-4 py-2 rounded transition-colors ${isActive
                                                ? 'bg-blue-600 text-white'
                                                : 'text-gray-700 hover:bg-gray-100'
                                            }`
                                        }
                                    >
                                        Additional Approvals
                                    </NavLink>
                                </li>
                                <li>
                                    <NavLink
                                        to="/analytics"
                                        className={({ isActive }) =>
                                            `block px-4 py-2 rounded transition-colors ${isActive
                                                ? 'bg-blue-600 text-white'
                                                : 'text-gray-700 hover:bg-gray-100'
                                            }`
                                        }
                                    >
                                        Advanced Analytics
                                    </NavLink>
                                </li>
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
