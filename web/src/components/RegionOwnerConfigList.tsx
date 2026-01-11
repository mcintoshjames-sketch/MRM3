import { useMemo, useState } from 'react';
import UserSearchSelect, { UserSearchOption } from './UserSearchSelect';

export type RegionOwnerConfig = {
    region_id: number;
    shared_model_owner_id: number | null;
};

type RegionOption = {
    region_id: number;
    code: string;
    name: string;
};

interface RegionOwnerConfigListProps {
    regions: RegionOption[];
    selectedRegionIds: number[];
    configs: RegionOwnerConfig[];
    onChange: (configs: RegionOwnerConfig[]) => void;
    users: UserSearchOption[];
    setUsers: React.Dispatch<React.SetStateAction<UserSearchOption[]>>;
    onRemoveRegion?: (regionId: number) => void;
    whollyOwnedRegionId?: number | null;
    allowRemove?: boolean;
    showBulkApply?: boolean;
}

const normalizeConfigs = (
    selectedRegionIds: number[],
    configs: RegionOwnerConfig[]
) => {
    const map = new Map(configs.map((config) => [config.region_id, config.shared_model_owner_id]));
    return selectedRegionIds.map((regionId) => ({
        region_id: regionId,
        shared_model_owner_id: map.get(regionId) ?? null
    }));
};

export default function RegionOwnerConfigList({
    regions,
    selectedRegionIds,
    configs,
    onChange,
    users,
    setUsers,
    onRemoveRegion,
    whollyOwnedRegionId,
    allowRemove = true,
    showBulkApply = true
}: RegionOwnerConfigListProps) {
    const [bulkOwnerId, setBulkOwnerId] = useState<number | null>(null);

    const regionMap = useMemo(() => {
        return new Map(regions.map((region) => [region.region_id, region]));
    }, [regions]);

    const orderedRegions = useMemo(() => {
        const uniqueRegionIds = Array.from(new Set(selectedRegionIds));
        return uniqueRegionIds
            .map((regionId) => regionMap.get(regionId))
            .filter((region): region is RegionOption => Boolean(region))
            .sort((a, b) => a.name.localeCompare(b.name));
    }, [selectedRegionIds, regionMap]);

    const normalizedConfigs = useMemo(
        () => normalizeConfigs(selectedRegionIds, configs),
        [selectedRegionIds, configs]
    );

    const handleOwnerChange = (regionId: number, ownerId: number | null) => {
        const nextConfigs = normalizeConfigs(selectedRegionIds, normalizedConfigs).map((config) =>
            config.region_id === regionId
                ? { ...config, shared_model_owner_id: ownerId }
                : config
        );
        onChange(nextConfigs);
    };

    const handleApplyAll = () => {
        if (selectedRegionIds.length === 0) return;
        const nextConfigs = normalizeConfigs(selectedRegionIds, normalizedConfigs).map((config) => ({
            ...config,
            shared_model_owner_id: bulkOwnerId
        }));
        onChange(nextConfigs);
    };

    if (selectedRegionIds.length === 0) {
        return (
            <div className="text-xs text-gray-500">
                No deployment regions selected yet.
            </div>
        );
    }

    return (
        <div className="mt-3 space-y-4">
            {showBulkApply && selectedRegionIds.length > 1 && (
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                    <div className="text-sm font-medium text-gray-700 mb-2">Apply owner to all regions</div>
                    <div className="flex flex-col md:flex-row md:items-end gap-2">
                        <div className="flex-1">
                            <UserSearchSelect
                                value={bulkOwnerId}
                                onChange={(userId) => setBulkOwnerId(userId)}
                                users={users}
                                setUsers={setUsers}
                                placeholder="Search users or enter an email..."
                            />
                        </div>
                        <button
                            type="button"
                            onClick={handleApplyAll}
                            className="btn-secondary px-3 py-2 text-sm"
                            disabled={selectedRegionIds.length === 0}
                        >
                            Apply to All
                        </button>
                    </div>
                </div>
            )}

            <div className="space-y-3">
                {orderedRegions.map((region) => {
                    const config = normalizedConfigs.find((item) => item.region_id === region.region_id);
                    const ownerId = config?.shared_model_owner_id ?? null;
                    const isWhollyOwned = whollyOwnedRegionId === region.region_id;

                    return (
                        <div key={region.region_id} className="rounded-lg border border-gray-200 p-3">
                            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                                <div>
                                    <div className="text-sm font-medium text-gray-900">
                                        {region.name} ({region.code})
                                    </div>
                                    {isWhollyOwned && (
                                        <div className="mt-1 text-xs text-indigo-700">
                                            Governance region (wholly-owned)
                                        </div>
                                    )}
                                </div>
                                <div className="w-full md:max-w-md">
                                    <UserSearchSelect
                                        value={ownerId}
                                        onChange={(userId) => handleOwnerChange(region.region_id, userId)}
                                        users={users}
                                        setUsers={setUsers}
                                        placeholder="Optional regional owner"
                                    />
                                </div>
                                {allowRemove && onRemoveRegion && !isWhollyOwned && (
                                    <button
                                        type="button"
                                        onClick={() => onRemoveRegion(region.region_id)}
                                        className="text-xs text-red-600 hover:text-red-800"
                                    >
                                        Remove
                                    </button>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
