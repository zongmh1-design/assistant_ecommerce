import { apiClient } from './client'
import type { PaginatedResponse, PageQuery } from '../types/api'
import type { Store, StoreCreate, StoreUpdate } from '../types/store'

export function listStores(query: PageQuery = {}): Promise<PaginatedResponse<Store>> {
  return apiClient('/stores', {}, query)
}

export function getStore(storeId: number): Promise<Store> {
  return apiClient(`/stores/${storeId}`)
}

export function createStore(data: StoreCreate): Promise<Store> {
  return apiClient('/stores', { method: 'POST', body: JSON.stringify(data) })
}

export function updateStore(storeId: number, data: StoreUpdate): Promise<Store> {
  return apiClient(`/stores/${storeId}`, { method: 'PATCH', body: JSON.stringify(data) })
}
