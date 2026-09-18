import { ReloadOutlined, RobotOutlined } from '@ant-design/icons'
import { Alert, App, Button, Card, List, Select, Space, Tag, Typography } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  confirmAdRecommendation,
  generateAdRecommendation,
  getAdRecommendation,
  listAdRecommendations,
  updateAdRecommendation,
} from '../api/adRecommendations'
import { useAuth } from '../auth/AuthContext'
import { AdRecommendationConfirmationModal } from '../components/AdRecommendationConfirmationModal'
import { AdRecommendationDetailDrawer } from '../components/AdRecommendationDetailDrawer'
import { AdRecommendationEditModal } from '../components/AdRecommendationEditModal'
import { PageEmpty, PageError, PageLoading } from '../components/PageState'
import { PaginationControls } from '../components/PaginationControls'
import type {
  AdRecommendation,
  AdRecommendationConfirmStatus,
  AdRecommendationConfirmation,
  AdRecommendationUpdate,
} from '../types/adRecommendation'

const PAGE_SIZE = 20
const statusLabels: Record<AdRecommendationConfirmStatus, string> = { pending: '待确认', confirmed: '已确认', rejected: '已驳回' }
const statusColors: Record<AdRecommendationConfirmStatus, string> = { pending: 'gold', confirmed: 'green', rejected: 'red' }

function formatDate(value: string): string {
  return new Date(value).toLocaleString('zh-CN')
}

export function AdRecommendationsPage({ productId }: { productId: number }) {
  const { canWrite } = useAuth()
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [items, setItems] = useState<AdRecommendation[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<AdRecommendationConfirmStatus | undefined>()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [generating, setGenerating] = useState(false)
  const [generateError, setGenerateError] = useState('')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [selected, setSelected] = useState<AdRecommendation | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editing, setEditing] = useState<AdRecommendation | null>(null)
  const [decision, setDecision] = useState<'confirmed' | 'rejected' | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await listAdRecommendations(productId, {
        page,
        page_size: PAGE_SIZE,
        ...(statusFilter ? { confirm_status: statusFilter } : {}),
      })
      setItems(response.items)
      setTotal(response.total)
      setSelectedId((current) => response.items.some((item) => item.id === current) ? current : response.items[0]?.id || null)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '投放建议列表加载失败')
    } finally {
      setLoading(false)
    }
  }, [page, productId, statusFilter])

  useEffect(() => { void load() }, [load])
  useEffect(() => { setPage(1); setSelectedId(null); setSelected(null) }, [statusFilter])

  const loadDetail = useCallback(async (recommendationId: number) => {
    setDetailLoading(true)
    setDetailError('')
    try {
      const value = await getAdRecommendation(productId, recommendationId)
      setSelected(value)
    } catch (reason) {
      setSelected(null)
      setDetailError(reason instanceof ApiError ? reason.message : '投放建议详情加载失败')
    } finally {
      setDetailLoading(false)
    }
  }, [productId])

  useEffect(() => {
    if (selectedId !== null) {
      void loadDetail(selectedId)
    }
  }, [loadDetail, selectedId])

  const openDetail = (recommendation: AdRecommendation) => {
    setSelectedId(recommendation.id)
    setDrawerOpen(true)
  }

  const handleGenerate = async () => {
    setGenerating(true)
    setGenerateError('')
    try {
      const recommendation = await generateAdRecommendation(productId)
      setSelectedId(recommendation.id)
      setSelected(recommendation)
      setDrawerOpen(true)
      message.success('投放建议已生成，等待人工确认')
      await load()
    } catch (reason) {
      const safeMessage = reason instanceof ApiError ? reason.message : '投放建议生成失败，请稍后重试'
      setGenerateError(safeMessage)
      message.error(safeMessage)
    } finally {
      setGenerating(false)
    }
  }

  const handleEdit = async (changes: AdRecommendationUpdate) => {
    if (!editing) return
    await updateAdRecommendation(productId, editing.id, changes)
    const refreshed = await getAdRecommendation(productId, editing.id)
    setSelected(refreshed)
    setItems((current) => current.map((item) => item.id === refreshed.id ? refreshed : item))
    setEditing(null)
    message.success('投放建议已保存')
  }

  const handleDecision = async (payload: AdRecommendationConfirmation) => {
    if (!selected) return
    const refreshed = await confirmAdRecommendation(productId, selected.id, payload)
    setSelected(refreshed)
    setItems((current) => current.map((item) => item.id === refreshed.id ? refreshed : item))
    setDecision(null)
    message.success(payload.confirm_status === 'confirmed' ? '投放建议已确认' : '投放建议已驳回')
    await load()
  }

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <div className="section-heading">
        <div>
          <Typography.Title level={4}>投放建议</Typography.Title>
          <Typography.Text type="secondary">AI 仅提供投放策略建议，需人工确认，不会自动执行广告投放。</Typography.Text>
        </div>
        {canWrite && <Button type="primary" icon={<RobotOutlined />} loading={generating} disabled={generating} onClick={() => void handleGenerate()}>生成投放建议</Button>}
      </div>
      {canWrite && <Alert type="info" showIcon title="人工控制边界" description="确认建议只代表可以用于后续实验规划，不代表已经创建广告或修改预算。" />}
      {generateError && <Alert type="error" showIcon closable title="投放建议生成失败" description={generateError} onClose={() => setGenerateError('')} />}
      <Card title="投放建议历史" extra={<Button icon={<ReloadOutlined />} loading={loading} disabled={generating} onClick={() => void load()}>刷新</Button>}>
        <Space wrap style={{ marginBottom: 16 }}>
          <Select
            aria-label="投放建议状态"
            allowClear
            placeholder="全部状态"
            style={{ width: 150 }}
            value={statusFilter}
            onChange={(value: AdRecommendationConfirmStatus | undefined) => setStatusFilter(value)}
            options={Object.entries(statusLabels).map(([value, label]) => ({ value, label }))}
          />
        </Space>
        {loading ? <PageLoading /> : error ? <PageError message={error} onRetry={() => void load()} /> : items.length === 0 ? (
          <PageEmpty description="当前商品暂无投放建议" />
        ) : (
          <>
            <List
              itemLayout="vertical"
              dataSource={items}
              renderItem={(item) => (
                <List.Item
                  key={item.id}
                  className={item.id === selectedId ? 'ad-history-item ad-history-item-selected' : 'ad-history-item'}
                  onClick={() => openDetail(item)}
                  actions={[<span key="created">{formatDate(item.created_at)}</span>]}
                >
                  <List.Item.Meta
                    title={<Space><span>投放建议 #{item.id}</span><Tag color={statusColors[item.confirm_status]}>{statusLabels[item.confirm_status]}</Tag></Space>}
                    description={item.provider_name ? `${item.provider_name}${item.model_name ? ` / ${item.model_name}` : ''}` : '未记录 Provider'}
                  />
                  <Typography.Paragraph ellipsis={{ rows: 2 }}>{item.summary_text}</Typography.Paragraph>
                  <Typography.Text type="secondary">目标：{item.objective_text}</Typography.Text>
                </List.Item>
              )}
            />
            <PaginationControls page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
          </>
        )}
      </Card>
      {detailLoading && drawerOpen && <PageLoading />}
      {detailError && drawerOpen && <PageError message={detailError} onRetry={selectedId === null ? undefined : () => void loadDetail(selectedId)} />}
      <AdRecommendationDetailDrawer
        recommendation={selected}
        open={drawerOpen}
        canWrite={canWrite}
        onClose={() => setDrawerOpen(false)}
        onEdit={() => setEditing(selected)}
        onDecision={setDecision}
        onCreateExperiment={() => selected && navigate(`/products/${productId}/ad-experiments?recommendation_id=${selected.id}`)}
      />
      <AdRecommendationEditModal
        open={Boolean(editing)}
        recommendation={editing}
        onCancel={() => setEditing(null)}
        onSubmit={handleEdit}
      />
      <AdRecommendationConfirmationModal
        open={Boolean(decision)}
        decision={decision}
        onCancel={() => setDecision(null)}
        onSubmit={handleDecision}
      />
    </Space>
  )
}
