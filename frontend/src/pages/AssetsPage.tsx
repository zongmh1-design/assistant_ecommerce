import { CheckCircleOutlined, ReloadOutlined, SyncOutlined } from '@ant-design/icons'
import { Alert, App, Button, Card, InputNumber, Select, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { getGeneratedAsset, listGeneratedAssets, syncGeneratedAssets, updateGeneratedAsset } from '../api/assets'
import { useAuth } from '../auth/AuthContext'
import { AssetReviewModal } from '../components/AssetReviewModal'
import { PageEmpty, PageError, PageLoading } from '../components/PageState'
import { PaginationControls } from '../components/PaginationControls'
import type { AssetReviewStatus, AssetType, GeneratedAsset, GeneratedAssetUpdate, AssetSyncResult } from '../types/asset'

const PAGE_SIZE = 20
const reviewLabels: Record<AssetReviewStatus, string> = { pending: '待审核', approved: '已通过', rejected: '已驳回' }
const reviewColors: Record<AssetReviewStatus, string> = { pending: 'gold', approved: 'green', rejected: 'red' }

function formatDate(value: string): string { return new Date(value).toLocaleString('zh-CN') }

function AssetPreview({ asset }: { asset: GeneratedAsset }) {
  const isMock = asset.asset_url.startsWith('mock://')
  if (isMock) {
    return <div className="mock-asset-placeholder"><Typography.Text strong>{asset.asset_type === 'image' ? 'Mock Image Asset' : 'Mock Video Asset'}</Typography.Text><Typography.Text type="secondary">{asset.asset_url}</Typography.Text></div>
  }
  return <a href={asset.asset_url} target="_blank" rel="noreferrer">打开素材</a>
}

export function AssetsPage({ productId }: { productId: number }) {
  const { canWrite } = useAuth()
  const { message } = App.useApp()
  const [items, setItems] = useState<GeneratedAsset[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [assetType, setAssetType] = useState<AssetType | undefined>()
  const [reviewStatus, setReviewStatus] = useState<AssetReviewStatus | undefined>()
  const [creativePlanId, setCreativePlanId] = useState<number | undefined>()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<AssetSyncResult | null>(null)
  const [editing, setEditing] = useState<GeneratedAsset | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await listGeneratedAssets(productId, { asset_type: assetType, review_status: reviewStatus, creative_plan_id: creativePlanId, page, page_size: PAGE_SIZE })
      setItems(response.items)
      setTotal(response.total)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '素材列表加载失败')
    } finally {
      setLoading(false)
    }
  }, [assetType, creativePlanId, page, productId, reviewStatus])

  useEffect(() => { void load() }, [load])
  useEffect(() => { setPage(1) }, [assetType, creativePlanId, reviewStatus])

  const handleSync = async () => {
    setSyncing(true)
    setSyncResult(null)
    try {
      const result = await syncGeneratedAssets(productId)
      setSyncResult(result)
      await load()
      if (result.failed_count) message.warning(`已同步 ${result.synced_count} 个任务，${result.failed_count} 个任务未能同步`)
      else message.success(`已同步 ${result.synced_count} 个成功任务`)
    } catch (reason) {
      message.error(reason instanceof ApiError ? reason.message : '素材同步失败')
    } finally {
      setSyncing(false)
    }
  }

  const handleUpdate = async (changes: GeneratedAssetUpdate) => {
    if (!editing) return
    await updateGeneratedAsset(productId, editing.id, changes)
    const refreshed = await getGeneratedAsset(productId, editing.id)
    setItems((current) => current.map((item) => item.id === refreshed.id ? refreshed : item))
    setEditing(null)
    message.success('素材信息已保存')
  }

  const columns: ColumnsType<GeneratedAsset> = [
    { title: '预览', key: 'preview', render: (_, asset) => <AssetPreview asset={asset} /> },
    { title: '类型', dataIndex: 'asset_type', render: (value: AssetType) => value === 'image' ? '图片' : '视频' },
    { title: '版本', dataIndex: 'version_no', render: (value: number) => `v${value}` },
    { title: '模型', dataIndex: 'model_name' },
    { title: '尺寸 / 时长', key: 'dimensions', render: (_, asset) => asset.asset_type === 'image' ? (asset.width && asset.height ? `${asset.width} × ${asset.height}` : '—') : asset.duration_sec !== null ? `${asset.duration_sec} 秒` : '—' },
    { title: '审核状态', dataIndex: 'review_status', render: (value: AssetReviewStatus) => <Tag color={reviewColors[value]}>{reviewLabels[value]}</Tag> },
    { title: '使用场景', dataIndex: 'usage_scene', render: (value: string | null) => value || '—' },
    { title: '评分', dataIndex: 'score', render: (value: number | null) => value ?? '—' },
    { title: '标签', dataIndex: 'tags_json', render: (value: string[]) => value.length ? <Space wrap>{value.map((tag) => <Tag key={tag}>{tag}</Tag>)}</Space> : '—' },
    { title: '创建时间', dataIndex: 'created_at', render: (value: string) => formatDate(value) },
    { title: '操作', key: 'actions', render: (_, asset) => <Button type="link" icon={canWrite ? <CheckCircleOutlined /> : undefined} onClick={() => setEditing(asset)}>{canWrite ? '审核 / 编辑' : '查看详情'}</Button> },
  ]

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <div className="section-heading">
        <div><Typography.Title level={4}>素材库</Typography.Title><Typography.Text type="secondary">生成任务结果需显式同步后才成为正式素材，并由人工审核。</Typography.Text></div>
        {canWrite && <Button type="primary" icon={<SyncOutlined />} loading={syncing} disabled={syncing} onClick={() => void handleSync()}>同步成功任务</Button>}
      </div>
      {syncResult && (
        <Alert type={syncResult.failed_count ? 'warning' : 'success'} showIcon title={`同步完成：成功 ${syncResult.synced_count}，跳过 ${syncResult.skipped_count}，失败 ${syncResult.failed_count}`} description={syncResult.failures.length ? <ul>{syncResult.failures.map((failure) => <li key={`${failure.job_id}-${failure.code}`}>任务 #{failure.job_id}：{failure.message}</li>)}</ul> : '没有需要说明的失败项。'} closable onClose={() => setSyncResult(null)} />
      )}
      <Card>
        <Space wrap style={{ marginBottom: 16 }}>
          <Select aria-label="素材类型" allowClear placeholder="全部类型" style={{ width: 140 }} value={assetType} onChange={(value: AssetType | undefined) => setAssetType(value)} options={[{ value: 'image', label: '图片' }, { value: 'video', label: '视频' }]} />
          <Select aria-label="审核状态" allowClear placeholder="全部审核状态" style={{ width: 160 }} value={reviewStatus} onChange={(value: AssetReviewStatus | undefined) => setReviewStatus(value)} options={Object.entries(reviewLabels).map(([value, label]) => ({ value, label }))} />
          <InputNumber aria-label="创意方案 ID" min={1} placeholder="创意方案 ID" value={creativePlanId} onChange={(value) => setCreativePlanId(value === null ? undefined : value)} />
          <Button icon={<ReloadOutlined />} disabled={loading} onClick={() => void load()}>刷新</Button>
        </Space>
        {loading ? <PageLoading /> : error ? <PageError message={error} onRetry={() => void load()} /> : items.length === 0 ? <PageEmpty description="暂无正式素材" /> : (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}><Table rowKey="id" columns={columns} dataSource={items} pagination={false} /><PaginationControls page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} /></Space>
        )}
      </Card>
      <AssetReviewModal open={Boolean(editing)} asset={editing} canWrite={canWrite} onCancel={() => setEditing(null)} onSubmit={handleUpdate} />
    </Space>
  )
}
