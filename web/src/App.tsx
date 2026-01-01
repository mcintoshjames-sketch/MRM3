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
import ValidationAlertsPage from './pages/ValidationAlertsPage';
import ValidationRequestDetailPage from './pages/ValidationRequestDetailPage';
import ValidatorDashboardPage from './pages/ValidatorDashboardPage';
import ModelOwnerDashboardPage from './pages/ModelOwnerDashboardPage';
import WorkflowConfigurationPage from './pages/WorkflowConfigurationPage';
import BatchDelegatesPage from './pages/BatchDelegatesPage';
import RegionsPage from './pages/RegionsPage';
import ValidationPoliciesPage from './pages/ValidationPoliciesPage';
import MRSAReviewPoliciesPage from './pages/MRSAReviewPoliciesPage';
import MyPendingSubmissionsPage from './pages/MyPendingSubmissionsPage';
import MyDeploymentTasksPage from './pages/MyDeploymentTasksPage';
import MyMRSAReviewsPage from './pages/MyMRSAReviewsPage';
import RegionalComplianceReportPage from './pages/RegionalComplianceReportPage';
import ReportsPage from './pages/ReportsPage';
import AnalyticsPage from './pages/AnalyticsPage';
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
import MyPortfolioReportPage from './pages/MyPortfolioReportPage';
import ExceptionsReportPage from './pages/ExceptionsReportPage';
import ReadyToDeployPage from './pages/ReadyToDeployPage';
import PublicLandingPage from './pages/PublicLandingPage';
import PublicOverviewPage from './pages/PublicOverviewPage';
import PublicGuidesIndexPage from './pages/PublicGuidesIndexPage';
import PublicGuidePage from './pages/PublicGuidePage';
import PrivacyPolicyPage from './pages/PrivacyPolicyPage';
import AboutPage from './pages/AboutPage';
import {
    canManageApproverRoles,
    canManageAttestations,
    canManageConditionalApprovals,
    canManageDelegates,
    canManageIrps,
    canManageMonitoringPlans,
    canManageMrsaReviewPolicies,
    canManageRegions,
    canManageTaxonomy,
    canManageUsers,
    canManageValidationPolicies,
    canManageWorkflowConfig,
    canViewAdminDashboard,
    canViewApproverDashboard,
    canViewAuditLogs,
    canViewValidationAlerts,
    canViewValidatorDashboard
} from './utils/roleUtils';

function App() {
    const { user, loading } = useAuth();

    if (loading) {
        return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
    }

    const getDefaultRoute = () => {
        if (!user) return '/login';
        if (canViewAdminDashboard(user)) return '/dashboard';
        if (canViewValidatorDashboard(user)) return '/validator-dashboard';
        if (canViewApproverDashboard(user)) return '/approver-dashboard';
        return '/my-dashboard';
    };

    const isAdminOrValidator = canViewAdminDashboard(user) || canViewValidatorDashboard(user);

    return (
        <Routes>
            <Route path="/" element={user ? <Navigate to={getDefaultRoute()} /> : <PublicLandingPage />} />
            <Route path="/overview" element={<PublicOverviewPage />} />
            <Route path="/guides" element={<PublicGuidesIndexPage />} />
            <Route path="/guides/:slug" element={<PublicGuidePage />} />
            <Route path="/privacy-policy" element={<PrivacyPolicyPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/login" element={!user ? <LoginPage /> : <Navigate to={getDefaultRoute()} />} />
            <Route path="/dashboard" element={canViewAdminDashboard(user) ? <AdminDashboardPage /> : <Navigate to="/models" />} />
            <Route path="/validator-dashboard" element={canViewValidatorDashboard(user) ? <ValidatorDashboardPage /> : <Navigate to="/models" />} />
            <Route path="/approver-dashboard" element={canViewApproverDashboard(user) ? <ApproverDashboardPage /> : <Navigate to="/models" />} />
            <Route path="/my-dashboard" element={
                user
                    ? (isAdminOrValidator
                        ? <Navigate to={getDefaultRoute()} />
                        : (canViewApproverDashboard(user)
                            ? <Navigate to="/approver-dashboard" />
                            : <ModelOwnerDashboardPage />))
                    : <Navigate to="/login" />
            } />
            <Route path="/models" element={user ? <ModelsPage /> : <Navigate to="/login" />} />
            <Route path="/models/:model_id/versions/:version_id" element={user ? <ModelChangeRecordPage /> : <Navigate to="/login" />} />
            <Route path="/models/:id" element={user ? <ModelDetailsPage /> : <Navigate to="/login" />} />
            <Route path="/models/:id/decommission" element={user ? <DecommissioningRequestPage /> : <Navigate to="/login" />} />
            <Route path="/validation-workflow" element={user ? <ValidationWorkflowPage /> : <Navigate to="/login" />} />
            <Route path="/validation-workflow/new" element={user ? <ValidationWorkflowPage /> : <Navigate to="/login" />} />
            <Route path="/validation-workflow/:id" element={user ? <ValidationRequestDetailPage /> : <Navigate to="/login" />} />
            <Route path="/validation-alerts" element={canViewValidationAlerts(user) ? <ValidationAlertsPage /> : <Navigate to="/models" />} />
            <Route path="/recommendations" element={user ? <RecommendationsPage /> : <Navigate to="/login" />} />
            <Route path="/recommendations/:id" element={user ? <RecommendationDetailPage /> : <Navigate to="/login" />} />
            <Route path="/my-pending-submissions" element={user ? <MyPendingSubmissionsPage /> : <Navigate to="/login" />} />
            <Route path="/my-deployment-tasks" element={user ? <MyDeploymentTasksPage /> : <Navigate to="/login" />} />
            <Route path="/my-mrsa-reviews" element={user ? <MyMRSAReviewsPage /> : <Navigate to="/login" />} />
            <Route path="/my-monitoring" element={canManageMonitoringPlans(user) ? <Navigate to="/monitoring-plans" /> : (user ? <MyMonitoringPage /> : <Navigate to="/login" />)} />
            <Route path="/my-monitoring-tasks" element={user ? <MyMonitoringTasksPage /> : <Navigate to="/login" />} />
            <Route path="/pending-decommissioning" element={user ? <PendingDecommissioningPage /> : <Navigate to="/login" />} />
            <Route path="/reference-data" element={canManageTaxonomy(user) ? <ReferenceDataPage /> : <Navigate to="/models" />} />
            <Route path="/vendors" element={<Navigate to="/reference-data" />} />
            <Route path="/vendors/:id" element={canManageTaxonomy(user) ? <VendorDetailsPage /> : <Navigate to="/models" />} />
            <Route path="/users" element={<Navigate to="/reference-data" />} />
            <Route path="/users/:id" element={canManageUsers(user) ? <UserDetailsPage /> : <Navigate to="/models" />} />
            <Route path="/taxonomy" element={canManageTaxonomy(user) ? <TaxonomyPage /> : <Navigate to="/models" />} />
            <Route path="/audit" element={canViewAuditLogs(user) ? <AuditPage /> : <Navigate to="/models" />} />
            <Route path="/workflow-config" element={canManageWorkflowConfig(user) ? <WorkflowConfigurationPage /> : <Navigate to="/models" />} />
            <Route path="/batch-delegates" element={canManageDelegates(user) ? <BatchDelegatesPage /> : <Navigate to="/models" />} />
            <Route path="/regions" element={canManageRegions(user) ? <RegionsPage /> : <Navigate to="/models" />} />
            <Route path="/validation-policies" element={canManageValidationPolicies(user) ? <ValidationPoliciesPage /> : <Navigate to="/models" />} />
            <Route path="/mrsa-review-policies" element={canManageMrsaReviewPolicies(user) ? <MRSAReviewPoliciesPage /> : <Navigate to="/models" />} />
            <Route path="/component-definitions" element={<Navigate to="/taxonomy?tab=component-definitions" />} />
            <Route
                path="/configuration-history"
                element={canManageTaxonomy(user) ? <Navigate to="/taxonomy?tab=component-definitions&componentTab=version-history" /> : <Navigate to="/models" />}
            />
            <Route path="/approver-roles" element={canManageApproverRoles(user) ? <ApproverRolesPage /> : <Navigate to="/models" />} />
            <Route path="/additional-approval-rules" element={canManageConditionalApprovals(user) ? <ConditionalApprovalRulesPage /> : <Navigate to="/models" />} />
            <Route path="/fry-config" element={<Navigate to="/taxonomy" />} />
            <Route path="/monitoring-plans" element={canManageMonitoringPlans(user) ? <MonitoringPlansPage /> : <Navigate to="/models" />} />
            <Route path="/monitoring/:id" element={user ? <MonitoringPlanDetailPage /> : <Navigate to="/login" />} />
            <Route path="/monitoring/cycles/:cycleId" element={user ? <MonitoringCycleDetailPage /> : <Navigate to="/login" />} />
            <Route path="/reports" element={user ? <ReportsPage /> : <Navigate to="/login" />} />
            <Route path="/reports/regional-compliance" element={user ? <RegionalComplianceReportPage /> : <Navigate to="/login" />} />
            <Route path="/reports/deviation-trends" element={user ? <DeviationTrendsReportPage /> : <Navigate to="/login" />} />
            <Route path="/reports/overdue-revalidation" element={user ? <OverdueRevalidationReportPage /> : <Navigate to="/login" />} />
            <Route path="/reports/name-changes" element={user ? <NameChangesReportPage /> : <Navigate to="/login" />} />
            <Route path="/reports/critical-limitations" element={user ? <CriticalLimitationsReportPage /> : <Navigate to="/login" />} />
            <Route path="/reports/kpi" element={user ? <KPIReportPage /> : <Navigate to="/login" />} />
            <Route path="/reports/my-portfolio" element={user ? <MyPortfolioReportPage /> : <Navigate to="/login" />} />
            <Route path="/reports/exceptions" element={user ? <ExceptionsReportPage /> : <Navigate to="/login" />} />
            <Route path="/reports/ready-to-deploy" element={user ? <ReadyToDeployPage /> : <Navigate to="/login" />} />
            <Route path="/analytics" element={user ? <AnalyticsPage /> : <Navigate to="/login" />} />
            <Route path="/attestations" element={canManageAttestations(user) ? <AttestationCyclesPage /> : <Navigate to="/models" />} />
            <Route path="/my-attestations" element={user ? <MyAttestationsPage /> : <Navigate to="/login" />} />
            <Route path="/attestations/:id" element={user ? <AttestationDetailPage /> : <Navigate to="/login" />} />
            <Route path="/attestations/bulk/:cycleId" element={user ? <BulkAttestationPage /> : <Navigate to="/login" />} />
            <Route path="/irps" element={canManageIrps(user) ? <IRPsPage /> : <Navigate to="/models" />} />
            <Route path="/irps/:id" element={user ? <IRPDetailPage /> : <Navigate to="/login" />} />
            <Route path="*" element={<Navigate to={user ? getDefaultRoute() : '/'} />} />
        </Routes>
    );
}

export default App;
