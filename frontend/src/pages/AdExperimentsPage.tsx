import { ReloadOutlined, RobotOutlined } from '@ant-design/icons'
import { Alert, App, Button, Card, Select, Space, Tag, Typography } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  generateAdExperiment,
  getAdExperiment,
  listAdExperiments,
  updateAdExperiment,
  updateAdExperimentStatus,
} from '../api/adExperiments'
import { listAdRecommendations } from '../api/adRecommendations'
import { listGeneratedAssets } from '../api/assets'
import { useAuth } from '../auth/AuthContext'
import { listPromotionLinks } from '../api/promotionLinks'
import { AdExperimentDetailDrawer } from '../components/AdExperimentDetailDrawer'
import { AdExperimentFormModal } from '../components/AdExperimentFormModal'
import { PageEmpty, PageError, PageLoading } from '../components/PageState'
import { PaginationControls } from '../components/PaginationControls'
import type { GeneratedAsset } from '../types/asset'
import type { AdExperiment, AdExperimentGenerateInput, AdExperimentStatus, AdExperimentStatusUpdate, AdExperimentUpdate } from '../types/adExperiment'
import type { AdRecommendation } from '../types/adRecommendation'
import type { PromotionLink } from '../types/promotionLink'

const PAGE_SIZE = 20
const statusLabels: Record<AdExperimentStatus, string> = {
  draft: '草稿', confirmed: '已确认', running: '实验执行中', finished: '实验已结束', cancelled: '已取消',
}
const statusColors: Record<AdExperimentStatus, string> = {
  draft: 'default', confirmed: 'blue', running: 'processing', finished: 'green', cancelled: 'red',
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString('zh-CN')
}

export function AdExperimentsPage({ productId }: { productId: number }) {
  const { canWrite } = useAuth()
  const { message } = App.useApp()
  const [searchParams] = useSearchParams()
  const queryRecommendationId = Number(searchParams.get('recommendation_id'))
  const preselectedRecommendationId = Number.isInteger(queryRecommendationId) && queryRecommendationId > 0 ? queryRecommendationId : undefined
  const [items, setItems] = useState<AdExperiment[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<AdExperimentStatus | undefined>()
  const [recommendationFilter, setRecommendationFilter] = useState<number | undefined>()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [generating, setGenerating] = useState(false)
  const [generateError, setGenerateError] = useState('')
  const [selectorError, setSelectorError] = useState('')
  const [recommendations, setRecommendations] = useState<AdRecommendation[]>([])
  const [assets, setAssets] = useState<GeneratedAsset[]>([])
  const [links, setLinks] = useState<PromotionLink[]>([])
  const [selectorLoading, setSelectorLoading] = useState(true)
  const [selected, setSelected] = useState<AdExperiment | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<AdExperiment | null>(null)

  const recommendationMap = useMemo(() => new Map(recommendations.map((item) => [item.id, item])), [recommendations])

  const loadSelectors = useCallback(async () => {
    setSelectorLoading(true)
    setSelectorError('')
    try {
      const [recommendationResponse, assetResponse, linkResponse] = await Promise.all([
        listAdRecommendations(productId, { confirm_status: 'confirmed', page: 1, page_size: 100 }),
        listGeneratedAssets(productId, { review_status: 'approved', page: 1, page_size: 100 }),
        listPromotionLinks(productId, { status: 'active', page: 1, page_size: 100 }),
      ])
      setRecommendations(recommendationResponse.items)
      setAssets(assetResponse.items)
      setLinks(linkResponse.items)
    } catch (reason) {
      setSelectorError(reason instanceof ApiError ? reason.message : '实验可选资源加载失败')
    } finally {
      setSelectorLoading(false)
    }
  }, [productId])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await listAdExperiments(productId, {
        page,
        page_size: PAGE_SIZE,
        ...(statusFilter ? { experiment_status: statusFilter } : {}),
        ...(recommendationFilter ? { ad_recommendation_id: recommendationFilter } : {}),
      })
      setItems(response.items)
      setTotal(response.total)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '实验计划列表加载失败')
    } finally {
      setLoading(false)
    }
  }, [page, productId, recommendationFilter, statusFilter])

  useEffect(() => { void loadSelectors() }, [loadSelectors])
  useEffect(() => { void load() }, [load])
  useEffect(() => { setPage(1) }, [recommendationFilter, statusFilter])

  const loadDetail = useCallback(async (experimentId: number) => {
    setDetailLoading(true)
    setDetailError('')
    try {
      setSelected(await getAdExperiment(productId, experimentId))
    } catch (reason) {
      setSelected(null)
      setDetailError(reason instanceof ApiError ? reason.message : '实验计划详情加载失败')
    } finally {
      setDetailLoading(false)
    }
  }, [productId])

  const openDetail = (experiment: AdExperiment) => {
    setSelectedId(experiment.id)
    setDrawerOpen(true)
    void loadDetail(experiment.id)
  }

  const handleGenerate = async (data: AdExperimentGenerateInput) => {
    setGenerating(true)
    setGenerateError('')
    try {
      const experiment = await generateAdExperiment(productId, data)
      setSelected(experiment)
      setSelectedId(experiment.id)
      setFormOpen(false)
      setDrawerOpen(true)
      message.success('实验计划已生成，当前为草稿')
      await load()
    } catch (reason) {
      const safeMessage = reason instanceof ApiError ? reason.message : '实验计划生成失败，请稍后重试'
      setGenerateError(safeMessage)
      message.error(safeMessage)
    } finally {
      setGenerating(false)
    }
  }

  const handleEdit = async (changes: AdExperimentUpdate) => {
    if (!editing) return
    await updateAdExperiment(productId, editing.id, changes)
    const refreshed = await getAdExperiment(productId, editing.id)
    setSelected(refreshed)
    setItems((current) => current.map((item) => item.id === refreshed.id ? refreshed : item))
    setEditing(null)
    message.success('实验计划已保存')
  }

  const handleStatus = async (status: AdExperimentStatus) => {
    if (!selected) return
    const payload: AdExperimentStatusUpdate = { experiment_status: status }
    try {
      const refreshed = await updateAdExperimentStatus(productId, selected.id, payload)
      setSelected(refreshed)
      setItems((current) => current.map((item) => item.id === refreshed.id ? refreshed : item))
      message.success(`实验状态已更新为：${statusLabels[status]}`)
      await load()
    } catch (reason) {
      message.error(reason instanceof ApiError ? reason.message : '实验状态更新失败')
    }
  }

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <div className="section-heading">
        <div>
          <Typography.Title level={4}>投放实验</Typography.Title>
          <Typography.Text type="secondary">实验计划由人工确认和维护；系统不会自动创建广告或执行投放。</Typography.Text>
        </div>
        {canWrite && <Button type="primary" icon={<RobotOutlined />} loading={generating} disabled={generating || selectorLoading || !recommendations.length} onClick={() => { setEditing(null); setGenerateError(''); setFormOpen(true) }}>生成实验计划</Button>}
      </div>
      {canWrite && <Alert type="info" showIcon title="实验状态边界" description="“实验执行中”只表示运营人员标记实验进入执行阶段，不代表系统已调用广告平台。" />}
      {selectorError && <Alert type="warning" showIcon title="可选资源加载失败" description={selectorError} />}
      {generateError && <Alert type="error" showIcon closable title="实验计划生成失败" description={generateError} onClose={() => setGenerateError('')} />}
      <Card title="实验计划历史" extra={<Button icon={<ReloadOutlined />} loading={loading} onClick={() => void load()}>刷新</Button>}>
        <Space wrap style={{ marginBottom: 16 }}>
          <Select aria-label="实验状态" allowClear placeholder="全部状态" style={{ width: 160 }} value={statusFilter} onChange={(value: AdExperimentStatus | undefined) => setStatusFilter(value)} options={Object.entries(statusLabels).map(([value, label]) => ({ value, label }))} />
          <Select aria-label="来源投放建议" allowClear placeholder="全部投放建议" style={{ width: 260 }} value={recommendationFilter} onChange={(value: number | undefined) => setRecommendationFilter(value)} options={recommendations.map((item) => ({ value: item.id, label: `#${item.id} · ${item.summary_text.slice(0, 28)}` }))} />
        </Space>
        {loading ? <PageLoading /> : error ? <PageError message={error} onRetry={() => void load()} /> : items.length === 0 ? (
          <PageEmpty description="当前商品暂无实验计划" />
        ) : (
          <>
            {items.map((experiment) => {
              const recommendation = recommendationMap.get(experiment.ad_recommendation_id)
              return (
                <Card key={experiment.id} size="small" className="ad-history-item" onClick={() => openDetail(experiment)} style={{ marginBottom: 12 }}>
                  <Space orientation="vertical" style={{ width: '100%' }}>
                    <Space wrap><Typography.Text strong>{experiment.experiment_name}</Typography.Text><Tag color={statusColors[experiment.experiment_status]}>{statusLabels[experiment.experiment_status]}</Tag></Space>
                    <Typography.Text type="secondary">来源：{recommendation ? recommendation.summary_text : `投放建议 #${experiment.ad_recommendation_id}`}</Typography.Text>
                    <Typography.Text>{experiment.hypothesis_text}</Typography.Text>
                    <Space wrap><Typography.Text type="secondary">预算：{experiment.budget_amount}</Typography.Text><Typography.Text type="secondary">创建：{formatDate(experiment.created_at)}</Typography.Text><Button type="link" onClick={(event) => { event.stopPropagation(); openDetail(experiment) }}>查看详情</Button></Space>
                  </Space>
                </Card>
              )
            })}
            <PaginationControls page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
          </>
        )}
      </Card>
      {detailLoading && drawerOpen && <PageLoading />}
      {detailError && drawerOpen && <PageError message={detailError} onRetry={selectedId === null ? undefined : () => void loadDetail(selectedId)} />}
      <AdExperimentDetailDrawer
        experiment={selected}
        open={drawerOpen}
        canWrite={canWrite}
        recommendations={recommendations}
        assets={assets}
        links={links}
        onClose={() => setDrawerOpen(false)}
        onEdit={() => { setDrawerOpen(false); setEditing(selected); setFormOpen(true) }}
        onStatus={(status) => void handleStatus(status)}
      />
      <AdExperimentFormModal
        open={formOpen}
        experiment={editing}
        recommendationId={preselectedRecommendationId}
        recommendations={recommendations}
        assets={assets}
        links={links}
        onCancel={() => { setFormOpen(false); setEditing(null) }}
        onGenerate={handleGenerate}
        onUpdate={handleEdit}
      />
    </Space>
  )
}
