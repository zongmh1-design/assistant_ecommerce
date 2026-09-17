import type { Platform } from './store'

export type ProductStatus = 'draft' | 'active' | 'inactive'

export interface Product {
  id: number
  store_id: number
  name: string
  platform: Platform
  category: string | null
  price: string
  cost: string | null
  target_audience: string | null
  selling_points: string[]
  product_url: string | null
  images_json: string[]
  status: ProductStatus
  created_at: string
  updated_at: string
}

export interface ProductCreate {
  store_id: number
  name: string
  platform: Platform
  category?: string | null
  price: string
  cost?: string | null
  target_audience?: string | null
  selling_points?: string[]
  product_url?: string | null
  images_json?: string[]
  status?: ProductStatus
}

export type ProductUpdate = Partial<ProductCreate>
