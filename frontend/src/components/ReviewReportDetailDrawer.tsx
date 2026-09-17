import { EditOutlined } from '@ant-design/icons'
import { Button, Card, Collapse, Descriptions, Drawer, List, Space, Tag, Typography } from 'antd'
import type { ReviewReport } from '../types/reviewReport'

function formatDate(value: string): string {
  return new Date(value).toLocaleString('zh-CN')
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function display(value: unknown): string {
  if (value === null || value === undefined) return '—'
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

function ContextSummary({ context }: { context: Record<string, unknown> }) {
  const period = isRecord(context.review_period) ? context.review_period : null
  const aggregate = isRecord(context.aggregated_performance) ? context.aggregated_performance : null
  return (
    <Descriptions bordered column={2} size="small">
      <Descriptions.Item label="纳入记录数">{period ? display(period.included_count) : '—'}</Descriptions.Item>
      <Descriptions.Item label="排除记录数">{period ? display(period.excluded_count) : '—'}</Descriptions.Item>
      <Descriptions.Item label="总曝光">{aggregate ? display(aggregate.total_impressions) : '—'}</Descriptions.Item>
      <Descriptions.Item label="总点击">{aggregate ? display(aggregate.total_clicks) : '—'}</Descriptions.Item>
      <Descriptions.Item label="总转化">{aggregate ? display(aggregate.total_conversions) : '—'}</Descriptions.Item>
      <Descriptions.Item label="总支出">{aggregate ? `¥${display(aggregate.total_spend)}` : '—'}</Descriptions.Item>
      <Descriptions.Item label="总收入">{aggregate ? `¥${display(aggregate.total_revenue)}` : '—'}</Descriptions.Item>
      <Descriptions.Item label="整体 CTR">{aggregate ? display(aggregate.overall_ctr) : '—'}</Descriptions.Item>
      <Descriptions.Item label="整体 CVR">{aggregate ? display(aggregate.overall_conversion_rate) : '—'}</Descriptions.Item>
      <Descriptions.Item label="整体 ROI">{aggregate ? display(aggregate.overall_roi) : '—'}</Descriptions.Item>
    </Descriptions>
  )
}

export function ReviewReportDetailDrawer({
  report,
  open,
  canWrite,
  onClose,
  onEdit,
}: {
  report: ReviewReport | null
  open: boolean
  canWrite: boolean
  onClose: () => void
  onEdit: () => void
}) {
  return (
    <Drawer open={open} onClose={onClose} size="large" title={report ? `经营分析报告 · #${report.id}` : '经营分析报告'}>
      {report && (
        <Space orientation="vertical" size="large" style={{ width: '100%' }}>
          <div className="section-heading">
            <div><Typography.Text type="secondary">报告周期</Typography.Text><div>{formatDate(report.period_start)} - {formatDate(report.period_end)}</div></div>
            {canWrite && <Button icon={<EditOutlined />} onClick={onEdit}>编辑报告</Button>}
          </div>
          <Card title="周期摘要"><Typography.Paragraph>{report.summary_text}</Typography.Paragraph></Card>
          <Card title="核心发现">
            <List dataSource={report.insights_json} renderItem={(item) => <List.Item><Space orientation="vertical" style={{ width: '100%' }}><Typography.Text strong>{item.title}</Typography.Text><Typography.Text>{item.finding}</Typography.Text><Typography.Text type="secondary">数据依据：{item.evidence}</Typography.Text></Space></List.Item>} />
          </Card>
          <Card title="问题判断">
            <List dataSource={report.problem_judgements_json} renderItem={(item) => <List.Item><Space orientation="vertical" style={{ width: '100%' }}><Space><Typography.Text strong>{item.problem}</Typography.Text><Tag color={item.severity === 'high' ? 'red' : item.severity === 'medium' ? 'orange' : 'blue'}>{item.severity}</Tag></Space><Typography.Text type="secondary">数据依据：{item.evidence}</Typography.Text></Space></List.Item>} />
          </Card>
          <Card title="下一步动作">
            <List dataSource={report.next_actions_json} renderItem={(item) => <List.Item><Space orientation="vertical" style={{ width: '100%' }}><Space><Typography.Text strong>{item.action}</Typography.Text><Tag color={item.priority === 'high' ? 'red' : item.priority === 'medium' ? 'orange' : 'blue'}>{item.priority}</Tag></Space><Typography.Text type="secondary">理由：{item.rationale}</Typography.Text></Space></List.Item>} />
          </Card>
          <Collapse items={[{ key: 'context', label: '查看生成依据（汇总快照）', children: <ContextSummary context={report.input_context_json} /> }]} />
          <Typography.Text type="secondary">{report.provider_name ? `AI Provider：${report.provider_name}` : '未记录 Provider'}{report.model_name ? ` · Model：${report.model_name}` : ''} · 生成时间：{formatDate(report.created_at)}</Typography.Text>
        </Space>
      )}
    </Drawer>
  )
}

