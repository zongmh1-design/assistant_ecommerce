import { apiClient } from './client'
import type { PaginatedResponse, PageQuery } from '../types/api'
import type { ProductSku, ProductSkuCreate, ProductSkuUpdate } from '../types/sku'

export function listProductSkus(productId: number, query: PageQuery = {}): Promise<PaginatedResponse<ProductSku>> {
  return apiClient(`/products/${productId}/skus`, {}, query)
}

export function getSku(skuId: number): Promise<ProductSku> {
  return apiClient(`/skus/${skuId}`)
}

export function createSku(productId: number, data: ProductSkuCreate): Promise<ProductSku> {
  return apiClient(`/products/${productId}/skus`, { method: 'POST', body: JSON.stringify(data) })
}

export function updateSku(skuId: number, data: ProductSkuUpdate): Promise<ProductSku> {
  return apiClient(`/skus/${skuId}`, { method: 'PATCH', body: JSON.stringify(data) })
}
