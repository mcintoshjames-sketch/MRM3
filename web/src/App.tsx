import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import LoginPage from './pages/LoginPage';
import ModelsPage from './pages/ModelsPage';
import ModelDetailsPage from './pages/ModelDetailsPage';
import ModelChangeRecordPage from './pages/ModelChangeRecordPage';
import VendorDetailsPage from './pages/VendorDetailsPage';
import UserDetailsPage from './pages/UserDetailsPage';
import TaxonomyPage from './pages/TaxonomyPage';
import AuditPage from './pages/AuditPage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import ValidationWorkflowPage from './pages/ValidationWorkflowPage';
import ValidationRequestDetailPage from './pages/ValidationRequestDetailPage';
import ValidatorDashboardPage from './pages/ValidatorDashboardPage';
import ModelOwnerDashboardPage from './pages/ModelOwnerDashboardPage';
import WorkflowConfigurationPage from './pages/WorkflowConfigurationPage';
import BatchDelegatesPage from './pages/BatchDelegatesPage';
import RegionsPage from './pages/RegionsPage';
import ValidationPoliciesPage from './pages/ValidationPoliciesPage';
import MyPendingSubmissionsPage from './pages/MyPendingSubmissionsPage';
import MyDeploymentTasksPage from './pages/MyDeploymentTasksPage';
import RegionalComplianceReportPage from './pages/RegionalComplianceReportPage';
import ReportsPage from './pages/ReportsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import ComponentDefinitionsPage from './pages/ComponentDefinitionsPage';
import ConfigurationHistoryPage from './pages/ConfigurationHistoryPage';
import DeviationTrendsReportPage from './pages/DeviationTrendsReportPage';
import ApproverRolesPage from './pages/ApproverRolesPage';
import ConditionalApprovalRulesPage from './pages/ConditionalApprovalRulesPage';
// FryConfigPage moved to TaxonomyPage as "FRY 14 Config" tab
import OverdueRevalidationReportPage from './pages/OverdueRevalidationReportPage';
import NameChangesReportPage from './pages/NameChangesReportPage';
import CriticalLimitationsReportPage from './pages/CriticalLimitationsReportPage';
import KPIReportPage from './pages/KPIReportPage';
import DecommissioningRequestPage from './pages/DecommissioningRequestPage';
import PendingDecommissioningPage from './pages/PendingDecommissioningPage';
import MonitoringPlansPage from './pages/MonitoringPlansPage';
import MonitoringPlanDetailPage from './pages/MonitoringPlanDetailPage';
import MonitoringCycleDetailPage from './pages/MonitoringCycleDetailPage';
import MyMonitoringPage from './pages/MyMonitoringPage';
import MyMonitoringTasksPage from './pages/MyMonitoringTasksPage';
import RecommendationsPage from './pages/RecommendationsPage';
import RecommendationDetailPage from './pages/RecommendationDetailPage';
import AttestationCyclesPage from './pages/AttestationCyclesPage';
import MyAttestationsPage from './pages/MyAttestationsPage';
import AttestationDetailPage from './pages/AttestationDetailPage';
import BulkAttestationPage from './pages/BulkAttestationPage';
import ReferenceDataPage from './pages/ReferenceDataPage';
import ApproverDashboardPage from './pages/ApproverDashboardPage';
import IRPsPage from './pages/IRPsPage';
import IRPDetailPage from './pages/IRPDetailPage';

function App() {
    const { user, loading } = useAuth();

    if (loading) {
        return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
    }

    const getDefaultRoute = () => {
        if (!user) return '/login';
        if (user.role === 'Admin') return '/dashboard';
        if (user.role === 'Validator') return '/validator-dashboard';
        return '/my-dashboard';
    };

    return (
        <Routes>
            <Route path="/login" element={!user ? <LoginPage /> : <Navigate to={getDefaultRoute()} />} />
            <Route path="/dashboard" element={user?.role === 'Admin' ? <AdminDashboardPage /> : <Navigate to="/models" />} />
            <Route path="/validator-dashboard" element={user?.role === 'Validator' ? <ValidatorDashboardPage /> : <Navigate to="/models" />} />
            <Route path="/approver-dashboard" element={user?.role === 'Admin' || user?.role === 'Global Approver' || user?.role === 'Regional Approver' ? <ApproverDashboardPage /> : <Navigate to="/models" />} />
            <Route path="/my-dashboard" element={user && user.role !== 'Admin' && user.role !== 'Validator' ? <ModelOwnerDashboardPage /> : <Navigate to={getDefaultRoute()} />} />
            <Route path="/models" element={user ? <ModelsPage /> : <Navigate to="/login" />} />
            <Route path="/models/:model_id/versions/:version_id" element={user ? <ModelChangeRecordPage /> : <Navigate to="/login" />} />
            <Route path="/models/:id" element={user ? <ModelDetailsPage /> : <Navigate to="/login" />} />
            <Route path="/models/:id/decommission" element={user ? <DecommissioningRequestPage /> : <Navigate to="/login" />} />
            <Route path="/validation-workflow" element={user ? <ValidationWorkflowPage /> : <Navigate to="/login" />} />
            <Route path="/validation-workflow/new" element={user ? <ValidationWorkflowPage /> : <Navigate to="/login" />} />
            <Route path="/validation-workflow/:id" element={user ? <ValidationRequestDetailPage /> : <Navigate to="/login" />} />
            <Route path="/recommendations" element={user ? <RecommendationsPage /> : <Navigate to="/login" />} />
            <Route path="/recommendations/:id" element={user ? <RecommendationDetailPage /> : <Navigate to="/login" />} />
            <Route path="/my-pending-submissions" element={user ? <MyPendingSubmissionsPage /> : <Navigate to="/login" />} />
            <Route path="/my-deployment-tasks" element={user ? <MyDeploymentTasksPage /> : <Navigate to="/login" />} />
            <Route path="/my-monitoring" element={user?.role === 'Admin' ? <Navigate to="/monitoring-plans" /> : (user ? <MyMonitoringPage /> : <Navigate to="/login" />)} />
            <Route path="/my-monitoring-tasks" element={user ? <MyMonitoringTasksPage /> : <Navigate to="/login" />} />
            <Route path="/pending-decommissioning" element={user ? <PendingDecommissioningPage /> : <Navigate to="/login" />} />
            <Route path="/reference-data" element={user?.role === 'Admin' || user?.role === 'Validator' ? <ReferenceDataPage /> : <Navigate to="/models" />} />
            <Route path="/vendors" element={<Navigate to="/reference-data" />} />
            <Route path="/vendors/:id" element={user?.role === 'Admin' || user?.role === 'Validator' ? <VendorDetailsPage /> : <Navigate to="/models" />} />
            <Route path="/users" element={<Navigate to="/reference-data" />} />
            <Route path="/users/:id" element={user?.role === 'Admin' || user?.role === 'Validator' ? <UserDetailsPage /> : <Navigate to="/models" />} />
            <Route path="/taxonomy" element={user?.role === 'Admin' || user?.role === 'Validator' ? <TaxonomyPage /> : <Navigate to="/models" />} />
            <Route path="/audit" element={user?.role === 'Admin' || user?.role === 'Validator' ? <AuditPage /> : <Navigate to="/models" />} />
            <Route path="/workflow-config" element={user?.role === 'Admin' ? <WorkflowConfigurationPage /> : <Navigate to="/models" />} />
            <Route path="/batch-delegates" element={user?.role === 'Admin' ? <BatchDelegatesPage /> : <Navigate to="/models" />} />
            <Route path="/regions" element={user?.role === 'Admin' ? <RegionsPage /> : <Navigate to="/models" />} />
            <Route path="/validation-policies" element={user?.role === 'Admin' ? <ValidationPoliciesPage /> : <Navigate to="/models" />} />
            <Route path="/component-definitions" element={user?.role === 'Admin' ? <ComponentDefinitionsPage /> : <Navigate to="/models" />} />
            <Route path="/configuration-history" element={user?.role === 'Admin' ? <ConfigurationHistoryPage /> : <Navigate to="/models" />} />
            <Route path="/approver-roles" element={user?.role === 'Admin' ? <ApproverRolesPage /> : <Navigate to="/models" />} />
            <Route path="/additional-approval-rules" element={user?.role === 'Admin' ? <ConditionalApprovalRulesPage /> : <Navigate to="/models" />} />
            <Route path="/fry-config" element={<Navigate to="/taxonomy" />} />
            <Route path="/monitoring-plans" element={user?.role === 'Admin' ? <MonitoringPlansPage /> : <Navigate to="/models" />} />
            <Route path="/monitoring/:id" element={user ? <MonitoringPlanDetailPage /> : <Navigate to="/login" />} />
            <Route path="/monitoring/cycles/:cycleId" element={user ? <MonitoringCycleDetailPage /> : <Navigate to="/login" />} />
            <Route path="/reports" element={user ? <ReportsPage /> : <Navigate to="/login" />} />
            <Route path="/reports/regional-compliance" element={user ? <RegionalComplianceReportPage /> : <Navigate to="/login" />} />
            <Route path="/reports/deviation-trends" element={user ? <DeviationTrendsReportPage /> : <Navigate to="/login" />} />
            <Route path="/reports/overdue-revalidation" element={user ? <OverdueRevalidationReportPage /> : <Navigate to="/login" />} />
            <Route path="/reports/name-changes" element={user ? <NameChangesReportPage /> : <Navigate to="/login" />} />
            <Route path="/reports/critical-limitations" element={user ? <CriticalLimitationsReportPage /> : <Navigate to="/login" />} />
            <Route path="/reports/kpi" element={user ? <KPIReportPage /> : <Navigate to="/login" />} />
            <Route path="/analytics" element={user ? <AnalyticsPage /> : <Navigate to="/login" />} />
            <Route path="/attestations" element={user?.role === 'Admin' ? <AttestationCyclesPage /> : <Navigate to="/models" />} />
            <Route path="/my-attestations" element={user ? <MyAttestationsPage /> : <Navigate to="/login" />} />
            <Route path="/attestations/:id" element={user ? <AttestationDetailPage /> : <Navigate to="/login" />} />
            <Route path="/attestations/bulk/:cycleId" element={user ? <BulkAttestationPage /> : <Navigate to="/login" />} />
            <Route path="/irps" element={user?.role === 'Admin' ? <IRPsPage /> : <Navigate to="/models" />} />
            <Route path="/irps/:id" element={user?.role === 'Admin' ? <IRPDetailPage /> : <Navigate to="/models" />} />
            <Route path="/" element={<Navigate to={getDefaultRoute()} />} />
        </Routes>
    );
}

export default App;
