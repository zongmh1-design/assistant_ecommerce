export type ProductSkuStatus = 'active' | 'inactive'

export interface ProductSku {
  id: number
  product_id: number
  sku_code: string
  sku_name: string
  spec_json: Record<string, string>
  price: string
  cost: string | null
  status: ProductSkuStatus
  platform_sku_id: string | null
  created_at: string
  updated_at: string
}

export interface ProductSkuCreate {
  sku_code: string
  sku_name: string
  spec_json: Record<string, string>
  price: string
  cost?: string | null
  status?: ProductSkuStatus
  platform_sku_id?: string | null
}

export type ProductSkuUpdate = Partial<ProductSkuCreate>
