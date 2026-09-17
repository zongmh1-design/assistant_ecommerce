import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { App as AntdApp } from 'antd'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import { AdRecommendationsPage } from '../pages/AdRecommendationsPage'
import { AdExperimentsPage } from '../pages/AdExperimentsPage'
import type { AdRecommendation } from '../types/adRecommendation'
import type { AdExperiment } from '../types/adExperiment'
import type { GeneratedAsset } from '../types/asset'
import type { PromotionLink } from '../types/promotionLink'

const recommendationMocks = vi.hoisted(() => ({
  generateAdRecommendation: vi.fn(),
  listAdRecommendations: vi.fn(),
  getAdRecommendation: vi.fn(),
  updateAdRecommendation: vi.fn(),
  confirmAdRecommendation: vi.fn(),
}))
const experimentMocks = vi.hoisted(() => ({
  generateAdExperiment: vi.fn(),
  listAdExperiments: vi.fn(),
  getAdExperiment: vi.fn(),
  updateAdExperiment: vi.fn(),
  updateAdExperimentStatus: vi.fn(),
}))
const assetMocks = vi.hoisted(() => ({ listGeneratedAssets: vi.fn() }))
const linkMocks = vi.hoisted(() => ({ listPromotionLinks: vi.fn() }))
const authState = vi.hoisted(() => ({ canWrite: true }))

vi.mock('../api/adRecommendations', () => ({
  generateAdRecommendation: recommendationMocks.generateAdRecommendation,
  listAdRecommendations: recommendationMocks.listAdRecommendations,
  getAdRecommendation: recommendationMocks.getAdRecommendation,
  updateAdRecommendation: recommendationMocks.updateAdRecommendation,
  confirmAdRecommendation: recommendationMocks.confirmAdRecommendation,
}))
vi.mock('../api/adExperiments', () => ({
  generateAdExperiment: experimentMocks.generateAdExperiment,
  listAdExperiments: experimentMocks.listAdExperiments,
  getAdExperiment: experimentMocks.getAdExperiment,
  updateAdExperiment: experimentMocks.updateAdExperiment,
  updateAdExperimentStatus: experimentMocks.updateAdExperimentStatus,
}))
vi.mock('../api/assets', () => ({ listGeneratedAssets: assetMocks.listGeneratedAssets }))
vi.mock('../api/promotionLinks', () => ({ listPromotionLinks: linkMocks.listPromotionLinks }))
vi.mock('../auth/AuthContext', () => ({ useAuth: () => authState }))

vi.mock('../components/AdRecommendationDetailDrawer', async () => {
  const React = await import('react')
  return {
    AdRecommendationDetailDrawer: ({
      recommendation,
      open,
      canWrite,
      onEdit,
      onDecision,
      onCreateExperiment,
    }: {
      recommendation: AdRecommendation | null
      open: boolean
      canWrite: boolean
      onClose: () => void
      onEdit: () => void
      onDecision: (value: 'confirmed' | 'rejected') => void
      onCreateExperiment: () => void
    }) => {
      if (!open || !recommendation) return null
      return React.createElement(
        'section',
        { role: 'dialog', 'aria-label': '投放建议详情' },
        React.createElement('h3', null, recommendation.summary_text),
        React.createElement('div', null, recommendation.objective_text),
        React.createElement('div', null, recommendation.audience_segments_json[0]?.segment_name),
        canWrite && recommendation.confirm_status === 'pending'
          ? React.createElement('div', null,
            React.createElement('button', { onClick: onEdit }, '编辑建议'),
            React.createElement('button', { onClick: () => onDecision('confirmed') }, '确认建议'),
            React.createElement('button', { onClick: () => onDecision('rejected') }, '驳回建议'),
          )
          : null,
        canWrite && recommendation.confirm_status === 'confirmed'
          ? React.createElement('button', { onClick: onCreateExperiment }, '创建实验计划')
          : null,
      )
    },
  }
})

vi.mock('../components/AdRecommendationEditModal', async () => {
  const React = await import('react')
  return {
    AdRecommendationEditModal: ({ open, onCancel, onSubmit }: { open: boolean; recommendation: AdRecommendation | null; onCancel: () => void; onSubmit: (value: { summary_text: string }) => Promise<void> }) => open
      ? React.createElement('section', { role: 'dialog', 'aria-label': '编辑投放建议' },
        React.createElement('button', { onClick: async () => { await onSubmit({ summary_text: '人工修改建议' }) } }, '保存投放建议'),
        React.createElement('button', { onClick: onCancel }, '取消'))
      : null,
  }
})

vi.mock('../components/AdRecommendationConfirmationModal', async () => {
  const React = await import('react')
  return {
    AdRecommendationConfirmationModal: ({ open, decision, onCancel, onSubmit }: { open: boolean; decision: 'confirmed' | 'rejected' | null; onCancel: () => void; onSubmit: (value: { confirm_status: 'confirmed' | 'rejected'; confirm_remark: string }) => Promise<void> }) => open && decision
      ? React.createElement('section', { role: 'dialog', 'aria-label': '人工确认投放建议' },
        React.createElement('button', { onClick: async () => { await onSubmit({ confirm_status: decision, confirm_remark: '人工审核备注' }) } }, decision === 'confirmed' ? '提交确认' : '提交驳回'),
        React.createElement('button', { onClick: onCancel }, '取消'))
      : null,
  }
})

vi.mock('../components/AdExperimentFormModal', async () => {
  const React = await import('react')
  return {
    AdExperimentFormModal: ({ open, experiment, recommendationId, recommendations, assets, links, onCancel, onGenerate, onUpdate }: {
      open: boolean
      experiment: AdExperiment | null
      recommendationId?: number
      recommendations: AdRecommendation[]
      assets: GeneratedAsset[]
      links: PromotionLink[]
      onCancel: () => void
      onGenerate: (value: { recommendation_id: number; related_asset_id?: number; related_link_id?: number }) => Promise<void>
      onUpdate: (value: { experiment_name: string }) => Promise<void>
    }) => {
      if (!open) return null
      if (experiment) {
        return React.createElement('section', { role: 'dialog', 'aria-label': '编辑实验计划' },
          React.createElement('button', { onClick: async () => { await onUpdate({ experiment_name: '人工修改实验' }) } }, '保存实验计划'),
          React.createElement('button', { onClick: onCancel }, '取消'))
      }
      return React.createElement('section', { role: 'dialog', 'aria-label': '生成实验计划' },
        React.createElement('div', null, `可选建议 ${recommendations.length}，素材 ${assets.length}，链接 ${links.length}`),
        React.createElement('button', {
          onClick: async () => { await onGenerate({ recommendation_id: recommendationId ?? recommendations[0].id, related_asset_id: assets[0]?.id, related_link_id: links[0]?.id }) },
        }, '提交生成实验计划'),
        React.createElement('button', { onClick: onCancel }, '取消'))
    },
  }
})

vi.mock('../components/AdExperimentDetailDrawer', async () => {
  const React = await import('react')
  return {
    AdExperimentDetailDrawer: ({ experiment, open, canWrite, onEdit, onStatus }: { experiment: AdExperiment | null; open: boolean; canWrite: boolean; onClose: () => void; onEdit: () => void; onStatus: (value: AdExperiment['experiment_status']) => void }) => {
      if (!open || !experiment) return null
      return React.createElement('section', { role: 'dialog', 'aria-label': '实验计划详情' },
        React.createElement('h3', null, experiment.experiment_name),
        React.createElement('div', null, experiment.hypothesis_text),
        canWrite && experiment.experiment_status === 'draft' ? React.createElement('div', null,
          React.createElement('button', { onClick: onEdit }, '编辑实验计划'),
          React.createElement('button', { onClick: () => onStatus('confirmed') }, '确认实验'),
          React.createElement('button', { onClick: () => onStatus('cancelled') }, '取消实验'),
        ) : null,
        canWrite && experiment.experiment_status === 'confirmed' ? React.createElement('button', { onClick: () => onStatus('running') }, '开始执行') : null,
        canWrite && experiment.experiment_status === 'running' ? React.createElement('div', null,
          React.createElement('button', { onClick: () => onStatus('finished') }, '标记已结束'),
          React.createElement('button', { onClick: () => onStatus('cancelled') }, '取消实验'),
        ) : null,
      )
    },
  }
})

const recommendation: AdRecommendation = {
  id: 51,
  product_id: 20,
  summary_text: '优先测试轻量卖点',
  objective_text: '验证点击意愿',
  audience_segments_json: [{ segment_name: '通勤用户', description: '需要便携设备的人群', rationale: '与商品定位匹配' }],
  budget_plan_json: { total_budget: '100.00', currency: 'CNY', allocation: [{ channel_or_test: '主图测试', amount: '100.00', rationale: '先验证素材' }], rationale: '小预算验证' },
  creative_tests_json: [{ test_name: '主图 A/B', asset_reference: '主图方案 A', hypothesis: '轻量卖点更吸引点击', success_metric: '点击率' }],
  bid_strategy_json: { strategy_name: '保守测试', rationale: '控制风险', constraints: ['不承诺收益'] },
  risk_controls_json: [{ risk: '预算浪费', mitigation: '小额开始' }],
  next_steps_json: ['记录真实表现'],
  confirm_status: 'pending',
  confirmed_by: null,
  confirmed_at: null,
  confirm_remark: null,
  provider_name: 'mock',
  model_name: 'mock-ad',
  usage_json: null,
  input_context_json: {},
  created_at: '2026-09-17T03:00:00Z',
  updated_at: '2026-09-17T03:00:00Z',
}
const confirmedRecommendation: AdRecommendation = { ...recommendation, id: 52, confirm_status: 'confirmed', confirmed_by: 1, confirmed_at: '2026-09-17T03:10:00Z' }
const rejectedRecommendation: AdRecommendation = { ...recommendation, id: 54, confirm_status: 'rejected', confirmed_by: 1, confirmed_at: '2026-09-17T03:10:00Z', confirm_remark: '暂不采用' }
const experiment: AdExperiment = {
  id: 61,
  product_id: 20,
  ad_recommendation_id: 52,
  related_asset_id: 71,
  related_link_id: 81,
  experiment_name: '轻量卖点素材测试',
  target_text: '验证主图点击意愿',
  audience_text: '通勤用户',
  budget_amount: '100.00',
  success_metric_text: '观察点击率',
  hypothesis_text: '突出轻量卖点会提升点击意愿',
  experiment_status: 'draft',
  provider_name: 'mock',
  model_name: 'mock-experiment',
  usage_json: null,
  input_context_json: {},
  created_at: '2026-09-17T03:20:00Z',
  updated_at: '2026-09-17T03:20:00Z',
}
const asset: GeneratedAsset = {
  id: 71, product_id: 20, creative_plan_id: 11, generation_job_id: 31, asset_type: 'image', asset_url: 'mock://image/71.png', model_name: 'mock', width: 1024, height: 1024, duration_sec: null, review_status: 'approved', version_no: 1, usage_scene: '主图', score: 90, tags_json: ['轻量'], remark: null, created_at: '2026-09-17T03:00:00Z', updated_at: '2026-09-17T03:00:00Z',
}
const link: PromotionLink = {
  id: 81, product_id: 20, link_name: '主图测试链接', target_url: 'https://example.com/p/20', tracking_code: 'demo81', utm_json: {}, status: 'active', click_count: 2, scene_text: '素材测试', created_at: '2026-09-17T03:00:00Z', updated_at: '2026-09-17T03:00:00Z',
}

function page<T>(items: T[]) { return { items, total: items.length, page: 1, page_size: 20 } }
function renderPage(element: React.ReactElement, initialEntries = ['/']) {
  return render(<AntdApp><MemoryRouter initialEntries={initialEntries}>{element}</MemoryRouter></AntdApp>)
}

beforeEach(() => {
  vi.clearAllMocks()
  authState.canWrite = true
  recommendationMocks.listAdRecommendations.mockResolvedValue(page([recommendation]))
  recommendationMocks.getAdRecommendation.mockResolvedValue(recommendation)
  recommendationMocks.generateAdRecommendation.mockResolvedValue({ ...recommendation, id: 53 })
  recommendationMocks.updateAdRecommendation.mockResolvedValue({ ...recommendation, summary_text: '人工修改建议' })
  recommendationMocks.confirmAdRecommendation.mockImplementation(async (_productId: number, _id: number, value: { confirm_status: 'confirmed' | 'rejected'; confirm_remark?: string | null }) => ({ ...recommendation, confirm_status: value.confirm_status, confirm_remark: value.confirm_remark ?? null, confirmed_by: 1, confirmed_at: '2026-09-17T03:30:00Z' }))
  experimentMocks.listAdExperiments.mockResolvedValue(page([experiment]))
  experimentMocks.getAdExperiment.mockResolvedValue(experiment)
  experimentMocks.generateAdExperiment.mockResolvedValue({ ...experiment, id: 62 })
  experimentMocks.updateAdExperiment.mockResolvedValue({ ...experiment, experiment_name: '人工修改实验' })
  experimentMocks.updateAdExperimentStatus.mockImplementation(async (_productId: number, _id: number, value: { experiment_status: AdExperiment['experiment_status'] }) => ({ ...experiment, experiment_status: value.experiment_status }))
  assetMocks.listGeneratedAssets.mockResolvedValue(page([asset]))
  linkMocks.listPromotionLinks.mockResolvedValue(page([link]))
})

describe('AdRecommendation frontend', () => {
  it('renders structured history/detail and generates a new recommendation', async () => {
    renderPage(<AdRecommendationsPage productId={20} />)
    expect(await screen.findByText('优先测试轻量卖点')).toBeInTheDocument()
    fireEvent.click(screen.getByText('投放建议 #51'))
    expect(await screen.findByText('通勤用户')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /生成投放建议/ }))
    await waitFor(() => expect(recommendationMocks.generateAdRecommendation).toHaveBeenCalledWith(20))
  })

  it('supports pending edit and human confirmation without accepting confirmed_by from the UI', async () => {
    renderPage(<AdRecommendationsPage productId={20} />)
    fireEvent.click(await screen.findByText('投放建议 #51'))
    fireEvent.click(await screen.findByRole('button', { name: '编辑建议' }))
    fireEvent.click(await screen.findByRole('button', { name: '保存投放建议' }))
    await waitFor(() => expect(recommendationMocks.updateAdRecommendation).toHaveBeenCalledWith(20, 51, { summary_text: '人工修改建议' }))
    fireEvent.click(screen.getByRole('button', { name: '确认建议' }))
    fireEvent.click(await screen.findByRole('button', { name: '提交确认' }))
    await waitFor(() => expect(recommendationMocks.confirmAdRecommendation).toHaveBeenCalledWith(20, 51, { confirm_status: 'confirmed', confirm_remark: '人工审核备注' }))
    expect(recommendationMocks.confirmAdRecommendation.mock.calls[0][2]).not.toHaveProperty('confirmed_by')
  }, 30000)

  it('supports rejection and freezes terminal recommendations', async () => {
    const pendingRender = renderPage(<AdRecommendationsPage productId={20} />)
    fireEvent.click(await screen.findByText('投放建议 #51'))
    fireEvent.click(await screen.findByRole('button', { name: '驳回建议' }))
    fireEvent.click(await screen.findByRole('button', { name: '提交驳回' }))
    await waitFor(() => expect(recommendationMocks.confirmAdRecommendation).toHaveBeenCalledWith(20, 51, { confirm_status: 'rejected', confirm_remark: '人工审核备注' }))

    pendingRender.unmount()
    recommendationMocks.listAdRecommendations.mockResolvedValue(page([rejectedRecommendation]))
    recommendationMocks.getAdRecommendation.mockResolvedValue(rejectedRecommendation)
    const terminalRender = renderPage(<AdRecommendationsPage productId={20} />)
    fireEvent.click(await screen.findByText('投放建议 #54'))
    expect((await screen.findAllByText('优先测试轻量卖点')).length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: /编辑建议|确认建议|驳回建议|创建实验计划/ })).not.toBeInTheDocument()
    terminalRender.unmount()
  }, 30000)

  it('shows safe provider errors and keeps viewer read-only', async () => {
    recommendationMocks.generateAdRecommendation.mockRejectedValue(new ApiError(502, 'invalid_llm_output', '模型输出格式不正确'))
    const firstRender = renderPage(<AdRecommendationsPage productId={20} />)
    fireEvent.click(await screen.findByRole('button', { name: /生成投放建议/ }))
    expect(await screen.findByText('模型输出格式不正确')).toBeInTheDocument()
    expect(screen.queryByText(/API Key|Authorization|traceback/i)).not.toBeInTheDocument()
    firstRender.unmount()
    authState.canWrite = false
    renderPage(<AdRecommendationsPage productId={20} />)
    expect(await screen.findByText('优先测试轻量卖点')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /生成投放建议/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByText('投放建议 #51'))
    expect(await screen.findByText('通勤用户')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /编辑建议|确认建议|驳回建议/ })).not.toBeInTheDocument()
  }, 30000)

  it('disables recommendation generation while the AI request is pending', async () => {
    let resolve: ((value: AdRecommendation) => void) | undefined
    recommendationMocks.generateAdRecommendation.mockReturnValue(new Promise((done) => { resolve = done }))
    renderPage(<AdRecommendationsPage productId={20} />)
    const button = await screen.findByRole('button', { name: /生成投放建议/ })
    fireEvent.click(button)
    expect(button).toHaveAttribute('disabled')
    resolve?.({ ...recommendation, id: 55 })
    await waitFor(() => expect(recommendationMocks.generateAdRecommendation).toHaveBeenCalledWith(20))
  })

  it('shows explicit empty states for recommendations and experiments', async () => {
    recommendationMocks.listAdRecommendations.mockResolvedValue(page([]))
    const recommendationRender = renderPage(<AdRecommendationsPage productId={20} />)
    expect(await screen.findByText('当前商品暂无投放建议')).toBeInTheDocument()
    recommendationRender.unmount()

    experimentMocks.listAdExperiments.mockResolvedValue(page([]))
    renderPage(<AdExperimentsPage productId={20} />)
    expect(await screen.findByText('当前商品暂无实验计划')).toBeInTheDocument()
  })
})

describe('AdExperiment frontend', () => {
  it('loads only confirmed recommendations and generates an experiment with approved asset/link', async () => {
    recommendationMocks.listAdRecommendations.mockResolvedValue(page([confirmedRecommendation]))
    renderPage(<AdExperimentsPage productId={20} />, ['/products/20/ad-experiments?recommendation_id=52'])
    expect(await screen.findByText('轻量卖点素材测试')).toBeInTheDocument()
    expect(recommendationMocks.listAdRecommendations).toHaveBeenCalledWith(20, { confirm_status: 'confirmed', page: 1, page_size: 100 })
    fireEvent.click(screen.getByRole('button', { name: /生成实验计划/ }))
    expect(await screen.findByText('可选建议 1，素材 1，链接 1')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '提交生成实验计划' }))
    await waitFor(() => expect(experimentMocks.generateAdExperiment).toHaveBeenCalledWith(20, { recommendation_id: 52, related_asset_id: 71, related_link_id: 81 }))
    expect(experimentMocks.generateAdExperiment.mock.calls[0][1]).not.toHaveProperty('confirmed_by')
  })

  it('edits draft content and uses independent status transitions', async () => {
    renderPage(<AdExperimentsPage productId={20} />)
    fireEvent.click(await screen.findByRole('button', { name: /查看详情/ }))
    fireEvent.click(await screen.findByRole('button', { name: '编辑实验计划' }))
    fireEvent.click(await screen.findByRole('button', { name: '保存实验计划' }))
    await waitFor(() => expect(experimentMocks.updateAdExperiment).toHaveBeenCalledWith(20, 61, { experiment_name: '人工修改实验' }))
    fireEvent.click(screen.getByRole('button', { name: /查看详情/ }))
    expect(await screen.findByRole('button', { name: '确认实验' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '确认实验' }))
    await waitFor(() => expect(experimentMocks.updateAdExperimentStatus).toHaveBeenCalledWith(20, 61, { experiment_status: 'confirmed' }))
  }, 30000)

  it('allows confirmed to running, but viewer has no write controls', async () => {
    experimentMocks.listAdExperiments.mockResolvedValue(page([{ ...experiment, experiment_status: 'confirmed' }]))
    experimentMocks.getAdExperiment.mockResolvedValue({ ...experiment, experiment_status: 'confirmed' })
    const firstRender = renderPage(<AdExperimentsPage productId={20} />)
    fireEvent.click(await screen.findByRole('button', { name: /查看详情/ }))
    fireEvent.click(await screen.findByRole('button', { name: '开始执行' }))
    await waitFor(() => expect(experimentMocks.updateAdExperimentStatus).toHaveBeenCalledWith(20, 61, { experiment_status: 'running' }))
    firstRender.unmount()
    authState.canWrite = false
    renderPage(<AdExperimentsPage productId={20} />)
    expect(await screen.findByText('轻量卖点素材测试')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /生成实验计划/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /查看详情/ }))
    expect(await screen.findByText('突出轻量卖点会提升点击意愿')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /开始执行|确认实验|编辑实验计划/ })).not.toBeInTheDocument()
  }, 30000)

  it('supports draft cancellation and running terminal transitions', async () => {
    renderPage(<AdExperimentsPage productId={20} />)
    fireEvent.click(await screen.findByRole('button', { name: /查看详情/ }))
    fireEvent.click(await screen.findByRole('button', { name: '取消实验' }))
    await waitFor(() => expect(experimentMocks.updateAdExperimentStatus).toHaveBeenCalledWith(20, 61, { experiment_status: 'cancelled' }))

    const running = { ...experiment, experiment_status: 'running' as const }
    experimentMocks.listAdExperiments.mockResolvedValue(page([running]))
    experimentMocks.getAdExperiment.mockResolvedValue(running)
    const runningRender = renderPage(<AdExperimentsPage productId={20} />)
    fireEvent.click(await screen.findByRole('button', { name: /查看详情/ }))
    fireEvent.click(await screen.findByRole('button', { name: '标记已结束' }))
    await waitFor(() => expect(experimentMocks.updateAdExperimentStatus).toHaveBeenCalledWith(20, 61, { experiment_status: 'finished' }))
    runningRender.unmount()
  }, 30000)

  it('disables experiment generation while the AI request is pending and freezes finished plans', async () => {
    let resolve: ((value: AdExperiment) => void) | undefined
    experimentMocks.generateAdExperiment.mockReturnValue(new Promise((done) => { resolve = done }))
    renderPage(<AdExperimentsPage productId={20} />)
    expect(await screen.findByText('轻量卖点素材测试')).toBeInTheDocument()
    const generate = await screen.findByRole('button', { name: /生成实验计划/ })
    fireEvent.click(generate)
    fireEvent.click(await screen.findByRole('button', { name: '提交生成实验计划' }))
    expect(generate).toHaveAttribute('disabled')
    resolve?.({ ...experiment, id: 63 })
    await waitFor(() => expect(experimentMocks.generateAdExperiment).toHaveBeenCalled())

    experimentMocks.listAdExperiments.mockResolvedValue(page([{ ...experiment, experiment_status: 'finished' }]))
    experimentMocks.getAdExperiment.mockResolvedValue({ ...experiment, experiment_status: 'finished' })
    const terminalRender = renderPage(<AdExperimentsPage productId={20} />)
    fireEvent.click(await screen.findByRole('button', { name: /查看详情/ }))
    expect((await screen.findAllByText('突出轻量卖点会提升点击意愿')).length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: /编辑实验计划|确认实验|开始执行|标记已结束|取消实验/ })).not.toBeInTheDocument()
    terminalRender.unmount()
  }, 30000)
})
