/**
 * useColumnPreferences Hook
 *
 * Reusable hook for managing column visibility, saved views, and CSV export column selection.
 * Integrates with ExportViews API for persistence across devices.
 *
 * Usage:
 * ```tsx
 * const availableColumns = [
 *     { key: 'name', label: 'Name', default: true },
 *     { key: 'status', label: 'Status', default: true },
 *     { key: 'created_at', label: 'Created Date', default: false },
 * ];
 *
 * const defaultViews = {
 *     default: { id: 'default', name: 'Default View', columns: ['name', 'status'], isDefault: true },
 *     full: { id: 'full', name: 'All Columns', columns: ['name', 'status', 'created_at'], isDefault: true },
 * };
 *
 * const {
 *     selectedColumns,
 *     currentViewId,
 *     allViews,
 *     toggleColumn,
 *     selectAllColumns,
 *     deselectAllColumns,
 *     loadView,
 *     saveView,
 *     deleteView,
 *     startEditView,
 *     loadExportViews,
 *     // Modal state
 *     showColumnsModal, setShowColumnsModal,
 *     showSaveViewModal, setShowSaveViewModal,
 *     newViewName, setNewViewName,
 *     newViewDescription, setNewViewDescription,
 *     newViewIsPublic, setNewViewIsPublic,
 *     editingViewId,
 * } = useColumnPreferences({
 *     entityType: 'models',
 *     availableColumns,
 *     defaultViews,
 * });
 * ```
 */

import { useState, useMemo, useCallback, useEffect } from 'react';
import { exportViewsApi, ExportView } from '../api/exportViews';

export interface ColumnDefinition {
    key: string;
    label: string;
    default: boolean;
}

export interface PresetView {
    id: string;
    name: string;
    columns: string[];
    isDefault: boolean;
}

export interface CombinedView extends PresetView {
    isPublic?: boolean;
    dbView?: ExportView;
}

interface UseColumnPreferencesOptions {
    /** Entity type for ExportViews API (e.g., 'models', 'validation_requests', 'recommendations') */
    entityType: string;
    /** Available columns with key, label, and default visibility */
    availableColumns: ColumnDefinition[];
    /** Preset views provided by the page */
    defaultViews: Record<string, PresetView>;
    /** Auto-load views from API on mount (default: true) */
    autoLoad?: boolean;
}

interface UseColumnPreferencesReturn {
    // Column state
    selectedColumns: string[];
    setSelectedColumns: React.Dispatch<React.SetStateAction<string[]>>;
    currentViewId: string;
    setCurrentViewId: React.Dispatch<React.SetStateAction<string>>;

    // Views
    allViews: Record<string, CombinedView>;
    dbViews: ExportView[];

    // Column actions
    toggleColumn: (columnKey: string) => void;
    selectAllColumns: () => void;
    deselectAllColumns: () => void;
    loadView: (viewId: string) => void;

    // View persistence
    saveView: () => Promise<void>;
    deleteView: (viewId: string) => Promise<void>;
    startEditView: (viewId: string) => void;
    loadExportViews: () => Promise<void>;

    // Modal state
    showColumnsModal: boolean;
    setShowColumnsModal: React.Dispatch<React.SetStateAction<boolean>>;
    showSaveViewModal: boolean;
    setShowSaveViewModal: React.Dispatch<React.SetStateAction<boolean>>;
    newViewName: string;
    setNewViewName: React.Dispatch<React.SetStateAction<string>>;
    newViewDescription: string;
    setNewViewDescription: React.Dispatch<React.SetStateAction<string>>;
    newViewIsPublic: boolean;
    setNewViewIsPublic: React.Dispatch<React.SetStateAction<boolean>>;
    editingViewId: number | null;
    setEditingViewId: React.Dispatch<React.SetStateAction<number | null>>;

    // Helpers
    availableColumns: ColumnDefinition[];
    getDefaultColumns: () => string[];
}

export function useColumnPreferences({
    entityType,
    availableColumns,
    defaultViews,
    autoLoad = true,
}: UseColumnPreferencesOptions): UseColumnPreferencesReturn {
    // Database views from API
    const [dbViews, setDbViews] = useState<ExportView[]>([]);

    // Current view and column selection
    const [currentViewId, setCurrentViewId] = useState<string>('default');
    const [selectedColumns, setSelectedColumns] = useState<string[]>(() =>
        availableColumns.filter(col => col.default).map(col => col.key)
    );

    // Modal state
    const [showColumnsModal, setShowColumnsModal] = useState(false);
    const [showSaveViewModal, setShowSaveViewModal] = useState(false);
    const [newViewName, setNewViewName] = useState('');
    const [newViewDescription, setNewViewDescription] = useState('');
    const [newViewIsPublic, setNewViewIsPublic] = useState(false);
    const [editingViewId, setEditingViewId] = useState<number | null>(null);

    // Helper to get default columns
    const getDefaultColumns = useCallback(() => {
        return availableColumns.filter(col => col.default).map(col => col.key);
    }, [availableColumns]);

    // Combined views: default views + database views
    const allViews = useMemo<Record<string, CombinedView>>(() => {
        const combined: Record<string, CombinedView> = {};

        // Add default views
        Object.entries(defaultViews).forEach(([key, view]) => {
            combined[key] = { ...view };
        });

        // Add database views
        dbViews.forEach(view => {
            combined[`db_${view.view_id}`] = {
                id: `db_${view.view_id}`,
                name: view.view_name,
                columns: view.columns,
                isDefault: false,
                isPublic: view.is_public,
                dbView: view
            };
        });

        return combined;
    }, [defaultViews, dbViews]);

    // Load views from API
    const loadExportViews = useCallback(async () => {
        try {
            const views = await exportViewsApi.list(entityType);
            setDbViews(views);
        } catch (error) {
            console.error('Failed to load export views:', error);
        }
    }, [entityType]);

    // Auto-load views on mount
    useEffect(() => {
        if (autoLoad) {
            loadExportViews();
        }
    }, [autoLoad, loadExportViews]);

    // Toggle a single column
    const toggleColumn = useCallback((columnKey: string) => {
        setSelectedColumns(prev => {
            if (prev.includes(columnKey)) {
                return prev.filter(k => k !== columnKey);
            } else {
                return [...prev, columnKey];
            }
        });
    }, []);

    // Select all columns
    const selectAllColumns = useCallback(() => {
        setSelectedColumns(availableColumns.map(col => col.key));
    }, [availableColumns]);

    // Deselect all columns
    const deselectAllColumns = useCallback(() => {
        setSelectedColumns([]);
    }, []);

    // Load a view by ID
    const loadView = useCallback((viewId: string) => {
        const view = allViews[viewId];
        if (view) {
            setSelectedColumns(view.columns);
            setCurrentViewId(viewId);
        }
    }, [allViews]);

    // Save current view (create or update)
    const saveView = useCallback(async () => {
        if (!newViewName.trim()) {
            alert('Please enter a name for this view.');
            return;
        }

        try {
            if (editingViewId) {
                // Update existing view
                await exportViewsApi.update(editingViewId, {
                    view_name: newViewName,
                    columns: selectedColumns,
                    is_public: newViewIsPublic,
                    description: newViewDescription || undefined
                });
            } else {
                // Create new view
                const newView = await exportViewsApi.create({
                    entity_type: entityType,
                    view_name: newViewName,
                    columns: selectedColumns,
                    is_public: newViewIsPublic,
                    description: newViewDescription || undefined
                });
                setCurrentViewId(`db_${newView.view_id}`);
            }

            // Reload views from API
            await loadExportViews();

            // Reset form
            setNewViewName('');
            setNewViewDescription('');
            setNewViewIsPublic(false);
            setShowSaveViewModal(false);
            setEditingViewId(null);
        } catch (error: any) {
            console.error('Failed to save view:', error);
            alert(`Failed to save view: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
        }
    }, [editingViewId, newViewName, newViewDescription, newViewIsPublic, selectedColumns, entityType, loadExportViews]);

    // Delete a view
    const deleteView = useCallback(async (viewId: string) => {
        const view = allViews[viewId];
        if (!view) return;

        if (view.isDefault) {
            alert('Cannot delete default views.');
            return;
        }

        if (!confirm(`Delete view "${view.name}"?`)) {
            return;
        }

        try {
            // Extract numeric ID from db_X format
            const numericId = parseInt(viewId.replace('db_', ''));
            await exportViewsApi.delete(numericId);

            // Reload views
            await loadExportViews();

            // If deleted view was current, switch to default
            if (currentViewId === viewId) {
                setCurrentViewId('default');
                const defaultView = defaultViews['default'];
                if (defaultView) {
                    setSelectedColumns(defaultView.columns);
                }
            }
        } catch (error: any) {
            console.error('Failed to delete view:', error);
            alert(`Failed to delete view: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
        }
    }, [allViews, currentViewId, defaultViews, loadExportViews]);

    // Start editing a view
    const startEditView = useCallback((viewId: string) => {
        const view = allViews[viewId];
        if (!view) return;

        if (view.isDefault) {
            alert('Cannot edit default views. You can save a copy with a new name.');
            return;
        }

        // Extract numeric ID from db_X format
        const numericId = parseInt(viewId.replace('db_', ''));
        setEditingViewId(numericId);
        setNewViewName(view.name);
        if (view.dbView) {
            setNewViewDescription(view.dbView.description || '');
            setNewViewIsPublic(view.dbView.is_public);
        }
        setShowSaveViewModal(true);
    }, [allViews]);

    return {
        // Column state
        selectedColumns,
        setSelectedColumns,
        currentViewId,
        setCurrentViewId,

        // Views
        allViews,
        dbViews,

        // Column actions
        toggleColumn,
        selectAllColumns,
        deselectAllColumns,
        loadView,

        // View persistence
        saveView,
        deleteView,
        startEditView,
        loadExportViews,

        // Modal state
        showColumnsModal,
        setShowColumnsModal,
        showSaveViewModal,
        setShowSaveViewModal,
        newViewName,
        setNewViewName,
        newViewDescription,
        setNewViewDescription,
        newViewIsPublic,
        setNewViewIsPublic,
        editingViewId,
        setEditingViewId,

        // Helpers
        availableColumns,
        getDefaultColumns,
    };
}
