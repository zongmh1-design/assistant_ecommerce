import { apiClient, apiClientBlob } from './client'
import type { PerformanceImportPreview, PerformanceImportResult } from '../types/performanceImport'

export function previewPerformanceImport(productId: number, file: File): Promise<PerformanceImportPreview> {
  const body = new FormData()
  body.append('file', file)
  return apiClient(`/products/${productId}/performance-records/import/preview`, { method: 'POST', body })
}

export function importPerformanceRecords(productId: number, file: File): Promise<PerformanceImportResult> {
  const body = new FormData()
  body.append('file', file)
  return apiClient(`/products/${productId}/performance-records/import`, { method: 'POST', body })
}

export function downloadPerformanceTemplate(): Promise<Blob> {
  return apiClientBlob('/workspace/templates/performance-records')
}

