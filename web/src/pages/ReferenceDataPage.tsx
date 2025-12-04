import { useState } from 'react';
import Layout from '../components/Layout';
import { VendorsContent } from './VendorsPage';
import { UsersContent } from './UsersPage';

type TabType = 'vendors' | 'users';

export default function ReferenceDataPage() {
    const [activeTab, setActiveTab] = useState<TabType>('vendors');

    return (
        <Layout>
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-2xl font-bold">Reference Data</h2>
                    <p className="text-gray-600 text-sm mt-1">
                        Manage vendors and users for the model inventory
                    </p>
                </div>
            </div>

            {/* Tabs */}
            <div className="mb-6">
                <nav className="flex space-x-4 border-b border-gray-200">
                    <button
                        onClick={() => setActiveTab('vendors')}
                        className={`pb-3 px-1 border-b-2 font-medium text-sm ${
                            activeTab === 'vendors'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                    >
                        Vendors
                    </button>
                    <button
                        onClick={() => setActiveTab('users')}
                        className={`pb-3 px-1 border-b-2 font-medium text-sm ${
                            activeTab === 'users'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                    >
                        Users
                    </button>
                </nav>
            </div>

            {/* Tab Content */}
            {activeTab === 'vendors' && <VendorsContent />}
            {activeTab === 'users' && <UsersContent />}
        </Layout>
    );
}
