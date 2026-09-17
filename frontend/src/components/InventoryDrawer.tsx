import { Alert, App, Button, Descriptions, Drawer, Form, Input, InputNumber, Modal, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { adjustInventory, getInventory, listInventoryMovements } from '../api/inventory'
import { useAuth } from '../auth/AuthContext'
import { PageError, PageLoading } from './PageState'
import { PaginationControls } from './PaginationControls'
import type { InventoryItem, InventoryMovement } from '../types/inventory'
import type { ProductSku } from '../types/sku'

const PAGE_SIZE = 10
const movementLabels = { initial: '初始化', inbound: '入库', outbound: '出库', adjustment: '调整' }

export function InventoryDrawer({
  sku,
  open,
  onClose,
  onChanged,
}: {
  sku: ProductSku | null
  open: boolean
  onClose: () => void
  onChanged: () => Promise<void>
}) {
  const { canWrite } = useAuth()
  const { message } = App.useApp()
  const [form] = Form.useForm<{ change_qty: number; reason_text: string }>()
  const [inventory, setInventory] = useState<InventoryItem | null>(null)
  const [movements, setMovements] = useState<InventoryMovement[]>([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [adjustOpen, setAdjustOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [adjustError, setAdjustError] = useState('')

  const load = useCallback(async () => {
    if (!sku || !open) return
    setLoading(true)
    setError('')
    try {
      const [current, history] = await Promise.all([
        getInventory(sku.id),
        listInventoryMovements(sku.id, { page, page_size: PAGE_SIZE }),
      ])
      setInventory(current)
      setMovements(history.items)
      setTotal(history.total)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '库存信息加载失败')
    } finally {
      setLoading(false)
    }
  }, [sku, open, page])

  useEffect(() => {
    void load()
  }, [load])

  const submitAdjustment = async () => {
    if (!sku) return
    const values = await form.validateFields()
    setSaving(true)
    setAdjustError('')
    try {
      await adjustInventory(sku.id, values)
      setAdjustOpen(false)
      form.resetFields()
      await Promise.all([load(), onChanged()])
      message.success('库存调整成功，当前库存与流水已刷新')
    } catch (reason) {
      setAdjustError(reason instanceof ApiError ? reason.message : '库存调整失败')
    } finally {
      setSaving(false)
    }
  }

  const columns: ColumnsType<InventoryMovement> = [
    { title: '类型', dataIndex: 'movement_type', render: (value: InventoryMovement['movement_type']) => movementLabels[value] },
    {
      title: '变化量',
      dataIndex: 'change_qty',
      render: (value: number) => <Typography.Text type={value >= 0 ? 'success' : 'danger'}>{value > 0 ? `+${value}` : value}</Typography.Text>,
    },
    { title: '调整前', dataIndex: 'before_qty' },
    { title: '调整后', dataIndex: 'after_qty' },
    { title: '原因', dataIndex: 'reason_text' },
    { title: '时间', dataIndex: 'created_at', render: (value: string) => new Date(value).toLocaleString('zh-CN') },
  ]

  return (
    <>
      <Drawer open={open} onClose={onClose} width={900} title={sku ? `${sku.sku_name} · 库存` : '库存'}>
        {loading ? <PageLoading /> : error ? <PageError message={error} onRetry={() => void load()} /> : inventory ? (
          <Space orientation="vertical" size="large" style={{ width: '100%' }}>
            {sku?.status === 'inactive' && <Alert type="warning" showIcon title="该 SKU 已停用，后端禁止继续调整库存" />}
            <Descriptions bordered column={3}>
              <Descriptions.Item label="当前库存">{inventory.stock_qty}</Descriptions.Item>
              <Descriptions.Item label="锁定库存">{inventory.locked_qty}</Descriptions.Item>
              <Descriptions.Item label="可用库存"><Tag color="blue">{inventory.available_qty}</Tag></Descriptions.Item>
              <Descriptions.Item label="预警阈值">{inventory.warning_threshold}</Descriptions.Item>
              <Descriptions.Item label="库位" span={2}>{inventory.location_text || '—'}</Descriptions.Item>
            </Descriptions>
            <div className="section-heading">
              <Typography.Title level={4}>库存流水</Typography.Title>
              {canWrite && sku?.status === 'active' && (
                <Button type="primary" onClick={() => { setAdjustError(''); setAdjustOpen(true) }}>调整库存</Button>
              )}
            </div>
            <Table rowKey="id" columns={columns} dataSource={movements} pagination={false} locale={{ emptyText: '暂无库存流水' }} />
            <PaginationControls page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
          </Space>
        ) : null}
      </Drawer>
      <Modal
        open={adjustOpen}
        title="调整库存"
        okText="确认调整"
        cancelText="取消"
        confirmLoading={saving}
        onOk={submitAdjustment}
        onCancel={() => setAdjustOpen(false)}
      >
        <Alert
          type="info"
          showIcon
          title="填写库存变化量"
          description="正数表示入库，负数表示出库；这不是新的绝对库存值。每次调整都会由后端生成库存流水。"
          className="form-alert"
        />
        {adjustError && <Alert type="error" showIcon title={adjustError} className="form-alert" />}
        <Form form={form} layout="vertical">
          <Form.Item
            label="库存变化量"
            name="change_qty"
            rules={[{ required: true, message: '请输入库存变化量' }, { validator: (_, value) => value === 0 ? Promise.reject(new Error('变化量不能为 0')) : Promise.resolve() }]}
          >
            <InputNumber precision={0} style={{ width: '100%' }} placeholder="例如 10 或 -5" />
          </Form.Item>
          <Form.Item label="调整原因" name="reason_text" rules={[{ required: true, message: '请输入调整原因' }]}>
            <Input.TextArea rows={3} maxLength={500} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
