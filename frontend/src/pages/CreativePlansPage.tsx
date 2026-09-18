import { EditOutlined, FileImageOutlined, PlayCircleOutlined, ReloadOutlined, RobotOutlined } from '@ant-design/icons'
import { Alert, App, Button, Card, Collapse, Descriptions, List, Select, Space, Tabs, Tag, Typography } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import {
  generateMainImagePlans,
  generateVideoScripts,
  getCreativePlan,
  listCreativePlans,
  updateCreativePlan,
} from '../api/creativePlans'
import { createImageGenerationJob, createVideoGenerationJob } from '../api/generationJobs'
import { useAuth } from '../auth/AuthContext'
import { CreativePlanEditModal } from '../components/CreativePlanEditModal'
import { PageEmpty, PageError, PageLoading } from '../components/PageState'
import { PaginationControls } from '../components/PaginationControls'
import type {
  CreativePlan,
  CreativePlanStatus,
  CreativePlanUpdate,
  MainImageContent,
  StoryboardScene,
  VideoScriptContent,
} from '../types/creativePlan'

const PAGE_SIZE = 20
type PlanTab = 'main_image' | 'video_script'

const statusLabels: Record<CreativePlanStatus, string> = { draft: '草稿', selected: '已采用', archived: '已归档' }
const statusColors: Record<CreativePlanStatus, string> = { draft: 'default', selected: 'green', archived: 'default' }

function formatDate(value: string): string {
  return new Date(value).toLocaleString('zh-CN')
}

function isMainImageContent(value: unknown): value is MainImageContent {
  if (typeof value !== 'object' || value === null) return false
  const content = value as Record<string, unknown>
  return ['visual_structure', 'core_copy', 'highlighted_selling_points'].every((key) => Array.isArray(content[key]))
}

function isVideoScriptContent(value: unknown): value is VideoScriptContent {
  if (typeof value !== 'object' || value === null) return false
  const content = value as Record<string, unknown>
  return typeof content.opening_hook === 'string'
    && Array.isArray(content.storyboard)
    && Array.isArray(content.voiceover)
    && typeof content.conversion_cta === 'string'
}

function ContentList({ title, values }: { title: string; values: string[] }) {
  return (
    <div>
      <Typography.Title level={5}>{title}</Typography.Title>
      <List size="small" bordered dataSource={values} locale={{ emptyText: '暂无内容' }} renderItem={(value) => <List.Item>{value}</List.Item>} />
    </div>
  )
}

function PlanContent({ plan }: { plan: CreativePlan }) {
  if (plan.plan_type === 'main_image' && isMainImageContent(plan.content_json)) {
    return (
      <div className="creative-plan-sections">
        <ContentList title="画面结构" values={plan.content_json.visual_structure as string[]} />
        <ContentList title="核心文案" values={plan.content_json.core_copy as string[]} />
        <ContentList title="重点卖点" values={plan.content_json.highlighted_selling_points as string[]} />
      </div>
    )
  }
  if (plan.plan_type === 'video_script' && isVideoScriptContent(plan.content_json)) {
    const scenes = [...plan.content_json.storyboard].sort((left, right) => left.scene_no - right.scene_no)
    return (
      <div className="creative-plan-sections">
        <Descriptions bordered size="small" column={1}>
          <Descriptions.Item label="开头钩子">{plan.content_json.opening_hook}</Descriptions.Item>
          <Descriptions.Item label="转化引导">{plan.content_json.conversion_cta}</Descriptions.Item>
        </Descriptions>
        <ContentList title="口播文案" values={plan.content_json.voiceover as string[]} />
        <div>
          <Typography.Title level={5}>分镜</Typography.Title>
          <List
            size="small"
            bordered
            dataSource={scenes}
            locale={{ emptyText: '暂无分镜' }}
            renderItem={(scene: StoryboardScene) => (
              <List.Item>
                <Space direction="vertical" size={0}>
                  <Typography.Text strong>#{scene.scene_no} · {scene.duration_hint}</Typography.Text>
                  <Typography.Text>{scene.visual}</Typography.Text>
                  <Typography.Text type="secondary">口播：{scene.voiceover}</Typography.Text>
                </Space>
              </List.Item>
            )}
          />
        </div>
      </div>
    )
  }
  return <Alert type="warning" showIcon title="方案内容格式无法展示" description="后端返回的结构化内容不符合当前页面支持的格式。" />
}

function PlanCard({
  plan,
  canWrite,
  onSelect,
  onEdit,
  onUse,
  onCreateJob,
}: {
  plan: CreativePlan
  canWrite: boolean
  onSelect: () => void
  onEdit: () => void
  onUse: () => void
  onCreateJob: () => void
}) {
  return (
    <Card
      className={plan.status === 'archived' ? 'creative-plan-card creative-plan-card-archived' : 'creative-plan-card'}
      title={<Space><span>{plan.title}</span><Tag color={statusColors[plan.status]}>{statusLabels[plan.status]}</Tag></Space>}
      onClick={onSelect}
      extra={canWrite && (
        <Space onClick={(event) => event.stopPropagation()}>
          {plan.status !== 'archived' && <Button size="small" icon={<EditOutlined />} onClick={onEdit}>编辑</Button>}
          {plan.status === 'draft' && <Button size="small" type="primary" onClick={onUse}>采用此方案</Button>}
          {plan.status === 'selected' && (
            <Button size="small" type="primary" icon={plan.plan_type === 'main_image' ? <FileImageOutlined /> : <PlayCircleOutlined />} onClick={onCreateJob}>
              {plan.plan_type === 'main_image' ? '创建图片生成任务' : '创建视频生成任务'}
            </Button>
          )}
        </Space>
      )}
    >
      <Typography.Paragraph type="secondary">方案理由：{plan.rationale_text}</Typography.Paragraph>
      <PlanContent plan={plan} />
      <Collapse
        ghost
        items={[{
          key: 'metadata',
          label: '生成信息',
          children: <Space wrap><Typography.Text type="secondary">生成时间：{formatDate(plan.created_at)}</Typography.Text>{plan.provider_name && <Typography.Text type="secondary">Provider：{plan.provider_name}</Typography.Text>}{plan.model_name && <Typography.Text type="secondary">Model：{plan.model_name}</Typography.Text>}</Space>,
        }]}
      />
    </Card>
  )
}

export function CreativePlansPage({ productId }: { productId: number }) {
  const { canWrite } = useAuth()
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<PlanTab>('main_image')
  const [statusFilter, setStatusFilter] = useState<CreativePlanStatus | undefined>()
  const [items, setItems] = useState<CreativePlan[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [generating, setGenerating] = useState(false)
  const [generateError, setGenerateError] = useState('')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [editing, setEditing] = useState<CreativePlan | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await listCreativePlans(productId, {
        plan_type: activeTab,
        ...(statusFilter ? { status: statusFilter } : {}),
        page,
        page_size: PAGE_SIZE,
      })
      setItems(response.items)
      setTotal(response.total)
      setSelectedId((current) => response.items.some((item) => item.id === current) ? current : response.items[0]?.id || null)
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '创意方案加载失败')
    } finally {
      setLoading(false)
    }
  }, [activeTab, page, productId, statusFilter])

  useEffect(() => { void load() }, [load])

  useEffect(() => {
    setPage(1)
    setSelectedId(null)
  }, [activeTab, statusFilter])

  const handleGenerate = async () => {
    setGenerating(true)
    setGenerateError('')
    try {
      const generated = activeTab === 'main_image' ? await generateMainImagePlans(productId) : await generateVideoScripts(productId)
      if (generated.length) setSelectedId(generated[0].id)
      message.success(`本次已生成 ${generated.length} 条${activeTab === 'main_image' ? '主图方案' : '视频脚本'}`)
      await load()
    } catch (reason) {
      const safeMessage = reason instanceof ApiError ? reason.message : '创意方案生成失败，请稍后重试'
      setGenerateError(safeMessage)
      message.error(safeMessage)
    } finally {
      setGenerating(false)
    }
  }

  const handleEdit = async (changes: CreativePlanUpdate) => {
    if (!editing) return
    await updateCreativePlan(productId, editing.id, changes)
    const refreshed = await getCreativePlan(productId, editing.id)
    setItems((current) => current.map((item) => item.id === refreshed.id ? refreshed : item))
    setEditing(null)
    message.success('创意方案已保存')
  }

  const handleStatus = async (plan: CreativePlan, status: CreativePlanStatus) => {
    try {
      await updateCreativePlan(productId, plan.id, { status })
      await load()
      message.success('方案状态已更新')
    } catch (reason) {
      message.error(reason instanceof ApiError ? reason.message : '方案状态更新失败')
    }
  }

  const handleCreateJob = async (plan: CreativePlan) => {
    try {
      const job = plan.plan_type === 'main_image'
        ? await createImageGenerationJob(productId, plan.id)
        : await createVideoGenerationJob(productId, plan.id)
      message.success(`生成任务 #${job.id} 已创建，当前等待运行`)
      navigate(`/products/${productId}/generation-jobs`)
    } catch (reason) {
      message.error(reason instanceof ApiError ? reason.message : '生成任务创建失败')
    }
  }

  const tabLabel = activeTab === 'main_image' ? '主图方案' : '视频脚本'
  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <div className="section-heading">
        <div>
          <Typography.Title level={4}>创意方案</Typography.Title>
          <Typography.Text type="secondary">当前生成的是文字创意方向，后续生成任务和素材审核仍需人工控制。</Typography.Text>
        </div>
        {canWrite && <Button type="primary" icon={<RobotOutlined />} loading={generating} disabled={generating} onClick={() => void handleGenerate()}>生成{tabLabel}</Button>}
      </div>
      {canWrite && <Alert type="info" showIcon title="AI 生成说明" description="方案基于当前商品和诊断信息生成，可人工编辑；不会直接生成图片或视频。" />}
      {generateError && <Alert type="error" showIcon closable title="创意方案生成失败" description={generateError} onClose={() => setGenerateError('')} />}
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={(key) => setActiveTab(key as PlanTab)}
          items={[{ key: 'main_image', label: '主图方案' }, { key: 'video_script', label: '视频脚本' }]}
        />
        <Space wrap style={{ marginBottom: 16 }}>
          <Typography.Text>状态筛选：</Typography.Text>
          <Select
            allowClear
            placeholder="全部状态"
            style={{ width: 150 }}
            value={statusFilter}
            onChange={(value: CreativePlanStatus | undefined) => setStatusFilter(value)}
            options={Object.entries(statusLabels).map(([value, label]) => ({ value, label }))}
          />
          <Button icon={<ReloadOutlined />} disabled={loading || generating} onClick={() => void load()}>刷新</Button>
        </Space>
        {loading ? <PageLoading /> : error ? <PageError message={error} onRetry={() => void load()} /> : items.length === 0 ? (
          <PageEmpty description={`暂无${tabLabel}`} />
        ) : (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            {items.map((plan) => (
              <PlanCard
                key={plan.id}
                plan={plan}
                canWrite={canWrite}
                onSelect={() => setSelectedId(plan.id)}
                onEdit={() => setEditing(plan)}
                onUse={() => void handleStatus(plan, 'selected')}
                onCreateJob={() => void handleCreateJob(plan)}
              />
            ))}
            <PaginationControls page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
          </Space>
        )}
      </Card>
      {selectedId !== null && items.find((item) => item.id === selectedId)?.status === 'selected' && (
        <Alert type="success" showIcon title="已采用的方案可以进入生成任务" description="请使用方案卡片中的生成任务按钮；任务成功后还需要在素材库显式同步并人工审核。" />
      )}
      <CreativePlanEditModal
        open={Boolean(editing)}
        plan={editing}
        onCancel={() => setEditing(null)}
        onSubmit={handleEdit}
      />
    </Space>
  )
}
