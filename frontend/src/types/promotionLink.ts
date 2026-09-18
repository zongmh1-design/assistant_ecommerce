import type { PaginatedResponse } from './api'

export type PromotionLinkStatus = 'active' | 'inactive'

export interface PromotionLinkUtm {
  utm_source?: string | null
  utm_medium?: string | null
  utm_campaign?: string | null
  utm_content?: string | null
  utm_term?: string | null
}

export interface PromotionLinkSuggestion {
  link_name: string
  scene_text: string
  utm_source: string
  utm_medium: string
  utm_campaign: string
  utm_content: string
  rationale: string
}

export interface PromotionLink {
  id: number
  product_id: number
  link_name: string
  target_url: string
  tracking_code: string
  utm_json: PromotionLinkUtm
  status: PromotionLinkStatus
  click_count: number
  scene_text: string | null
  created_at: string
  updated_at: string
}

export interface PromotionLinkCreate {
  link_name: string
  target_url: string
  utm_json: PromotionLinkUtm
  scene_text?: string | null
}

export interface PromotionLinkUpdate {
  link_name?: string
  target_url?: string
  utm_json?: PromotionLinkUtm
  scene_text?: string | null
  status?: PromotionLinkStatus
}

export interface PromotionLinkClick {
  id: number
  promotion_link_id: number
  clicked_at: string
  client_ip: string | null
  user_agent: string | null
}

export type PromotionLinkListResponse = PaginatedResponse<PromotionLink>
export type PromotionLinkClickListResponse = PaginatedResponse<PromotionLinkClick>
