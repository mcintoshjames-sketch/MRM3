import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import MRSAReviewDashboardWidget from '../components/MRSAReviewDashboardWidget';
import { useTableSort } from '../hooks/useTableSort';
import { useAuth } from '../contexts/AuthContext';
import { irpApi, IRP, IRPCreate, IRPUpdate } from '../api/irp';
import api from '../api/client';
import { canManageIrps } from '../utils/roleUtils';
import MultiSelectDropdown from '../components/MultiSelectDropdown';

interface User {
    user_id: number;
    email: string;
    full_name: string;
}

export default function IRPsPage() {
    const { user } = useAuth();
    const canManageIrpsFlag = canManageIrps(user);
    type TabType = 'irps' | 'mrsa-review-status';
    const [activeTab, setActiveTab] = useState<TabType>('irps');

    const [irps, setIrps] = useState<IRP[]>([]);
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [editingIrp, setEditingIrp] = useState<IRP | null>(null);
    const [formData, setFormData] = useState<IRPCreate>({
        process_name: '',
        description: '',
        contact_user_id: 0,
        is_active: true,
        mrsa_ids: []
    });

    // Filter state
    const [filters, setFilters] = useState({
        contact_user_ids: [] as number[],
        status: 'active' as 'all' | 'active' | 'inactive',
        review_date_from: '',
        review_date_to: '',
        certification_status: 'all' as 'all' | 'certified' | 'not_certified'
    });

    // Contact user searchable dropdown state (for form)
    const [contactUserSearch, setContactUserSearch] = useState('');
    const [showContactUserDropdown, setShowContactUserDropdown] = useState(false);

    // Apply filters
    const filteredIrps = useMemo(() => {
        return irps.filter(irp => {
            // Contact user filter (multi-select)
            if (filters.contact_user_ids.length > 0 && !filters.contact_user_ids.includes(irp.contact_user_id)) {
                return false;
            }

            // Status filter
            if (filters.status !== 'all') {
                const shouldBeActive = filters.status === 'active';
                if (irp.is_active !== shouldBeActive) return false;
            }

            // Last review date range filter
            if (filters.review_date_from && irp.latest_review_date) {
                if (irp.latest_review_date < filters.review_date_from) return false;
            }
            if (filters.review_date_to && irp.latest_review_date) {
                if (irp.latest_review_date > filters.review_date_to) return false;
            }
            // If date filter is set but IRP has no review date, exclude it
            if ((filters.review_date_from || filters.review_date_to) && !irp.latest_review_date) {
                return false;
            }

            // Certification status filter
            if (filters.certification_status !== 'all') {
                const hasCertification = irp.latest_certification_date !== null && irp.latest_certification_date !== undefined;
                const shouldBeCertified = filters.certification_status === 'certified';
                if (hasCertification !== shouldBeCertified) return false;
            }

            return true;
        });
    }, [irps, filters]);

    // Table sorting (applied to filtered data)
    const { sortedData, requestSort, getSortIcon } = useTableSort<IRP>(filteredIrps, 'process_name');

    // Check if any filters are active (for clear button)
    const hasActiveFilters = useMemo(() => {
        return filters.contact_user_ids.length > 0 ||
            filters.status !== 'active' ||
            filters.review_date_from !== '' ||
            filters.review_date_to !== '' ||
            filters.certification_status !== 'all';
    }, [filters]);

    // Clear all filters
    const clearFilters = () => {
        setFilters({
            contact_user_ids: [],
            status: 'active',
            review_date_from: '',
            review_date_to: '',
            certification_status: 'all'
        });
    };

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [irpsData, usersResponse] = await Promise.all([
                irpApi.list(),
                api.get('/auth/users')
            ]);
            setIrps(irpsData);
            setUsers(usersResponse.data);
        } catch (error) {
            console.error('Failed to fetch data:', error);
        } finally {
            setLoading(false);
        }
    };

    const resetForm = () => {
        setFormData({
            process_name: '',
            description: '',
            contact_user_id: 0,
            is_active: true,
            mrsa_ids: []
        });
        setContactUserSearch('');
        setShowContactUserDropdown(false);
        setEditingIrp(null);
        setShowForm(false);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.contact_user_id) {
            alert('Please select a contact user');
            return;
        }
        try {
            if (editingIrp) {
                const updateData: IRPUpdate = {
                    process_name: formData.process_name,
                    description: formData.description || undefined,
                    contact_user_id: formData.contact_user_id,
                    is_active: formData.is_active
                };
                await irpApi.update(editingIrp.irp_id, updateData);
            } else {
                await irpApi.create(formData);
            }
            resetForm();
            fetchData();
        } catch (error: any) {
            console.error('Failed to save IRP:', error);
            alert(error.response?.data?.detail || 'Failed to save IRP');
        }
    };

    const handleEdit = (irp: IRP) => {
        setEditingIrp(irp);
        setFormData({
            process_name: irp.process_name,
            description: irp.description || '',
            contact_user_id: irp.contact_user_id,
            is_active: irp.is_active,
            mrsa_ids: []
        });
        setContactUserSearch(irp.contact_user?.full_name || '');
        setShowForm(true);
    };

    const handleDelete = async (irpId: number) => {
        if (!confirm('Are you sure you want to delete this IRP? This action cannot be undone.')) return;

        try {
            await irpApi.delete(irpId);
            fetchData();
        } catch (error: any) {
            console.error('Failed to delete IRP:', error);
            alert(error.response?.data?.detail || 'Failed to delete IRP');
        }
    };

    const exportToCsv = () => {
        const headers = ['IRP ID', 'Process Name', 'Contact', 'Status', 'Covered MRSAs', 'Latest Review', 'Latest Certification', 'Created'];
        const csvData = sortedData.map(irp => [
            irp.irp_id,
            irp.process_name,
            irp.contact_user?.full_name || '',
            irp.is_active ? 'Active' : 'Inactive',
            irp.covered_mrsa_count,
            irp.latest_review_date || '',
            irp.latest_certification_date || '',
            irp.created_at.split('T')[0]
        ]);

        const csvContent = [headers, ...csvData]
            .map(row => row.map(cell => `"${cell}"`).join(','))
            .join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `irps_${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-64">Loading...</div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="p-6">
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">Independent Review Processes (IRPs)</h1>
                        <p className="text-sm text-gray-600 mt-1">
                            Manage IRPs that provide governance coverage for high-risk MRSAs
                        </p>
                    </div>
                    {activeTab === 'irps' && (
                        <div className="flex gap-2">
                            <button onClick={exportToCsv} className="btn-secondary">
                                Export CSV
                            </button>
                            {canManageIrpsFlag && (
                                <button onClick={() => setShowForm(true)} className="btn-primary">
                                    + Add IRP
                                </button>
                            )}
                        </div>
                    )}
                </div>

                <div className="border-b border-gray-200 mb-6">
                    <nav className="-mb-px flex space-x-8">
                        <button
                            onClick={() => setActiveTab('irps')}
                            className={`py-2 px-1 border-b-2 font-medium text-sm ${
                                activeTab === 'irps'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                        >
                            IRPs
                        </button>
                        <button
                            onClick={() => setActiveTab('mrsa-review-status')}
                            className={`py-2 px-1 border-b-2 font-medium text-sm ${
                                activeTab === 'mrsa-review-status'
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                        >
                            MRSA Review Status
                        </button>
                    </nav>
                </div>

                {activeTab === 'mrsa-review-status' && (
                    <div className="mb-6">
                        <MRSAReviewDashboardWidget
                            title="MRSA Review Status"
                            description="Monitor independent review obligations across MRSAs covered by IRPs."
                            showPolicyLink={canManageIrpsFlag}
                        />
                    </div>
                )}

                {activeTab === 'irps' && (
                    <>
                        {/* Filters */}
                        <div className="bg-white p-4 rounded-lg shadow-md mb-6">
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
                                {/* Contact User */}
                                <MultiSelectDropdown
                                    label="Contact"
                                    placeholder="All Contacts"
                                    options={users.map(u => ({
                                        value: u.user_id,
                                        label: u.full_name,
                                        secondaryLabel: u.email
                                    }))}
                                    selectedValues={filters.contact_user_ids}
                                    onChange={(values) => setFilters({ ...filters, contact_user_ids: values as number[] })}
                                />

                                {/* Status */}
                                <div>
                                    <label className="block text-xs font-medium text-gray-700 mb-1">
                                        Status
                                    </label>
                                    <select
                                        value={filters.status}
                                        onChange={(e) => setFilters({ ...filters, status: e.target.value as 'all' | 'active' | 'inactive' })}
                                        className="w-full input-field text-sm"
                                    >
                                        <option value="all">All Statuses</option>
                                        <option value="active">Active</option>
                                        <option value="inactive">Inactive</option>
                                    </select>
                                </div>

                                {/* Last Review Date From */}
                                <div>
                                    <label className="block text-xs font-medium text-gray-700 mb-1">
                                        Review Date From
                                    </label>
                                    <input
                                        type="date"
                                        value={filters.review_date_from}
                                        onChange={(e) => setFilters({ ...filters, review_date_from: e.target.value })}
                                        className="w-full input-field text-sm"
                                    />
                                </div>

                                {/* Last Review Date To */}
                                <div>
                                    <label className="block text-xs font-medium text-gray-700 mb-1">
                                        Review Date To
                                    </label>
                                    <input
                                        type="date"
                                        value={filters.review_date_to}
                                        onChange={(e) => setFilters({ ...filters, review_date_to: e.target.value })}
                                        className="w-full input-field text-sm"
                                    />
                                </div>

                                {/* Certification Status */}
                                <div>
                                    <label className="block text-xs font-medium text-gray-700 mb-1">
                                        Certification
                                    </label>
                                    <select
                                        value={filters.certification_status}
                                        onChange={(e) => setFilters({ ...filters, certification_status: e.target.value as 'all' | 'certified' | 'not_certified' })}
                                        className="w-full input-field text-sm"
                                    >
                                        <option value="all">All</option>
                                        <option value="certified">Certified</option>
                                        <option value="not_certified">Not Certified</option>
                                    </select>
                                </div>
                            </div>

                            {/* Filter summary and clear button */}
                            <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-200">
                                <div className="text-sm text-gray-600">
                                    Showing <span className="font-medium">{sortedData.length}</span> of <span className="font-medium">{irps.length}</span> IRPs
                                </div>
                                {hasActiveFilters && (
                                    <button
                                        type="button"
                                        onClick={clearFilters}
                                        className="text-sm text-red-600 hover:text-red-800"
                                    >
                                        Clear Filters
                                    </button>
                                )}
                            </div>
                        </div>

                        {/* Form */}
                        {showForm && (
                            <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                                <h3 className="text-lg font-bold mb-4">
                                    {editingIrp ? 'Edit IRP' : 'Create New IRP'}
                                </h3>
                                <form onSubmit={handleSubmit}>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="mb-4">
                                            <label htmlFor="process_name" className="block text-sm font-medium mb-2">
                                                Process Name *
                                            </label>
                                            <input
                                                id="process_name"
                                                type="text"
                                                className="input-field"
                                                value={formData.process_name}
                                                onChange={(e) => setFormData({ ...formData, process_name: e.target.value })}
                                                required
                                            />
                                        </div>
                                        <div className="mb-4">
                                            <label htmlFor="contact_user_id" className="block text-sm font-medium mb-2">
                                                Contact User *
                                            </label>
                                            <div className="relative">
                                                <input
                                                    type="text"
                                                    placeholder="Type to search users..."
                                                    value={contactUserSearch}
                                                    onChange={(e) => {
                                                        setContactUserSearch(e.target.value);
                                                        setShowContactUserDropdown(true);
                                                        // Clear selection if user is typing new text
                                                        if (formData.contact_user_id && e.target.value !== users.find(u => u.user_id === formData.contact_user_id)?.full_name) {
                                                            setFormData({ ...formData, contact_user_id: 0 });
                                                        }
                                                    }}
                                                    onFocus={() => setShowContactUserDropdown(true)}
                                                    className="input-field"
                                                />
                                                {showContactUserDropdown && contactUserSearch.length > 0 && (
                                                    <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
                                                        {users
                                                            .filter((u) =>
                                                                u.full_name.toLowerCase().includes(contactUserSearch.toLowerCase()) ||
                                                                u.email.toLowerCase().includes(contactUserSearch.toLowerCase())
                                                            )
                                                            .slice(0, 50)
                                                            .map((u) => (
                                                                <div
                                                                    key={u.user_id}
                                                                    className="px-4 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                                                                    onClick={() => {
                                                                        setFormData({ ...formData, contact_user_id: u.user_id });
                                                                        setContactUserSearch(u.full_name);
                                                                        setShowContactUserDropdown(false);
                                                                    }}
                                                                >
                                                                    <div className="font-medium">{u.full_name}</div>
                                                                    <div className="text-xs text-gray-500">{u.email}</div>
                                                                </div>
                                                            ))}
                                                        {users.filter((u) =>
                                                            u.full_name.toLowerCase().includes(contactUserSearch.toLowerCase()) ||
                                                            u.email.toLowerCase().includes(contactUserSearch.toLowerCase())
                                                        ).length === 0 && (
                                                            <div className="px-4 py-2 text-sm text-gray-500">No users found</div>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                            {formData.contact_user_id > 0 && (
                                                <p className="mt-1 text-sm text-green-600">
                                                    Selected: {users.find(u => u.user_id === formData.contact_user_id)?.full_name}
                                                </p>
                                            )}
                                        </div>
                                        <div className="mb-4 col-span-2">
                                            <label htmlFor="description" className="block text-sm font-medium mb-2">
                                                Description
                                            </label>
                                            <textarea
                                                id="description"
                                                className="input-field"
                                                rows={3}
                                                value={formData.description}
                                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                                placeholder="Describe the IRP scope and purpose..."
                                            />
                                        </div>
                                        <div className="mb-4">
                                            <label className="flex items-center gap-2">
                                                <input
                                                    type="checkbox"
                                                    checked={formData.is_active}
                                                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                                                    className="h-4 w-4 text-blue-600 rounded"
                                                />
                                                <span className="text-sm font-medium text-gray-700">Active</span>
                                            </label>
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <button type="submit" className="btn-primary">
                                            {editingIrp ? 'Update' : 'Create'}
                                        </button>
                                        <button type="button" onClick={resetForm} className="btn-secondary">
                                            Cancel
                                        </button>
                                    </div>
                                </form>
                            </div>
                        )}

                        {/* Table */}
                        <div className="bg-white rounded-lg shadow-md overflow-hidden">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th
                                            className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                            onClick={() => requestSort('irp_id')}
                                        >
                                            <div className="flex items-center gap-2">
                                                ID
                                                {getSortIcon('irp_id')}
                                            </div>
                                        </th>
                                        <th
                                            className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                            onClick={() => requestSort('process_name')}
                                        >
                                            <div className="flex items-center gap-2">
                                                Process Name
                                                {getSortIcon('process_name')}
                                            </div>
                                        </th>
                                        <th
                                            className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                            onClick={() => requestSort('contact_user.full_name')}
                                        >
                                            <div className="flex items-center gap-2">
                                                Contact
                                                {getSortIcon('contact_user.full_name')}
                                            </div>
                                        </th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                            Status
                                        </th>
                                        <th
                                            className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                            onClick={() => requestSort('covered_mrsa_count')}
                                        >
                                            <div className="flex items-center gap-2">
                                                MRSAs
                                                {getSortIcon('covered_mrsa_count')}
                                            </div>
                                        </th>
                                        <th
                                            className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                            onClick={() => requestSort('latest_review_date')}
                                        >
                                            <div className="flex items-center gap-2">
                                                Latest Review
                                                {getSortIcon('latest_review_date')}
                                            </div>
                                        </th>
                                        <th
                                            className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                                            onClick={() => requestSort('latest_certification_date')}
                                        >
                                            <div className="flex items-center gap-2">
                                                Certification
                                                {getSortIcon('latest_certification_date')}
                                            </div>
                                        </th>
                                        {canManageIrpsFlag && (
                                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                Actions
                                            </th>
                                        )}
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {sortedData.length === 0 ? (
                                        <tr>
                                            <td colSpan={canManageIrpsFlag ? 8 : 7} className="px-4 py-2 text-center text-gray-500">
                                                No IRPs found. {canManageIrpsFlag && 'Click "Add IRP" to create one.'}
                                            </td>
                                        </tr>
                                    ) : (
                                        sortedData.map((irp) => (
                                            <tr key={irp.irp_id} className="hover:bg-gray-50">
                                                <td className="px-4 py-2 whitespace-nowrap text-sm">
                                                    {irp.irp_id}
                                                </td>
                                                <td className="px-4 py-2 whitespace-nowrap text-sm">
                                                    <Link
                                                        to={`/irps/${irp.irp_id}`}
                                                        className="font-medium text-blue-600 hover:text-blue-800"
                                                    >
                                                        {irp.process_name}
                                                    </Link>
                                                </td>
                                                <td className="px-4 py-2 whitespace-nowrap text-sm">
                                                    {irp.contact_user?.full_name || '-'}
                                                </td>
                                                <td className="px-4 py-2 whitespace-nowrap text-sm">
                                                    <span className={`px-2 py-1 text-xs rounded font-medium ${
                                                        irp.is_active
                                                            ? 'bg-green-100 text-green-800'
                                                            : 'bg-gray-100 text-gray-700'
                                                    }`}>
                                                        {irp.is_active ? 'Active' : 'Inactive'}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-2 whitespace-nowrap text-sm">
                                                    <span className="px-2 py-1 bg-amber-100 text-amber-800 rounded text-xs font-medium">
                                                        {irp.covered_mrsa_count}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-2 whitespace-nowrap text-sm">
                                                    {irp.latest_review_date ? (
                                                        <div className="flex flex-col">
                                                            <span>{irp.latest_review_date}</span>
                                                            {irp.latest_review_outcome && (
                                                                <span className={`text-xs px-1.5 py-0.5 rounded mt-0.5 inline-block w-fit ${
                                                                    irp.latest_review_outcome === 'Satisfactory'
                                                                        ? 'bg-green-100 text-green-700'
                                                                        : irp.latest_review_outcome === 'Conditionally Satisfactory'
                                                                            ? 'bg-yellow-100 text-yellow-700'
                                                                            : 'bg-red-100 text-red-700'
                                                                }`}>
                                                                    {irp.latest_review_outcome}
                                                                </span>
                                                            )}
                                                        </div>
                                                    ) : (
                                                        <span className="text-gray-400">No reviews</span>
                                                    )}
                                                </td>
                                                <td className="px-4 py-2 whitespace-nowrap text-sm">
                                                    {irp.latest_certification_date || (
                                                        <span className="text-gray-400">Not certified</span>
                                                    )}
                                                </td>
                                                {canManageIrpsFlag && (
                                                    <td className="px-4 py-2 whitespace-nowrap text-sm">
                                                        <div className="flex gap-2">
                                                            <button
                                                                onClick={() => handleEdit(irp)}
                                                                className="text-blue-600 hover:text-blue-800"
                                                            >
                                                                Edit
                                                            </button>
                                                            <button
                                                                onClick={() => handleDelete(irp.irp_id)}
                                                                className="text-red-600 hover:text-red-800"
                                                            >
                                                                Delete
                                                            </button>
                                                        </div>
                                                    </td>
                                                )}
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </>
                )}
            </div>
        </Layout>
    );
}
