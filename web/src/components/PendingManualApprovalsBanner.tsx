import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import api from '../api/client';

interface PendingManualApprovalItem {
    request_id: number;
}

interface PendingManualApprovalsResponse {
    count: number;
    pending_approvals?: PendingManualApprovalItem[];
}

const DASHBOARD_PATHS = new Set([
    '/dashboard',
    '/my-dashboard',
    '/approver-dashboard',
    '/validator-dashboard'
]);

export default function PendingManualApprovalsBanner() {
    const [count, setCount] = useState(0);
    const [pendingApprovals, setPendingApprovals] = useState<PendingManualApprovalItem[]>([]);
    const location = useLocation();

    useEffect(() => {
        let active = true;
        const fetchPendingApprovals = async () => {
            try {
                const response = await api.get<PendingManualApprovalsResponse>(
                    '/validation-workflow/dashboard/my-pending-approvals'
                );
                if (active) {
                    setCount(response.data?.count ?? 0);
                    setPendingApprovals(response.data?.pending_approvals ?? []);
                }
            } catch {
                if (active) {
                    setCount(0);
                    setPendingApprovals([]);
                }
            }
        };
        fetchPendingApprovals();
        return () => {
            active = false;
        };
    }, []);

    const pendingRequestIds = useMemo(() => {
        const ids = pendingApprovals.map(approval => approval.request_id).filter(Number.isFinite);
        return Array.from(new Set(ids));
    }, [pendingApprovals]);

    const singleRequestId = pendingRequestIds.length === 1 ? pendingRequestIds[0] : null;
    const targetLink = singleRequestId
        ? `/validation-workflow/${singleRequestId}?tab=approvals`
        : '/validation-workflow?assigned_to_me=true';

    if (!DASHBOARD_PATHS.has(location.pathname) || count < 1) {
        return null;
    }

    return (
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-6 rounded">
            <div className="flex items-center">
                <div className="text-sm text-yellow-800">
                    You have <strong>{count}</strong> pending approval request(s) assigned to you.{' '}
                    <Link to={targetLink} className="underline text-yellow-900">
                        View now
                    </Link>
                </div>
            </div>
        </div>
    );
}
