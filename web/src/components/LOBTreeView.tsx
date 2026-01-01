import React, { useState, useEffect } from 'react';
import { LOBUnitTreeNode, LOBUnitCreate, LOBUnitUpdate, lobApi } from '../api/lob';
import { useAuth } from '../contexts/AuthContext';
import { canManageLob } from '../utils/roleUtils';

interface LOBTreeViewProps {
    onSelectLOB?: (lob: LOBUnitTreeNode | null) => void;
    selectedLOBId?: number | null;
    showInactive?: boolean;
}

interface TreeNodeProps {
    node: LOBUnitTreeNode;
    level: number;
    expandedNodes: Set<number>;
    toggleExpand: (id: number) => void;
    selectedId: number | null;
    onSelect: (node: LOBUnitTreeNode) => void;
    onEdit: (node: LOBUnitTreeNode) => void;
    onAddChild: (parent: LOBUnitTreeNode) => void;
    onDeactivate: (node: LOBUnitTreeNode) => void;
    canManageLob: boolean;
}

const TreeNode: React.FC<TreeNodeProps> = ({
    node,
    level,
    expandedNodes,
    toggleExpand,
    selectedId,
    onSelect,
    onEdit,
    onAddChild,
    onDeactivate,
    canManageLob
}) => {
    const hasChildren = node.children && node.children.length > 0;
    const isExpanded = expandedNodes.has(node.lob_id);
    const isSelected = selectedId === node.lob_id;

    return (
        <div className="select-none">
            <div
                className={`flex items-center py-1.5 px-2 rounded cursor-pointer hover:bg-gray-100 ${
                    isSelected ? 'bg-blue-100 border-l-4 border-blue-500' : ''
                } ${!node.is_active ? 'opacity-50' : ''}`}
                style={{ paddingLeft: `${level * 20 + 8}px` }}
                onClick={() => onSelect(node)}
            >
                {/* Expand/Collapse button */}
                <button
                    className="w-5 h-5 mr-1 flex items-center justify-center text-gray-500 hover:text-gray-700"
                    onClick={(e) => {
                        e.stopPropagation();
                        if (hasChildren) toggleExpand(node.lob_id);
                    }}
                >
                    {hasChildren ? (
                        isExpanded ? (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                        ) : (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                        )
                    ) : (
                        <span className="w-4" />
                    )}
                </button>

                {/* Folder/Document icon */}
                <span className="mr-2">
                    {hasChildren ? (
                        <svg className="w-5 h-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
                        </svg>
                    ) : (
                        <svg className="w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                        </svg>
                    )}
                </span>

                {/* Name, org_unit, and code */}
                <div className="flex-1 min-w-0">
                    <span className="text-xs text-blue-600 font-mono">[{node.org_unit}]</span>
                    <span className="ml-1 font-medium text-gray-900 truncate">{node.name}</span>
                    <span className="ml-2 text-xs text-gray-500">({node.code})</span>
                    {node.user_count > 0 && (
                        <span className="ml-2 text-xs bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded-full">
                            {node.user_count} user{node.user_count !== 1 ? 's' : ''}
                        </span>
                    )}
                    {!node.is_active && (
                        <span className="ml-2 text-xs bg-red-100 text-red-600 px-1.5 py-0.5 rounded-full">
                            Inactive
                        </span>
                    )}
                </div>

                {/* Action buttons (Admin only) */}
                {canManageLob && (
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 hover:opacity-100">
                        <button
                            className="p-1 text-gray-400 hover:text-blue-600"
                            onClick={(e) => { e.stopPropagation(); onEdit(node); }}
                            title="Edit"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                        </button>
                        <button
                            className="p-1 text-gray-400 hover:text-green-600"
                            onClick={(e) => { e.stopPropagation(); onAddChild(node); }}
                            title="Add Child"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                            </svg>
                        </button>
                        {node.is_active && (
                            <button
                                className="p-1 text-gray-400 hover:text-red-600"
                                onClick={(e) => { e.stopPropagation(); onDeactivate(node); }}
                                title="Deactivate"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                                </svg>
                            </button>
                        )}
                    </div>
                )}
            </div>

            {/* Children */}
            {hasChildren && isExpanded && (
                <div>
                    {node.children.map((child) => (
                        <TreeNode
                            key={child.lob_id}
                            node={child}
                            level={level + 1}
                            expandedNodes={expandedNodes}
                            toggleExpand={toggleExpand}
                            selectedId={selectedId}
                            onSelect={onSelect}
                            onEdit={onEdit}
                            onAddChild={onAddChild}
                            onDeactivate={onDeactivate}
                            canManageLob={canManageLob}
                        />
                    ))}
                </div>
            )}
        </div>
    );
};

interface LOBFormModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (data: LOBUnitCreate | LOBUnitUpdate) => Promise<void>;
    editNode?: LOBUnitTreeNode | null;
    parentNode?: LOBUnitTreeNode | null;
}

const LOBFormModal: React.FC<LOBFormModalProps> = ({
    isOpen,
    onClose,
    onSave,
    editNode,
    parentNode
}) => {
    const [code, setCode] = useState('');
    const [name, setName] = useState('');
    const [orgUnit, setOrgUnit] = useState('');
    const [sortOrder, setSortOrder] = useState(0);
    const [isActive, setIsActive] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (editNode) {
            setCode(editNode.code);
            setName(editNode.name);
            setOrgUnit(editNode.org_unit);
            setSortOrder(editNode.sort_order);
            setIsActive(editNode.is_active);
        } else {
            setCode('');
            setName('');
            setOrgUnit('');
            setSortOrder(0);
            setIsActive(true);
        }
        setError(null);
    }, [editNode, isOpen]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setSaving(true);

        try {
            if (editNode) {
                await onSave({ code, name, org_unit: orgUnit, sort_order: sortOrder, is_active: isActive });
            } else {
                await onSave({
                    code,
                    name,
                    org_unit: orgUnit,
                    parent_id: parentNode?.lob_id || null,
                    sort_order: sortOrder
                });
            }
            onClose();
        } catch (err: unknown) {
            const errorMsg = err instanceof Error ? err.message : 'Failed to save LOB unit';
            setError(errorMsg);
        } finally {
            setSaving(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
                <h3 className="text-lg font-semibold mb-4">
                    {editNode ? 'Edit LOB Unit' : parentNode ? `Add Child under "${parentNode.name}"` : 'Add Root LOB Unit'}
                </h3>

                {error && (
                    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Code <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            value={code}
                            onChange={(e) => setCode(e.target.value.toUpperCase())}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="e.g., RETAIL, GM, FX"
                            required
                            pattern="[A-Za-z0-9_]+"
                            title="Only letters, numbers, and underscores"
                        />
                        <p className="text-xs text-gray-500 mt-1">Only letters, numbers, and underscores</p>
                    </div>

                    <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Name <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="e.g., Retail Banking"
                            required
                        />
                    </div>

                    <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Org Unit <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            value={orgUnit}
                            onChange={(e) => setOrgUnit(e.target.value.toUpperCase())}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                            placeholder="e.g., 12345 or S0001"
                            required
                            maxLength={5}
                            pattern="[0-9]{5}|S[0-9]{4}"
                            title="5 digits (e.g., 12345) or S followed by 4 digits (e.g., S0001)"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                            5-digit org unit ID (e.g., 12345) or synthetic S#### (e.g., S0001)
                        </p>
                    </div>

                    <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Sort Order
                        </label>
                        <input
                            type="number"
                            value={sortOrder}
                            onChange={(e) => setSortOrder(parseInt(e.target.value) || 0)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>

                    {editNode && (
                        <div className="mb-4">
                            <label className="flex items-center">
                                <input
                                    type="checkbox"
                                    checked={isActive}
                                    onChange={(e) => setIsActive(e.target.checked)}
                                    className="mr-2"
                                />
                                <span className="text-sm font-medium text-gray-700">Active</span>
                            </label>
                        </div>
                    )}

                    <div className="flex justify-end gap-2 mt-6">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                            disabled={saving}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="px-4 py-2 text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
                            disabled={saving}
                        >
                            {saving ? 'Saving...' : 'Save'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

const LOBTreeView: React.FC<LOBTreeViewProps> = ({
    onSelectLOB,
    selectedLOBId,
    showInactive = false
}) => {
    const { user } = useAuth();
    const canManageLobFlag = canManageLob(user);

    const [tree, setTree] = useState<LOBUnitTreeNode[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [expandedNodes, setExpandedNodes] = useState<Set<number>>(new Set());
    const [selectedId, setSelectedId] = useState<number | null>(selectedLOBId || null);

    // Modal state
    const [modalOpen, setModalOpen] = useState(false);
    const [editNode, setEditNode] = useState<LOBUnitTreeNode | null>(null);
    const [parentNode, setParentNode] = useState<LOBUnitTreeNode | null>(null);

    // Confirmation dialog state
    const [confirmDeactivate, setConfirmDeactivate] = useState<LOBUnitTreeNode | null>(null);

    const fetchTree = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await lobApi.getLOBTree(!showInactive);
            setTree(data);
            // Auto-expand first level
            const firstLevelIds = data.map(n => n.lob_id);
            setExpandedNodes(new Set(firstLevelIds));
        } catch (err) {
            setError('Failed to load LOB hierarchy');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTree();
    }, [showInactive]);

    useEffect(() => {
        setSelectedId(selectedLOBId || null);
    }, [selectedLOBId]);

    const toggleExpand = (id: number) => {
        setExpandedNodes(prev => {
            const next = new Set(prev);
            if (next.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }
            return next;
        });
    };

    const handleSelect = (node: LOBUnitTreeNode) => {
        setSelectedId(node.lob_id);
        onSelectLOB?.(node);
    };

    const handleEdit = (node: LOBUnitTreeNode) => {
        setEditNode(node);
        setParentNode(null);
        setModalOpen(true);
    };

    const handleAddChild = (parent: LOBUnitTreeNode) => {
        setEditNode(null);
        setParentNode(parent);
        setModalOpen(true);
    };

    const handleAddRoot = () => {
        setEditNode(null);
        setParentNode(null);
        setModalOpen(true);
    };

    const handleDeactivate = (node: LOBUnitTreeNode) => {
        setConfirmDeactivate(node);
    };

    const confirmDeactivation = async () => {
        if (!confirmDeactivate) return;

        try {
            await lobApi.deactivateLOBUnit(confirmDeactivate.lob_id);
            await fetchTree();
            setConfirmDeactivate(null);
        } catch (err: unknown) {
            const errorMsg = err instanceof Error ? err.message : 'Failed to deactivate LOB unit';
            alert(errorMsg);
        }
    };

    const handleSave = async (data: LOBUnitCreate | LOBUnitUpdate) => {
        if (editNode) {
            await lobApi.updateLOBUnit(editNode.lob_id, data as LOBUnitUpdate);
        } else {
            await lobApi.createLOBUnit(data as LOBUnitCreate);
        }
        await fetchTree();
    };

    const expandAll = () => {
        const allIds = new Set<number>();
        const collectIds = (nodes: LOBUnitTreeNode[]) => {
            nodes.forEach(n => {
                allIds.add(n.lob_id);
                if (n.children) collectIds(n.children);
            });
        };
        collectIds(tree);
        setExpandedNodes(allIds);
    };

    const collapseAll = () => {
        setExpandedNodes(new Set());
    };

    if (loading) {
        return (
            <div className="p-4 text-center text-gray-500">
                Loading LOB hierarchy...
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-4 text-center text-red-600">
                {error}
                <button
                    onClick={fetchTree}
                    className="ml-2 text-blue-600 underline"
                >
                    Retry
                </button>
            </div>
        );
    }

    return (
        <div className="border border-gray-200 rounded-lg">
            {/* Toolbar */}
            <div className="flex items-center justify-between p-2 border-b border-gray-200 bg-gray-50">
                <div className="flex gap-2">
                    <button
                        onClick={expandAll}
                        className="px-2 py-1 text-xs text-gray-600 hover:text-gray-800 hover:bg-gray-200 rounded"
                    >
                        Expand All
                    </button>
                    <button
                        onClick={collapseAll}
                        className="px-2 py-1 text-xs text-gray-600 hover:text-gray-800 hover:bg-gray-200 rounded"
                    >
                        Collapse All
                    </button>
                </div>
                {canManageLobFlag && (
                    <button
                        onClick={handleAddRoot}
                        className="px-3 py-1 text-sm text-white bg-blue-600 rounded hover:bg-blue-700"
                    >
                        + Add Root
                    </button>
                )}
            </div>

            {/* Tree content */}
            <div className="p-2 max-h-[500px] overflow-y-auto">
                {tree.length === 0 ? (
                    <div className="p-4 text-center text-gray-500">
                        No LOB units found. {canManageLobFlag && 'Click "Add Root" to create one.'}
                    </div>
                ) : (
                    tree.map((node) => (
                        <TreeNode
                            key={node.lob_id}
                            node={node}
                            level={0}
                            expandedNodes={expandedNodes}
                            toggleExpand={toggleExpand}
                            selectedId={selectedId}
                            onSelect={handleSelect}
                            onEdit={handleEdit}
                            onAddChild={handleAddChild}
                            onDeactivate={handleDeactivate}
                            canManageLob={canManageLobFlag}
                        />
                    ))
                )}
            </div>

            {/* Form Modal */}
            <LOBFormModal
                isOpen={modalOpen}
                onClose={() => setModalOpen(false)}
                onSave={handleSave}
                editNode={editNode}
                parentNode={parentNode}
            />

            {/* Deactivation Confirmation */}
            {confirmDeactivate && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-md">
                        <h3 className="text-lg font-semibold mb-4">Confirm Deactivation</h3>
                        <p className="text-gray-600 mb-4">
                            Are you sure you want to deactivate <strong>{confirmDeactivate.name}</strong>?
                        </p>
                        {confirmDeactivate.user_count > 0 && (
                            <p className="text-amber-600 text-sm mb-4">
                                Warning: This LOB has {confirmDeactivate.user_count} assigned user(s).
                                They will need to be reassigned.
                            </p>
                        )}
                        <div className="flex justify-end gap-2">
                            <button
                                onClick={() => setConfirmDeactivate(null)}
                                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={confirmDeactivation}
                                className="px-4 py-2 text-white bg-red-600 rounded-md hover:bg-red-700"
                            >
                                Deactivate
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default LOBTreeView;
