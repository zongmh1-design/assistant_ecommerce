import { apiClient } from './client'
import type { PageQuery } from '../types/api'
import type { ProductDiagnosis, ProductDiagnosisListResponse, ProductDiagnosisUpdate } from '../types/diagnosis'

export function generateDiagnosis(productId: number): Promise<ProductDiagnosis> {
  return apiClient(`/products/${productId}/diagnoses/generate`, { method: 'POST' })
}

export function listDiagnoses(productId: number, query: PageQuery = {}): Promise<ProductDiagnosisListResponse> {
  return apiClient(`/products/${productId}/diagnoses`, {}, query)
}

export function getDiagnosis(productId: number, diagnosisId: number): Promise<ProductDiagnosis> {
  return apiClient(`/products/${productId}/diagnoses/${diagnosisId}`)
}

export function updateDiagnosis(
  productId: number,
  diagnosisId: number,
  data: ProductDiagnosisUpdate,
): Promise<ProductDiagnosis> {
  return apiClient(`/products/${productId}/diagnoses/${diagnosisId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}
