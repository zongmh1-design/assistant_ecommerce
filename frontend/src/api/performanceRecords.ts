import { apiClient } from './client'
import type {
  PerformanceRecord,
  PerformanceRecordCreate,
  PerformanceRecordListResponse,
  PerformanceRecordQuery,
  PerformanceRecordUpdate,
} from '../types/performanceRecord'

export function listPerformanceRecords(
  productId: number,
  query: PerformanceRecordQuery = {},
): Promise<PerformanceRecordListResponse> {
  return apiClient(`/products/${productId}/performance-records`, {}, query)
}

export function createPerformanceRecord(productId: number, data: PerformanceRecordCreate): Promise<PerformanceRecord> {
  return apiClient(`/products/${productId}/performance-records`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function getPerformanceRecord(productId: number, recordId: number): Promise<PerformanceRecord> {
  return apiClient(`/products/${productId}/performance-records/${recordId}`)
}

export function updatePerformanceRecord(
  productId: number,
  recordId: number,
  data: PerformanceRecordUpdate,
): Promise<PerformanceRecord> {
  return apiClient(`/products/${productId}/performance-records/${recordId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

