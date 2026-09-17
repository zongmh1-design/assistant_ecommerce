import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'
import { ApiError } from '../api/client'
import { CompetitorsPage } from '../pages/CompetitorsPage'
import { SkuInventoryPage } from '../pages/SkuInventoryPage'
import type { Competitor, PublicLinkParseTask } from '../types/competitor'
import type { InventoryItem, InventoryMovement } from '../types/inventory'
import type { Product } from '../types/product'
import type { ProductSku, ProductSkuCreate } from '../types/sku'
import type { Store } from '../types/store'

const mocks = vi.hoisted(() => ({
  getCurrentUser: vi.fn(),
  login: vi.fn(),
  getProduct: vi.fn(),
  listProducts: vi.fn(),
  getStore: vi.fn(),
  listStores: vi.fn(),
  createStore: vi.fn(),
  updateStore: vi.fn(),
  listProductSkus: vi.fn(),
  getSku: vi.fn(),
  createSku: vi.fn(),
  updateSku: vi.fn(),
  getInventory: vi.fn(),
  adjustInventory: vi.fn(),
  listInventoryMovements: vi.fn(),
  listCompetitors: vi.fn(),
  createCompetitor: vi.fn(),
  updateCompetitor: vi.fn(),
  createLinkParseTask: vi.fn(),
  getLinkParseTask: vi.fn(),
  runLinkParseTask: vi.fn(),
  confirmLinkParseTask: vi.fn(),
}))
const authState = vi.hoisted(() => ({ canWrite: true }))

vi.mock('antd', async (importOriginal) => {
  const actual = await importOriginal<typeof import('antd')>()
  const React = await import('react')
  type OverlayProps = {
    open?: boolean
    title?: ReactNode
    children?: ReactNode
    onOk?: () => void
    onCancel?: () => void
    onClose?: () => void
    okText?: ReactNode
    cancelText?: ReactNode
    footer?: ReactNode
  }
  const Modal = ({ open, title, children, onOk, onCancel, okText = '确定', cancelText = '取消', footer }: OverlayProps) => {
    if (!open) return null
    return React.createElement(
      'section',
      { role: 'dialog', 'aria-label': typeof title === 'string' ? title : undefined },
      title,
      children,
      footer === null ? null : React.createElement('button', { onClick: onOk }, okText),
      React.createElement('button', { onClick: onCancel }, cancelText),
    )
  }
  const Drawer = ({ open, title, children, onClose }: OverlayProps) => {
    if (!open) return null
    return React.createElement(
      'section',
      { role: 'dialog', 'aria-label': typeof title === 'string' ? title : undefined },
      title,
      children,
      React.createElement('button', { onClick: onClose }, '关闭抽屉'),
    )
  }
  const App = Object.assign(actual.App, {
    useApp: () => ({
      message: { success: vi.fn() },
    }),
  })
  return { ...actual, Modal, Drawer, App }
})

vi.mock('../api/auth', () => ({ login: mocks.login, getCurrentUser: mocks.getCurrentUser }))
vi.mock('../auth/AuthContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../auth/AuthContext')>()
  return { ...actual, useAuth: () => authState }
})
vi.mock('../api/products', () => ({
  getProduct: mocks.getProduct,
  listProducts: mocks.listProducts,
  createProduct: vi.fn(),
  updateProduct: vi.fn(),
}))
vi.mock('../api/stores', () => ({
  getStore: mocks.getStore,
  listStores: mocks.listStores,
  createStore: mocks.createStore,
  updateStore: mocks.updateStore,
}))
vi.mock('../api/skus', () => ({
  listProductSkus: mocks.listProductSkus,
  getSku: mocks.getSku,
  createSku: mocks.createSku,
  updateSku: mocks.updateSku,
}))
vi.mock('../api/inventory', () => ({
  getInventory: mocks.getInventory,
  adjustInventory: mocks.adjustInventory,
  listInventoryMovements: mocks.listInventoryMovements,
}))
vi.mock('../api/competitors', () => ({
  listCompetitors: mocks.listCompetitors,
  createCompetitor: mocks.createCompetitor,
  updateCompetitor: mocks.updateCompetitor,
  createLinkParseTask: mocks.createLinkParseTask,
  getLinkParseTask: mocks.getLinkParseTask,
  runLinkParseTask: mocks.runLinkParseTask,
  confirmLinkParseTask: mocks.confirmLinkParseTask,
}))
vi.mock('../components/SkuFormModal', async () => {
  const React = await import('react')
  return {
    SkuFormModal: ({ open, onSubmit }: { open: boolean; onSubmit: (data: ProductSkuCreate) => Promise<void> }) => open
      ? React.createElement(
          'section',
          { role: 'dialog', 'aria-label': '创建 SKU' },
          React.createElement('label', null, 'SKU 编码', React.createElement('input', { 'aria-label': 'SKU 编码' })),
          React.createElement('label', null, 'SKU 名称', React.createElement('input', { 'aria-label': 'SKU 名称' })),
          React.createElement('label', null, '价格', React.createElement('input', { 'aria-label': '价格' })),
          React.createElement('button', {
            onClick: () => void onSubmit({
              sku_code: 'NEW-01', sku_name: '新规格', spec_json: {}, price: '88.00',
              cost: null, status: 'active', platform_sku_id: null,
            }),
          }, '保存'),
        )
      : null,
  }
})
vi.mock('../components/CompetitorFormModal', async () => {
  const React = await import('react')
  return {
    CompetitorFormModal: ({ open, onSubmit }: { open: boolean; onSubmit: (data: Record<string, unknown>) => Promise<void> }) => open
      ? React.createElement(
          'section',
          { role: 'dialog', 'aria-label': '手工添加竞品' },
          React.createElement('label', null, '竞品名称', React.createElement('input', { 'aria-label': '竞品名称' })),
          React.createElement('label', null, '公开商品链接', React.createElement('input', { 'aria-label': '公开商品链接' })),
          React.createElement('button', {
            onClick: () => void onSubmit({
              name: '新竞品', platform: 'other', url: 'https://example.com/new', price: null,
              sales_hint: null, title: null, main_image: null, selling_points: [], review_keywords: [],
            }),
          }, '保存'),
        )
      : null,
  }
})

const store: Store = {
  id: 10, store_name: 'Demo 店铺', platform: 'taobao', external_store_id: null,
  owner_name: null, remark: null, created_at: '2026-09-16T00:00:00Z', updated_at: '2026-09-16T00:00:00Z',
}
const product: Product = {
  id: 20, store_id: 10, name: '移动电源', platform: 'taobao', category: '数码',
  price: '99.00', cost: '50.00', target_audience: '通勤用户', selling_points: ['轻量'],
  product_url: null, images_json: [], status: 'active',
  created_at: '2026-09-16T00:00:00Z', updated_at: '2026-09-16T00:00:00Z',
}
const sku: ProductSku = {
  id: 30, product_id: 20, sku_code: 'SKU-RED', sku_name: '红色款', spec_json: { color: 'red' },
  price: '99.00', cost: '50.00', status: 'active', platform_sku_id: null,
  created_at: '2026-09-16T00:00:00Z', updated_at: '2026-09-16T00:00:00Z',
}
const inventory: InventoryItem = {
  id: 40, sku_id: 30, stock_qty: 20, locked_qty: 2, warning_threshold: 5,
  location_text: 'A-01', available_qty: 18, updated_at: '2026-09-16T00:00:00Z',
}
const movement: InventoryMovement = {
  id: 50, sku_id: 30, movement_type: 'inbound', change_qty: 20, before_qty: 0, after_qty: 20,
  reason_text: '采购入库', reference_type: null, reference_id: null, created_at: '2026-09-16T00:00:00Z',
}
const competitor: Competitor = {
  id: 60, product_id: 20, name: '竞品 A', platform: 'jd', url: 'https://example.com/a',
  price: '89.00', sales_hint: 'Mock 提示', title: '竞品标题', main_image: null,
  selling_points: ['便携'], review_keywords: ['续航'],
  created_at: '2026-09-16T00:00:00Z', updated_at: '2026-09-16T00:00:00Z',
}
const pendingTask: PublicLinkParseTask = {
  id: 70, product_id: 20, source_url: 'https://example.com/phone-case-001', task_status: 'pending',
  attempts: 0, result_json: null, error_message: null, confirmed_competitor_id: null,
  created_at: '2026-09-16T00:00:00Z', updated_at: '2026-09-16T00:00:00Z',
}
const succeededTask: PublicLinkParseTask = {
  ...pendingTask,
  task_status: 'succeeded',
  attempts: 1,
  result_json: {
    name: '解析候选竞品', platform: 'other', price: '59.90', title: 'Mock 候选',
    selling_points: ['磁吸'], review_keywords: ['手感'], data_source: 'mock_demo',
  },
}

function page<T>(items: T[]) {
  return { items, total: items.length, page: 1, page_size: 20 }
}

function renderSkus() {
  return render(<SkuInventoryPage productId={20} />)
}

function renderCompetitors() {
  return render(<CompetitorsPage productId={20} />)
}

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear()
  authState.canWrite = true
  mocks.getProduct.mockResolvedValue(product)
  mocks.getStore.mockResolvedValue(store)
  mocks.listStores.mockResolvedValue(page([store]))
  mocks.listProductSkus.mockResolvedValue(page([sku]))
  mocks.getInventory.mockResolvedValue(inventory)
  mocks.listInventoryMovements.mockResolvedValue(page([movement]))
  mocks.listCompetitors.mockResolvedValue(page([competitor]))
})

describe('SKU and inventory', () => {
  it('shows SKU list and current inventory from backend', async () => {
    renderSkus()
    expect(await screen.findByText('SKU-RED')).toBeInTheDocument()
    expect(screen.getByText('20')).toBeInTheDocument()
    expect(screen.getByText('18')).toBeInTheDocument()
  })

  it('shows an explicit empty state', async () => {
    mocks.listProductSkus.mockResolvedValue(page([]))
    renderSkus()
    expect(await screen.findByText('暂无 SKU')).toBeInTheDocument()
  })

  it('creates a SKU and lets backend initialize inventory', async () => {
    renderSkus()
    await screen.findByText('SKU-RED')
    mocks.createSku.mockResolvedValue(sku)
    fireEvent.click(screen.getByRole('button', { name: /创建 SKU/ }))
    fireEvent.change(screen.getByLabelText('SKU 编码'), { target: { value: 'NEW-01' } })
    fireEvent.change(screen.getByLabelText('SKU 名称'), { target: { value: '新规格' } })
    fireEvent.change(screen.getByLabelText('价格'), { target: { value: '88.00' } })
    fireEvent.click(screen.getByRole('button', { name: /保\s*存/ }))
    await waitFor(() => expect(mocks.createSku).toHaveBeenCalled())
    await waitFor(() => expect(mocks.listProductSkus.mock.calls.length).toBeGreaterThan(1))
    expect(mocks.adjustInventory).not.toHaveBeenCalled()
  })

  it('preserves SKU field validation details from a 422 response', () => {
    const error = new ApiError(422, 'http_422', '提交内容未通过校验', { sku_code: '编码已存在' })
    expect(error.status).toBe(422)
    expect(error.fieldErrors.sku_code).toBe('编码已存在')
  })

  it('renders product/SKU 404 safely', async () => {
    mocks.listProductSkus.mockRejectedValue(new ApiError(404, 'product_not_found', 'not found'))
    renderSkus()
    expect(await screen.findByText('当前商品下不存在该 SKU 或商品不存在')).toBeInTheDocument()
  })

  it('shows movements and refreshes inventory and history after adjustment', async () => {
    mocks.adjustInventory.mockResolvedValue({ ...inventory, stock_qty: 25, available_qty: 23 })
    renderSkus()
    fireEvent.click(await screen.findByRole('button', { name: '库存与流水' }))
    expect(await screen.findByText('采购入库')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '调整库存' }))
    fireEvent.change(screen.getByLabelText('库存变化量'), { target: { value: '5' } })
    fireEvent.change(screen.getByLabelText('调整原因'), { target: { value: '补货' } })
    fireEvent.click(screen.getByRole('button', { name: '确认调整' }))
    await waitFor(() => expect(mocks.adjustInventory).toHaveBeenCalledWith(30, { change_qty: 5, reason_text: '补货' }))
    await waitFor(() => expect(mocks.listInventoryMovements.mock.calls.length).toBeGreaterThan(1))
    expect(mocks.getInventory.mock.calls.length).toBeGreaterThan(1)
  })

  it('shows adjustment business errors', async () => {
    mocks.adjustInventory.mockRejectedValue(new ApiError(409, 'insufficient_stock', '库存不足'))
    renderSkus()
    fireEvent.click(await screen.findByRole('button', { name: '库存与流水' }))
    await screen.findByText('采购入库')
    fireEvent.click(screen.getByRole('button', { name: '调整库存' }))
    fireEvent.change(screen.getByLabelText('库存变化量'), { target: { value: '-99' } })
    fireEvent.change(screen.getByLabelText('调整原因'), { target: { value: '出库' } })
    fireEvent.click(screen.getByRole('button', { name: '确认调整' }))
    expect(await screen.findByText('库存不足')).toBeInTheDocument()
  })

  it('keeps viewer read-only', async () => {
    authState.canWrite = false
    renderSkus()
    await screen.findByText('SKU-RED')
    expect(screen.queryByRole('button', { name: /创建 SKU/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '库存与流水' }))
    await screen.findByText('采购入库')
    expect(screen.queryByRole('button', { name: '调整库存' })).not.toBeInTheDocument()
  })
})

describe('competitors and public-link parsing', () => {
  it('shows competitor list', async () => {
    renderCompetitors()
    expect(await screen.findByText('竞品 A')).toBeInTheDocument()
    expect(screen.getByText('¥89.00')).toBeInTheDocument()
  })

  it('shows competitor empty and API error states', async () => {
    mocks.listCompetitors.mockResolvedValueOnce(page([]))
    const view = renderCompetitors()
    expect(await screen.findByText('暂无竞品')).toBeInTheDocument()
    view.unmount()
    mocks.listCompetitors.mockRejectedValue(new ApiError(500, 'server_error', '竞品服务异常'))
    renderCompetitors()
    expect(await screen.findByText('竞品服务异常')).toBeInTheDocument()
  })

  it('manually creates a competitor', async () => {
    mocks.createCompetitor.mockResolvedValue(competitor)
    renderCompetitors()
    await screen.findByText('竞品 A')
    fireEvent.click(screen.getByRole('button', { name: /手工添加/ }))
    fireEvent.change(screen.getByLabelText('竞品名称'), { target: { value: '新竞品' } })
    fireEvent.change(screen.getByLabelText('公开商品链接'), { target: { value: 'https://example.com/new' } })
    fireEvent.click(screen.getByRole('button', { name: /保\s*存/ }))
    await waitFor(() => expect(mocks.createCompetitor).toHaveBeenCalled())
    await waitFor(() => expect(mocks.listCompetitors.mock.calls.length).toBeGreaterThan(1))
  })

  it('keeps competitor actions hidden for viewer', async () => {
    authState.canWrite = false
    renderCompetitors()
    await screen.findByText('竞品 A')
    expect(screen.queryByRole('button', { name: /手工添加/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /从公开链接解析/ })).not.toBeInTheDocument()
  })

  it('creates, runs and confirms a public-link parse task', async () => {
    mocks.createLinkParseTask.mockResolvedValue(pendingTask)
    mocks.runLinkParseTask.mockResolvedValue(succeededTask)
    mocks.confirmLinkParseTask.mockResolvedValue(competitor)
    renderCompetitors()
    await screen.findByText('竞品 A')
    fireEvent.click(screen.getByRole('button', { name: /从公开链接解析/ }))
    fireEvent.change(screen.getByLabelText('公开商品 URL'), { target: { value: pendingTask.source_url } })
    fireEvent.click(screen.getByRole('button', { name: '创建解析任务' }))
    expect(await screen.findByText('待解析')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '开始解析' }))
    expect(await screen.findByText('解析候选竞品')).toBeInTheDocument()
    expect(mocks.confirmLinkParseTask).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: '确认并创建竞品' }))
    await waitFor(() => expect(mocks.confirmLinkParseTask).toHaveBeenCalledWith(20, 70))
  })

  it('shows failed state and uses the existing run endpoint for retry', async () => {
    const failed = { ...pendingTask, task_status: 'failed' as const, attempts: 1, error_message: 'Mock 解析失败' }
    mocks.createLinkParseTask.mockResolvedValue(pendingTask)
    mocks.runLinkParseTask.mockResolvedValueOnce(failed).mockResolvedValueOnce(succeededTask)
    renderCompetitors()
    await screen.findByText('竞品 A')
    fireEvent.click(screen.getByRole('button', { name: /从公开链接解析/ }))
    fireEvent.change(screen.getByLabelText('公开商品 URL'), { target: { value: pendingTask.source_url } })
    fireEvent.click(screen.getByRole('button', { name: '创建解析任务' }))
    fireEvent.click(await screen.findByRole('button', { name: '开始解析' }))
    expect(await screen.findByText('Mock 解析失败')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '重新解析' }))
    expect(await screen.findByText('解析候选竞品')).toBeInTheDocument()
    expect(mocks.runLinkParseTask).toHaveBeenCalledTimes(2)
  })
})
