import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import ModelHierarchyModal from './ModelHierarchyModal';

interface HierarchyRelation {
    id: number;
    parent_model_id?: number;
    child_model_id?: number;
    model_id: number;
    model_name: string;
    relation_type: string;
    relation_type_id: number;
    effective_date: string | null;
    end_date: string | null;
    notes: string | null;
}

interface Props {
    modelId: number;
    modelName: string;
}

export default function ModelHierarchySection({ modelId, modelName }: Props) {
    const { user } = useAuth();
    const [parents, setParents] = useState<HierarchyRelation[]>([]);
    const [children, setChildren] = useState<HierarchyRelation[]>([]);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [modalType, setModalType] = useState<'parent' | 'child'>('child');
    const [editData, setEditData] = useState<HierarchyRelation | undefined>();

    useEffect(() => {
        fetchHierarchyData();
    }, [modelId]);

    const fetchHierarchyData = async () => {
        try {
            setLoading(true);
            const [parentsRes, childrenRes] = await Promise.all([
                api.get(`/models/${modelId}/hierarchy/parents`),
                api.get(`/models/${modelId}/hierarchy/children`)
            ]);
            setParents(parentsRes.data);
            setChildren(childrenRes.data);
        } catch (error) {
            console.error('Error fetching hierarchy data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleAddParent = () => {
        setEditData(undefined);
        setModalType('parent');
        setIsModalOpen(true);
    };

    const handleAddChild = () => {
        setEditData(undefined);
        setModalType('child');
        setIsModalOpen(true);
    };

    const handleEdit = (relation: HierarchyRelation, type: 'parent' | 'child') => {
        setEditData(relation);
        setModalType(type);
        setIsModalOpen(true);
    };

    const handleDelete = async (relationId: number) => {
        if (!window.confirm('Are you sure you want to delete this hierarchy relationship?')) {
            return;
        }

        try {
            await api.delete(`/hierarchy/${relationId}`);
            await fetchHierarchyData();
        } catch (error: any) {
            console.error('Error deleting hierarchy:', error);
            alert(error.response?.data?.detail || 'Failed to delete hierarchy relationship');
        }
    };

    const handleModalSuccess = () => {
        fetchHierarchyData();
    };

    const exportToCSV = (data: HierarchyRelation[], type: 'parents' | 'children') => {
        if (data.length === 0) {
            alert('No data to export');
            return;
        }

        const headers = ['Model Name', 'Relationship Type', 'Effective Date', 'End Date', 'Notes'];
        const rows = data.map(relation => [
            relation.model_name,
            relation.relation_type,
            relation.effective_date || '',
            relation.end_date || '',
            relation.notes || ''
        ]);

        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        const today = new Date().toISOString().split('T')[0];
        link.setAttribute('href', url);
        link.setAttribute('download', `model_${modelId}_${type}_${today}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const isAdmin = user?.role === 'Admin';
    const hasActiveParent = parents.length > 0;

    if (loading) {
        return (
            <div className="text-center py-4 text-gray-500">
                Loading hierarchy data...
            </div>
        );
    }

    const hasParents = parents.length > 0;
    const hasChildren = children.length > 0;

    if (!hasParents && !hasChildren) {
        return (
            <>
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No Hierarchy Relationships</h3>
                    <p className="mt-1 text-sm text-gray-500">
                        This model has no parent or child relationships defined.
                    </p>
                    {isAdmin && (
                        <div className="mt-6 flex justify-center space-x-3">
                            <button
                                onClick={handleAddParent}
                                disabled={hasActiveParent}
                                className={`inline-flex items-center px-4 py-2 border shadow-sm text-sm font-medium rounded-md ${hasActiveParent
                                    ? 'border-gray-200 text-gray-400 bg-gray-100 cursor-not-allowed'
                                    : 'border-gray-300 text-gray-700 bg-white hover:bg-gray-50'
                                    }`}
                                title={hasActiveParent ? 'This model already has a parent. A model can only have one parent.' : 'Add parent model'}
                            >
                                <svg className="-ml-1 mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                </svg>
                                Add Parent Model
                            </button>
                            <button
                                onClick={handleAddChild}
                                className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                            >
                                <svg className="-ml-1 mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                </svg>
                                Add Sub-Model
                            </button>
                        </div>
                    )}
                </div>

                <ModelHierarchyModal
                    isOpen={isModalOpen}
                    onClose={() => setIsModalOpen(false)}
                    onSuccess={handleModalSuccess}
                    currentModelId={modelId}
                    currentModelName={modelName}
                    relationshipType={modalType}
                    editData={editData}
                />
            </>
        );
    }

    return (
        <>
            <div className="space-y-6">
                {/* Parent Models Section */}
                {hasParents && (
                    <div>
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-medium text-gray-900">Parent Models</h3>
                            <div className="flex space-x-2">
                                <button
                                    onClick={() => exportToCSV(parents, 'parents')}
                                    className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                                >
                                    <svg className="-ml-0.5 mr-1.5 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                    Export CSV
                                </button>
                                {isAdmin && (
                                    <div className="flex flex-col items-end">
                                        <button
                                            onClick={handleAddParent}
                                            disabled
                                            className="inline-flex items-center px-3 py-1.5 border border-gray-200 shadow-sm text-sm font-medium rounded-md text-gray-400 bg-gray-100 cursor-not-allowed"
                                            title="This model already has a parent. A model can only have one parent for clear ownership and governance."
                                        >
                                            <svg className="-ml-0.5 mr-1.5 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                            </svg>
                                            Add Parent
                                        </button>
                                        <p className="mt-1 text-xs text-gray-500">A model can only have one parent</p>
                                    </div>
                                )}
                            </div>
                        </div>
                        <div className="bg-white shadow overflow-hidden sm:rounded-md">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Parent Model
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Relationship Type
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Effective Date
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            End Date
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Notes
                                        </th>
                                        {isAdmin && (
                                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Actions
                                            </th>
                                        )}
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {parents.map((relation) => (
                                        <tr key={relation.id} className="hover:bg-gray-50">
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <Link
                                                    to={`/models/${relation.model_id}`}
                                                    className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
                                                >
                                                    {relation.model_name}
                                                </Link>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                                                    {relation.relation_type}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {relation.effective_date || '-'}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {relation.end_date || '-'}
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-500">
                                                {relation.notes || '-'}
                                            </td>
                                            {isAdmin && (
                                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                    <button
                                                        onClick={() => handleEdit(relation, 'parent')}
                                                        className="text-blue-600 hover:text-blue-900 mr-3"
                                                    >
                                                        Edit
                                                    </button>
                                                    <button
                                                        onClick={() => handleDelete(relation.id)}
                                                        className="text-red-600 hover:text-red-900"
                                                    >
                                                        Delete
                                                    </button>
                                                </td>
                                            )}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {/* Child Models (Sub-Models) Section */}
                {hasChildren && (
                    <div>
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-medium text-gray-900">Sub-Models</h3>
                            <div className="flex space-x-2">
                                <button
                                    onClick={() => exportToCSV(children, 'children')}
                                    className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                                >
                                    <svg className="-ml-0.5 mr-1.5 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                    Export CSV
                                </button>
                                {isAdmin && (
                                    <button
                                        onClick={handleAddChild}
                                        className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                                    >
                                        <svg className="-ml-0.5 mr-1.5 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                        </svg>
                                        Add Sub-Model
                                    </button>
                                )}
                            </div>
                        </div>
                        <div className="bg-white shadow overflow-hidden sm:rounded-md">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Sub-Model
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Relationship Type
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Effective Date
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            End Date
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Notes
                                        </th>
                                        {isAdmin && (
                                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Actions
                                            </th>
                                        )}
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {children.map((relation) => (
                                        <tr key={relation.id} className="hover:bg-gray-50">
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <Link
                                                    to={`/models/${relation.model_id}`}
                                                    className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
                                                >
                                                    {relation.model_name}
                                                </Link>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                                                    {relation.relation_type}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {relation.effective_date || '-'}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {relation.end_date || '-'}
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-500">
                                                {relation.notes || '-'}
                                            </td>
                                            {isAdmin && (
                                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                    <button
                                                        onClick={() => handleEdit(relation, 'child')}
                                                        className="text-blue-600 hover:text-blue-900 mr-3"
                                                    >
                                                        Edit
                                                    </button>
                                                    <button
                                                        onClick={() => handleDelete(relation.id)}
                                                        className="text-red-600 hover:text-red-900"
                                                    >
                                                        Delete
                                                    </button>
                                                </td>
                                            )}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
            </div>

            <ModelHierarchyModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onSuccess={handleModalSuccess}
                currentModelId={modelId}
                currentModelName={modelName}
                relationshipType={modalType}
                editData={editData}
            />
        </>
    );
}
