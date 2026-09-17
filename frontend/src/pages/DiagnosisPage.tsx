import { EditOutlined, ReloadOutlined, RobotOutlined } from '@ant-design/icons'
import { Alert, App, Button, Card, Collapse, Descriptions, Divider, List, Space, Typography } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { generateDiagnosis, getDiagnosis, listDiagnoses, updateDiagnosis } from '../api/diagnoses'
import { useAuth } from '../auth/AuthContext'
import { DiagnosisEditModal } from '../components/DiagnosisEditModal'
import { PageEmpty, PageError, PageLoading } from '../components/PageState'
import { PaginationControls } from '../components/PaginationControls'
import type { ProductDiagnosis, ProductDiagnosisUpdate } from '../types/diagnosis'

const PAGE_SIZE = 20

function formatDate(value: string): string {
  return new Date(value).toLocaleString('zh-CN')
}

function listSummary(values: string[]): string {
  return values.length ? values.join('；') : '—'
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function DiagnosisContextSummary({ context }: { context: Record<string, unknown> }) {
  const product = isRecord(context.product) ? context.product : null
  const competitors = Array.isArray(context.competitors) ? context.competitors : []
  return (
    <Descriptions bordered size="small" column={2}>
      <Descriptions.Item label="商品名称">{product && typeof product.name === 'string' ? product.name : '—'}</Descriptions.Item>
      <Descriptions.Item label="平台">{product && typeof product.platform === 'string' ? product.platform : '—'}</Descriptions.Item>
      <Descriptions.Item label="分类">{product && typeof product.category === 'string' ? product.category : '—'}</Descriptions.Item>
      <Descriptions.Item label="价格">{product && (typeof product.price === 'string' || typeof product.price === 'number') ? `¥${product.price}` : '—'}</Descriptions.Item>
      <Descriptions.Item label="竞品样本">{competitors.length} 个</Descriptions.Item>
      <Descriptions.Item label="目标人群">{product && typeof product.target_audience === 'string' ? product.target_audience : '—'}</Descriptions.Item>
    </Descriptions>
  )
}

function DiagnosisDetail({
  diagnosis,
  canWrite,
  onEdit,
}: {
  diagnosis: ProductDiagnosis
  canWrite: boolean
  onEdit: () => void
}) {
  return (
    <Card
      title="诊断详情"
      extra={canWrite ? <Button icon={<EditOutlined />} onClick={onEdit}>编辑诊断</Button> : undefined}
    >
      <Descriptions bordered column={1}>
        <Descriptions.Item label="商品定位">{diagnosis.positioning}</Descriptions.Item>
        <Descriptions.Item label="价格带分析">{diagnosis.price_band}</Descriptions.Item>
      </Descriptions>
      <div className="diagnosis-sections">
        {[
          ['目标人群洞察', diagnosis.audience_insights],
          ['用户痛点', diagnosis.pain_points],
          ['卖点分析', diagnosis.selling_point_analysis],
          ['风险', diagnosis.risks],
          ['优化建议', diagnosis.recommendations],
        ].map(([title, values]) => (
          <div key={title as string}>
            <Typography.Title level={5}>{title as string}</Typography.Title>
            <List size="small" bordered dataSource={values as string[]} renderItem={(item) => <List.Item>{item}</List.Item>} />
          </div>
        ))}
      </div>
      <Divider />
      <Space wrap>
        <Typography.Text type="secondary">来源：{diagnosis.source_type}</Typography.Text>
        {diagnosis.provider_name && <Typography.Text type="secondary">AI Provider：{diagnosis.provider_name}</Typography.Text>}
        {diagnosis.model_name && <Typography.Text type="secondary">Model：{diagnosis.model_name}</Typography.Text>}
        <Typography.Text type="secondary">生成时间：{formatDate(diagnosis.created_at)}</Typography.Text>
      </Space>
      <Collapse
        ghost
        items={[{
          key: 'context',
          label: '查看生成依据（业务快照）',
          children: <DiagnosisContextSummary context={diagnosis.input_context_json} />,
        }]}
      />
    </Card>
  )
}

export function DiagnosisPage({ productId }: { productId: number }) {
  const { canWrite } = useAuth()
  const { message } = App.useApp()
  const [items, setItems] = useState<ProductDiagnosis[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [selectedDiagnosis, setSelectedDiagnosis] = useState<ProductDiagnosis | null>(null)
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError] = useState('')
  const [detailError, setDetailError] = useState('')
  const [generating, setGenerating] = useState(false)
  const [generateError, setGenerateError] = useState('')
  const [editOpen, setEditOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await listDiagnoses(productId, { page, page_size: PAGE_SIZE })
      setItems(response.items)
      setTotal(response.total)
      if (response.items.length === 0) {
        setSelectedId(null)
        setSelectedDiagnosis(null)
      } else {
        setSelectedId((currentId) => response.items.some((item) => item.id === currentId) ? currentId : response.items[0].id)
      }
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '诊断历史加载失败')
    } finally {
      setLoading(false)
    }
  }, [page, productId])

  useEffect(() => {
    void load()
  }, [load])

  const loadDetail = useCallback(async (diagnosisId: number) => {
    setDetailLoading(true)
    setDetailError('')
    try {
      const value = await getDiagnosis(productId, diagnosisId)
      setSelectedDiagnosis(value)
    } catch (reason) {
      setDetailError(reason instanceof ApiError ? reason.message : '诊断详情加载失败')
      setSelectedDiagnosis(null)
    } finally {
      setDetailLoading(false)
    }
  }, [productId])

  useEffect(() => {
    if (selectedId !== null) void loadDetail(selectedId)
  }, [loadDetail, selectedId])

  const handleGenerate = async () => {
    setGenerating(true)
    setGenerateError('')
    try {
      const diagnosis = await generateDiagnosis(productId)
      message.success('商品诊断已生成')
      setSelectedId(diagnosis.id)
      setSelectedDiagnosis(diagnosis)
      await load()
    } catch (reason) {
      setGenerateError(reason instanceof ApiError ? reason.message : '诊断生成失败，请稍后重试')
    } finally {
      setGenerating(false)
    }
  }

  const handleEdit = async (changes: ProductDiagnosisUpdate) => {
    if (!selectedDiagnosis) return
    const updated = await updateDiagnosis(productId, selectedDiagnosis.id, changes)
    setSelectedDiagnosis(updated)
    setItems((current) => current.map((item) => item.id === updated.id ? updated : item))
    setEditOpen(false)
    message.success('诊断已保存')
  }

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <div className="section-heading">
        <div>
          <Typography.Title level={4}>商品诊断</Typography.Title>
          <Typography.Text type="secondary">AI 基于当前商品与竞品生成结构化诊断，结果用于辅助运营判断并支持人工编辑。</Typography.Text>
        </div>
        {canWrite && <Button type="primary" icon={<RobotOutlined />} loading={generating} disabled={generating} onClick={() => void handleGenerate()}>生成商品诊断</Button>}
      </div>
      {canWrite && <Alert type="info" showIcon title="生成说明" description="系统将基于当前商品和当前竞品生成结构化诊断；没有竞品时仍按后端规则执行。" />}
      {generateError && <Alert type="error" showIcon closable onClose={() => setGenerateError('')} title="诊断生成失败" description={generateError} />}
      <Card title="诊断历史" extra={<Button icon={<ReloadOutlined />} onClick={() => void load()} disabled={loading || generating}>刷新</Button>}>
        {loading ? <PageLoading /> : error ? <PageError message={error} onRetry={() => void load()} /> : items.length === 0 ? (
          <PageEmpty description="当前商品还没有诊断结果" />
        ) : (
          <>
            <List
              itemLayout="vertical"
              dataSource={items}
              renderItem={(item) => (
                <List.Item
                  key={item.id}
                  className={item.id === selectedId ? 'diagnosis-history-item diagnosis-history-item-selected' : 'diagnosis-history-item'}
                  onClick={() => setSelectedId(item.id)}
                  actions={[<span key="created">{formatDate(item.created_at)}</span>, <span key="source">来源：{item.source_type}</span>]}
                >
                  <List.Item.Meta title={`诊断 #${item.id}`} description={item.provider_name ? `${item.provider_name}${item.model_name ? ` / ${item.model_name}` : ''}` : '未记录 Provider'} />
                  <Typography.Text>{item.positioning}</Typography.Text>
                  <Typography.Paragraph type="secondary" ellipsis={{ rows: 2 }}>{`风险：${listSummary(item.risks)}；建议：${listSummary(item.recommendations)}`}</Typography.Paragraph>
                </List.Item>
              )}
            />
            <PaginationControls page={page} pageSize={PAGE_SIZE} total={total} onChange={setPage} />
          </>
        )}
      </Card>
      {detailLoading ? <PageLoading /> : detailError ? <PageError message={detailError} onRetry={selectedId === null ? undefined : () => void loadDetail(selectedId)} /> : selectedDiagnosis ? (
        <DiagnosisDetail diagnosis={selectedDiagnosis} canWrite={canWrite} onEdit={() => setEditOpen(true)} />
      ) : null}
      <DiagnosisEditModal
        open={editOpen}
        diagnosis={selectedDiagnosis}
        onCancel={() => setEditOpen(false)}
        onSubmit={handleEdit}
      />
    </Space>
  )
}
