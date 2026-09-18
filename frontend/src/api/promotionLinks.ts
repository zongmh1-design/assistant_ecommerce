import { apiClient } from './client'
import type { PageQuery } from '../types/api'
import type {
  PromotionLink,
  PromotionLinkClickListResponse,
  PromotionLinkCreate,
  PromotionLinkListResponse,
  PromotionLinkStatus,
  PromotionLinkSuggestion,
  PromotionLinkUpdate,
} from '../types/promotionLink'

const DEFAULT_API_BASE_URL = '/api/v1'

export interface PromotionLinkQuery extends PageQuery {
  status?: PromotionLinkStatus
}

export function generatePromotionSuggestion(productId: number): Promise<PromotionLinkSuggestion> {
  return apiClient(`/products/${productId}/promotion-links/generate`, { method: 'POST' })
}

export function createPromotionLink(productId: number, data: PromotionLinkCreate): Promise<PromotionLink> {
  return apiClient(`/products/${productId}/promotion-links`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function listPromotionLinks(
  productId: number,
  query: PromotionLinkQuery = {},
): Promise<PromotionLinkListResponse> {
  return apiClient(`/products/${productId}/promotion-links`, {}, query)
}

export function getPromotionLink(productId: number, linkId: number): Promise<PromotionLink> {
  return apiClient(`/products/${productId}/promotion-links/${linkId}`)
}

export function updatePromotionLink(
  productId: number,
  linkId: number,
  data: PromotionLinkUpdate,
): Promise<PromotionLink> {
  return apiClient(`/products/${productId}/promotion-links/${linkId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function listPromotionLinkClicks(
  productId: number,
  linkId: number,
  query: PageQuery = {},
): Promise<PromotionLinkClickListResponse> {
  return apiClient(`/products/${productId}/promotion-links/${linkId}/clicks`, {}, query)
}

/** 根据当前 API 配置生成公开 tracking 跳转地址，不携带 Bearer Token。 */
export function buildTrackingUrl(trackingCode: string): string {
  const baseUrl = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '')
  const path = `${baseUrl}/r/${encodeURIComponent(trackingCode)}`
  if (/^https?:\/\//i.test(baseUrl)) return path
  if (typeof window === 'undefined') return path
  return `${window.location.origin}${path.startsWith('/') ? path : `/${path}`}`
}
