import { apiClient } from './client'
import type { PageQuery } from '../types/api'
import type {
  AdExperiment,
  AdExperimentGenerateInput,
  AdExperimentListResponse,
  AdExperimentStatus,
  AdExperimentStatusUpdate,
  AdExperimentUpdate,
} from '../types/adExperiment'

export interface AdExperimentQuery extends PageQuery {
  experiment_status?: AdExperimentStatus
  ad_recommendation_id?: number
}

export function generateAdExperiment(productId: number, data: AdExperimentGenerateInput): Promise<AdExperiment> {
  return apiClient(`/products/${productId}/ad-experiments/generate`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function listAdExperiments(
  productId: number,
  query: AdExperimentQuery = {},
): Promise<AdExperimentListResponse> {
  return apiClient(`/products/${productId}/ad-experiments`, {}, query)
}

export function getAdExperiment(productId: number, experimentId: number): Promise<AdExperiment> {
  return apiClient(`/products/${productId}/ad-experiments/${experimentId}`)
}

export function updateAdExperiment(
  productId: number,
  experimentId: number,
  data: AdExperimentUpdate,
): Promise<AdExperiment> {
  return apiClient(`/products/${productId}/ad-experiments/${experimentId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function updateAdExperimentStatus(
  productId: number,
  experimentId: number,
  data: AdExperimentStatusUpdate,
): Promise<AdExperiment> {
  return apiClient(`/products/${productId}/ad-experiments/${experimentId}/status`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}
