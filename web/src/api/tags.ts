import client from './client';

// ============================================================================
// Types
// ============================================================================

export interface TagCategory {
  category_id: number;
  name: string;
  description: string | null;
  color: string;
  sort_order: number;
  is_system: boolean;
  created_at: string;
  created_by_id: number | null;
  tag_count: number;
}

export interface TagCategoryWithTags extends TagCategory {
  tags: Tag[];
}

export interface Tag {
  tag_id: number;
  category_id: number;
  name: string;
  description: string | null;
  color: string | null;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  created_by_id: number | null;
  effective_color: string;
  model_count: number;
}

export interface TagWithCategory extends Tag {
  category: TagCategory;
}

export interface TagListItem {
  tag_id: number;
  name: string;
  color: string | null;
  effective_color: string;
  category_id: number;
  category_name: string;
  category_color: string;
}

export interface TagHistoryItem {
  history_id: number;
  model_id: number;
  tag_id: number;
  tag_name: string;
  category_name: string;
  action: 'ADDED' | 'REMOVED';
  performed_at: string;
  performed_by_id: number | null;
  performed_by_name: string | null;
}

export interface ModelTagHistoryResponse {
  model_id: number;
  total_count: number;
  history: TagHistoryItem[];
}

export interface BulkTagResponse {
  tag_id: number;
  total_requested: number;
  total_modified: number;
  already_had_tag?: number;
  did_not_have_tag?: number;
}

export interface CategoryUsage {
  category_id: number;
  category_name: string;
  category_color: string;
  tag_count: number;
  model_associations: number;
}

export interface TagUsageStatistics {
  total_tags: number;
  total_active_tags: number;
  total_categories: number;
  total_model_associations: number;
  tags_by_category: CategoryUsage[];
}

// ============================================================================
// Category API
// ============================================================================

export async function listCategories(): Promise<TagCategory[]> {
  const response = await client.get<TagCategory[]>('/tags/categories');
  return response.data;
}

export async function getCategory(categoryId: number): Promise<TagCategoryWithTags> {
  const response = await client.get<TagCategoryWithTags>(`/tags/categories/${categoryId}`);
  return response.data;
}

export async function createCategory(data: {
  name: string;
  description?: string;
  color?: string;
  sort_order?: number;
}): Promise<TagCategory> {
  const response = await client.post<TagCategory>('/tags/categories', data);
  return response.data;
}

export async function updateCategory(
  categoryId: number,
  data: {
    name?: string;
    description?: string;
    color?: string;
    sort_order?: number;
  }
): Promise<TagCategory> {
  const response = await client.patch<TagCategory>(`/tags/categories/${categoryId}`, data);
  return response.data;
}

export async function deleteCategory(categoryId: number): Promise<void> {
  await client.delete(`/tags/categories/${categoryId}`);
}

// ============================================================================
// Tag API
// ============================================================================

export async function listTags(params?: {
  category_id?: number;
  is_active?: boolean;
}): Promise<TagWithCategory[]> {
  const response = await client.get<TagWithCategory[]>('/tags/', { params });
  return response.data;
}

export async function getTag(tagId: number): Promise<TagWithCategory> {
  const response = await client.get<TagWithCategory>(`/tags/${tagId}`);
  return response.data;
}

export async function createTag(data: {
  category_id: number;
  name: string;
  description?: string;
  color?: string;
  sort_order?: number;
  is_active?: boolean;
}): Promise<Tag> {
  const response = await client.post<Tag>('/tags/', data);
  return response.data;
}

export async function updateTag(
  tagId: number,
  data: {
    name?: string;
    description?: string;
    color?: string;
    sort_order?: number;
    is_active?: boolean;
    category_id?: number;
  }
): Promise<Tag> {
  const response = await client.patch<Tag>(`/tags/${tagId}`, data);
  return response.data;
}

export async function deleteTag(tagId: number): Promise<void> {
  await client.delete(`/tags/${tagId}`);
}

// ============================================================================
// Model Tag Assignment API
// ============================================================================

export async function getModelTags(modelId: number): Promise<{
  model_id: number;
  tags: TagListItem[];
}> {
  const response = await client.get(`/tags/models/${modelId}/tags`);
  return response.data;
}

export async function addModelTags(
  modelId: number,
  tagIds: number[]
): Promise<{ model_id: number; tags: TagListItem[] }> {
  const response = await client.post(`/tags/models/${modelId}/tags`, { tag_ids: tagIds });
  return response.data;
}

export async function removeModelTag(modelId: number, tagId: number): Promise<void> {
  await client.delete(`/tags/models/${modelId}/tags/${tagId}`);
}

export async function getModelTagHistory(
  modelId: number,
  limit?: number
): Promise<ModelTagHistoryResponse> {
  const response = await client.get(`/tags/models/${modelId}/tags/history`, {
    params: limit ? { limit } : undefined,
  });
  return response.data;
}

// ============================================================================
// Bulk Operations API
// ============================================================================

export async function bulkAssignTag(
  tagId: number,
  modelIds: number[]
): Promise<BulkTagResponse> {
  const response = await client.post<BulkTagResponse>('/tags/bulk-assign', {
    tag_id: tagId,
    model_ids: modelIds,
  });
  return response.data;
}

export async function bulkRemoveTag(
  tagId: number,
  modelIds: number[]
): Promise<BulkTagResponse> {
  const response = await client.post<BulkTagResponse>('/tags/bulk-remove', {
    tag_id: tagId,
    model_ids: modelIds,
  });
  return response.data;
}

// ============================================================================
// Statistics API
// ============================================================================

export async function getTagUsageStatistics(): Promise<TagUsageStatistics> {
  const response = await client.get<TagUsageStatistics>('/tags/usage-statistics');
  return response.data;
}
