import { apiClient } from './client'
import type { PageQuery } from '../types/api'
import type {
  AssetReviewStatus,
  AssetSyncResult,
  AssetType,
  GeneratedAsset,
  GeneratedAssetListResponse,
  GeneratedAssetUpdate,
} from '../types/asset'

export function syncGeneratedAssets(productId: number): Promise<AssetSyncResult> {
  return apiClient(`/products/${productId}/assets/sync`, { method: 'POST' })
}

export function listGeneratedAssets(
  productId: number,
  query: PageQuery & { asset_type?: AssetType; review_status?: AssetReviewStatus; creative_plan_id?: number } = {},
): Promise<GeneratedAssetListResponse> {
  return apiClient(`/products/${productId}/assets`, {}, query)
}

export function getGeneratedAsset(productId: number, assetId: number): Promise<GeneratedAsset> {
  return apiClient(`/products/${productId}/assets/${assetId}`)
}

export function updateGeneratedAsset(
  productId: number,
  assetId: number,
  data: GeneratedAssetUpdate,
): Promise<GeneratedAsset> {
  return apiClient(`/products/${productId}/assets/${assetId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}
