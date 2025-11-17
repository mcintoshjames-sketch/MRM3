import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import LoginPage from './pages/LoginPage';
import ModelsPage from './pages/ModelsPage';
import ModelDetailsPage from './pages/ModelDetailsPage';
import VendorsPage from './pages/VendorsPage';
import UsersPage from './pages/UsersPage';
import TaxonomyPage from './pages/TaxonomyPage';

function App() {
    const { user, loading } = useAuth();

    if (loading) {
        return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
    }

    return (
        <Routes>
            <Route path="/login" element={!user ? <LoginPage /> : <Navigate to="/models" />} />
            <Route path="/models" element={user ? <ModelsPage /> : <Navigate to="/login" />} />
            <Route path="/models/:id" element={user ? <ModelDetailsPage /> : <Navigate to="/login" />} />
            <Route path="/vendors" element={user ? <VendorsPage /> : <Navigate to="/login" />} />
            <Route path="/users" element={user ? <UsersPage /> : <Navigate to="/login" />} />
            <Route path="/taxonomy" element={user ? <TaxonomyPage /> : <Navigate to="/login" />} />
            <Route path="/" element={<Navigate to={user ? "/models" : "/login"} />} />
        </Routes>
    );
}

export default App;
