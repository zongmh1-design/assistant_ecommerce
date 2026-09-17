import { EditOutlined, PlusOutlined } from '@ant-design/icons'
import { App, Button, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { getInventory } from '../api/inventory'
import { createSku, listProductSkus, updateSku } from '../api/skus'
import { useAuth } from '../auth/AuthContext'
import { InventoryDrawer } from '../components/InventoryDrawer'
import { PageEmpty, PageError, PageLoading } from '../components/PageState'
import { PaginationControls } from '../components/PaginationControls'
import { SkuFormModal } from '../components/SkuFormModal'
import type { InventoryItem } from '../types/inventory'
import type { ProductSku, ProductSkuCreate } from '../types/sku'

const PAGE_SIZE = 20

export function SkuInventoryPage({ productId }: { productId: number }) {
  const { canWrite } = useAuth()
  const { message } = App.useApp()
  const [items, setItems] = useState<ProductSku[]>([])
  const [inventories, setInventories] = useState<Record<number, InventoryItem>>({})
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<ProductSku | null>(null)
  const [inventorySku, setInventorySku] = useState<ProductSku | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const result = await listProductSkus(productId, { page, page_size: PAGE_SIZE })
      const inventoryPairs = await Promise.all(result.items.map(async (sku) => [sku.id, await getInventory(sku.id)] as const))
      setItems(result.items)
      setInventories(Object.fromEntries(inventoryPairs))
      setTotal(result.total)
    } catch (reason) {
      const message = reason instanceof ApiError && reason.status === 404
        ? '当前商品下不存在该 SKU 或商品不存在'
        : reason instanceof ApiError ? reason.message : 'SKU 与库存加载失败'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [productId, page])

  useEffect(() => {
    void load()
  }, [load])

  const columns: ColumnsType<ProductSku> = [
    { title: 'SKU 编码', dataIndex: 'sku_code' },
    { title: 'SKU 名称', dataIndex: 'sku_name' },
    { title: '规格', dataIndex: 'spec_json', render: (value: Record<string, string>) => Object.entries(value).map(([key, item]) => `${key}: ${item}`).join(' / ') || '—' },
    { title: '价格', dataIndex: 'price', render: (value: string) => `¥${value}` },
    { title: '状态', dataIndex: 'status', render: (value: ProductSku['status']) => <Tag color={value === 'active' ? 'green' : 'default'}>{value === 'active' ? '启用' : '停用'}</Tag> },
    { title: '当前库存', key: 'stock_qty', render: (_, sku) => inventories[sku.id]?.stock_qty ?? '—' },
    { title: '可用库存', key: 'available_qty', render: (_, sku) => inventories[sku.id]?.available_qty ?? '—' },
    {
      title: '操作',
      key: 'actions',
      render: (_, sku) => (
        <Space>
          <Button type="link" onClick={() => setInventorySku(sku)}>库存与流水</Button>
          {canWrite && <Button type="link" icon={<EditOutlined />} onClick={() => { setEditing(sku); setFormOpen(true) }}>编辑</Button>}
        </Space>
      ),
    },
  ]

  return (
    <>
      <div className="section-heading">
        <div>
          <Typography.Title level={4}>SKU / 库存</Typography.Title>
          <Typography.Text type="secondary">库存数量只能通过“调整库存”业务操作变化，并由后端保留流水。</Typography.Text>
        </div>
        {canWrite && <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); setFormOpen(true) }}>创建 SKU</Button>}
      </div>
      {loading ? <PageLoading /> : error ? <PageError message={error} onRetry={() => void load()} /> : items.length === 0 ? (
        <PageEmpty description="暂无 SKU" />
      ) : (
        <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
          <Table rowKey="id" columns={columns} dataSource={items} pagination={false} />
          <PaginationControls page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
        </Space>
      )}
      <SkuFormModal
        open={formOpen}
        sku={editing}
        onCancel={() => setFormOpen(false)}
        onSubmit={async (data: ProductSkuCreate) => {
          if (editing) await updateSku(editing.id, data)
          else await createSku(productId, data)
          setFormOpen(false)
          message.success(editing ? 'SKU 已更新' : 'SKU 已创建，库存已由后端自动初始化')
          await load()
        }}
      />
      <InventoryDrawer
        sku={inventorySku}
        open={Boolean(inventorySku)}
        onClose={() => setInventorySku(null)}
        onChanged={load}
      />
    </>
  )
}
