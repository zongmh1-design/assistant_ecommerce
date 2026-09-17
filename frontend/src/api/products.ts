import { apiClient } from './client'
import type { PaginatedResponse, PageQuery } from '../types/api'
import type { Product, ProductCreate, ProductStatus, ProductUpdate } from '../types/product'
import type { Platform } from '../types/store'

export interface ProductQuery extends PageQuery {
  store_id?: number
  platform?: Platform
  status?: ProductStatus
}

export function listProducts(query: ProductQuery = {}): Promise<PaginatedResponse<Product>> {
  return apiClient('/products', {}, query)
}

export function getProduct(productId: number): Promise<Product> {
  return apiClient(`/products/${productId}`)
}

export function createProduct(data: ProductCreate): Promise<Product> {
  return apiClient('/products', { method: 'POST', body: JSON.stringify(data) })
}

export function updateProduct(productId: number, data: ProductUpdate): Promise<Product> {
  return apiClient(`/products/${productId}`, { method: 'PATCH', body: JSON.stringify(data) })
}
