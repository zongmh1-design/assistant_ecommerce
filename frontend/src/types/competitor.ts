import type { Platform } from './store'

export interface Competitor {
  id: number
  product_id: number
  name: string
  platform: Platform
  url: string
  price: string | null
  sales_hint: string | null
  title: string | null
  main_image: string | null
  selling_points: string[]
  review_keywords: string[]
  created_at: string
  updated_at: string
}

export interface CompetitorCreate {
  name: string
  platform: Platform
  url: string
  price?: string | null
  sales_hint?: string | null
  title?: string | null
  main_image?: string | null
  selling_points?: string[]
  review_keywords?: string[]
}

export type CompetitorUpdate = Partial<CompetitorCreate>

export type PublicLinkParseTaskStatus = 'pending' | 'running' | 'succeeded' | 'failed'

export interface PublicLinkCandidate {
  name?: string
  platform?: Platform
  price?: string | null
  sales_hint?: string | null
  title?: string | null
  main_image?: string | null
  selling_points?: string[]
  review_keywords?: string[]
  data_source?: string
}

export interface PublicLinkParseTask {
  id: number
  product_id: number
  source_url: string
  task_status: PublicLinkParseTaskStatus
  attempts: number
  result_json: PublicLinkCandidate | null
  error_message: string | null
  confirmed_competitor_id: number | null
  created_at: string
  updated_at: string
}
