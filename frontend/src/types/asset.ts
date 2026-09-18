import type { PaginatedResponse } from './api'

export type AssetType = 'image' | 'video'
export type AssetReviewStatus = 'pending' | 'approved' | 'rejected'

export interface GeneratedAsset {
  id: number
  product_id: number
  creative_plan_id: number
  generation_job_id: number
  asset_type: AssetType
  asset_url: string
  model_name: string
  width: number | null
  height: number | null
  duration_sec: number | null
  review_status: AssetReviewStatus
  version_no: number
  usage_scene: string | null
  score: number | null
  tags_json: string[]
  remark: string | null
  created_at: string
  updated_at: string
}

export interface GeneratedAssetUpdate {
  review_status?: AssetReviewStatus
  usage_scene?: string | null
  score?: number | null
  tags_json?: string[]
  remark?: string | null
}

export interface AssetSyncFailure {
  job_id: number
  code: string
  message: string
}

export interface AssetSyncResult {
  synced_count: number
  skipped_count: number
  failed_count: number
  asset_ids: number[]
  failures: AssetSyncFailure[]
}

export type GeneratedAssetListResponse = PaginatedResponse<GeneratedAsset>
