import type { PaginatedResponse } from './api'

export type CreativePlanType = 'main_image' | 'video_script'
export type CreativePlanStatus = 'draft' | 'selected' | 'archived'

export interface StoryboardScene {
  scene_no: number
  visual: string
  duration_hint: string
  voiceover: string
}

export interface MainImageContent {
  visual_structure: string[]
  core_copy: string[]
  highlighted_selling_points: string[]
}

export interface VideoScriptContent {
  opening_hook: string
  storyboard: StoryboardScene[]
  voiceover: string[]
  conversion_cta: string
}

export type CreativePlanContent = MainImageContent | VideoScriptContent

export interface CreativePlan {
  id: number
  product_id: number
  plan_type: CreativePlanType
  title: string
  content_json: CreativePlanContent
  rationale_text: string
  status: CreativePlanStatus
  provider_name: string | null
  model_name: string | null
  usage_json: Record<string, number> | null
  input_context_json: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface CreativePlanUpdate {
  title?: string
  content_json?: CreativePlanContent
  rationale_text?: string
  status?: CreativePlanStatus
}

export type CreativePlanListResponse = PaginatedResponse<CreativePlan>
