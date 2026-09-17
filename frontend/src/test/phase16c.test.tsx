import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { App as AntdApp } from 'antd'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import { DiagnosisPage } from '../pages/DiagnosisPage'
import type { ProductDiagnosis } from '../types/diagnosis'

const mocks = vi.hoisted(() => ({
  listDiagnoses: vi.fn(),
  getDiagnosis: vi.fn(),
  generateDiagnosis: vi.fn(),
  updateDiagnosis: vi.fn(),
}))
const authState = vi.hoisted(() => ({ canWrite: true }))

vi.mock('../api/diagnoses', () => ({
  listDiagnoses: mocks.listDiagnoses,
  getDiagnosis: mocks.getDiagnosis,
  generateDiagnosis: mocks.generateDiagnosis,
  updateDiagnosis: mocks.updateDiagnosis,
}))
vi.mock('../auth/AuthContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../auth/AuthContext')>()
  return { ...actual, useAuth: () => authState }
})
vi.mock('../components/DiagnosisEditModal', async () => {
  const React = await import('react')
  return {
    DiagnosisEditModal: ({ open, onCancel, onSubmit }: {
      open: boolean
      onCancel: () => void
      onSubmit: (data: { positioning: string }) => Promise<void>
    }) => {
      const [error, setError] = React.useState('')
      if (!open) return null
      return React.createElement(
        'section',
        { role: 'dialog', 'aria-label': '编辑商品诊断' },
        React.createElement('button', {
          onClick: async () => {
            try {
              await onSubmit({ positioning: '人工编辑后的定位' })
            } catch (reason) {
              setError(reason instanceof Error ? reason.message : '保存失败')
            }
          },
        }, '保存修改'),
        React.createElement('button', { onClick: onCancel }, '取消'),
        error && React.createElement('div', null, error),
      )
    },
  }
})

const diagnosis: ProductDiagnosis = {
  id: 101,
  product_id: 20,
  source_type: 'mock_ai',
  positioning: '面向通勤用户的轻量实用商品',
  price_band: '中等价格带',
  audience_insights: ['重视便携', '关注性价比'],
  pain_points: ['携带不便', '选择成本高'],
  selling_point_analysis: ['轻量卖点明确'],
  risks: ['竞品样本有限'],
  recommendations: ['补充产品参数'],
  provider_name: 'mock_llm',
  model_name: 'mock-product-diagnosis',
  usage_json: null,
  input_context_json: {
    product: { name: '移动电源', platform: 'taobao', category: '数码', price: '99.00', target_audience: '通勤用户' },
    competitors: [],
  },
  raw_output: '{"mock":true}',
  created_at: '2026-09-16T10:00:00Z',
  updated_at: '2026-09-16T10:00:00Z',
}
const newerDiagnosis: ProductDiagnosis = {
  ...diagnosis,
  id: 102,
  positioning: '最新诊断定位',
  created_at: '2026-09-17T10:00:00Z',
}

function page<T>(items: T[]) {
  return { items, total: items.length, page: 1, page_size: 20 }
}

function renderPage() {
  return render(
    <AntdApp>
      <DiagnosisPage productId={20} />
    </AntdApp>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  authState.canWrite = true
  mocks.listDiagnoses.mockResolvedValue(page([diagnosis]))
  mocks.getDiagnosis.mockResolvedValue(diagnosis)
})

describe('Product diagnosis frontend', () => {
  it('shows an explicit empty state', async () => {
    mocks.listDiagnoses.mockResolvedValue(page([]))
    renderPage()
    expect(await screen.findByText('当前商品还没有诊断结果')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /生成商品诊断/ })).toBeInTheDocument()
  })

  it('shows diagnosis history latest first and loads detail', async () => {
    mocks.listDiagnoses.mockResolvedValue(page([newerDiagnosis, diagnosis]))
    mocks.getDiagnosis.mockImplementation(async (_productId: number, id: number) => id === 102 ? newerDiagnosis : diagnosis)
    renderPage()
    expect((await screen.findAllByText('最新诊断定位')).length).toBeGreaterThan(0)
    expect(await screen.findByText('诊断详情')).toBeInTheDocument()
    expect(screen.getByText('AI Provider：mock_llm')).toBeInTheDocument()
    expect(mocks.getDiagnosis).toHaveBeenCalledWith(20, 102)
  })

  it('renders structured arrays as readable list items', async () => {
    renderPage()
    expect(await screen.findByText('携带不便')).toBeInTheDocument()
    expect(screen.getByText('选择成本高')).toBeInTheDocument()
    expect(screen.getByText('补充产品参数')).toBeInTheDocument()
    expect(screen.queryByText(/\[.*携带不便/)).not.toBeInTheDocument()
  })

  it('shows generation loading and disables repeated requests', async () => {
    let resolveGeneration: ((value: ProductDiagnosis) => void) | undefined
    mocks.generateDiagnosis.mockReturnValue(new Promise((resolve) => { resolveGeneration = resolve }))
    renderPage()
    const button = await screen.findByRole('button', { name: /生成商品诊断/ })
    fireEvent.click(button)
    expect(button).toHaveAttribute('disabled')
    expect(await screen.findByText('生成说明')).toBeInTheDocument()
    resolveGeneration?.(newerDiagnosis)
  })

  it('generates successfully, refreshes history and selects the new detail', async () => {
    mocks.generateDiagnosis.mockResolvedValue(newerDiagnosis)
    mocks.listDiagnoses.mockResolvedValue(page([newerDiagnosis, diagnosis]))
    mocks.getDiagnosis.mockImplementation(async (_productId: number, id: number) => id === 102 ? newerDiagnosis : diagnosis)
    renderPage()
    expect(await screen.findByText('诊断 #102')).toBeInTheDocument()
    const listCallsBeforeGenerate = mocks.listDiagnoses.mock.calls.length
    fireEvent.click(await screen.findByRole('button', { name: /生成商品诊断/ }))
    expect((await screen.findAllByText('最新诊断定位')).length).toBeGreaterThan(0)
    await waitFor(() => expect(mocks.generateDiagnosis).toHaveBeenCalledWith(20))
    await waitFor(() => expect(mocks.listDiagnoses.mock.calls.length).toBeGreaterThan(listCallsBeforeGenerate))
    expect(screen.getByText('商品定位')).toBeInTheDocument()
  })

  it.each([
    ['llm_timeout_error', '模型请求超时'],
    ['invalid_llm_output', '模型输出格式不正确'],
  ])('shows safe provider error %s', async (code, message) => {
    mocks.generateDiagnosis.mockRejectedValue(new ApiError(502, code, message))
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /生成商品诊断/ }))
    expect(await screen.findByText(message)).toBeInTheDocument()
    expect(screen.queryByText(/Authorization|API Key|traceback/i)).not.toBeInTheDocument()
  })

  it('allows admin/operator to edit diagnosis and sends only changed fields', async () => {
    mocks.updateDiagnosis.mockResolvedValue({ ...diagnosis, positioning: '人工编辑后的定位' })
    renderPage()
    expect(await screen.findByText('面向通勤用户的轻量实用商品')).toBeInTheDocument()
    expect(await screen.findByText('诊断详情')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /编辑诊断/ }))
    fireEvent.click(screen.getByRole('button', { name: '保存修改' }))
    await waitFor(() => expect(mocks.updateDiagnosis).toHaveBeenCalledWith(20, 101, { positioning: '人工编辑后的定位' }))
    expect((await screen.findAllByText('人工编辑后的定位')).length).toBeGreaterThan(0)
  })

  it('shows edit validation errors without leaking internals', async () => {
    mocks.updateDiagnosis.mockRejectedValue(new ApiError(422, 'http_422', '提交内容未通过校验', { positioning: '定位不能为空' }))
    renderPage()
    await screen.findByText('面向通勤用户的轻量实用商品')
    await screen.findByText('诊断详情')
    fireEvent.click(screen.getByRole('button', { name: /编辑诊断/ }))
    fireEvent.click(screen.getByRole('button', { name: '保存修改' }))
    expect(await screen.findByText('提交内容未通过校验')).toBeInTheDocument()
    expect(screen.queryByText(/password|Authorization|stack trace/i)).not.toBeInTheDocument()
  })

  it('keeps viewer read-only', async () => {
    authState.canWrite = false
    renderPage()
    await screen.findByText('面向通勤用户的轻量实用商品')
    expect(screen.queryByRole('button', { name: /生成商品诊断/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /编辑诊断/ })).not.toBeInTheDocument()
  })

  it('shows product diagnosis 404 safely', async () => {
    mocks.listDiagnoses.mockRejectedValue(new ApiError(404, 'product_not_found', '当前商品不存在'))
    renderPage()
    expect(await screen.findByText('当前商品不存在')).toBeInTheDocument()
  })

  it('shows a diagnosis detail 404 and provides retry', async () => {
    mocks.getDiagnosis.mockRejectedValue(new ApiError(404, 'product_diagnosis_not_found', '诊断记录不存在'))
    renderPage()
    expect(await screen.findByText('诊断记录不存在')).toBeInTheDocument()
    expect(screen.getByText('重试')).toBeInTheDocument()
  })
})
