import { ReactNode } from 'react';
import { Link, NavLink } from 'react-router-dom';

function NavItem({ to, label }: { to: string; label: string }) {
    return (
        <NavLink
            to={to}
            className={({ isActive }) =>
                `text-sm font-medium ${isActive ? 'text-blue-700' : 'text-gray-700 hover:text-gray-900'}`
            }
        >
            {label}
        </NavLink>
    );
}

export default function PublicLayout({ children }: { children: ReactNode }) {
    return (
        <div className="min-h-screen bg-gray-50">
            <header className="bg-white border-b border-gray-200">
                <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
                    <Link to="/" className="flex items-baseline gap-2">
                        <span className="text-lg font-bold text-gray-900">QMIS</span>
                        <span className="text-sm text-gray-500">Quantitative Methods Information System</span>
                    </Link>

                    <nav className="hidden sm:flex items-center gap-6">
                        <NavItem to="/overview" label="System Overview" />
                        <NavItem to="/guides" label="User Guides" />
                        <NavItem to="/about" label="About" />
                    </nav>

                    <div className="flex items-center gap-2">
                        <Link to="/login" className="btn-primary">
                            Login
                        </Link>
                    </div>
                </div>
            </header>

            <main>
                {children}
            </main>

            <footer className="border-t border-gray-200 bg-white">
                <div className="max-w-5xl mx-auto px-4 py-8 text-sm text-gray-600 flex flex-col gap-2">
                    <div>
                        Public information only. Sign in to access application data.
                    </div>
                    <div className="flex gap-4">
                        <span>© {new Date().getFullYear()} QMIS</span>
                        <Link to="/privacy-policy" className="hover:text-gray-900">Privacy Policy</Link>
                        <Link to="/about" className="hover:text-gray-900">About</Link>
                    </div>
                </div>
            </footer>
        </div>
    );
}
