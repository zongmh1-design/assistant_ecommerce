import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import RootApp from '../RootApp'
import type { Product } from '../types/product'
import type { Store } from '../types/store'
import type { User } from '../types/auth'

const mocks = vi.hoisted(() => ({
  login: vi.fn(),
  getCurrentUser: vi.fn(),
  listProducts: vi.fn(),
  getProduct: vi.fn(),
  createProduct: vi.fn(),
  updateProduct: vi.fn(),
  listStores: vi.fn(),
  getStore: vi.fn(),
  createStore: vi.fn(),
  updateStore: vi.fn(),
  listDiagnoses: vi.fn(),
  getDiagnosis: vi.fn(),
  generateDiagnosis: vi.fn(),
  updateDiagnosis: vi.fn(),
}))

vi.mock('../api/auth', () => ({ login: mocks.login, getCurrentUser: mocks.getCurrentUser }))
vi.mock('../api/products', () => ({
  listProducts: mocks.listProducts,
  getProduct: mocks.getProduct,
  createProduct: mocks.createProduct,
  updateProduct: mocks.updateProduct,
}))
vi.mock('../api/stores', () => ({
  listStores: mocks.listStores,
  getStore: mocks.getStore,
  createStore: mocks.createStore,
  updateStore: mocks.updateStore,
}))
vi.mock('../api/diagnoses', () => ({
  listDiagnoses: mocks.listDiagnoses,
  getDiagnosis: mocks.getDiagnosis,
  generateDiagnosis: mocks.generateDiagnosis,
  updateDiagnosis: mocks.updateDiagnosis,
}))

const admin: User = {
  id: 1,
  username: 'admin',
  display_name: '管理员',
  role: 'admin',
  status: 'active',
  last_login_at: null,
  created_at: '2026-09-16T00:00:00Z',
  updated_at: '2026-09-16T00:00:00Z',
}
const viewer: User = { ...admin, id: 2, username: 'viewer', display_name: '查看人员', role: 'viewer' }
const store: Store = {
  id: 10,
  store_name: 'Demo 店铺',
  platform: 'taobao',
  external_store_id: null,
  owner_name: '运营',
  remark: null,
  created_at: '2026-09-16T00:00:00Z',
  updated_at: '2026-09-16T00:00:00Z',
}
const product: Product = {
  id: 20,
  store_id: 10,
  name: '轻量磁吸移动电源',
  platform: 'taobao',
  category: '数码配件',
  price: '99.00',
  cost: '45.00',
  target_audience: '通勤用户',
  selling_points: ['轻量', '磁吸'],
  product_url: null,
  images_json: [],
  status: 'active',
  created_at: '2026-09-16T00:00:00Z',
  updated_at: '2026-09-16T00:00:00Z',
}

function page<T>(items: T[]) {
  return { items, total: items.length, page: 1, page_size: 10 }
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <RootApp />
    </MemoryRouter>,
  )
}

function authenticateAs(user: User = admin) {
  sessionStorage.setItem('ecommerce_access_token', 'test-token')
  mocks.getCurrentUser.mockResolvedValue(user)
}

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear()
  mocks.listProducts.mockResolvedValue(page([]))
  mocks.listStores.mockResolvedValue(page([store]))
  mocks.getProduct.mockResolvedValue(product)
  mocks.getStore.mockResolvedValue(store)
  mocks.listDiagnoses.mockResolvedValue(page([]))
})

describe('authentication foundation', () => {
  it('logs in and loads the current user', async () => {
    mocks.login.mockResolvedValue({ access_token: 'token', token_type: 'bearer' })
    mocks.getCurrentUser.mockResolvedValue(admin)
    renderAt('/login')
    await userEvent.type(screen.getByLabelText('用户名'), 'admin')
    await userEvent.type(screen.getByLabelText('密码'), 'secret')
    await userEvent.click(screen.getByRole('button', { name: /登\s*录/ }))
    expect(await screen.findByRole('heading', { name: '商品管理' })).toBeInTheDocument()
    expect(sessionStorage.getItem('ecommerce_access_token')).toBe('token')
  })

  it('shows a safe login failure', async () => {
    mocks.login.mockRejectedValue(new ApiError(401, 'invalid_credentials', '用户名或密码错误'))
    renderAt('/login')
    await userEvent.type(screen.getByLabelText('用户名'), 'admin')
    await userEvent.type(screen.getByLabelText('密码'), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: /登\s*录/ }))
    expect(await screen.findByText('用户名或密码错误')).toBeInTheDocument()
  })

  it('restores a token through auth/me', async () => {
    authenticateAs()
    renderAt('/products')
    expect((await screen.findAllByText('管理员')).length).toBeGreaterThan(0)
    expect(mocks.getCurrentUser).toHaveBeenCalled()
  })

  it('redirects unauthenticated users to login', async () => {
    renderAt('/products')
    expect(await screen.findByRole('button', { name: /登\s*录/ })).toBeInTheDocument()
    expect(mocks.listProducts).not.toHaveBeenCalled()
  })
})

describe('product pages', () => {
  it('hides write operations from viewer', async () => {
    authenticateAs(viewer)
    mocks.listProducts.mockResolvedValue(page([product]))
    renderAt('/products')
    expect(await screen.findByText(product.name)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '创建商品' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '编辑' })).not.toBeInTheDocument()
  })

  it('renders product list data', async () => {
    authenticateAs()
    mocks.listProducts.mockResolvedValue(page([product]))
    renderAt('/products')
    expect(await screen.findByText(product.name)).toBeInTheDocument()
    expect(screen.getByText('¥99.00')).toBeInTheDocument()
  })

  it('renders a distinct empty state', async () => {
    authenticateAs()
    renderAt('/products')
    expect(await screen.findByText('暂无商品')).toBeInTheDocument()
  })

  it('renders a product API error', async () => {
    authenticateAs()
    mocks.listProducts.mockRejectedValue(new ApiError(500, 'server_error', '商品服务异常'))
    renderAt('/products')
    expect(await screen.findByText('商品服务异常')).toBeInTheDocument()
  })

  it('creates a product with backend fields', async () => {
    authenticateAs()
    mocks.createProduct.mockResolvedValue(product)
    renderAt('/products/new')
    await screen.findByRole('heading', { name: '创建商品' })
    await userEvent.click(screen.getByLabelText('所属店铺'))
    await userEvent.click(await screen.findByText(store.store_name))
    await userEvent.type(screen.getByLabelText('商品名称'), product.name)
    await userEvent.type(screen.getByLabelText('价格'), '99.00')
    await userEvent.click(screen.getByRole('button', { name: '创建商品' }))
    await waitFor(() => expect(mocks.createProduct).toHaveBeenCalled())
    expect(await screen.findByText('商品概览')).toBeInTheDocument()
  })

  it('maps create validation errors to the form', async () => {
    authenticateAs()
    mocks.createProduct.mockRejectedValue(new ApiError(422, 'http_422', '提交内容未通过校验', { name: '名称无效' }))
    renderAt('/products/new')
    await screen.findByRole('heading', { name: '创建商品' })
    await userEvent.click(screen.getByLabelText('所属店铺'))
    await userEvent.click(await screen.findByText(store.store_name))
    await userEvent.type(screen.getByLabelText('商品名称'), '测试商品')
    await userEvent.type(screen.getByLabelText('价格'), '10.00')
    await userEvent.click(screen.getByRole('button', { name: '创建商品' }))
    expect(await screen.findByText('名称无效')).toBeInTheDocument()
  })

  it('sends only changed fields on edit', async () => {
    authenticateAs()
    mocks.updateProduct.mockResolvedValue({ ...product, name: '更新商品' })
    renderAt('/products/20/edit')
    const input = await screen.findByLabelText('商品名称')
    fireEvent.change(input, { target: { value: '更新商品' } })
    await userEvent.click(screen.getByRole('button', { name: '保存修改' }))
    await waitFor(() => expect(mocks.updateProduct).toHaveBeenCalledWith(20, { name: '更新商品' }))
  })

  it('opens the workbench and its diagnosis page', async () => {
    authenticateAs()
    renderAt('/products/20')
    expect(await screen.findByText('商品概览')).toBeInTheDocument()
    await userEvent.click(screen.getByText('商品诊断'))
    expect(await screen.findByRole('heading', { name: '商品诊断' })).toBeInTheDocument()
    expect(await screen.findByText('当前商品还没有诊断结果')).toBeInTheDocument()
  })
})
