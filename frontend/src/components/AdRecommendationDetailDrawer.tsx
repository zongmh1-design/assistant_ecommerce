import { CheckOutlined, EditOutlined, ExperimentOutlined, StopOutlined } from '@ant-design/icons'
import { Button, Card, Descriptions, Drawer, List, Space, Tag, Typography } from 'antd'
import type { AdRecommendation, AdRecommendationConfirmStatus } from '../types/adRecommendation'

const statusLabels: Record<AdRecommendationConfirmStatus, string> = {
  pending: '待确认',
  confirmed: '已确认',
  rejected: '已驳回',
}
const statusColors: Record<AdRecommendationConfirmStatus, string> = {
  pending: 'gold',
  confirmed: 'green',
  rejected: 'red',
}

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString('zh-CN') : '—'
}

function formatAmount(value: string): string {
  return `${value}`
}

export function AdRecommendationDetailDrawer({
  recommendation,
  open,
  canWrite,
  onClose,
  onEdit,
  onDecision,
  onCreateExperiment,
}: {
  recommendation: AdRecommendation | null
  open: boolean
  canWrite: boolean
  onClose: () => void
  onEdit: () => void
  onDecision: (decision: 'confirmed' | 'rejected') => void
  onCreateExperiment: () => void
}) {
  return (
    <Drawer open={open} onClose={onClose} size="large" title={recommendation ? `投放建议详情 · #${recommendation.id}` : '投放建议详情'}>
      {recommendation && (
        <Space orientation="vertical" size="large" style={{ width: '100%' }}>
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="状态"><Tag color={statusColors[recommendation.confirm_status]}>{statusLabels[recommendation.confirm_status]}</Tag></Descriptions.Item>
            <Descriptions.Item label="生成时间">{formatDate(recommendation.created_at)}</Descriptions.Item>
            <Descriptions.Item label="策略摘要" span={2}>{recommendation.summary_text}</Descriptions.Item>
            <Descriptions.Item label="本轮目标" span={2}>{recommendation.objective_text}</Descriptions.Item>
          </Descriptions>

          <Card size="small" title="人群建议">
            <List
              bordered
              dataSource={recommendation.audience_segments_json}
              locale={{ emptyText: '暂无人群建议' }}
              renderItem={(segment) => (
                <List.Item>
                  <Space orientation="vertical" size={2}>
                    <Typography.Text strong>{segment.segment_name}</Typography.Text>
                    <Typography.Text>{segment.description}</Typography.Text>
                    <Typography.Text type="secondary">理由：{segment.rationale}</Typography.Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>

          <Card size="small" title="预算建议">
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="总预算">{formatAmount(recommendation.budget_plan_json.total_budget)} {recommendation.budget_plan_json.currency}</Descriptions.Item>
              <Descriptions.Item label="预算理由">{recommendation.budget_plan_json.rationale}</Descriptions.Item>
            </Descriptions>
            <List
              size="small"
              header="预算分配"
              dataSource={recommendation.budget_plan_json.allocation}
              renderItem={(allocation) => <List.Item><Typography.Text>{allocation.channel_or_test}：{formatAmount(allocation.amount)} {recommendation.budget_plan_json.currency}；{allocation.rationale}</Typography.Text></List.Item>}
            />
          </Card>

          <Card size="small" title="素材测试">
            <List
              bordered
              dataSource={recommendation.creative_tests_json}
              locale={{ emptyText: '暂无素材测试建议' }}
              renderItem={(test) => (
                <List.Item>
                  <Space orientation="vertical" size={2}>
                    <Typography.Text strong>{test.test_name}</Typography.Text>
                    <Typography.Text>素材引用：{test.asset_reference}</Typography.Text>
                    <Typography.Text>假设：{test.hypothesis}</Typography.Text>
                    <Typography.Text type="secondary">成功指标：{test.success_metric}</Typography.Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>

          <Card size="small" title="出价策略">
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="策略名称">{recommendation.bid_strategy_json.strategy_name}</Descriptions.Item>
              <Descriptions.Item label="策略理由">{recommendation.bid_strategy_json.rationale}</Descriptions.Item>
              <Descriptions.Item label="约束"><List size="small" dataSource={recommendation.bid_strategy_json.constraints} renderItem={(item) => <List.Item>{item}</List.Item>} /></Descriptions.Item>
            </Descriptions>
          </Card>

          <Card size="small" title="风险控制">
            <List
              bordered
              dataSource={recommendation.risk_controls_json}
              locale={{ emptyText: '暂无风险控制建议' }}
              renderItem={(item) => <List.Item><Typography.Text><Typography.Text strong>{item.risk}</Typography.Text>：{item.mitigation}</Typography.Text></List.Item>}
            />
          </Card>

          <Card size="small" title="下一步动作">
            <List bordered dataSource={recommendation.next_steps_json} renderItem={(item) => <List.Item>{item}</List.Item>} />
          </Card>

          {recommendation.confirm_remark && <Card size="small" title="人工备注"><Typography.Paragraph>{recommendation.confirm_remark}</Typography.Paragraph></Card>}
          <Space wrap>
            <Typography.Text type="secondary">Provider：{recommendation.provider_name || '未记录'}</Typography.Text>
            <Typography.Text type="secondary">Model：{recommendation.model_name || '未记录'}</Typography.Text>
            <Typography.Text type="secondary">确认人：{recommendation.confirmed_by ?? '未确认'}</Typography.Text>
            <Typography.Text type="secondary">确认时间：{formatDate(recommendation.confirmed_at)}</Typography.Text>
          </Space>

          {canWrite && recommendation.confirm_status === 'pending' && (
            <Space wrap>
              <Button icon={<EditOutlined />} onClick={onEdit}>编辑建议</Button>
              <Button type="primary" icon={<CheckOutlined />} onClick={() => onDecision('confirmed')}>确认建议</Button>
              <Button danger icon={<StopOutlined />} onClick={() => onDecision('rejected')}>驳回建议</Button>
            </Space>
          )}
          {canWrite && recommendation.confirm_status === 'confirmed' && (
            <Button type="primary" icon={<ExperimentOutlined />} onClick={onCreateExperiment}>创建实验计划</Button>
          )}
        </Space>
      )}
    </Drawer>
  )
}
