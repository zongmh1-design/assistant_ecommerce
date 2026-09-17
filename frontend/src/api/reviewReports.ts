import { apiClient } from './client'
import type {
  ReviewReport,
  ReviewReportGenerateInput,
  ReviewReportListResponse,
  ReviewReportQuery,
  ReviewReportUpdate,
} from '../types/reviewReport'

export function generateReviewReport(productId: number, data: ReviewReportGenerateInput): Promise<ReviewReport> {
  return apiClient(`/products/${productId}/review-reports/generate`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function listReviewReports(productId: number, query: ReviewReportQuery = {}): Promise<ReviewReportListResponse> {
  return apiClient(`/products/${productId}/review-reports`, {}, query)
}

export function getReviewReport(productId: number, reportId: number): Promise<ReviewReport> {
  return apiClient(`/products/${productId}/review-reports/${reportId}`)
}

export function updateReviewReport(
  productId: number,
  reportId: number,
  data: ReviewReportUpdate,
): Promise<ReviewReport> {
  return apiClient(`/products/${productId}/review-reports/${reportId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

