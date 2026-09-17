import type { PaginatedResponse } from './api'

export type AdRecommendationConfirmStatus = 'pending' | 'confirmed' | 'rejected'

export interface AudienceSegment {
  segment_name: string
  description: string
  rationale: string
}

export interface BudgetAllocation {
  channel_or_test: string
  amount: string
  rationale: string
}

export interface BudgetPlan {
  total_budget: string
  currency: string
  allocation: BudgetAllocation[]
  rationale: string
}

export interface CreativeTest {
  test_name: string
  asset_reference: string
  hypothesis: string
  success_metric: string
}

export interface BidStrategy {
  strategy_name: string
  rationale: string
  constraints: string[]
}

export interface RiskControl {
  risk: string
  mitigation: string
}

export interface AdRecommendation {
  id: number
  product_id: number
  summary_text: string
  objective_text: string
  audience_segments_json: AudienceSegment[]
  budget_plan_json: BudgetPlan
  creative_tests_json: CreativeTest[]
  bid_strategy_json: BidStrategy
  risk_controls_json: RiskControl[]
  next_steps_json: string[]
  confirm_status: AdRecommendationConfirmStatus
  confirmed_by: number | null
  confirmed_at: string | null
  confirm_remark: string | null
  provider_name: string | null
  model_name: string | null
  usage_json: Record<string, number> | null
  input_context_json: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface AdRecommendationUpdate {
  summary_text?: string
  objective_text?: string
  audience_segments_json?: AudienceSegment[]
  budget_plan_json?: BudgetPlan
  creative_tests_json?: CreativeTest[]
  bid_strategy_json?: BidStrategy
  risk_controls_json?: RiskControl[]
  next_steps_json?: string[]
}

export interface AdRecommendationConfirmation {
  confirm_status: Exclude<AdRecommendationConfirmStatus, 'pending'>
  confirm_remark?: string | null
}

export type AdRecommendationListResponse = PaginatedResponse<AdRecommendation>
