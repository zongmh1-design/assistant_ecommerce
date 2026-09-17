import { DownloadOutlined, EditOutlined, PlusOutlined, ReloadOutlined, UploadOutlined } from '@ant-design/icons'
import { Alert, App, Button, Card, Input, List, Select, Space, Tag, Typography } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { ApiError } from '../api/client'
import { listAdExperiments } from '../api/adExperiments'
import { listGeneratedAssets } from '../api/assets'
import { listCreativePlans } from '../api/creativePlans'
import { downloadPerformanceTemplate } from '../api/performanceImports'
import { createPerformanceRecord, getPerformanceRecord, listPerformanceRecords, updatePerformanceRecord } from '../api/performanceRecords'
import { listPromotionLinks } from '../api/promotionLinks'
import { useAuth } from '../auth/AuthContext'
import { PerformanceImportModal } from '../components/PerformanceImportModal'
import { PerformanceRecordDetailDrawer } from '../components/PerformanceRecordDetailDrawer'
import { PerformanceRecordFormModal } from '../components/PerformanceRecordFormModal'
import { PageEmpty, PageError, PageLoading } from '../components/PageState'
import { PaginationControls } from '../components/PaginationControls'
import type { AdExperiment } from '../types/adExperiment'
import type { CreativePlan } from '../types/creativePlan'
import type { GeneratedAsset } from '../types/asset'
import type { PerformanceRecord, PerformanceRecordCreate, PerformanceRecordQuery, PerformanceRecordUpdate } from '../types/performanceRecord'
import type { PromotionLink } from '../types/promotionLink'
import { formatRatio } from '../utils/metrics'

const PAGE_SIZE = 20

function formatDate(value: string): string {
  return new Date(value).toLocaleString('zh-CN')
}

function toUtc(value: string): string | undefined {
  return value ? new Date(value).toISOString() : undefined
}

export function PerformancePage({ productId }: { productId: number }) {
  const { canWrite } = useAuth()
  const { message } = App.useApp()
  const [items, setItems] = useState<PerformanceRecord[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [experimentFilter, setExperimentFilter] = useState<number | undefined>()
  const [assetFilter, setAssetFilter] = useState<number | undefined>()
  const [linkFilter, setLinkFilter] = useState<number | undefined>()
  const [periodStart, setPeriodStart] = useState('')
  const [periodEnd, setPeriodEnd] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectorError, setSelectorError] = useState('')
  const [selectorLoading, setSelectorLoading] = useState(true)
  const [creativePlans, setCreativePlans] = useState<CreativePlan[]>([])
  const [assets, setAssets] = useState<GeneratedAsset[]>([])
  const [links, setLinks] = useState<PromotionLink[]>([])
  const [experiments, setExperiments] = useState<AdExperiment[]>([])
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<PerformanceRecord | null>(null)
  const [importOpen, setImportOpen] = useState(false)
  const [selected, setSelected] = useState<PerformanceRecord | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')

  const loadSelectors = useCallback(async () => {
    setSelectorLoading(true)
    setSelectorError('')
    try {
      const [creativeResponse, assetResponse, linkResponse, experimentResponse] = await Promise.all([
        listCreativePlans(productId, { page: 1, page_size: 100 }),
        listGeneratedAssets(productId, { page: 1, page_size: 100 }),
        listPromotionLinks(productId, { page: 1, page_size: 100 }),
        listAdExperiments(productId, { page: 1, page_size: 100 }),
      ])
      setCreativePlans(creativeResponse.items)
      setAssets(assetResponse.items)
      setLinks(linkResponse.items)
      setExperiments(experimentResponse.items.filter((item) => item.experiment_status === 'running' || item.experiment_status === 'finished'))
    } catch (reason) {
      setSelectorError(reason instanceof ApiError ? reason.message : '经营数据关联对象加载失败')
    } finally {
      setSelectorLoading(false)
    }
  }, [productId])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    const query: PerformanceRecordQuery = {
      page,
      page_size: PAGE_SIZE,
      ...(experimentFilter ? { experiment_id: experimentFilter } : {}),
      ...(assetFilter ? { generated_asset_id: assetFilter } : {}),
      ...(linkFilter ? { promotion_link_id: linkFilter } : {}),
      ...(toUtc(periodStart) ? { period_start_from: toUtc(periodStart) } : {}),
      ...(toUtc(periodEnd) ? { period_end_to: toUtc(periodEnd) } : {}),
    }
    try {
      const response = await listPerformanceRecords(productId, query)
      setItems(response.items)
      setTotal(response.total)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '经营数据列表加载失败')
    } finally {
      setLoading(false)
    }
  }, [assetFilter, experimentFilter, linkFilter, page, periodEnd, periodStart, productId])

  useEffect(() => { void loadSelectors() }, [loadSelectors])
  useEffect(() => { void load() }, [load])
  useEffect(() => { setPage(1) }, [assetFilter, experimentFilter, linkFilter, periodEnd, periodStart])

  const experimentMap = useMemo(() => new Map(experiments.map((item) => [item.id, item])), [experiments])
  const assetMap = useMemo(() => new Map(assets.map((item) => [item.id, item])), [assets])
  const linkMap = useMemo(() => new Map(links.map((item) => [item.id, item])), [links])

  const openDetail = async (record: PerformanceRecord) => {
    setSelectedId(record.id)
    setDetailOpen(true)
    setDetailLoading(true)
    setDetailError('')
    try {
      setSelected(await getPerformanceRecord(productId, record.id))
    } catch (reason) {
      setSelected(null)
      setDetailError(reason instanceof ApiError ? reason.message : '经营数据详情加载失败')
    } finally {
      setDetailLoading(false)
    }
  }

  const handleCreate = async (data: PerformanceRecordCreate) => {
    await createPerformanceRecord(productId, data)
    setFormOpen(false)
    message.success('经营数据已录入')
    await load()
  }

  const handleUpdate = async (data: PerformanceRecordUpdate) => {
    if (!editing) return
    const updated = await updatePerformanceRecord(productId, editing.id, data)
    setEditing(null)
    setFormOpen(false)
    setSelected(updated)
    setItems((current) => current.map((item) => item.id === updated.id ? updated : item))
    message.success('经营数据已保存')
    await load()
  }

  const handleDownload = async () => {
    try {
      const blob = await downloadPerformanceTemplate()
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = 'performance-records-template.xlsx'
      anchor.click()
      URL.revokeObjectURL(url)
      message.success('模板下载已开始')
    } catch (reason) {
      message.error(reason instanceof ApiError ? reason.message : '模板下载失败')
    }
  }

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <div className="section-heading">
        <div><Typography.Title level={4}>经营数据</Typography.Title><Typography.Text type="secondary">原始经营数据由人工录入或文件导入；CTR、CVR、ROI 始终以后端计算结果为准。</Typography.Text></div>
        <Space wrap>
          <Button icon={<DownloadOutlined />} onClick={() => void handleDownload()}>下载模板</Button>
          {canWrite && <><Button icon={<UploadOutlined />} onClick={() => setImportOpen(true)}>批量导入</Button><Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); setFormOpen(true) }}>手工录入</Button></>}
        </Space>
      </div>
      {selectorError && <Alert type="warning" showIcon title="关联对象加载失败" description={selectorError} />}
      <Card title="经营数据历史" extra={<Button icon={<ReloadOutlined />} loading={loading} onClick={() => void load()}>刷新</Button>}>
        <Space wrap style={{ marginBottom: 16 }}>
          <Select aria-label="实验筛选" allowClear placeholder="全部实验" style={{ width: 190 }} loading={selectorLoading} value={experimentFilter} onChange={(value: number | undefined) => setExperimentFilter(value)} options={experiments.map((item) => ({ value: item.id, label: item.experiment_name }))} />
          <Select aria-label="素材筛选" allowClear placeholder="全部素材" style={{ width: 160 }} loading={selectorLoading} value={assetFilter} onChange={(value: number | undefined) => setAssetFilter(value)} options={assets.map((item) => ({ value: item.id, label: `${item.asset_type} v${item.version_no}` }))} />
          <Select aria-label="推广链接筛选" allowClear placeholder="全部推广链接" style={{ width: 190 }} loading={selectorLoading} value={linkFilter} onChange={(value: number | undefined) => setLinkFilter(value)} options={links.map((item) => ({ value: item.id, label: item.link_name }))} />
          <Input aria-label="周期开始筛选" type="datetime-local" value={periodStart} onChange={(event) => setPeriodStart(event.target.value)} style={{ width: 210 }} />
          <Input aria-label="周期结束筛选" type="datetime-local" value={periodEnd} onChange={(event) => setPeriodEnd(event.target.value)} style={{ width: 210 }} />
        </Space>
        {loading ? <PageLoading /> : error ? <PageError message={error} onRetry={() => void load()} /> : items.length === 0 ? <PageEmpty description="当前商品暂无经营数据" /> : (
          <>
            <List
              dataSource={items}
              renderItem={(item) => (
                <List.Item className="performance-list-item" onClick={() => void openDetail(item)} actions={[<Button key="detail" type="link" icon={<EditOutlined />} onClick={(event) => { event.stopPropagation(); void openDetail(item) }}>查看</Button>]}>
                  <List.Item.Meta title={<Space wrap><span>{formatDate(item.period_start)} - {formatDate(item.period_end)}</span><Tag color={item.roi !== null && Number(item.roi) >= 0 ? 'green' : 'red'}>ROI {formatRatio(item.roi)}</Tag></Space>} description={`曝光 ${item.impressions} · 点击 ${item.clicks} · 转化 ${item.conversions}`} />
                  <Space wrap><Typography.Text>CTR {formatRatio(item.ctr)}</Typography.Text><Typography.Text>CVR {formatRatio(item.conversion_rate)}</Typography.Text><Typography.Text>支出 ¥{item.spend}</Typography.Text><Typography.Text>收入 ¥{item.revenue}</Typography.Text><Typography.Text type="secondary">{item.experiment_id && experimentMap.get(item.experiment_id) ? `实验：${experimentMap.get(item.experiment_id)?.experiment_name}` : item.experiment_id ? `实验 #${item.experiment_id}` : '未关联实验'}</Typography.Text><Typography.Text type="secondary">{item.generated_asset_id && assetMap.get(item.generated_asset_id) ? `素材：${assetMap.get(item.generated_asset_id)?.asset_type} v${assetMap.get(item.generated_asset_id)?.version_no}` : item.generated_asset_id ? `素材 #${item.generated_asset_id}` : ''}</Typography.Text><Typography.Text type="secondary">{item.promotion_link_id && linkMap.get(item.promotion_link_id) ? `链接：${linkMap.get(item.promotion_link_id)?.link_name}` : item.promotion_link_id ? `链接 #${item.promotion_link_id}` : ''}</Typography.Text></Space>
                </List.Item>
              )}
            />
            <PaginationControls page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
          </>
        )}
      </Card>
      {detailLoading && detailOpen && <PageLoading />}
      {detailError && detailOpen && <PageError message={detailError} onRetry={selectedId === null ? undefined : () => { const item = items.find((value) => value.id === selectedId); if (item) void openDetail(item) }} />}
      <PerformanceRecordDetailDrawer record={selected} open={detailOpen} canWrite={canWrite} creativePlans={creativePlans} assets={assets} links={links} experiments={experiments} onClose={() => setDetailOpen(false)} onEdit={() => { setDetailOpen(false); setEditing(selected); setFormOpen(true) }} />
      <PerformanceRecordFormModal open={formOpen} record={editing} creativePlans={creativePlans} assets={assets.filter((item) => item.review_status === 'approved')} links={links} experiments={experiments} onCancel={() => { setFormOpen(false); setEditing(null) }} onCreate={handleCreate} onUpdate={handleUpdate} />
      <PerformanceImportModal open={importOpen} productId={productId} onCancel={() => setImportOpen(false)} onImported={() => void load()} />
    </Space>
  )
}
