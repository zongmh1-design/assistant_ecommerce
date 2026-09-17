import { apiClient } from './client'
import type { PageQuery } from '../types/api'
import type {
  AdRecommendation,
  AdRecommendationConfirmation,
  AdRecommendationConfirmStatus,
  AdRecommendationListResponse,
  AdRecommendationUpdate,
} from '../types/adRecommendation'

export interface AdRecommendationQuery extends PageQuery {
  confirm_status?: AdRecommendationConfirmStatus
}

export function generateAdRecommendation(productId: number): Promise<AdRecommendation> {
  return apiClient(`/products/${productId}/ad-recommendations/generate`, { method: 'POST' })
}

export function listAdRecommendations(
  productId: number,
  query: AdRecommendationQuery = {},
): Promise<AdRecommendationListResponse> {
  return apiClient(`/products/${productId}/ad-recommendations`, {}, query)
}

export function getAdRecommendation(productId: number, recommendationId: number): Promise<AdRecommendation> {
  return apiClient(`/products/${productId}/ad-recommendations/${recommendationId}`)
}

export function updateAdRecommendation(
  productId: number,
  recommendationId: number,
  data: AdRecommendationUpdate,
): Promise<AdRecommendation> {
  return apiClient(`/products/${productId}/ad-recommendations/${recommendationId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function confirmAdRecommendation(
  productId: number,
  recommendationId: number,
  data: AdRecommendationConfirmation,
): Promise<AdRecommendation> {
  return apiClient(`/products/${productId}/ad-recommendations/${recommendationId}/confirmation`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}
