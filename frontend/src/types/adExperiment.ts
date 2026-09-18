import type { PaginatedResponse } from './api'

export type AdExperimentStatus = 'draft' | 'confirmed' | 'running' | 'finished' | 'cancelled'

export interface AdExperiment {
  id: number
  product_id: number
  ad_recommendation_id: number
  related_asset_id: number | null
  related_link_id: number | null
  experiment_name: string
  target_text: string
  audience_text: string
  budget_amount: string
  success_metric_text: string
  hypothesis_text: string
  experiment_status: AdExperimentStatus
  provider_name: string | null
  model_name: string | null
  usage_json: Record<string, number> | null
  input_context_json: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface AdExperimentGenerateInput {
  recommendation_id: number
  related_asset_id?: number | null
  related_link_id?: number | null
}

export interface AdExperimentUpdate {
  experiment_name?: string
  target_text?: string
  audience_text?: string
  budget_amount?: string
  success_metric_text?: string
  hypothesis_text?: string
  related_asset_id?: number | null
  related_link_id?: number | null
}

export interface AdExperimentStatusUpdate {
  experiment_status: AdExperimentStatus
}

export type AdExperimentListResponse = PaginatedResponse<AdExperiment>
