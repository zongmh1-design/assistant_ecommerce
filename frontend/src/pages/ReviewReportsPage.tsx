import { EditOutlined, ReloadOutlined, RobotOutlined } from '@ant-design/icons'
import { Alert, App, Button, Card, Input, List, Space, Tag, Typography } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { generateReviewReport, getReviewReport, listReviewReports, updateReviewReport } from '../api/reviewReports'
import { useAuth } from '../auth/AuthContext'
import { PageEmpty, PageError, PageLoading } from '../components/PageState'
import { PaginationControls } from '../components/PaginationControls'
import { ReviewReportDetailDrawer } from '../components/ReviewReportDetailDrawer'
import { ReviewReportEditModal } from '../components/ReviewReportEditModal'
import { ReviewReportGenerateModal } from '../components/ReviewReportGenerateModal'
import type { ReviewReport, ReviewReportGenerateInput, ReviewReportQuery, ReviewReportUpdate } from '../types/reviewReport'

const PAGE_SIZE = 20

function formatDate(value: string): string {
  return new Date(value).toLocaleString('zh-CN')
}

function toUtc(value: string): string | undefined {
  return value ? new Date(value).toISOString() : undefined
}

export function ReviewReportsPage({ productId }: { productId: number }) {
  const { canWrite } = useAuth()
  const { message } = App.useApp()
  const [items, setItems] = useState<ReviewReport[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [periodStart, setPeriodStart] = useState('')
  const [periodEnd, setPeriodEnd] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [generateOpen, setGenerateOpen] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [generateError, setGenerateError] = useState('')
  const [selected, setSelected] = useState<ReviewReport | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const [editOpen, setEditOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    const query: ReviewReportQuery = {
      page,
      page_size: PAGE_SIZE,
      ...(toUtc(periodStart) ? { period_start_from: toUtc(periodStart) } : {}),
      ...(toUtc(periodEnd) ? { period_end_to: toUtc(periodEnd) } : {}),
    }
    try {
      const response = await listReviewReports(productId, query)
      setItems(response.items)
      setTotal(response.total)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '复盘报告历史加载失败')
    } finally {
      setLoading(false)
    }
  }, [page, periodEnd, periodStart, productId])

  useEffect(() => { void load() }, [load])
  useEffect(() => { setPage(1) }, [periodEnd, periodStart])

  const loadDetail = useCallback(async (reportId: number) => {
    setDetailLoading(true)
    setDetailError('')
    try {
      setSelected(await getReviewReport(productId, reportId))
    } catch (reason) {
      setSelected(null)
      setDetailError(reason instanceof ApiError ? reason.message : '复盘报告详情加载失败')
    } finally {
      setDetailLoading(false)
    }
  }, [productId])

  const openDetail = (report: ReviewReport) => {
    setSelectedId(report.id)
    setDetailOpen(true)
    void loadDetail(report.id)
  }

  const handleGenerate = async (data: ReviewReportGenerateInput) => {
    setGenerating(true)
    setGenerateError('')
    try {
      const report = await generateReviewReport(productId, data)
      setSelected(report)
      setSelectedId(report.id)
      setGenerateOpen(false)
      setDetailOpen(true)
      message.success('经营分析报告已生成')
      await load()
    } catch (reason) {
      const safeMessage = reason instanceof ApiError && reason.code === 'no_performance_data' ? '当前周期内没有可用于生成报告的经营数据。' : reason instanceof ApiError ? reason.message : '经营分析报告生成失败，请稍后重试'
      setGenerateError(safeMessage)
      message.error(safeMessage)
    } finally {
      setGenerating(false)
    }
  }

  const handleEdit = async (changes: ReviewReportUpdate) => {
    if (!selected) return
    const updated = await updateReviewReport(productId, selected.id, changes)
    setSelected(updated)
    setItems((current) => current.map((item) => item.id === updated.id ? updated : item))
    setEditOpen(false)
    message.success('经营分析报告已保存')
  }

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <div className="section-heading">
        <div><Typography.Title level={4}>复盘报告</Typography.Title><Typography.Text type="secondary">报告基于指定周期内的经营数据生成；AI 只负责解释和提出建议，不修改原始指标。</Typography.Text></div>
        {canWrite && <Button type="primary" icon={<RobotOutlined />} loading={generating} disabled={generating} onClick={() => { setGenerateError(''); setGenerateOpen(true) }}>生成经营分析报告</Button>}
      </div>
      {generateError && <Alert type="error" showIcon closable title="报告生成失败" description={generateError} onClose={() => setGenerateError('')} />}
      <Card title="报告历史" extra={<Button icon={<ReloadOutlined />} loading={loading} disabled={generating} onClick={() => void load()}>刷新</Button>}>
        <Space wrap style={{ marginBottom: 16 }}>
          <Input aria-label="报告开始筛选" type="datetime-local" value={periodStart} onChange={(event) => setPeriodStart(event.target.value)} style={{ width: 210 }} />
          <Input aria-label="报告结束筛选" type="datetime-local" value={periodEnd} onChange={(event) => setPeriodEnd(event.target.value)} style={{ width: 210 }} />
        </Space>
        {loading ? <PageLoading /> : error ? <PageError message={error} onRetry={() => void load()} /> : items.length === 0 ? <PageEmpty description="当前商品暂无复盘报告" /> : (
          <>
            <List
              dataSource={items}
              renderItem={(item) => (
                <List.Item className="review-history-item" onClick={() => openDetail(item)} actions={[<Button key="detail" type="link" icon={<EditOutlined />} onClick={(event) => { event.stopPropagation(); openDetail(item) }}>查看</Button>] }>
                  <List.Item.Meta title={<Space><span>报告 #{item.id}</span><Tag color="blue">{formatDate(item.period_start)} - {formatDate(item.period_end)}</Tag></Space>} description={item.provider_name ? `${item.provider_name}${item.model_name ? ` / ${item.model_name}` : ''}` : '未记录 Provider'} />
                  <Typography.Paragraph ellipsis={{ rows: 2 }}>{item.summary_text}</Typography.Paragraph>
                </List.Item>
              )}
            />
            <PaginationControls page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
          </>
        )}
      </Card>
      {detailLoading && detailOpen && <PageLoading />}
      {detailError && detailOpen && <PageError message={detailError} onRetry={selectedId === null ? undefined : () => void loadDetail(selectedId)} />}
      <ReviewReportDetailDrawer report={selected} open={detailOpen} canWrite={canWrite} onClose={() => setDetailOpen(false)} onEdit={() => { setDetailOpen(false); setEditOpen(true) }} />
      <ReviewReportEditModal report={selected} open={editOpen} onCancel={() => setEditOpen(false)} onSubmit={handleEdit} />
      <ReviewReportGenerateModal open={generateOpen} onCancel={() => setGenerateOpen(false)} onGenerate={handleGenerate} />
    </Space>
  )
}
