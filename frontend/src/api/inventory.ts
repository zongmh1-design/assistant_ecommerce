import { apiClient } from './client'
import type { PaginatedResponse, PageQuery } from '../types/api'
import type { InventoryAdjustment, InventoryItem, InventoryMovement } from '../types/inventory'

export function getInventory(skuId: number): Promise<InventoryItem> {
  return apiClient(`/skus/${skuId}/inventory`)
}

export function adjustInventory(skuId: number, data: InventoryAdjustment): Promise<InventoryItem> {
  return apiClient(`/skus/${skuId}/inventory/adjust`, { method: 'POST', body: JSON.stringify(data) })
}

export function listInventoryMovements(
  skuId: number,
  query: PageQuery = {},
): Promise<PaginatedResponse<InventoryMovement>> {
  return apiClient(`/skus/${skuId}/inventory/movements`, {}, query)
}
