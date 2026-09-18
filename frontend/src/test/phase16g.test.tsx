import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { App as AntdApp } from 'antd'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import { PerformancePage } from '../pages/PerformancePage'
import { ReviewReportsPage } from '../pages/ReviewReportsPage'
import type { AdExperiment } from '../types/adExperiment'
import type { CreativePlan } from '../types/creativePlan'
import type { GeneratedAsset } from '../types/asset'
import type { PerformanceRecord } from '../types/performanceRecord'
import type { PerformanceImportPreview, PerformanceImportResult } from '../types/performanceImport'
import type { PromotionLink } from '../types/promotionLink'
import type { ReviewReport } from '../types/reviewReport'

const performanceMocks = vi.hoisted(() => ({
  list: vi.fn(),
  create: vi.fn(),
  get: vi.fn(),
  update: vi.fn(),
}))
const importMocks = vi.hoisted(() => ({
  preview: vi.fn(),
  importRows: vi.fn(),
  download: vi.fn(),
}))
const reviewMocks = vi.hoisted(() => ({
  generate: vi.fn(),
  list: vi.fn(),
  get: vi.fn(),
  update: vi.fn(),
}))
const selectorMocks = vi.hoisted(() => ({
  creativePlans: vi.fn(),
  assets: vi.fn(),
  links: vi.fn(),
  experiments: vi.fn(),
}))
const authState = vi.hoisted(() => ({ canWrite: true }))

vi.mock('../api/performanceRecords', () => ({
  listPerformanceRecords: performanceMocks.list,
  createPerformanceRecord: performanceMocks.create,
  getPerformanceRecord: performanceMocks.get,
  updatePerformanceRecord: performanceMocks.update,
}))
vi.mock('../api/performanceImports', () => ({
  previewPerformanceImport: importMocks.preview,
  importPerformanceRecords: importMocks.importRows,
  downloadPerformanceTemplate: importMocks.download,
}))
vi.mock('../api/reviewReports', () => ({
  generateReviewReport: reviewMocks.generate,
  listReviewReports: reviewMocks.list,
  getReviewReport: reviewMocks.get,
  updateReviewReport: reviewMocks.update,
}))
vi.mock('../api/creativePlans', () => ({ listCreativePlans: selectorMocks.creativePlans }))
vi.mock('../api/assets', () => ({ listGeneratedAssets: selectorMocks.assets }))
vi.mock('../api/promotionLinks', () => ({ listPromotionLinks: selectorMocks.links }))
vi.mock('../api/adExperiments', () => ({ listAdExperiments: selectorMocks.experiments }))
vi.mock('../auth/AuthContext', () => ({ useAuth: () => authState }))

vi.mock('../components/PerformanceRecordFormModal', async () => {
  const React = await import('react')
  return {
    PerformanceRecordFormModal: ({ open, record, onCreate, onUpdate, onCancel }: { open: boolean; record: PerformanceRecord | null; onCreate: (value: Record<string, unknown>) => Promise<void>; onUpdate: (value: Record<string, unknown>) => Promise<void>; onCancel: () => void }) => open
      ? React.createElement('section', { role: 'dialog', 'aria-label': record ? '编辑经营数据' : '录入经营数据' },
        React.createElement('button', { onClick: async () => { await (record ? onUpdate({ clicks: 60 }) : onCreate({ period_start: '2026-09-01T00:00:00Z', period_end: '2026-09-02T00:00:00Z', impressions: 1000, clicks: 50, conversions: 5, spend: '100.00', revenue: '150.00' })) } }, record ? '保存经营数据' : '提交经营数据'),
        React.createElement('button', { onClick: onCancel }, '取消'))
      : null,
  }
})
vi.mock('../components/PerformanceRecordDetailDrawer', async () => {
  const React = await import('react')
  return {
    formatRatio: (value: string | null) => value === null ? '无定义' : `${(Number(value) * 100).toFixed(2)}%`,
    PerformanceRecordDetailDrawer: ({ record, open, canWrite, onEdit }: { record: PerformanceRecord | null; open: boolean; canWrite: boolean; onEdit: () => void }) => open && record
      ? React.createElement('section', { role: 'dialog', 'aria-label': '经营数据详情' },
        React.createElement('div', null, `CTR ${(Number(record.ctr) * 100).toFixed(2)}%`),
        canWrite ? React.createElement('button', { onClick: onEdit }, '编辑记录') : null)
      : null,
  }
})
vi.mock('../components/PerformanceImportModal', async () => {
  const React = await import('react')
  return {
    PerformanceImportModal: ({ open, onCancel, onImported }: { open: boolean; productId: number; onCancel: () => void; onImported: () => void }) => open
      ? React.createElement('section', { role: 'dialog', 'aria-label': '导入经营数据' },
        React.createElement('button', { onClick: async () => { await importMocks.preview(20, new File(['demo'], 'demo.csv')); await importMocks.importRows(20, new File(['demo'], 'demo.csv')); onImported() } }, '预览并导入'),
        React.createElement('button', { onClick: onCancel }, '取消'))
      : null,
  }
})
vi.mock('../components/ReviewReportGenerateModal', async () => {
  const React = await import('react')
  return {
    ReviewReportGenerateModal: ({ open, onCancel, onGenerate }: { open: boolean; onCancel: () => void; onGenerate: (value: { period_start: string; period_end: string }) => Promise<void> }) => open
      ? React.createElement('section', { role: 'dialog', 'aria-label': '生成经营分析报告' },
        React.createElement('button', { onClick: async () => { await onGenerate({ period_start: '2026-09-01T00:00:00Z', period_end: '2026-09-08T00:00:00Z' }) } }, '提交生成报告'),
        React.createElement('button', { onClick: onCancel }, '取消'))
      : null,
  }
})
vi.mock('../components/ReviewReportDetailDrawer', async () => {
  const React = await import('react')
  return {
    ReviewReportDetailDrawer: ({ report, open, canWrite, onEdit }: { report: ReviewReport | null; open: boolean; canWrite: boolean; onEdit: () => void }) => open && report
      ? React.createElement('section', { role: 'dialog', 'aria-label': '经营分析报告详情' },
        React.createElement('h3', null, report.summary_text),
        React.createElement('div', null, report.insights_json[0]?.evidence),
        canWrite ? React.createElement('button', { onClick: onEdit }, '编辑报告') : null)
      : null,
  }
})
vi.mock('../components/ReviewReportEditModal', async () => {
  const React = await import('react')
  return {
    ReviewReportEditModal: ({ open, onCancel, onSubmit }: { open: boolean; report: ReviewReport | null; onCancel: () => void; onSubmit: (value: { summary_text: string }) => Promise<void> }) => open
      ? React.createElement('section', { role: 'dialog', 'aria-label': '编辑经营分析报告' },
        React.createElement('button', { onClick: async () => { await onSubmit({ summary_text: '人工修订报告' }) } }, '保存报告'),
        React.createElement('button', { onClick: onCancel }, '取消'))
      : null,
  }
})

const creativePlan: CreativePlan = {
  id: 11, product_id: 20, plan_type: 'main_image', title: '主图方案 A', content_json: { visual_structure: [], core_copy: [], highlighted_selling_points: [] }, rationale_text: '测试', status: 'selected', provider_name: 'mock', model_name: 'mock', usage_json: null, input_context_json: {}, created_at: '2026-09-01T00:00:00Z', updated_at: '2026-09-01T00:00:00Z',
}
const asset: GeneratedAsset = {
  id: 71, product_id: 20, creative_plan_id: 11, generation_job_id: 31, asset_type: 'image', asset_url: 'mock://image/71.png', model_name: 'mock', width: 1024, height: 1024, duration_sec: null, review_status: 'approved', version_no: 1, usage_scene: '主图', score: 90, tags_json: ['轻量'], remark: null, created_at: '2026-09-01T00:00:00Z', updated_at: '2026-09-01T00:00:00Z',
}
const link: PromotionLink = {
  id: 81, product_id: 20, link_name: '主图链接', target_url: 'https://example.com', tracking_code: 'demo81', utm_json: {}, status: 'active', click_count: 2, scene_text: '测试', created_at: '2026-09-01T00:00:00Z', updated_at: '2026-09-01T00:00:00Z',
}
const experiment: AdExperiment = {
  id: 91, product_id: 20, ad_recommendation_id: 52, related_asset_id: 71, related_link_id: 81, experiment_name: '主图实验', target_text: '验证点击', audience_text: '通勤用户', budget_amount: '100.00', success_metric_text: '点击率', hypothesis_text: '轻量卖点提升点击', experiment_status: 'finished', provider_name: null, model_name: null, usage_json: null, input_context_json: {}, created_at: '2026-09-01T00:00:00Z', updated_at: '2026-09-01T00:00:00Z',
}
const record: PerformanceRecord = {
  id: 101, product_id: 20, creative_plan_id: 11, generated_asset_id: 71, promotion_link_id: 81, experiment_id: 91, period_start: '2026-09-01T00:00:00Z', period_end: '2026-09-08T00:00:00Z', impressions: 1000, clicks: 50, ctr: '0.050000', conversions: 5, conversion_rate: '0.100000', spend: '100.00', revenue: '150.00', roi: '0.500000', notes: null, created_at: '2026-09-08T00:00:00Z', updated_at: '2026-09-08T00:00:00Z',
}
const report: ReviewReport = {
  id: 111, product_id: 20, period_start: '2026-09-01T00:00:00Z', period_end: '2026-09-08T00:00:00Z', summary_text: '本周期点击效率稳定', insights_json: [{ title: '点击表现', finding: 'CTR 稳定', evidence: 'overall_ctr=0.050000' }], problem_judgements_json: [{ problem: '样本量仍需扩大', evidence: 'total_impressions=1000', severity: 'medium' }], next_actions_json: [{ action: '继续测试素材', rationale: '获得更多样本', priority: 'high' }], provider_name: 'mock', model_name: 'mock-review', usage_json: null, input_context_json: { aggregated_performance: { total_impressions: 1000, overall_ctr: '0.050000' } }, created_at: '2026-09-08T00:00:00Z', updated_at: '2026-09-08T00:00:00Z',
}

function page<T>(items: T[]) { return { items, total: items.length, page: 1, page_size: 20 } }
function renderPage(element: React.ReactElement) { return render(<AntdApp><MemoryRouter>{element}</MemoryRouter></AntdApp>) }

beforeEach(() => {
  vi.clearAllMocks()
  authState.canWrite = true
  performanceMocks.list.mockResolvedValue(page([record]))
  performanceMocks.get.mockResolvedValue(record)
  performanceMocks.create.mockResolvedValue(record)
  performanceMocks.update.mockResolvedValue({ ...record, clicks: 60, ctr: '0.060000' })
  importMocks.preview.mockResolvedValue({ total_rows: 2, valid_rows: 1, invalid_rows: 1, rows: [] } satisfies PerformanceImportPreview)
  importMocks.importRows.mockResolvedValue({ total_rows: 2, success_count: 1, failure_count: 1, successes: [{ row_number: 2, performance_record_id: 102 }], failures: [{ row_number: 3, errors: [{ field: 'clicks', error_code: 'clicks_exceed_impressions', message: '点击不能超过曝光' }] }] } satisfies PerformanceImportResult)
  importMocks.download.mockResolvedValue(new Blob(['xlsx']))
  selectorMocks.creativePlans.mockResolvedValue(page([creativePlan]))
  selectorMocks.assets.mockResolvedValue(page([asset]))
  selectorMocks.links.mockResolvedValue(page([link]))
  selectorMocks.experiments.mockResolvedValue(page([experiment]))
  reviewMocks.list.mockResolvedValue(page([report]))
  reviewMocks.get.mockResolvedValue(report)
  reviewMocks.generate.mockResolvedValue({ ...report, id: 112 })
  reviewMocks.update.mockResolvedValue({ ...report, summary_text: '人工修订报告' })
})

describe('PerformanceRecord frontend', () => {
  it('renders raw and derived metrics without recalculating business data', async () => {
    renderPage(<PerformancePage productId={20} />)
    expect(await screen.findByText('曝光 1000 · 点击 50 · 转化 5')).toBeInTheDocument()
    expect(screen.getByText('CTR 5.00%')).toBeInTheDocument()
    expect(screen.getByText('CVR 10.00%')).toBeInTheDocument()
    expect(screen.getByText('ROI 50.00%')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /手工录入/ }))
    fireEvent.click(await screen.findByRole('button', { name: '提交经营数据' }))
    await waitFor(() => expect(performanceMocks.create).toHaveBeenCalledWith(20, expect.objectContaining({ clicks: 50, spend: '100.00' })))
  })

  it('opens detail, edits record and supports empty ROI display', async () => {
    performanceMocks.list.mockResolvedValue(page([{ ...record, roi: null }]))
    renderPage(<PerformancePage productId={20} />)
    expect(await screen.findByText('ROI 无定义')).toBeInTheDocument()
    fireEvent.click(screen.getByText('曝光 1000 · 点击 50 · 转化 5'))
    fireEvent.click(await screen.findByRole('button', { name: '编辑记录' }))
    fireEvent.click(await screen.findByRole('button', { name: '保存经营数据' }))
    await waitFor(() => expect(performanceMocks.update).toHaveBeenCalledWith(20, 101, { clicks: 60 }))
  })

  it('runs preview/import and reports partial success', async () => {
    renderPage(<PerformancePage productId={20} />)
    fireEvent.click(await screen.findByRole('button', { name: /批量导入/ }))
    fireEvent.click(screen.getByRole('button', { name: '预览并导入' }))
    await waitFor(() => expect(importMocks.preview).toHaveBeenCalled())
    expect(importMocks.importRows).toHaveBeenCalled()
    expect(performanceMocks.list).toHaveBeenCalled()
  })

  it('keeps viewer read-only and allows template download', async () => {
    authState.canWrite = false
    renderPage(<PerformancePage productId={20} />)
    expect(await screen.findByText('曝光 1000 · 点击 50 · 转化 5')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /手工录入/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /批量导入/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /下载模板/ }))
    await waitFor(() => expect(importMocks.download).toHaveBeenCalled())
  })
})

describe('ReviewReport frontend', () => {
  it('renders structured report evidence and generates a new report', async () => {
    renderPage(<ReviewReportsPage productId={20} />)
    expect(await screen.findByText('本周期点击效率稳定')).toBeInTheDocument()
    fireEvent.click(screen.getByText('报告 #111'))
    expect(await screen.findByText('overall_ctr=0.050000')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /生成经营分析报告/ }))
    fireEvent.click(await screen.findByRole('button', { name: '提交生成报告' }))
    await waitFor(() => expect(reviewMocks.generate).toHaveBeenCalledWith(20, { period_start: '2026-09-01T00:00:00Z', period_end: '2026-09-08T00:00:00Z' }))
  })

  it('supports report editing and maps no-performance-data safely', async () => {
    renderPage(<ReviewReportsPage productId={20} />)
    fireEvent.click(await screen.findByText('报告 #111'))
    fireEvent.click(await screen.findByRole('button', { name: '编辑报告' }))
    fireEvent.click(await screen.findByRole('button', { name: '保存报告' }))
    await waitFor(() => expect(reviewMocks.update).toHaveBeenCalledWith(20, 111, { summary_text: '人工修订报告' }))

    reviewMocks.generate.mockRejectedValue(new ApiError(422, 'no_performance_data', '周期内没有数据'))
    fireEvent.click(screen.getByRole('button', { name: /生成经营分析报告/ }))
    fireEvent.click(await screen.findByRole('button', { name: '提交生成报告' }))
    expect(await screen.findByText('当前周期内没有可用于生成报告的经营数据。')).toBeInTheDocument()
  })

  it('keeps reports read-only for viewer and supports empty history', async () => {
    authState.canWrite = false
    reviewMocks.list.mockResolvedValue(page([]))
    renderPage(<ReviewReportsPage productId={20} />)
    expect(await screen.findByText('当前商品暂无复盘报告')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /生成经营分析报告/ })).not.toBeInTheDocument()
  })
})
