import { apiClient } from './client'
import type { PageQuery } from '../types/api'
import type {
  CreativePlan,
  CreativePlanListResponse,
  CreativePlanStatus,
  CreativePlanType,
  CreativePlanUpdate,
} from '../types/creativePlan'

export function generateMainImagePlans(productId: number): Promise<CreativePlan[]> {
  return apiClient(`/products/${productId}/creative-plans/main-images/generate`, { method: 'POST' })
}

export function generateVideoScripts(productId: number): Promise<CreativePlan[]> {
  return apiClient(`/products/${productId}/creative-plans/video-scripts/generate`, { method: 'POST' })
}

export function listCreativePlans(
  productId: number,
  query: PageQuery & { plan_type?: CreativePlanType; status?: CreativePlanStatus } = {},
): Promise<CreativePlanListResponse> {
  return apiClient(`/products/${productId}/creative-plans`, {}, query)
}

export function getCreativePlan(productId: number, planId: number): Promise<CreativePlan> {
  return apiClient(`/products/${productId}/creative-plans/${planId}`)
}

export function updateCreativePlan(
  productId: number,
  planId: number,
  data: CreativePlanUpdate,
): Promise<CreativePlan> {
  return apiClient(`/products/${productId}/creative-plans/${planId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}
