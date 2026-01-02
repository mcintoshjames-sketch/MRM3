import React, { useEffect, useMemo, useState } from 'react';
import { lobApi, LOBUnitTeamTreeNode } from '../api/lob';
import { assignLOBToTeam, removeLOBFromTeam } from '../api/teams';

interface TeamLOBAssignmentProps {
    teamId: number;
    teamName: string;
    canManage: boolean;
    onAssignmentsUpdated?: () => void;
}

const TeamLOBAssignment: React.FC<TeamLOBAssignmentProps> = ({
    teamId,
    teamName,
    canManage,
    onAssignmentsUpdated
}) => {
    const [tree, setTree] = useState<LOBUnitTeamTreeNode[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [expandedNodes, setExpandedNodes] = useState<Set<number>>(new Set());
    const [lastWarnings, setLastWarnings] = useState<string[]>([]);
    const [savingId, setSavingId] = useState<number | null>(null);

    const fetchTree = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await lobApi.getLOBTreeWithTeams(false);
            setTree(response.lob_units || []);
        } catch (err) {
            console.error('Failed to load LOB tree:', err);
            setError('Failed to load LOB tree');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTree();
    }, [teamId]);

    const { nodeMap, parentMap } = useMemo(() => {
        const nodeLookup = new Map<number, LOBUnitTeamTreeNode>();
        const parentLookup = new Map<number, number | null>();

        const walk = (nodes: LOBUnitTeamTreeNode[], parentId: number | null) => {
            nodes.forEach((node) => {
                nodeLookup.set(node.lob_id, node);
                parentLookup.set(node.lob_id, parentId);
                if (node.children?.length) {
                    walk(node.children, node.lob_id);
                }
            });
        };

        walk(tree, null);
        return { nodeMap: nodeLookup, parentMap: parentLookup };
    }, [tree]);

    const matchesQuery = (node: LOBUnitTeamTreeNode) => {
        const query = searchQuery.trim().toLowerCase();
        if (!query) return true;
        return (
            node.name.toLowerCase().includes(query) ||
            node.org_unit.toLowerCase().includes(query)
        );
    };

    const filterTree = (nodes: LOBUnitTeamTreeNode[]): LOBUnitTeamTreeNode[] => {
        const query = searchQuery.trim().toLowerCase();
        if (!query) return nodes;

        const filterNode = (node: LOBUnitTeamTreeNode): LOBUnitTeamTreeNode | null => {
            const filteredChildren = node.children
                ? node.children.map(filterNode).filter(Boolean) as LOBUnitTeamTreeNode[]
                : [];
            const isMatch = matchesQuery(node);
            if (isMatch || filteredChildren.length > 0) {
                return { ...node, children: filteredChildren };
            }
            return null;
        };

        return nodes.map(filterNode).filter(Boolean) as LOBUnitTeamTreeNode[];
    };

    const filteredTree = useMemo(() => filterTree(tree), [tree, searchQuery]);

    const toggleExpand = (lobId: number) => {
        setExpandedNodes((prev) => {
            const next = new Set(prev);
            if (next.has(lobId)) {
                next.delete(lobId);
            } else {
                next.add(lobId);
            }
            return next;
        });
    };

    const findAncestorWithTeam = (lobId: number): LOBUnitTeamTreeNode | null => {
        let currentId = parentMap.get(lobId);
        while (currentId) {
            const node = nodeMap.get(currentId);
            if (node && node.direct_team_id) {
                return node;
            }
            currentId = parentMap.get(currentId);
        }
        return null;
    };

    const countDescendantsWithDirectTeam = (node: LOBUnitTeamTreeNode): number => {
        if (!node.children) return 0;
        let count = 0;
        node.children.forEach((child) => {
            if (child.direct_team_id && child.direct_team_id !== teamId) {
                count += 1;
            }
            count += countDescendantsWithDirectTeam(child);
        });
        return count;
    };

    const buildWarnings = (node: LOBUnitTeamTreeNode, assigning: boolean) => {
        if (!assigning) return [];

        const warnings: string[] = [];
        if (node.direct_team_id && node.direct_team_id !== teamId) {
            warnings.push(`This will reassign LOB from ${node.direct_team_name || `Team ${node.direct_team_id}`} to ${teamName}.`);
        }

        const ancestor = findAncestorWithTeam(node.lob_id);
        if (ancestor && ancestor.direct_team_id !== teamId) {
            warnings.push(`This LOB currently inherits from ${ancestor.direct_team_name || `Team ${ancestor.direct_team_id}`}. Direct assignment will override.`);
        }

        const descendantCount = countDescendantsWithDirectTeam(node);
        if (descendantCount > 0) {
            warnings.push(`${descendantCount} descendant LOBs have their own team assignments (these will NOT be affected).`);
        }

        return warnings;
    };

    const handleToggleAssignment = async (node: LOBUnitTeamTreeNode) => {
        if (!canManage || savingId) return;

        const assigning = node.direct_team_id !== teamId;
        setSavingId(node.lob_id);
        setLastWarnings(buildWarnings(node, assigning));

        try {
            if (assigning) {
                await assignLOBToTeam(teamId, node.lob_id);
            } else {
                await removeLOBFromTeam(teamId, node.lob_id);
            }
            await fetchTree();
            onAssignmentsUpdated?.();
        } catch (err) {
            console.error('Failed to update team assignment:', err);
            setError('Failed to update team assignment');
        } finally {
            setSavingId(null);
        }
    };

    const renderNode = (node: LOBUnitTeamTreeNode, depth: number = 0) => {
        const hasChildren = node.children && node.children.length > 0;
        const isExpanded = searchQuery.trim() ? true : expandedNodes.has(node.lob_id);
        const isDirect = node.direct_team_id === teamId;
        const isEffective = node.effective_team_id === teamId;
        const isOtherTeam = node.effective_team_id && node.effective_team_id !== teamId;

        const statusClass = isEffective
            ? 'bg-green-50 border-green-200'
            : isOtherTeam
                ? 'bg-amber-50 border-amber-200'
                : 'bg-gray-50 border-gray-200';

        const matchClass = searchQuery.trim() && matchesQuery(node) ? 'text-blue-700' : 'text-gray-900';

        return (
            <div key={node.lob_id}>
                <div
                    className={`flex items-center gap-2 border rounded-md px-2 py-1 mb-1 ${statusClass}`}
                    style={{ marginLeft: depth * 16 }}
                >
                    {hasChildren ? (
                        <button
                            type="button"
                            onClick={() => toggleExpand(node.lob_id)}
                            className="text-gray-500 hover:text-gray-700"
                        >
                            {isExpanded ? '▾' : '▸'}
                        </button>
                    ) : (
                        <span className="w-4" />
                    )}
                    {canManage && (
                        <input
                            type="checkbox"
                            checked={isDirect}
                            onChange={() => handleToggleAssignment(node)}
                            disabled={savingId === node.lob_id}
                            className="h-4 w-4 text-green-600 border-gray-300 rounded"
                        />
                    )}
                    <div className="flex flex-col">
                        <div className="flex items-center gap-2">
                            <span className={`text-sm font-medium ${matchClass}`}>
                                {node.name}
                            </span>
                            <span className="text-xs text-gray-500">[{node.org_unit}]</span>
                            {!node.is_active && (
                                <span className="text-xs text-red-600">Inactive</span>
                            )}
                            {node.direct_team_id && !node.direct_team_name && (
                                <span className="text-xs text-red-600">Unknown team</span>
                            )}
                        </div>
                        <div className="text-xs text-gray-500">
                            {isDirect && 'Direct assignment'}
                            {!isDirect && isEffective && `Inherited (${node.effective_team_name || 'Team'})`}
                            {isOtherTeam && `Assigned to ${node.effective_team_name || `Team ${node.effective_team_id}`}`}
                            {!node.effective_team_id && 'Unassigned'}
                        </div>
                    </div>
                </div>
                {hasChildren && isExpanded && (
                    <div>
                        {node.children.map((child) => renderNode(child, depth + 1))}
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-700">LOB Assignments</h3>
                <button
                    onClick={fetchTree}
                    className="text-xs text-blue-600 hover:text-blue-800"
                >
                    Refresh
                </button>
            </div>

            <input
                type="text"
                placeholder="Search by name or org unit..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            />

            {lastWarnings.length > 0 && (
                <div className="border border-amber-200 bg-amber-50 text-amber-800 text-xs rounded-md p-3">
                    <div className="font-semibold mb-1">Assignment warnings</div>
                    <ul className="list-disc pl-4 space-y-1">
                        {lastWarnings.map((warning, idx) => (
                            <li key={idx}>{warning}</li>
                        ))}
                    </ul>
                </div>
            )}

            {error && (
                <div className="border border-red-200 bg-red-50 text-red-700 text-xs rounded-md p-3">
                    {error}
                </div>
            )}

            {loading ? (
                <div className="text-sm text-gray-500">Loading LOB hierarchy...</div>
            ) : (
                <div className="max-h-[420px] overflow-auto pr-2">
                    {filteredTree.length === 0 ? (
                        <div className="text-sm text-gray-500">No matching LOB units.</div>
                    ) : (
                        filteredTree.map((node) => renderNode(node))
                    )}
                </div>
            )}

            <div className="flex flex-wrap gap-4 text-xs text-gray-500">
                <div className="flex items-center gap-2">
                    <span className="w-3 h-3 bg-green-100 border border-green-300 rounded" />
                    Selected Team
                </div>
                <div className="flex items-center gap-2">
                    <span className="w-3 h-3 bg-amber-100 border border-amber-300 rounded" />
                    Other Team(s)
                </div>
                <div className="flex items-center gap-2">
                    <span className="w-3 h-3 bg-gray-100 border border-gray-300 rounded" />
                    Unassigned
                </div>
            </div>
        </div>
    );
};

export default TeamLOBAssignment;
