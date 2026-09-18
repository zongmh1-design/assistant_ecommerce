import type { PaginatedResponse } from './api'

export type ReviewSeverity = 'low' | 'medium' | 'high'
export type ReviewPriority = 'high' | 'medium' | 'low'

export interface ReviewInsight {
  title: string
  finding: string
  evidence: string
}

export interface ProblemJudgement {
  problem: string
  evidence: string
  severity: ReviewSeverity
}

export interface ReviewNextAction {
  action: string
  rationale: string
  priority: ReviewPriority
}

export interface ReviewReport {
  id: number
  product_id: number
  period_start: string
  period_end: string
  summary_text: string
  insights_json: ReviewInsight[]
  problem_judgements_json: ProblemJudgement[]
  next_actions_json: ReviewNextAction[]
  provider_name: string | null
  model_name: string | null
  usage_json: Record<string, number> | null
  input_context_json: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface ReviewReportGenerateInput {
  period_start: string
  period_end: string
}

export interface ReviewReportUpdate {
  summary_text?: string
  insights_json?: ReviewInsight[]
  problem_judgements_json?: ProblemJudgement[]
  next_actions_json?: ReviewNextAction[]
}

export interface ReviewReportQuery {
  page?: number
  page_size?: number
  period_start_from?: string
  period_end_to?: string
}

export type ReviewReportListResponse = PaginatedResponse<ReviewReport>

