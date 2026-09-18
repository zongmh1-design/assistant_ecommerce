import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { App as AntdApp } from 'antd'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import { CreativePlansPage } from '../pages/CreativePlansPage'
import { GenerationJobsPage } from '../pages/GenerationJobsPage'
import { AssetsPage } from '../pages/AssetsPage'
import type { CreativePlan } from '../types/creativePlan'
import type { GenerationJob, GenerationJobDetail } from '../types/generationJob'
import type { GeneratedAsset } from '../types/asset'

const creativeMocks = vi.hoisted(() => ({
  listCreativePlans: vi.fn(),
  getCreativePlan: vi.fn(),
  generateMainImagePlans: vi.fn(),
  generateVideoScripts: vi.fn(),
  updateCreativePlan: vi.fn(),
  createImageGenerationJob: vi.fn(),
  createVideoGenerationJob: vi.fn(),
}))
const jobMocks = vi.hoisted(() => ({
  listGenerationJobs: vi.fn(),
  getGenerationJob: vi.fn(),
  runGenerationJob: vi.fn(),
  retryGenerationJob: vi.fn(),
  cancelGenerationJob: vi.fn(),
}))
const assetMocks = vi.hoisted(() => ({
  listGeneratedAssets: vi.fn(),
  getGeneratedAsset: vi.fn(),
  syncGeneratedAssets: vi.fn(),
  updateGeneratedAsset: vi.fn(),
}))
const authState = vi.hoisted(() => ({ canWrite: true }))

vi.mock('../api/creativePlans', () => ({
  listCreativePlans: creativeMocks.listCreativePlans,
  getCreativePlan: creativeMocks.getCreativePlan,
  generateMainImagePlans: creativeMocks.generateMainImagePlans,
  generateVideoScripts: creativeMocks.generateVideoScripts,
  updateCreativePlan: creativeMocks.updateCreativePlan,
}))
vi.mock('../api/generationJobs', () => ({
  createImageGenerationJob: creativeMocks.createImageGenerationJob,
  createVideoGenerationJob: creativeMocks.createVideoGenerationJob,
  listGenerationJobs: jobMocks.listGenerationJobs,
  getGenerationJob: jobMocks.getGenerationJob,
  runGenerationJob: jobMocks.runGenerationJob,
  retryGenerationJob: jobMocks.retryGenerationJob,
  cancelGenerationJob: jobMocks.cancelGenerationJob,
}))
vi.mock('../api/assets', () => ({
  listGeneratedAssets: assetMocks.listGeneratedAssets,
  getGeneratedAsset: assetMocks.getGeneratedAsset,
  syncGeneratedAssets: assetMocks.syncGeneratedAssets,
  updateGeneratedAsset: assetMocks.updateGeneratedAsset,
}))
vi.mock('../auth/AuthContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../auth/AuthContext')>()
  return { ...actual, useAuth: () => authState }
})
vi.mock('../components/CreativePlanEditModal', async () => {
  const React = await import('react')
  return {
    CreativePlanEditModal: ({ open, onCancel, onSubmit }: { open: boolean; onCancel: () => void; onSubmit: (data: { title: string }) => Promise<void> }) => {
      if (!open) return null
      return React.createElement('section', { role: 'dialog', 'aria-label': '编辑创意方案' },
        React.createElement('button', { onClick: async () => { await onSubmit({ title: '人工修改方案' }) } }, '保存创意方案'),
        React.createElement('button', { onClick: onCancel }, '取消'))
    },
  }
})
vi.mock('../components/AssetReviewModal', async () => {
  const React = await import('react')
  return {
    AssetReviewModal: ({ open, onCancel, onSubmit }: { open: boolean; onCancel: () => void; onSubmit: (data: { review_status: 'approved' }) => Promise<void> }) => {
      if (!open) return null
      return React.createElement('section', { role: 'dialog', 'aria-label': '审核素材' },
        React.createElement('button', { onClick: async () => { await onSubmit({ review_status: 'approved' }) } }, '保存审核'),
        React.createElement('button', { onClick: onCancel }, '取消'))
    },
  }
})

const mainPlan: CreativePlan = {
  id: 11,
  product_id: 20,
  plan_type: 'main_image',
  title: '轻量通勤主图',
  content_json: { visual_structure: ['左侧产品主体'], core_copy: ['通勤随身充'], highlighted_selling_points: ['轻量'] },
  rationale_text: '突出便携',
  status: 'draft',
  provider_name: 'mock_llm',
  model_name: 'mock-main-image',
  usage_json: null,
  input_context_json: {},
  created_at: '2026-09-17T01:00:00Z',
  updated_at: '2026-09-17T01:00:00Z',
}
const videoPlan: CreativePlan = {
  ...mainPlan,
  id: 12,
  plan_type: 'video_script',
  title: '通勤短视频脚本',
  content_json: { opening_hook: '电量告急怎么办？', storyboard: [{ scene_no: 1, visual: '展示产品', duration_hint: '3秒', voiceover: '随手一充' }], voiceover: ['随手一充'], conversion_cta: '立即了解' },
}
const selectedImagePlan: CreativePlan = { ...mainPlan, id: 13, status: 'selected', title: '已采用主图' }

const pendingJob: GenerationJob = {
  id: 31, product_id: 20, creative_plan_id: 13, job_kind: 'image', job_status: 'pending', attempts: 0, max_attempts: 3,
  locked_at: null, locked_by: null, next_run_at: null, result_json: null, error_message: null, started_at: null, finished_at: null,
  created_at: '2026-09-17T01:00:00Z', updated_at: '2026-09-17T01:00:00Z',
}
const failedJob: GenerationJob = { ...pendingJob, id: 32, job_status: 'failed', attempts: 1, error_message: 'Mock generator failed' }
const runningJob: GenerationJob = { ...pendingJob, id: 33, job_status: 'running', attempts: 1 }
const jobDetail: GenerationJobDetail = { ...pendingJob, job_status: 'succeeded', attempts: 1, result_json: { asset_type: 'image', url: 'mock://images/job-31.png', width: 1024, height: 1024 }, events: [
  { id: 1, job_id: 31, event_type: 'created', event_message: '任务已创建', created_at: '2026-09-17T01:00:00Z' },
  { id: 2, job_id: 31, event_type: 'started', event_message: '任务开始运行', created_at: '2026-09-17T01:01:00Z' },
  { id: 3, job_id: 31, event_type: 'succeeded', event_message: '任务运行成功', created_at: '2026-09-17T01:02:00Z' },
] }
const asset: GeneratedAsset = {
  id: 41, product_id: 20, creative_plan_id: 13, generation_job_id: 31, asset_type: 'image', asset_url: 'mock://images/job-31.png', model_name: 'mock_image_generator', width: 1024, height: 1024, duration_sec: null,
  review_status: 'pending', version_no: 1, usage_scene: null, score: null, tags_json: ['主图'], remark: null, created_at: '2026-09-17T01:00:00Z', updated_at: '2026-09-17T01:00:00Z',
}

function page<T>(items: T[]) { return { items, total: items.length, page: 1, page_size: 20 } }
function renderPage(element: React.ReactElement) { return render(<AntdApp><MemoryRouter>{element}</MemoryRouter></AntdApp>) }

beforeEach(() => {
  vi.clearAllMocks()
  authState.canWrite = true
  creativeMocks.listCreativePlans.mockImplementation(async (_id: number, query: { plan_type?: string }) => page(query.plan_type === 'video_script' ? [videoPlan] : [mainPlan]))
  creativeMocks.getCreativePlan.mockResolvedValue(mainPlan)
  creativeMocks.generateMainImagePlans.mockResolvedValue([{ ...mainPlan, id: 14 }, { ...mainPlan, id: 15 }, { ...mainPlan, id: 16 }])
  creativeMocks.generateVideoScripts.mockResolvedValue([{ ...videoPlan, id: 17 }, { ...videoPlan, id: 18 }, { ...videoPlan, id: 19 }])
  creativeMocks.updateCreativePlan.mockResolvedValue(mainPlan)
  creativeMocks.createImageGenerationJob.mockResolvedValue(pendingJob)
  creativeMocks.createVideoGenerationJob.mockResolvedValue({ ...pendingJob, job_kind: 'video' })
  jobMocks.listGenerationJobs.mockResolvedValue(page([pendingJob]))
  jobMocks.getGenerationJob.mockResolvedValue(jobDetail)
  jobMocks.runGenerationJob.mockResolvedValue(jobDetail)
  jobMocks.retryGenerationJob.mockResolvedValue({ ...jobDetail, job_status: 'pending' })
  jobMocks.cancelGenerationJob.mockResolvedValue({ ...pendingJob, job_status: 'cancelled' })
  assetMocks.listGeneratedAssets.mockResolvedValue(page([asset]))
  assetMocks.getGeneratedAsset.mockResolvedValue(asset)
  assetMocks.syncGeneratedAssets.mockResolvedValue({ synced_count: 1, skipped_count: 1, failed_count: 1, asset_ids: [41], failures: [{ job_id: 99, code: 'invalid_result', message: '结果格式不完整' }] })
  assetMocks.updateGeneratedAsset.mockResolvedValue({ ...asset, review_status: 'approved' })
})

describe('Creative plans frontend', () => {
  it('renders structured main image content and generates three plans', async () => {
    renderPage(<CreativePlansPage productId={20} />)
    expect(await screen.findByText('左侧产品主体')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /生成主图方案/ }))
    await waitFor(() => expect(creativeMocks.generateMainImagePlans).toHaveBeenCalledWith(20))
    expect(await screen.findByText(/本次已生成 3 条主图方案/)).toBeInTheDocument()
  })

  it('switches to video scripts and renders storyboard fields', async () => {
    renderPage(<CreativePlansPage productId={20} />)
    fireEvent.click(await screen.findByRole('tab', { name: '视频脚本' }))
    expect(await screen.findByText('电量告急怎么办？')).toBeInTheDocument()
    expect(screen.getByText('展示产品')).toBeInTheDocument()
    expect(screen.getByText('立即了解')).toBeInTheDocument()
  })

  it('keeps generation loading disabled and viewer read-only', async () => {
    let resolve: ((value: CreativePlan[]) => void) | undefined
    creativeMocks.generateMainImagePlans.mockReturnValue(new Promise((done) => { resolve = done }))
    const firstRender = renderPage(<CreativePlansPage productId={20} />)
    const generate = await screen.findByRole('button', { name: /生成主图方案/ })
    fireEvent.click(generate)
    expect(generate).toHaveAttribute('disabled')
    resolve?.([mainPlan])
    authState.canWrite = false
    firstRender.unmount()
    renderPage(<CreativePlansPage productId={20} />)
    expect(await screen.findByText('轻量通勤主图')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /生成主图方案/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '采用此方案' })).not.toBeInTheDocument()
  })

  it('selects a plan, creates an image job, and edits through PATCH', async () => {
    creativeMocks.listCreativePlans.mockResolvedValue(page([mainPlan, selectedImagePlan]))
    creativeMocks.getCreativePlan.mockResolvedValue(selectedImagePlan)
    renderPage(<CreativePlansPage productId={20} />)
    expect(await screen.findByText('已采用主图')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '采用此方案' }))
    await waitFor(() => expect(creativeMocks.updateCreativePlan).toHaveBeenCalledWith(20, 11, { status: 'selected' }))
    fireEvent.click(screen.getAllByRole('button', { name: /编辑/ })[0])
    fireEvent.click(await screen.findByRole('button', { name: '保存创意方案' }))
    await waitFor(() => expect(creativeMocks.updateCreativePlan).toHaveBeenCalledWith(20, 11, { title: '人工修改方案' }))
    fireEvent.click(screen.getByRole('button', { name: /创建图片生成任务/ }))
    await waitFor(() => expect(creativeMocks.createImageGenerationJob).toHaveBeenCalledWith(20, 13))
  })

  it('shows safe AI errors', async () => {
    creativeMocks.generateMainImagePlans.mockRejectedValue(new ApiError(502, 'invalid_llm_output', '模型输出格式不正确'))
    renderPage(<CreativePlansPage productId={20} />)
    fireEvent.click(await screen.findByRole('button', { name: /生成主图方案/ }))
    expect(await screen.findByText('模型输出格式不正确')).toBeInTheDocument()
    expect(screen.queryByText(/API Key|Authorization|traceback/i)).not.toBeInTheDocument()
  })
})

describe('Generation jobs frontend', () => {
  it('runs pending job and reloads the job state', async () => {
    renderPage(<GenerationJobsPage productId={20} />)
    fireEvent.click(await screen.findByRole('button', { name: /运行任务/ }))
    await waitFor(() => expect(jobMocks.runGenerationJob).toHaveBeenCalledWith(20, 31))
    expect(jobMocks.getGenerationJob).toHaveBeenCalledWith(20, 31)
    expect(await screen.findByText('任务已执行')).toBeInTheDocument()
  })

  it('offers retry for failed jobs and no fake cancel for running jobs', async () => {
    jobMocks.listGenerationJobs.mockResolvedValue(page([failedJob]))
    renderPage(<GenerationJobsPage productId={20} />)
    fireEvent.click(await screen.findByRole('button', { name: /重试/ }))
    await waitFor(() => expect(jobMocks.retryGenerationJob).toHaveBeenCalledWith(20, 32))
    jobMocks.listGenerationJobs.mockResolvedValue(page([runningJob]))
    renderPage(<GenerationJobsPage productId={20} />)
    expect(await screen.findByText('执行中，当前不支持强制取消')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '取消' })).not.toBeInTheDocument()
  })

  it('shows event timeline and mock result explanation', async () => {
    renderPage(<GenerationJobsPage productId={20} />)
    fireEvent.click(await screen.findByRole('button', { name: /详情/ }))
    expect(await screen.findByText('事件时间线')).toBeInTheDocument()
    expect(screen.getByText('任务运行成功')).toBeInTheDocument()
    expect(screen.getByText(/结果仍需同步到素材库/)).toBeInTheDocument()
  })
})

describe('Generated assets frontend', () => {
  it('syncs assets and keeps partial failures visible', async () => {
    renderPage(<AssetsPage productId={20} />)
    expect(await screen.findByText('Mock Image Asset')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /同步成功任务/ }))
    expect(await screen.findByText(/同步完成：成功 1，跳过 1，失败 1/)).toBeInTheDocument()
    expect(screen.getByText(/结果格式不完整/)).toBeInTheDocument()
  })

  it('allows review update and keeps viewer read-only', async () => {
    const firstRender = renderPage(<AssetsPage productId={20} />)
    await screen.findByText('Mock Image Asset')
    fireEvent.click(screen.getByRole('button', { name: /审核 \/ 编辑/ }))
    fireEvent.click(await screen.findByRole('button', { name: '保存审核' }))
    await waitFor(() => expect(assetMocks.updateGeneratedAsset).toHaveBeenCalledWith(20, 41, { review_status: 'approved' }))
    authState.canWrite = false
    firstRender.unmount()
    renderPage(<AssetsPage productId={20} />)
    await screen.findByText('Mock Image Asset')
    expect(screen.getByText('查看详情')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '同步成功任务' })).not.toBeInTheDocument()
  })
})
