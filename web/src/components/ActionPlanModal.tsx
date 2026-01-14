import { useState, useEffect } from 'react';
import { recommendationsApi, Recommendation, ActionPlanTaskCreate } from '../api/recommendations';

interface User {
    user_id: number;
    email: string;
    full_name: string;
}

interface ActionPlanModalProps {
    recommendation: Recommendation;
    users: User[];
    onClose: () => void;
    onSuccess: () => void;
}

interface TaskForm {
    description: string;
    owner_id: number | null;
    target_date: string;
}

export default function ActionPlanModal({ recommendation, users, onClose, onSuccess }: ActionPlanModalProps) {
    const currentStatus = recommendation.current_status?.code || '';
    const isReviewMode = currentStatus === 'REC_PENDING_VALIDATOR_REVIEW';

    // Get initial owner name for the default assigned user
    const getInitialOwnerName = () => {
        if (recommendation.assigned_to_id) {
            const user = users.find(u => u.user_id === recommendation.assigned_to_id);
            return user?.full_name || '';
        }
        return '';
    };

    // For submitting new action plan
    const [tasks, setTasks] = useState<TaskForm[]>([
        { description: '', owner_id: recommendation.assigned_to_id, target_date: recommendation.current_target_date }
    ]);

    // Owner search state per task
    const [ownerSearchQueries, setOwnerSearchQueries] = useState<string[]>([getInitialOwnerName()]);
    const [showOwnerDropdowns, setShowOwnerDropdowns] = useState<boolean[]>([false]);

    // For reviewing action plan
    const [reviewDecision, setReviewDecision] = useState<'APPROVE' | 'REQUEST_CHANGES'>('APPROVE');
    const [reviewComments, setReviewComments] = useState('');

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Update search queries when users load (fixes timing issue where users array is empty on mount)
    useEffect(() => {
        if (users.length > 0 && recommendation.assigned_to_id) {
            const assignedUser = users.find(u => u.user_id === recommendation.assigned_to_id);
            if (assignedUser) {
                setOwnerSearchQueries(prev =>
                    prev.map((query, idx) => {
                        // Only update if empty and task has the assigned owner
                        if (!query && tasks[idx]?.owner_id === recommendation.assigned_to_id) {
                            return assignedUser.full_name;
                        }
                        return query;
                    })
                );
            }
        }
    }, [users, recommendation.assigned_to_id]);

    const addTask = () => {
        setTasks([...tasks, {
            description: '',
            owner_id: recommendation.assigned_to_id,
            target_date: recommendation.current_target_date
        }]);
        setOwnerSearchQueries([...ownerSearchQueries, getInitialOwnerName()]);
        setShowOwnerDropdowns([...showOwnerDropdowns, false]);
    };

    const removeTask = (index: number) => {
        if (tasks.length > 1) {
            setTasks(tasks.filter((_, i) => i !== index));
            setOwnerSearchQueries(ownerSearchQueries.filter((_, i) => i !== index));
            setShowOwnerDropdowns(showOwnerDropdowns.filter((_, i) => i !== index));
        }
    };

    const updateOwnerSearch = (index: number, query: string) => {
        const updated = [...ownerSearchQueries];
        updated[index] = query;
        setOwnerSearchQueries(updated);
    };

    const setOwnerDropdownVisible = (index: number, visible: boolean) => {
        const updated = [...showOwnerDropdowns];
        updated[index] = visible;
        setShowOwnerDropdowns(updated);
    };

    const selectOwner = (index: number, user: User) => {
        updateTask(index, 'owner_id', user.user_id);
        updateOwnerSearch(index, user.full_name);
        setOwnerDropdownVisible(index, false);
    };

    const updateTask = (index: number, field: keyof TaskForm, value: any) => {
        const updated = [...tasks];
        updated[index] = { ...updated[index], [field]: value };
        setTasks(updated);
    };

    const handleSubmitActionPlan = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        // Validate tasks
        const invalidTasks = tasks.some(t => !t.description.trim() || !t.owner_id || !t.target_date);
        if (invalidTasks) {
            setError('All tasks must have a description, owner, and target date');
            return;
        }

        try {
            setLoading(true);
            const taskData: ActionPlanTaskCreate[] = tasks.map(t => ({
                description: t.description.trim(),
                owner_id: t.owner_id!,
                target_date: t.target_date
            }));
            await recommendationsApi.submitActionPlan(recommendation.recommendation_id, taskData);
            onSuccess();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to submit action plan');
        } finally {
            setLoading(false);
        }
    };

    const handleReviewActionPlan = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        try {
            setLoading(true);
            if (reviewDecision === 'APPROVE') {
                await recommendationsApi.finalize(recommendation.recommendation_id);
            } else {
                await recommendationsApi.requestActionPlanRevisions(
                    recommendation.recommendation_id,
                    reviewComments.trim()
                );
            }
            onSuccess();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to submit review');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                <div className="p-6">
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="text-lg font-bold">
                            {isReviewMode ? 'Review Action Plan' : 'Submit Action Plan'}
                        </h3>
                        <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    {error && (
                        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                            {error}
                        </div>
                    )}

                    {isReviewMode ? (
                        // Review Mode - Validator reviewing action plan
                        <form onSubmit={handleReviewActionPlan}>
                            {/* Show existing tasks */}
                            {recommendation.action_plan_tasks && recommendation.action_plan_tasks.length > 0 && (
                                <div className="bg-gray-50 p-4 rounded-lg mb-4">
                                    <h4 className="font-medium mb-3">Proposed Action Plan</h4>
                                    <div className="space-y-3">
                                        {recommendation.action_plan_tasks.map((task, index) => (
                                            <div key={task.task_id} className="border-l-4 border-blue-400 pl-3 py-2">
                                                <div className="flex justify-between items-start">
                                                    <div>
                                                        <span className="text-sm font-medium text-gray-500">Task {index + 1}</span>
                                                        <p className="text-gray-800">{task.description}</p>
                                                    </div>
                                                </div>
                                                <div className="mt-1 text-sm text-gray-500">
                                                    <span>Owner: {task.owner?.full_name}</span>
                                                    <span className="mx-2">•</span>
                                                    <span>Target: {task.target_date}</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Decision <span className="text-red-500">*</span>
                                    </label>
                                    <div className="space-y-2">
                                        <label className="flex items-center">
                                            <input
                                                type="radio"
                                                value="APPROVE"
                                                checked={reviewDecision === 'APPROVE'}
                                                onChange={() => setReviewDecision('APPROVE')}
                                                className="mr-2"
                                            />
                                            <span className="text-green-700">Approve Action Plan</span>
                                            <span className="text-sm text-gray-500 ml-2">
                                                (Developer can begin work)
                                            </span>
                                        </label>
                                        <label className="flex items-center">
                                            <input
                                                type="radio"
                                                value="REQUEST_CHANGES"
                                                checked={reviewDecision === 'REQUEST_CHANGES'}
                                                onChange={() => setReviewDecision('REQUEST_CHANGES')}
                                                className="mr-2"
                                            />
                                            <span className="text-orange-700">Request Changes</span>
                                            <span className="text-sm text-gray-500 ml-2">
                                                (Developer must revise plan)
                                            </span>
                                        </label>
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Review Comments
                                        {reviewDecision === 'REQUEST_CHANGES' && <span className="text-red-500"> *</span>}
                                    </label>
                                    <textarea
                                        value={reviewComments}
                                        onChange={(e) => setReviewComments(e.target.value)}
                                        rows={3}
                                        className="input-field"
                                        placeholder={reviewDecision === 'REQUEST_CHANGES'
                                            ? "Explain what changes are needed..."
                                            : "Optional comments..."}
                                        required={reviewDecision === 'REQUEST_CHANGES'}
                                    />
                                </div>
                            </div>

                            <div className="flex justify-end gap-3 mt-6 pt-4 border-t">
                                <button
                                    type="button"
                                    onClick={onClose}
                                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                                    disabled={loading}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className={`px-4 py-2 text-white rounded ${
                                        reviewDecision === 'APPROVE'
                                            ? 'bg-green-600 hover:bg-green-700'
                                            : 'bg-orange-600 hover:bg-orange-700'
                                    }`}
                                    disabled={loading}
                                >
                                    {loading ? 'Submitting...' : reviewDecision === 'APPROVE' ? 'Approve Plan' : 'Request Changes'}
                                </button>
                            </div>
                        </form>
                    ) : (
                        // Submit Mode - Developer creating action plan
                        <form onSubmit={handleSubmitActionPlan}>
                            <p className="text-sm text-gray-600 mb-4">
                                Create an action plan with specific tasks to remediate this recommendation.
                                Each task should have a clear owner and target date.
                            </p>

                            <div className="space-y-4">
                                {tasks.map((task, index) => (
                                    <div key={index} className="border rounded-lg p-4">
                                        <div className="flex justify-between items-center mb-3">
                                            <span className="font-medium">Task {index + 1}</span>
                                            {tasks.length > 1 && (
                                                <button
                                                    type="button"
                                                    onClick={() => removeTask(index)}
                                                    className="text-red-500 hover:text-red-700 text-sm"
                                                >
                                                    Remove
                                                </button>
                                            )}
                                        </div>

                                        <div className="space-y-3">
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    Description <span className="text-red-500">*</span>
                                                </label>
                                                <textarea
                                                    value={task.description}
                                                    onChange={(e) => updateTask(index, 'description', e.target.value)}
                                                    rows={2}
                                                    className="input-field"
                                                    placeholder="Describe the task..."
                                                    required
                                                />
                                            </div>

                                            <div className="grid grid-cols-2 gap-3">
                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                                        Task Owner <span className="text-red-500">*</span>
                                                    </label>
                                                    <div className="relative">
                                                        <input
                                                            type="text"
                                                            placeholder="Type to search users..."
                                                            value={ownerSearchQueries[index] || ''}
                                                            onChange={(e) => {
                                                                updateOwnerSearch(index, e.target.value);
                                                                setOwnerDropdownVisible(index, true);
                                                                // Clear selection if user modifies text
                                                                if (task.owner_id) {
                                                                    const selectedUser = users.find(u => u.user_id === task.owner_id);
                                                                    if (selectedUser && e.target.value !== selectedUser.full_name) {
                                                                        updateTask(index, 'owner_id', null);
                                                                    }
                                                                }
                                                            }}
                                                            onFocus={() => setOwnerDropdownVisible(index, true)}
                                                            onBlur={() => {
                                                                // Delay to allow click to register
                                                                setTimeout(() => setOwnerDropdownVisible(index, false), 200);
                                                            }}
                                                            className="input-field"
                                                        />
                                                        {showOwnerDropdowns[index] && ownerSearchQueries[index]?.length > 0 && (
                                                            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-48 overflow-y-auto">
                                                                {users
                                                                    .filter((u) =>
                                                                        u.full_name.toLowerCase().includes((ownerSearchQueries[index] || '').toLowerCase()) ||
                                                                        u.email.toLowerCase().includes((ownerSearchQueries[index] || '').toLowerCase())
                                                                    )
                                                                    .slice(0, 50)
                                                                    .map((u) => (
                                                                        <div
                                                                            key={u.user_id}
                                                                            className="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                                                                            onMouseDown={() => selectOwner(index, u)}
                                                                        >
                                                                            <div className="font-medium">{u.full_name}</div>
                                                                            <div className="text-gray-500 text-xs">{u.email}</div>
                                                                        </div>
                                                                    ))}
                                                                {users.filter((u) =>
                                                                    u.full_name.toLowerCase().includes((ownerSearchQueries[index] || '').toLowerCase()) ||
                                                                    u.email.toLowerCase().includes((ownerSearchQueries[index] || '').toLowerCase())
                                                                ).length === 0 && (
                                                                    <div className="px-3 py-2 text-sm text-gray-500">No users found</div>
                                                                )}
                                                            </div>
                                                        )}
                                                    </div>
                                                    {task.owner_id && users.find(u => u.user_id === task.owner_id) && (
                                                        <p className="mt-1 text-xs text-green-600">
                                                            ✓ Selected: {users.find(u => u.user_id === task.owner_id)!.full_name}
                                                        </p>
                                                    )}
                                                </div>

                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                                        Target Date <span className="text-red-500">*</span>
                                                    </label>
                                                    <input
                                                        type="date"
                                                        value={task.target_date}
                                                        onChange={(e) => updateTask(index, 'target_date', e.target.value)}
                                                        className="input-field"
                                                        min={new Date().toISOString().split('T')[0]}
                                                        required
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ))}

                                <button
                                    type="button"
                                    onClick={addTask}
                                    className="w-full py-2 border-2 border-dashed border-gray-300 text-gray-500 rounded hover:border-gray-400 hover:text-gray-600"
                                >
                                    + Add Another Task
                                </button>
                            </div>

                            <div className="flex justify-end gap-3 mt-6 pt-4 border-t">
                                <button
                                    type="button"
                                    onClick={onClose}
                                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                                    disabled={loading}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
                                    disabled={loading}
                                >
                                    {loading ? 'Submitting...' : 'Submit Action Plan'}
                                </button>
                            </div>
                        </form>
                    )}
                </div>
            </div>
        </div>
    );
}
