import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import api from '../api/client';
import { savedQueriesApi, SavedQuery } from '../api/savedQueries';

export default function AnalyticsPage() {
    const [query, setQuery] = useState('SELECT * FROM models LIMIT 10;');
    const [results, setResults] = useState<any[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    // Saved queries state
    const [savedQueries, setSavedQueries] = useState<SavedQuery[]>([]);
    const [selectedQueryId, setSelectedQueryId] = useState<number | null>(null);
    const [showSaveModal, setShowSaveModal] = useState(false);
    const [saveQueryName, setSaveQueryName] = useState('');
    const [saveQueryDescription, setSaveQueryDescription] = useState('');
    const [saveQueryIsPublic, setSaveQueryIsPublic] = useState(false);
    const [saveLoading, setSaveLoading] = useState(false);

    useEffect(() => {
        loadSavedQueries();
    }, []);

    const loadSavedQueries = async () => {
        try {
            const queries = await savedQueriesApi.list();
            setSavedQueries(queries);
        } catch (err) {
            console.error('Failed to load saved queries:', err);
        }
    };

    const handleLoadQuery = (queryId: number) => {
        const savedQuery = savedQueries.find(q => q.query_id === queryId);
        if (savedQuery) {
            setQuery(savedQuery.query_text);
            setSelectedQueryId(queryId);
        }
    };

    const handleSaveQuery = async () => {
        if (!saveQueryName.trim()) {
            alert('Please enter a query name');
            return;
        }

        setSaveLoading(true);
        try {
            await savedQueriesApi.create({
                query_name: saveQueryName,
                query_text: query,
                description: saveQueryDescription || undefined,
                is_public: saveQueryIsPublic,
            });
            await loadSavedQueries();
            setShowSaveModal(false);
            setSaveQueryName('');
            setSaveQueryDescription('');
            setSaveQueryIsPublic(false);
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to save query');
        } finally {
            setSaveLoading(false);
        }
    };

    const handleDeleteQuery = async (queryId: number) => {
        if (!confirm('Are you sure you want to delete this saved query?')) {
            return;
        }

        try {
            await savedQueriesApi.delete(queryId);
            await loadSavedQueries();
            if (selectedQueryId === queryId) {
                setSelectedQueryId(null);
            }
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to delete query');
        }
    };

    const handleRunQuery = async () => {
        setLoading(true);
        setError(null);
        setResults([]);
        try {
            const response = await api.post('/analytics/query', { query });
            setResults(response.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message || 'An error occurred');
        } finally {
            setLoading(false);
        }
    };

    const handleExportCSV = () => {
        if (results.length === 0) return;

        try {
            // Get headers from first row
            const headers = Object.keys(results[0]);

            // Generate CSV rows
            const rows = results.map(row => {
                return headers.map(header => {
                    let value = row[header];
                    if (value === null || value === undefined) {
                        return '';
                    }
                    value = String(value);
                    // Escape quotes and wrap in quotes if necessary
                    value = value.replace(/"/g, '""');
                    if (value.includes(',') || value.includes('"') || value.includes('\n')) {
                        value = `"${value}"`;
                    }
                    return value;
                }).join(',');
            });

            // Combine headers and rows
            const csv = [headers.join(','), ...rows].join('\n');

            // Create blob and download
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;

            const date = new Date().toISOString().split('T')[0];
            link.setAttribute('download', `query_results_${date}.csv`);

            document.body.appendChild(link);
            link.click();

            link.parentNode?.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Failed to export CSV:', error);
            alert('Failed to export CSV.');
        }
    };

    return (
        <Layout>
            <div className="flex flex-col h-full">
                <h2 className="text-2xl font-bold mb-4">Advanced Analytics (SQL)</h2>

                <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4">
                    <div className="flex">
                        <div className="flex-shrink-0">
                            <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                            </svg>
                        </div>
                        <div className="ml-3">
                            <p className="text-sm text-yellow-700">
                                Warning: You are executing raw SQL queries against the database. Only read-only statements (SELECT, WITH, EXPLAIN, SHOW, VALUES, TABLE) are allowed.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Saved Queries Controls */}
                <div className="mb-4 flex gap-2 items-center">
                    <label className="text-sm font-medium text-gray-700">Saved Queries:</label>
                    <select
                        className="border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        value={selectedQueryId || ''}
                        onChange={(e) => handleLoadQuery(Number(e.target.value))}
                    >
                        <option value="">-- Select a saved query --</option>
                        {savedQueries.map((sq) => (
                            <option key={sq.query_id} value={sq.query_id}>
                                {sq.is_public ? '🌐 ' : ''}{sq.query_name}
                            </option>
                        ))}
                    </select>
                    {selectedQueryId && (
                        <button
                            onClick={() => handleDeleteQuery(selectedQueryId)}
                            className="text-red-600 hover:text-red-800 text-sm"
                            title="Delete selected query"
                        >
                            Delete
                        </button>
                    )}
                </div>

                <div className="mb-4">
                    <textarea
                        className="w-full h-32 p-4 font-mono text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Enter your SQL query here..."
                    />
                </div>

                <div className="mb-6 flex gap-2">
                    <button
                        onClick={handleRunQuery}
                        disabled={loading}
                        className={`btn-primary ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                        {loading ? 'Running...' : 'Run Query'}
                    </button>
                    <button
                        onClick={() => setShowSaveModal(true)}
                        className="btn-secondary"
                    >
                        Save Query
                    </button>
                    {results.length > 0 && (
                        <button
                            onClick={handleExportCSV}
                            className="btn-secondary"
                        >
                            Export CSV
                        </button>
                    )}
                </div>

                {error && (
                    <div className="bg-red-50 border-l-4 border-red-400 p-4 mb-6">
                        <div className="flex">
                            <div className="flex-shrink-0">
                                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                </svg>
                            </div>
                            <div className="ml-3">
                                <p className="text-sm text-red-700">{error}</p>
                            </div>
                        </div>
                    </div>
                )}

                {results.length > 0 && (
                    <div className="flex-1 overflow-auto border rounded-lg shadow">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    {Object.keys(results[0]).map((key) => (
                                        <th
                                            key={key}
                                            className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                                        >
                                            {key}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {results.map((row, i) => (
                                    <tr key={i} className="hover:bg-gray-50">
                                        {Object.values(row).map((value: any, j) => (
                                            <td key={j} className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {value === null ? 'NULL' : String(value)}
                                            </td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {results.length === 0 && !loading && !error && (
                    <div className="text-center text-gray-500 mt-10">
                        No results to display. Run a query to see data.
                    </div>
                )}

                {/* Save Query Modal */}
                {showSaveModal && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg">
                            <h2 className="text-2xl font-bold mb-4">Save Query</h2>

                            <div className="mb-4">
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Query Name *
                                </label>
                                <input
                                    type="text"
                                    value={saveQueryName}
                                    onChange={(e) => setSaveQueryName(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    placeholder="e.g., High-Risk Models Report"
                                    required
                                />
                            </div>

                            <div className="mb-4">
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Description (Optional)
                                </label>
                                <textarea
                                    value={saveQueryDescription}
                                    onChange={(e) => setSaveQueryDescription(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    placeholder="What does this query do?"
                                    rows={3}
                                />
                            </div>

                            <div className="mb-6">
                                <label className="flex items-center">
                                    <input
                                        type="checkbox"
                                        checked={saveQueryIsPublic}
                                        onChange={(e) => setSaveQueryIsPublic(e.target.checked)}
                                        className="mr-2"
                                    />
                                    <span className="text-sm text-gray-700">
                                        Make this query public (visible to all users)
                                    </span>
                                </label>
                            </div>

                            <div className="flex justify-end gap-3">
                                <button
                                    onClick={() => {
                                        setShowSaveModal(false);
                                        setSaveQueryName('');
                                        setSaveQueryDescription('');
                                        setSaveQueryIsPublic(false);
                                    }}
                                    className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                                    disabled={saveLoading}
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleSaveQuery}
                                    className="btn-primary"
                                    disabled={saveLoading || !saveQueryName.trim()}
                                >
                                    {saveLoading ? 'Saving...' : 'Save Query'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </Layout>
    );
}
