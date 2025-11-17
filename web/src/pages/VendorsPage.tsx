import { useState, useEffect } from 'react';
import api from '../api/client';
import Layout from '../components/Layout';

interface Vendor {
    vendor_id: number;
    name: string;
    contact_info: string;
    created_at: string;
}

export default function VendorsPage() {
    const [vendors, setVendors] = useState<Vendor[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [editingVendor, setEditingVendor] = useState<Vendor | null>(null);
    const [formData, setFormData] = useState({
        name: '',
        contact_info: ''
    });

    useEffect(() => {
        fetchVendors();
    }, []);

    const fetchVendors = async () => {
        try {
            const response = await api.get('/vendors/');
            setVendors(response.data);
        } catch (error) {
            console.error('Failed to fetch vendors:', error);
        } finally {
            setLoading(false);
        }
    };

    const resetForm = () => {
        setFormData({ name: '', contact_info: '' });
        setEditingVendor(null);
        setShowForm(false);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            if (editingVendor) {
                await api.patch(`/vendors/${editingVendor.vendor_id}`, formData);
            } else {
                await api.post('/vendors/', formData);
            }
            resetForm();
            fetchVendors();
        } catch (error) {
            console.error('Failed to save vendor:', error);
        }
    };

    const handleEdit = (vendor: Vendor) => {
        setEditingVendor(vendor);
        setFormData({
            name: vendor.name,
            contact_info: vendor.contact_info || ''
        });
        setShowForm(true);
    };

    const handleDelete = async (vendorId: number) => {
        if (!confirm('Are you sure you want to delete this vendor?')) return;

        try {
            await api.delete(`/vendors/${vendorId}`);
            fetchVendors();
        } catch (error) {
            console.error('Failed to delete vendor:', error);
        }
    };

    if (loading) {
        return (
            <Layout>
                <div className="flex items-center justify-center h-full">Loading...</div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold">Vendors</h2>
                <button onClick={() => setShowForm(true)} className="btn-primary">
                    + Add Vendor
                </button>
            </div>

            {showForm && (
                <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                    <h3 className="text-lg font-bold mb-4">
                        {editingVendor ? 'Edit Vendor' : 'Create New Vendor'}
                    </h3>
                    <form onSubmit={handleSubmit}>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="mb-4">
                                <label htmlFor="name" className="block text-sm font-medium mb-2">
                                    Vendor Name
                                </label>
                                <input
                                    id="name"
                                    type="text"
                                    className="input-field"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    required
                                />
                            </div>
                            <div className="mb-4">
                                <label htmlFor="contact_info" className="block text-sm font-medium mb-2">
                                    Contact Info
                                </label>
                                <input
                                    id="contact_info"
                                    type="text"
                                    className="input-field"
                                    value={formData.contact_info}
                                    onChange={(e) => setFormData({ ...formData, contact_info: e.target.value })}
                                    placeholder="email@vendor.com"
                                />
                            </div>
                        </div>
                        <div className="flex gap-2">
                            <button type="submit" className="btn-primary">
                                {editingVendor ? 'Update' : 'Create'}
                            </button>
                            <button type="button" onClick={resetForm} className="btn-secondary">
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            )}

            <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                ID
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Name
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Contact Info
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Created
                            </th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                Actions
                            </th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {vendors.length === 0 ? (
                            <tr>
                                <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                                    No vendors yet. Click "Add Vendor" to create one.
                                </td>
                            </tr>
                        ) : (
                            vendors.map((vendor) => (
                                <tr key={vendor.vendor_id}>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        {vendor.vendor_id}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap font-medium">
                                        {vendor.name}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        {vendor.contact_info || '-'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        {new Date(vendor.created_at).toLocaleDateString()}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <button
                                            onClick={() => handleEdit(vendor)}
                                            className="text-blue-600 hover:text-blue-800 text-sm mr-3"
                                        >
                                            Edit
                                        </button>
                                        <button
                                            onClick={() => handleDelete(vendor.vendor_id)}
                                            className="text-red-600 hover:text-red-800 text-sm"
                                        >
                                            Delete
                                        </button>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </Layout>
    );
}
