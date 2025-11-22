import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import LoginPage from './pages/LoginPage';
import ModelsPage from './pages/ModelsPage';
import ModelDetailsPage from './pages/ModelDetailsPage';
import ModelChangeRecordPage from './pages/ModelChangeRecordPage';
import VendorsPage from './pages/VendorsPage';
import VendorDetailsPage from './pages/VendorDetailsPage';
import UsersPage from './pages/UsersPage';
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
            <Route path="/my-dashboard" element={user && user.role !== 'Admin' && user.role !== 'Validator' ? <ModelOwnerDashboardPage /> : <Navigate to={getDefaultRoute()} />} />
            <Route path="/models" element={user ? <ModelsPage /> : <Navigate to="/login" />} />
            <Route path="/models/:model_id/versions/:version_id" element={user ? <ModelChangeRecordPage /> : <Navigate to="/login" />} />
            <Route path="/models/:id" element={user ? <ModelDetailsPage /> : <Navigate to="/login" />} />
            <Route path="/validation-workflow" element={user ? <ValidationWorkflowPage /> : <Navigate to="/login" />} />
            <Route path="/validation-workflow/new" element={user ? <ValidationWorkflowPage /> : <Navigate to="/login" />} />
            <Route path="/validation-workflow/:id" element={user ? <ValidationRequestDetailPage /> : <Navigate to="/login" />} />
            <Route path="/my-pending-submissions" element={user ? <MyPendingSubmissionsPage /> : <Navigate to="/login" />} />
            <Route path="/my-deployment-tasks" element={user ? <MyDeploymentTasksPage /> : <Navigate to="/login" />} />
            <Route path="/vendors" element={user ? <VendorsPage /> : <Navigate to="/login" />} />
            <Route path="/vendors/:id" element={user ? <VendorDetailsPage /> : <Navigate to="/login" />} />
            <Route path="/users" element={user ? <UsersPage /> : <Navigate to="/login" />} />
            <Route path="/users/:id" element={user ? <UserDetailsPage /> : <Navigate to="/login" />} />
            <Route path="/taxonomy" element={user ? <TaxonomyPage /> : <Navigate to="/login" />} />
            <Route path="/audit" element={user ? <AuditPage /> : <Navigate to="/login" />} />
            <Route path="/workflow-config" element={user?.role === 'Admin' ? <WorkflowConfigurationPage /> : <Navigate to="/models" />} />
            <Route path="/batch-delegates" element={user?.role === 'Admin' ? <BatchDelegatesPage /> : <Navigate to="/models" />} />
            <Route path="/regions" element={user?.role === 'Admin' ? <RegionsPage /> : <Navigate to="/models" />} />
            <Route path="/validation-policies" element={user?.role === 'Admin' ? <ValidationPoliciesPage /> : <Navigate to="/models" />} />
            <Route path="/component-definitions" element={user?.role === 'Admin' ? <ComponentDefinitionsPage /> : <Navigate to="/models" />} />
            <Route path="/configuration-history" element={user?.role === 'Admin' ? <ConfigurationHistoryPage /> : <Navigate to="/models" />} />
            <Route path="/reports" element={user ? <ReportsPage /> : <Navigate to="/login" />} />
            <Route path="/reports/regional-compliance" element={user ? <RegionalComplianceReportPage /> : <Navigate to="/login" />} />
            <Route path="/analytics" element={user ? <AnalyticsPage /> : <Navigate to="/login" />} />
            <Route path="/" element={<Navigate to={getDefaultRoute()} />} />
        </Routes>
    );
}

export default App;
