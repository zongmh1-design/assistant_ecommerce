export type InventoryMovementType = 'initial' | 'inbound' | 'outbound' | 'adjustment'

export interface InventoryItem {
  id: number
  sku_id: number
  stock_qty: number
  locked_qty: number
  warning_threshold: number
  location_text: string | null
  updated_at: string
  available_qty: number
}

export interface InventoryAdjustment {
  change_qty: number
  reason_text: string
  movement_type?: InventoryMovementType
  reference_type?: string | null
  reference_id?: string | null
}

export interface InventoryMovement {
  id: number
  sku_id: number
  movement_type: InventoryMovementType
  change_qty: number
  before_qty: number
  after_qty: number
  reason_text: string
  reference_type: string | null
  reference_id: string | null
  created_at: string
}
