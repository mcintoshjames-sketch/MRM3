import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface LayoutProps {
    children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    return (
        <div className="min-h-screen bg-gray-100 flex">
            {/* Side Panel */}
            <aside className="w-64 bg-white shadow-lg flex flex-col">
                <div className="p-4 border-b">
                    <h1 className="text-xl font-bold text-blue-600">MRM System v3</h1>
                </div>
                <nav className="flex-1 p-4">
                    <ul className="space-y-2">
                        <li>
                            <NavLink
                                to="/models"
                                className={({ isActive }) =>
                                    `block px-4 py-2 rounded transition-colors ${
                                        isActive
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
                                to="/vendors"
                                className={({ isActive }) =>
                                    `block px-4 py-2 rounded transition-colors ${
                                        isActive
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
                                    `block px-4 py-2 rounded transition-colors ${
                                        isActive
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
                                    `block px-4 py-2 rounded transition-colors ${
                                        isActive
                                            ? 'bg-blue-600 text-white'
                                            : 'text-gray-700 hover:bg-gray-100'
                                    }`
                                }
                            >
                                Taxonomy
                            </NavLink>
                        </li>
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
            <main className="flex-1 p-6">
                {children}
            </main>
        </div>
    );
}
