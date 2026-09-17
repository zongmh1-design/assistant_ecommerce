import type { PaginatedResponse } from './api'

export interface PerformanceRecord {
  id: number
  product_id: number
  creative_plan_id: number | null
  generated_asset_id: number | null
  promotion_link_id: number | null
  experiment_id: number | null
  period_start: string
  period_end: string
  impressions: number
  clicks: number
  ctr: string
  conversions: number
  conversion_rate: string
  spend: string
  revenue: string
  roi: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface PerformanceRecordCreate {
  creative_plan_id?: number | null
  generated_asset_id?: number | null
  promotion_link_id?: number | null
  experiment_id?: number | null
  period_start: string
  period_end: string
  impressions: number
  clicks: number
  conversions: number
  spend: string
  revenue: string
  notes?: string | null
}

export interface PerformanceRecordUpdate {
  creative_plan_id?: number | null
  generated_asset_id?: number | null
  promotion_link_id?: number | null
  experiment_id?: number | null
  period_start?: string
  period_end?: string
  impressions?: number
  clicks?: number
  conversions?: number
  spend?: string
  revenue?: string
  notes?: string | null
}

export interface PerformanceRecordQuery {
  page?: number
  page_size?: number
  experiment_id?: number
  generated_asset_id?: number
  promotion_link_id?: number
  period_start_from?: string
  period_end_to?: string
}

export type PerformanceRecordListResponse = PaginatedResponse<PerformanceRecord>

