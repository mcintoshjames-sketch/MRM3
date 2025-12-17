import { useState } from 'react';
import { recommendationsApi, Recommendation } from '../api/recommendations';

interface EvidenceSectionProps {
    recommendation: Recommendation;
    canUpload: boolean;
    onRefresh: () => void;
}

export default function EvidenceSection({ recommendation, canUpload, onRefresh }: EvidenceSectionProps) {
    const [showUploadForm, setShowUploadForm] = useState(false);
    const [description, setDescription] = useState('');
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleUpload = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!selectedFile) {
            setError('Please select a file to upload');
            return;
        }

        try {
            setLoading(true);
            // Extract file metadata
            const fileMetadata = {
                file_name: selectedFile.name,
                file_path: selectedFile.name,  // TODO: Backend should set this after upload to storage
                file_type: selectedFile.type || undefined,
                file_size_bytes: selectedFile.size,
                description: description.trim() || undefined
            };

            // Note: This sends metadata only. Full implementation requires:
            // 1. Backend multipart/form-data endpoint
            // 2. File storage (S3/local)
            // 3. FormData upload on frontend
            await recommendationsApi.uploadEvidence(recommendation.recommendation_id, fileMetadata);
            setDescription('');
            setSelectedFile(null);
            setShowUploadForm(false);
            onRefresh();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to upload evidence');
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (evidenceId: number) => {
        if (!confirm('Are you sure you want to delete this evidence?')) return;

        try {
            await recommendationsApi.deleteEvidence(recommendation.recommendation_id, evidenceId);
            onRefresh();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to delete evidence');
        }
    };

    const evidence = recommendation.closure_evidence || [];

    return (
        <div>
            {/* Upload Button / Form */}
            {canUpload && (
                <div className="mb-4">
                    {showUploadForm ? (
                        <form onSubmit={handleUpload} className="border rounded-lg p-4 bg-gray-50">
                            <h4 className="font-medium mb-3">Add Evidence</h4>

                            {error && (
                                <div className="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded mb-3 text-sm">
                                    {error}
                                </div>
                            )}

                            <div className="space-y-3">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Select File <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        type="file"
                                        onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                                        className="block w-full text-sm text-gray-500
                                            file:mr-4 file:py-2 file:px-4
                                            file:rounded file:border-0
                                            file:text-sm file:font-medium
                                            file:bg-blue-50 file:text-blue-700
                                            hover:file:bg-blue-100"
                                        required
                                    />
                                    {selectedFile && (
                                        <p className="text-xs text-gray-600 mt-1">
                                            Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                                        </p>
                                    )}
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Description <span className="text-gray-400">(Optional)</span>
                                    </label>
                                    <textarea
                                        value={description}
                                        onChange={(e) => setDescription(e.target.value)}
                                        rows={3}
                                        className="input-field"
                                        placeholder="Describe the evidence being uploaded..."
                                    />
                                </div>
                            </div>

                            <div className="flex justify-end gap-2 mt-4">
                                <button
                                    type="button"
                                    onClick={() => {
                                        setShowUploadForm(false);
                                        setDescription('');
                                        setSelectedFile(null);
                                        setError(null);
                                    }}
                                    className="px-3 py-1.5 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                                    disabled={loading}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                                    disabled={loading}
                                >
                                    {loading ? 'Adding...' : 'Add Evidence'}
                                </button>
                            </div>
                        </form>
                    ) : (
                        <button
                            onClick={() => setShowUploadForm(true)}
                            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                        >
                            + Add Evidence
                        </button>
                    )}
                </div>
            )}

            {/* Evidence List */}
            {evidence.length > 0 ? (
                <div className="space-y-3">
                    {evidence.map((item) => (
                        <div key={item.evidence_id} className="border rounded-lg p-4">
                            <div className="flex justify-between items-start">
                                <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1">
                                        <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                        </svg>
                                        <p className="text-gray-900 font-medium">{item.file_name}</p>
                                    </div>
                                    {item.description && (
                                        <p className="text-gray-700 text-sm mt-1">{item.description}</p>
                                    )}
                                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                                        {item.file_size_bytes && (
                                            <span>{(item.file_size_bytes / 1024).toFixed(1)} KB</span>
                                        )}
                                        {item.file_type && (
                                            <span>{item.file_type}</span>
                                        )}
                                    </div>
                                    <div className="mt-2 text-sm text-gray-500">
                                        <span>Uploaded by {item.uploaded_by?.full_name}</span>
                                        <span className="mx-2">•</span>
                                        <span>{item.uploaded_at?.split('T')[0]}</span>
                                    </div>
                                </div>
                                {canUpload && (
                                    <button
                                        onClick={() => handleDelete(item.evidence_id)}
                                        className="ml-4 text-red-500 hover:text-red-700"
                                        title="Delete evidence"
                                    >
                                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                        </svg>
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <p className="text-gray-500 text-center py-8">No evidence uploaded yet.</p>
            )}
        </div>
    );
}
