export type Platform = 'taobao' | 'tmall' | 'jd' | 'douyin' | 'pinduoduo' | 'other'

export interface Store {
  id: number
  store_name: string
  platform: Platform
  external_store_id: string | null
  owner_name: string | null
  remark: string | null
  created_at: string
  updated_at: string
}

export interface StoreCreate {
  store_name: string
  platform: Platform
  external_store_id?: string | null
  owner_name?: string | null
  remark?: string | null
}

export type StoreUpdate = Partial<StoreCreate>
