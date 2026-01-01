import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import client from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { Navigate } from 'react-router-dom';
import { canManageWorkflowConfig } from '../utils/roleUtils';

interface ConfigurationItem {
    config_item_id: number;
    component_id: number;
    section_number: string;
    section_title: string;
    component_code: string;
    component_title: string;
    expectation_high: string;
    expectation_medium: string;
    expectation_low: string;
    expectation_very_low: string;
}

interface Configuration {
    config_id: number;
    config_name: string;
    description: string | null;
    effective_date: string;
    created_by_user_id: number | null;
    created_at: string;
    is_active: boolean;
    config_items?: ConfigurationItem[];
}

const ConfigurationHistoryPage: React.FC = () => {
    const { user } = useAuth();
    const [configurations, setConfigurations] = useState<Configuration[]>([]);
    const [expandedConfigId, setExpandedConfigId] = useState<number | null>(null);
    const [expandedConfig, setExpandedConfig] = useState<Configuration | null>(null);
    const [loading, setLoading] = useState(true);
    const [loadingDetail, setLoadingDetail] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Admin check
    if (!user || !canManageWorkflowConfig(user)) {
        return <Navigate to="/models" />;
    }

    useEffect(() => {
        fetchConfigurations();
    }, []);

    const fetchConfigurations = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await client.get('/validation-workflow/configurations');
            setConfigurations(response.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to fetch configurations');
        } finally {
            setLoading(false);
        }
    };

    const handleExpandConfiguration = async (configId: number) => {
        if (expandedConfigId === configId) {
            // Collapse if already expanded
            setExpandedConfigId(null);
            setExpandedConfig(null);
            return;
        }

        setLoadingDetail(true);
        setError(null);
        try {
            const response = await client.get(`/validation-workflow/configurations/${configId}`);
            setExpandedConfig(response.data);
            setExpandedConfigId(configId);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to fetch configuration details');
        } finally {
            setLoadingDetail(false);
        }
    };

    const getExpectationBadgeColor = (expectation: string) => {
        switch (expectation) {
            case 'Required':
                return 'bg-blue-100 text-blue-800';
            case 'IfApplicable':
                return 'bg-gray-100 text-gray-800';
            case 'NotExpected':
                return 'bg-red-100 text-red-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    const formatExpectation = (expectation: string) => {
        switch (expectation) {
            case 'IfApplicable':
                return 'If Applicable';
            case 'NotExpected':
                return 'Not Expected';
            default:
                return expectation;
        }
    };

    // Group config items by section
    const groupItemsBySection = (items: ConfigurationItem[]) => {
        const grouped: { [key: string]: ConfigurationItem[] } = {};
        items.forEach(item => {
            const key = `${item.section_number}|${item.section_title}`;
            if (!grouped[key]) {
                grouped[key] = [];
            }
            grouped[key].push(item);
        });
        return grouped;
    };

    return (
        <Layout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex justify-between items-center">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">Component Definition Version History</h1>
                        <p className="text-gray-600 mt-2">
                            View all published versions of validation component definitions and their configuration snapshots
                        </p>
                    </div>
                </div>

                {/* Error Message */}
                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded">
                        {error}
                    </div>
                )}

                {/* Loading State */}
                {loading ? (
                    <div className="text-center py-12">
                        <div className="text-gray-500">Loading component definition history...</div>
                    </div>
                ) : (
                    <>
                        {/* Info Box */}
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                            <div className="flex items-start">
                                <div className="flex-shrink-0">
                                    <svg className="h-5 w-5 text-blue-400 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                                    </svg>
                                </div>
                                <div className="ml-3">
                                    <h3 className="text-sm font-medium text-blue-800">About Component Definition Versioning</h3>
                                    <div className="mt-2 text-sm text-blue-700">
                                        <p>
                                            Component definition versions represent point-in-time snapshots of all validation component requirements.
                                            When a validation plan is locked (moved to Review or Pending Approval), it captures the active
                                            component definitions at that moment, ensuring historical compliance and preventing retroactive changes.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Configurations List */}
                        {configurations.length === 0 ? (
                            <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                                No component definition versions found.
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {configurations.map(config => (
                                    <div key={config.config_id} className="bg-white rounded-lg shadow-md overflow-hidden">
                                        {/* Configuration Header */}
                                        <div
                                            className="px-6 py-4 bg-gray-50 border-b cursor-pointer hover:bg-gray-100 transition-colors"
                                            onClick={() => handleExpandConfiguration(config.config_id)}
                                        >
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center space-x-4">
                                                    <div>
                                                        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                                                            {config.config_name}
                                                            {config.is_active && (
                                                                <span className="bg-green-100 text-green-800 text-xs font-semibold px-2.5 py-0.5 rounded">
                                                                    ACTIVE
                                                                </span>
                                                            )}
                                                        </h3>
                                                        <p className="text-sm text-gray-600 mt-1">
                                                            {config.description || 'No description'}
                                                        </p>
                                                    </div>
                                                </div>
                                                <div className="flex items-center space-x-6 text-sm text-gray-600">
                                                    <div>
                                                        <span className="font-medium">Effective Date:</span>{' '}
                                                        {config.effective_date.split('T')[0]}
                                                    </div>
                                                    <div>
                                                        <span className="font-medium">Created:</span>{' '}
                                                        {config.created_at.split('T')[0]}
                                                    </div>
                                                    <svg
                                                        className={`w-5 h-5 text-gray-500 transition-transform ${
                                                            expandedConfigId === config.config_id ? 'rotate-180' : ''
                                                        }`}
                                                        fill="none"
                                                        stroke="currentColor"
                                                        viewBox="0 0 24 24"
                                                    >
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                                    </svg>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Expanded Configuration Details */}
                                        {expandedConfigId === config.config_id && (
                                            <div className="px-6 py-4">
                                                {loadingDetail ? (
                                                    <div className="text-center py-8 text-gray-500">
                                                        Loading configuration details...
                                                    </div>
                                                ) : expandedConfig ? (
                                                    <div className="space-y-4">
                                                        <div className="bg-blue-50 border border-blue-200 rounded p-3">
                                                            <p className="text-sm text-blue-800">
                                                                <strong>Configuration Snapshot:</strong> This configuration contains{' '}
                                                                {expandedConfig.config_items?.length || 0} component definitions as they existed on{' '}
                                                                {config.effective_date.split('T')[0]}.
                                                            </p>
                                                        </div>

                                                        {/* Component Items by Section */}
                                                        {expandedConfig.config_items && expandedConfig.config_items.length > 0 ? (
                                                            <>
                                                                {Object.entries(groupItemsBySection(expandedConfig.config_items)).map(([sectionKey, items]) => {
                                                                    const [sectionNum, sectionTitle] = sectionKey.split('|');
                                                                    return (
                                                                        <div key={sectionKey} className="border rounded-lg overflow-hidden">
                                                                            <div className="bg-gray-100 px-4 py-2 border-b">
                                                                                <h4 className="font-semibold text-gray-800">
                                                                                    Section {sectionNum} – {sectionTitle}
                                                                                </h4>
                                                                            </div>
                                                                            <div className="overflow-x-auto">
                                                                                <table className="min-w-full divide-y divide-gray-200">
                                                                                    <thead className="bg-gray-50">
                                                                                        <tr>
                                                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                                                                Component
                                                                                            </th>
                                                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                                                                High Risk
                                                                                            </th>
                                                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                                                                Medium Risk
                                                                                            </th>
                                                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                                                                Low Risk
                                                                                            </th>
                                                                                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                                                                Very Low Risk
                                                                                            </th>
                                                                                        </tr>
                                                                                    </thead>
                                                                                    <tbody className="bg-white divide-y divide-gray-200">
                                                                                        {items.map(item => (
                                                                                            <tr key={item.config_item_id} className="hover:bg-gray-50">
                                                                                                <td className="px-4 py-3">
                                                                                                    <div className="text-sm font-medium text-gray-900">
                                                                                                        {item.component_code}
                                                                                                    </div>
                                                                                                    <div className="text-sm text-gray-500">
                                                                                                        {item.component_title}
                                                                                                    </div>
                                                                                                </td>
                                                                                                <td className="px-4 py-3">
                                                                                                    <span className={`px-2 py-1 text-xs font-semibold rounded ${getExpectationBadgeColor(item.expectation_high)}`}>
                                                                                                        {formatExpectation(item.expectation_high)}
                                                                                                    </span>
                                                                                                </td>
                                                                                                <td className="px-4 py-3">
                                                                                                    <span className={`px-2 py-1 text-xs font-semibold rounded ${getExpectationBadgeColor(item.expectation_medium)}`}>
                                                                                                        {formatExpectation(item.expectation_medium)}
                                                                                                    </span>
                                                                                                </td>
                                                                                                <td className="px-4 py-3">
                                                                                                    <span className={`px-2 py-1 text-xs font-semibold rounded ${getExpectationBadgeColor(item.expectation_low)}`}>
                                                                                                        {formatExpectation(item.expectation_low)}
                                                                                                    </span>
                                                                                                </td>
                                                                                                <td className="px-4 py-3">
                                                                                                    <span className={`px-2 py-1 text-xs font-semibold rounded ${getExpectationBadgeColor(item.expectation_very_low)}`}>
                                                                                                        {formatExpectation(item.expectation_very_low)}
                                                                                                    </span>
                                                                                                </td>
                                                                                            </tr>
                                                                                        ))}
                                                                                    </tbody>
                                                                                </table>
                                                                            </div>
                                                                        </div>
                                                                    );
                                                                })}
                                                            </>
                                                        ) : (
                                                            <div className="text-center py-8 text-gray-500">
                                                                No component items found for this configuration.
                                                            </div>
                                                        )}
                                                    </div>
                                                ) : null}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </>
                )}
            </div>
        </Layout>
    );
};

export default ConfigurationHistoryPage;
