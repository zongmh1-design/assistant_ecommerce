import type { PaginatedResponse } from './api'

export interface ProductDiagnosis {
  id: number
  product_id: number
  source_type: string
  positioning: string
  price_band: string
  audience_insights: string[]
  pain_points: string[]
  selling_point_analysis: string[]
  risks: string[]
  recommendations: string[]
  provider_name: string | null
  model_name: string | null
  usage_json: Record<string, number> | null
  input_context_json: Record<string, unknown>
  raw_output: string
  created_at: string
  updated_at: string
}

export type ProductDiagnosisListResponse = PaginatedResponse<ProductDiagnosis>

export interface ProductDiagnosisUpdate {
  positioning?: string
  price_band?: string
  audience_insights?: string[]
  pain_points?: string[]
  selling_point_analysis?: string[]
  risks?: string[]
  recommendations?: string[]
}
