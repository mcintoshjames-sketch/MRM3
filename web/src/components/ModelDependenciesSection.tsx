import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { isAdmin } from '../utils/roleUtils';
import ModelDependencyModal from './ModelDependencyModal';

interface DependencyRelation {
    id: number;
    feeder_model_id?: number;
    consumer_model_id?: number;
    model_id: number;
    model_name: string;
    dependency_type: string;
    dependency_type_id: number;
    description: string | null;
    effective_date: string | null;
    end_date: string | null;
    is_active: boolean;
}

interface Props {
    modelId: number;
    modelName: string;
}

export default function ModelDependenciesSection({ modelId, modelName }: Props) {
    const { user } = useAuth();
    const [inbound, setInbound] = useState<DependencyRelation[]>([]);
    const [outbound, setOutbound] = useState<DependencyRelation[]>([]);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [modalDirection, setModalDirection] = useState<'inbound' | 'outbound'>('inbound');
    const [editData, setEditData] = useState<DependencyRelation | undefined>();

    useEffect(() => {
        fetchDependencyData();
    }, [modelId]);

    const fetchDependencyData = async () => {
        try {
            setLoading(true);
            const [inboundRes, outboundRes] = await Promise.all([
                api.get(`/models/${modelId}/dependencies/inbound`),
                api.get(`/models/${modelId}/dependencies/outbound`)
            ]);
            setInbound(inboundRes.data);
            setOutbound(outboundRes.data);
        } catch (error) {
            console.error('Error fetching dependency data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleAddInbound = () => {
        setEditData(undefined);
        setModalDirection('inbound');
        setIsModalOpen(true);
    };

    const handleAddOutbound = () => {
        setEditData(undefined);
        setModalDirection('outbound');
        setIsModalOpen(true);
    };

    const handleEdit = (dependency: DependencyRelation, direction: 'inbound' | 'outbound') => {
        setEditData(dependency);
        setModalDirection(direction);
        setIsModalOpen(true);
    };

    const handleDelete = async (dependencyId: number) => {
        if (!window.confirm('Are you sure you want to delete this dependency relationship?')) {
            return;
        }

        try {
            await api.delete(`/dependencies/${dependencyId}`);
            await fetchDependencyData();
        } catch (error: any) {
            console.error('Error deleting dependency:', error);
            alert(error.response?.data?.detail || 'Failed to delete dependency relationship');
        }
    };

    const handleModalSuccess = () => {
        fetchDependencyData();
    };

    const exportToCSV = (data: DependencyRelation[], direction: 'inbound' | 'outbound') => {
        if (data.length === 0) {
            alert('No data to export');
            return;
        }

        const headers = ['Model Name', 'Dependency Type', 'Description', 'Status', 'Effective Date', 'End Date'];
        const rows = data.map(dep => [
            dep.model_name,
            dep.dependency_type,
            dep.description || '',
            dep.is_active ? 'Active' : 'Inactive',
            dep.effective_date || '',
            dep.end_date || ''
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
        link.setAttribute('download', `model_${modelId}_dependencies_${direction}_${today}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const isAdminUser = isAdmin(user);

    if (loading) {
        return (
            <div className="text-center py-4 text-gray-500">
                Loading dependency data...
            </div>
        );
    }

    const hasInbound = inbound.length > 0;
    const hasOutbound = outbound.length > 0;

    if (!hasInbound && !hasOutbound) {
        return (
            <>
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                    </svg>
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No Data Dependencies</h3>
                    <p className="mt-1 text-sm text-gray-500">
                        This model has no inbound or outbound data dependencies defined.
                    </p>
                    {isAdminUser && (
                        <div className="mt-6 flex justify-center space-x-3">
                            <button
                                onClick={handleAddInbound}
                                className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                            >
                                <svg className="-ml-1 mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                </svg>
                                Add Inbound Dependency
                            </button>
                            <button
                                onClick={handleAddOutbound}
                                className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                            >
                                <svg className="-ml-1 mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                </svg>
                                Add Outbound Dependency
                            </button>
                        </div>
                    )}
                </div>

                <ModelDependencyModal
                    isOpen={isModalOpen}
                    onClose={() => setIsModalOpen(false)}
                    onSuccess={handleModalSuccess}
                    currentModelId={modelId}
                    currentModelName={modelName}
                    dependencyDirection={modalDirection}
                    editData={editData}
                />
            </>
        );
    }

    return (
        <>
            <div className="space-y-6">
                {/* Inbound Dependencies (Feeders) Section */}
                {hasInbound && (
                    <div>
                        <div className="flex justify-between items-center mb-4">
                            <div>
                                <h3 className="text-lg font-medium text-gray-900">
                                    Inbound Dependencies (Feeder Models)
                                </h3>
                                <p className="text-sm text-gray-600 mt-1">
                                    Models that provide data to this model.
                                </p>
                            </div>
                            <div className="flex space-x-2">
                                <button
                                    onClick={() => exportToCSV(inbound, 'inbound')}
                                    className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                                >
                                    <svg className="-ml-0.5 mr-1.5 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                    Export CSV
                                </button>
                                {isAdminUser && (
                                    <button
                                        onClick={handleAddInbound}
                                        className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                                    >
                                        <svg className="-ml-0.5 mr-1.5 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                        </svg>
                                        Add Inbound
                                    </button>
                                )}
                            </div>
                        </div>
                        <div className="bg-white shadow overflow-hidden sm:rounded-md">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Feeder Model
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Dependency Type
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Description
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Status
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Effective Date
                                        </th>
                                        {isAdminUser && (
                                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Actions
                                            </th>
                                        )}
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {inbound.map((dep) => (
                                        <tr key={dep.id} className="hover:bg-gray-50">
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <Link
                                                    to={`/models/${dep.model_id}`}
                                                    className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
                                                >
                                                    {dep.model_name}
                                                </Link>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-purple-100 text-purple-800">
                                                    {dep.dependency_type}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-500">
                                                {dep.description || '-'}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {dep.is_active ? (
                                                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                                                        Active
                                                    </span>
                                                ) : (
                                                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">
                                                        Inactive
                                                    </span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {dep.effective_date || '-'}
                                            </td>
                                            {isAdminUser && (
                                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                    <button
                                                        onClick={() => handleEdit(dep, 'inbound')}
                                                        className="text-blue-600 hover:text-blue-900 mr-3"
                                                    >
                                                        Edit
                                                    </button>
                                                    <button
                                                        onClick={() => handleDelete(dep.id)}
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

                {/* Outbound Dependencies (Consumers) Section */}
                {hasOutbound && (
                    <div>
                        <div className="flex justify-between items-center mb-4">
                            <div>
                                <h3 className="text-lg font-medium text-gray-900">
                                    Outbound Dependencies (Consumer Models)
                                </h3>
                                <p className="text-sm text-gray-600 mt-1">
                                    Models that consume data from this model.
                                </p>
                            </div>
                            <div className="flex space-x-2">
                                <button
                                    onClick={() => exportToCSV(outbound, 'outbound')}
                                    className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                                >
                                    <svg className="-ml-0.5 mr-1.5 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                    Export CSV
                                </button>
                                {isAdminUser && (
                                    <button
                                        onClick={handleAddOutbound}
                                        className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                                    >
                                        <svg className="-ml-0.5 mr-1.5 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                        </svg>
                                        Add Outbound
                                    </button>
                                )}
                            </div>
                        </div>
                        <div className="bg-white shadow overflow-hidden sm:rounded-md">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Consumer Model
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Dependency Type
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Description
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Status
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Effective Date
                                        </th>
                                        {isAdminUser && (
                                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Actions
                                            </th>
                                        )}
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {outbound.map((dep) => (
                                        <tr key={dep.id} className="hover:bg-gray-50">
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <Link
                                                    to={`/models/${dep.model_id}`}
                                                    className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
                                                >
                                                    {dep.model_name}
                                                </Link>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-indigo-100 text-indigo-800">
                                                    {dep.dependency_type}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-500">
                                                {dep.description || '-'}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                {dep.is_active ? (
                                                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                                                        Active
                                                    </span>
                                                ) : (
                                                    <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">
                                                        Inactive
                                                    </span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {dep.effective_date || '-'}
                                            </td>
                                            {isAdminUser && (
                                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                    <button
                                                        onClick={() => handleEdit(dep, 'outbound')}
                                                        className="text-blue-600 hover:text-blue-900 mr-3"
                                                    >
                                                        Edit
                                                    </button>
                                                    <button
                                                        onClick={() => handleDelete(dep.id)}
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

            <ModelDependencyModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onSuccess={handleModalSuccess}
                currentModelId={modelId}
                currentModelName={modelName}
                dependencyDirection={modalDirection}
                editData={editData}
            />
        </>
    );
}
