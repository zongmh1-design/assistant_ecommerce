import { apiClient } from './client'
import type { PaginatedResponse, PageQuery } from '../types/api'
import type {
  Competitor,
  CompetitorCreate,
  CompetitorUpdate,
  PublicLinkParseTask,
} from '../types/competitor'

export function listCompetitors(productId: number, query: PageQuery = {}): Promise<PaginatedResponse<Competitor>> {
  return apiClient(`/products/${productId}/competitors`, {}, query)
}

export function createCompetitor(productId: number, data: CompetitorCreate): Promise<Competitor> {
  return apiClient(`/products/${productId}/competitors`, { method: 'POST', body: JSON.stringify(data) })
}

export function updateCompetitor(competitorId: number, data: CompetitorUpdate): Promise<Competitor> {
  return apiClient(`/competitors/${competitorId}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export function createLinkParseTask(productId: number, sourceUrl: string): Promise<PublicLinkParseTask> {
  return apiClient(`/products/${productId}/competitors/import-url-tasks`, {
    method: 'POST',
    body: JSON.stringify({ source_url: sourceUrl }),
  })
}

export function getLinkParseTask(productId: number, taskId: number): Promise<PublicLinkParseTask> {
  return apiClient(`/products/${productId}/link-parse-tasks/${taskId}`)
}

export function runLinkParseTask(productId: number, taskId: number): Promise<PublicLinkParseTask> {
  return apiClient(`/products/${productId}/link-parse-tasks/${taskId}/run`, { method: 'POST' })
}

export function confirmLinkParseTask(productId: number, taskId: number): Promise<Competitor> {
  return apiClient(`/products/${productId}/link-parse-tasks/${taskId}/confirm`, { method: 'POST' })
}
