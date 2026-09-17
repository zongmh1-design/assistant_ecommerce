import { EyeOutlined, PlayCircleOutlined, ReloadOutlined, StopOutlined, SyncOutlined } from '@ant-design/icons'
import { Alert, App, Button, Select, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import {
  cancelGenerationJob,
  getGenerationJob,
  listGenerationJobs,
  retryGenerationJob,
  runGenerationJob,
} from '../api/generationJobs'
import { useAuth } from '../auth/AuthContext'
import { GenerationJobDetailDrawer } from '../components/GenerationJobDetailDrawer'
import { PageEmpty, PageError, PageLoading } from '../components/PageState'
import { PaginationControls } from '../components/PaginationControls'
import type { GenerationJob, GenerationJobKind, GenerationJobStatus } from '../types/generationJob'

const PAGE_SIZE = 20

const statusLabels: Record<GenerationJobStatus, string> = {
  pending: '待运行', running: '运行中', succeeded: '已成功', failed: '失败', cancelled: '已取消', timeout: '超时',
}
const statusColors: Record<GenerationJobStatus, string> = {
  pending: 'default', running: 'processing', succeeded: 'success', failed: 'error', cancelled: 'default', timeout: 'warning',
}

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString('zh-CN') : '—'
}

export function GenerationJobsPage({ productId }: { productId: number }) {
  const { canWrite } = useAuth()
  const { message } = App.useApp()
  const [items, setItems] = useState<GenerationJob[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [jobKind, setJobKind] = useState<GenerationJobKind | undefined>()
  const [jobStatus, setJobStatus] = useState<GenerationJobStatus | undefined>()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionKey, setActionKey] = useState<string | null>(null)
  const [detailId, setDetailId] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await listGenerationJobs(productId, { job_kind: jobKind, job_status: jobStatus, page, page_size: PAGE_SIZE })
      setItems(response.items)
      setTotal(response.total)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '生成任务加载失败')
    } finally {
      setLoading(false)
    }
  }, [jobKind, jobStatus, page, productId])

  useEffect(() => { void load() }, [load])
  useEffect(() => { setPage(1) }, [jobKind, jobStatus])

  const runAction = async (job: GenerationJob, action: 'run' | 'retry' | 'cancel') => {
    setActionKey(`${action}-${job.id}`)
    try {
      if (action === 'run') await runGenerationJob(productId, job.id)
      if (action === 'retry') await retryGenerationJob(productId, job.id)
      if (action === 'cancel') await cancelGenerationJob(productId, job.id)
      await getGenerationJob(productId, job.id)
      await load()
      message.success(action === 'run' ? '任务已执行' : action === 'retry' ? '任务已重新排队' : '任务已取消')
    } catch (reason) {
      message.error(reason instanceof ApiError ? reason.message : '任务操作失败，请稍后重试')
    } finally {
      setActionKey(null)
    }
  }

  const columns: ColumnsType<GenerationJob> = [
    { title: '任务 ID', dataIndex: 'id' },
    { title: '类型', dataIndex: 'job_kind', render: (value: GenerationJobKind) => value === 'image' ? '图片' : '视频' },
    { title: '状态', dataIndex: 'job_status', render: (value: GenerationJobStatus) => <Tag color={statusColors[value]}>{statusLabels[value]}</Tag> },
    { title: '尝试次数', render: (_, job) => `${job.attempts} / ${job.max_attempts}` },
    { title: '创建时间', dataIndex: 'created_at', render: (value: string) => formatDate(value) },
    { title: '开始时间', dataIndex: 'started_at', render: (value: string | null) => formatDate(value) },
    { title: '完成时间', dataIndex: 'finished_at', render: (value: string | null) => formatDate(value) },
    { title: '错误', dataIndex: 'error_message', render: (value: string | null) => value ? <Typography.Text type="danger" ellipsis={{ tooltip: value }}>{value}</Typography.Text> : '—' },
    {
      title: '操作',
      key: 'actions',
      render: (_, job) => (
        <Space wrap>
          <Button type="link" icon={<EyeOutlined />} onClick={() => setDetailId(job.id)}>详情</Button>
          {canWrite && job.job_status === 'pending' && <Button type="link" icon={<PlayCircleOutlined />} loading={actionKey === `run-${job.id}`} onClick={() => void runAction(job, 'run')}>运行任务</Button>}
          {canWrite && (job.job_status === 'failed' || job.job_status === 'timeout') && <Button type="link" icon={<SyncOutlined />} loading={actionKey === `retry-${job.id}`} onClick={() => void runAction(job, 'retry')}>重试</Button>}
          {canWrite && job.job_status === 'pending' && <Button type="link" danger icon={<StopOutlined />} loading={actionKey === `cancel-${job.id}`} onClick={() => void runAction(job, 'cancel')}>取消</Button>}
          {job.job_status === 'running' && <Typography.Text type="secondary">执行中，当前不支持强制取消</Typography.Text>}
        </Space>
      ),
    },
  ]

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <div className="section-heading">
        <div>
          <Typography.Title level={4}>生成任务</Typography.Title>
          <Typography.Text type="secondary">任务由已采用的创意方案创建；运行结果需显式同步到素材库。</Typography.Text>
        </div>
        <Button icon={<ReloadOutlined />} disabled={loading} onClick={() => void load()}>刷新</Button>
      </div>
      <Alert type="info" showIcon title="任务执行说明" description="当前使用 Mock 图片/视频生成器，运行请求会等待后端执行完成，不代表接入真实生成模型。" />
      <Space wrap>
        <Select allowClear placeholder="全部类型" style={{ width: 140 }} value={jobKind} onChange={(value: GenerationJobKind | undefined) => setJobKind(value)} options={[{ value: 'image', label: '图片' }, { value: 'video', label: '视频' }]} />
        <Select allowClear placeholder="全部状态" style={{ width: 150 }} value={jobStatus} onChange={(value: GenerationJobStatus | undefined) => setJobStatus(value)} options={Object.entries(statusLabels).map(([value, label]) => ({ value, label }))} />
      </Space>
      {loading ? <PageLoading /> : error ? <PageError message={error} onRetry={() => void load()} /> : items.length === 0 ? (
        <PageEmpty description="暂无生成任务" />
      ) : (
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Table rowKey="id" columns={columns} dataSource={items} pagination={false} />
          <PaginationControls page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
        </Space>
      )}
      <GenerationJobDetailDrawer productId={productId} jobId={detailId} open={detailId !== null} onClose={() => setDetailId(null)} />
    </Space>
  )
}
