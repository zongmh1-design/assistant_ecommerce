import { Alert, Button, Card, Form, Input, Modal, Space } from 'antd'
import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import type {
  AdRecommendation,
  AdRecommendationUpdate,
  AudienceSegment,
  BidStrategy,
  BudgetAllocation,
  BudgetPlan,
  CreativeTest,
  RiskControl,
} from '../types/adRecommendation'

interface RecommendationFormValues {
  summary_text: string
  objective_text: string
  audience_segments: AudienceSegment[]
  total_budget: string
  currency: string
  allocation: BudgetAllocation[]
  budget_rationale: string
  creative_tests: CreativeTest[]
  bid_strategy_name: string
  bid_strategy_rationale: string
  bid_constraints: string
  risk_controls: RiskControl[]
  next_steps: string
}

function linesToArray(value: string): string[] {
  return value.split('\n').map((item) => item.trim()).filter(Boolean)
}

function arrayToLines(values: string[]): string {
  return values.join('\n')
}

function valuesFromRecommendation(recommendation: AdRecommendation): RecommendationFormValues {
  return {
    summary_text: recommendation.summary_text,
    objective_text: recommendation.objective_text,
    audience_segments: recommendation.audience_segments_json.map((item) => ({ ...item })),
    total_budget: recommendation.budget_plan_json.total_budget,
    currency: recommendation.budget_plan_json.currency,
    allocation: recommendation.budget_plan_json.allocation.map((item) => ({ ...item })),
    budget_rationale: recommendation.budget_plan_json.rationale,
    creative_tests: recommendation.creative_tests_json.map((item) => ({ ...item })),
    bid_strategy_name: recommendation.bid_strategy_json.strategy_name,
    bid_strategy_rationale: recommendation.bid_strategy_json.rationale,
    bid_constraints: arrayToLines(recommendation.bid_strategy_json.constraints),
    risk_controls: recommendation.risk_controls_json.map((item) => ({ ...item })),
    next_steps: arrayToLines(recommendation.next_steps_json),
  }
}

function toUpdate(values: RecommendationFormValues, initial: RecommendationFormValues): AdRecommendationUpdate {
  const changes: AdRecommendationUpdate = {}
  const textFields: Array<keyof Pick<RecommendationFormValues, 'summary_text' | 'objective_text'>> = ['summary_text', 'objective_text']
  for (const field of textFields) {
    if (values[field] !== initial[field]) changes[field] = values[field].trim()
  }

  const audienceSegments = values.audience_segments.map((item) => ({
    segment_name: item.segment_name.trim(),
    description: item.description.trim(),
    rationale: item.rationale.trim(),
  }))
  if (JSON.stringify(audienceSegments) !== JSON.stringify(initial.audience_segments)) changes.audience_segments_json = audienceSegments

  const budgetPlan: BudgetPlan = {
    total_budget: values.total_budget.trim(),
    currency: values.currency.trim().toUpperCase(),
    allocation: values.allocation.map((item) => ({
      channel_or_test: item.channel_or_test.trim(),
      amount: item.amount.trim(),
      rationale: item.rationale.trim(),
    })),
    rationale: values.budget_rationale.trim(),
  }
  const initialBudget: BudgetPlan = {
    total_budget: initial.total_budget,
    currency: initial.currency,
    allocation: initial.allocation,
    rationale: initial.budget_rationale,
  }
  if (JSON.stringify(budgetPlan) !== JSON.stringify(initialBudget)) changes.budget_plan_json = budgetPlan

  const creativeTests = values.creative_tests.map((item) => ({
    test_name: item.test_name.trim(),
    asset_reference: item.asset_reference.trim(),
    hypothesis: item.hypothesis.trim(),
    success_metric: item.success_metric.trim(),
  }))
  if (JSON.stringify(creativeTests) !== JSON.stringify(initial.creative_tests)) changes.creative_tests_json = creativeTests

  const bidStrategy: BidStrategy = {
    strategy_name: values.bid_strategy_name.trim(),
    rationale: values.bid_strategy_rationale.trim(),
    constraints: linesToArray(values.bid_constraints),
  }
  const initialBidStrategy: BidStrategy = {
    strategy_name: initial.bid_strategy_name,
    rationale: initial.bid_strategy_rationale,
    constraints: linesToArray(initial.bid_constraints),
  }
  if (JSON.stringify(bidStrategy) !== JSON.stringify(initialBidStrategy)) changes.bid_strategy_json = bidStrategy

  const riskControls = values.risk_controls.map((item) => ({ risk: item.risk.trim(), mitigation: item.mitigation.trim() }))
  if (JSON.stringify(riskControls) !== JSON.stringify(initial.risk_controls)) changes.risk_controls_json = riskControls

  const nextSteps = linesToArray(values.next_steps)
  if (JSON.stringify(nextSteps) !== JSON.stringify(linesToArray(initial.next_steps))) changes.next_steps_json = nextSteps
  return changes
}

export function AdRecommendationEditModal({
  open,
  recommendation,
  onCancel,
  onSubmit,
}: {
  open: boolean
  recommendation: AdRecommendation | null
  onCancel: () => void
  onSubmit: (data: AdRecommendationUpdate) => Promise<void>
}) {
  const [form] = Form.useForm<RecommendationFormValues>()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open || !recommendation) return
    form.resetFields()
    form.setFieldsValue(valuesFromRecommendation(recommendation))
    setError('')
  }, [form, open, recommendation])

  const submit = async () => {
    if (!recommendation) return
    const values = await form.validateFields()
    const changes = toUpdate(values, valuesFromRecommendation(recommendation))
    if (!Object.keys(changes).length) {
      onCancel()
      return
    }
    setSaving(true)
    setError('')
    try {
      await onSubmit(changes)
    } catch (reason) {
      if (reason instanceof ApiError) {
        setError(reason.message)
        const fields = Object.entries(reason.fieldErrors).map(([name, message]) => ({ name: name as keyof RecommendationFormValues, errors: [message] }))
        if (fields.length) form.setFields(fields)
      } else {
        setError('投放建议保存失败，请稍后重试')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      title="编辑投放建议"
      okText="保存修改"
      cancelText="取消"
      confirmLoading={saving}
      onOk={() => void submit()}
      onCancel={onCancel}
      width={900}
      destroyOnHidden
    >
      {error && <Alert type="error" showIcon title={error} className="form-alert" />}
      <Form<RecommendationFormValues> form={form} layout="vertical">
        <Form.Item label="策略摘要" name="summary_text" rules={[{ required: true, message: '请输入策略摘要' }]}>
          <Input.TextArea rows={3} />
        </Form.Item>
        <Form.Item label="本轮目标" name="objective_text" rules={[{ required: true, message: '请输入本轮目标' }]}>
          <Input.TextArea rows={3} />
        </Form.Item>
        <Form.List name="audience_segments">
          {(fields, { add, remove }) => (
            <Card size="small" title="人群建议" extra={<Button onClick={() => add({ segment_name: '', description: '', rationale: '' })}>增加人群</Button>}>
              <Space orientation="vertical" style={{ width: '100%' }}>
                {fields.map((field, index) => (
                  <div className="ad-form-row" key={field.key}>
                    <Form.Item label={`人群 ${index + 1} 名称`} name={[field.name, 'segment_name']} rules={[{ required: true, message: '请输入人群名称' }]}>
                      <Input />
                    </Form.Item>
                    <Form.Item label="描述" name={[field.name, 'description']} rules={[{ required: true, message: '请输入人群描述' }]}>
                      <Input.TextArea rows={2} />
                    </Form.Item>
                    <Form.Item label="理由" name={[field.name, 'rationale']} rules={[{ required: true, message: '请输入建议理由' }]}>
                      <Input.TextArea rows={2} />
                    </Form.Item>
                    <Button type="link" danger onClick={() => remove(field.name)}>删除</Button>
                  </div>
                ))}
              </Space>
            </Card>
          )}
        </Form.List>
        <Card size="small" title="预算建议">
          <Space orientation="vertical" style={{ width: '100%' }}>
            <Space style={{ width: '100%' }} align="start">
              <Form.Item label="总预算" name="total_budget" rules={[{ required: true, message: '请输入总预算' }]} style={{ flex: 1 }}>
                <Input placeholder="例如 100.00" />
              </Form.Item>
              <Form.Item label="币种" name="currency" rules={[{ required: true, message: '请输入币种' }]} style={{ width: 140 }}>
                <Input maxLength={3} />
              </Form.Item>
            </Space>
            <Form.List name="allocation">
              {(fields, { add, remove }) => (
                <Card size="small" title="预算分配" extra={<Button onClick={() => add({ channel_or_test: '', amount: '', rationale: '' })}>增加分配</Button>}>
                  <Space orientation="vertical" style={{ width: '100%' }}>
                    {fields.map((field, index) => (
                      <div className="ad-form-row" key={field.key}>
                        <Form.Item label={`分配 ${index + 1}`} name={[field.name, 'channel_or_test']} rules={[{ required: true, message: '请输入分配对象' }]}>
                          <Input placeholder="渠道或测试" />
                        </Form.Item>
                        <Form.Item label="金额" name={[field.name, 'amount']} rules={[{ required: true, message: '请输入金额' }]}>
                          <Input />
                        </Form.Item>
                        <Form.Item label="理由" name={[field.name, 'rationale']} rules={[{ required: true, message: '请输入分配理由' }]}>
                          <Input />
                        </Form.Item>
                        <Button type="link" danger onClick={() => remove(field.name)}>删除</Button>
                      </div>
                    ))}
                  </Space>
                </Card>
              )}
            </Form.List>
            <Form.Item label="预算理由" name="budget_rationale" rules={[{ required: true, message: '请输入预算理由' }]}>
              <Input.TextArea rows={2} />
            </Form.Item>
          </Space>
        </Card>
        <Form.List name="creative_tests">
          {(fields, { add, remove }) => (
            <Card size="small" title="素材测试" extra={<Button onClick={() => add({ test_name: '', asset_reference: '', hypothesis: '', success_metric: '' })}>增加测试</Button>}>
              <Space orientation="vertical" style={{ width: '100%' }}>
                {fields.map((field, index) => (
                  <div className="ad-form-row" key={field.key}>
                    <Form.Item label={`测试 ${index + 1}`} name={[field.name, 'test_name']} rules={[{ required: true, message: '请输入测试名称' }]}>
                      <Input />
                    </Form.Item>
                    <Form.Item label="素材引用" name={[field.name, 'asset_reference']} rules={[{ required: true, message: '请输入素材引用' }]}>
                      <Input />
                    </Form.Item>
                    <Form.Item label="假设" name={[field.name, 'hypothesis']} rules={[{ required: true, message: '请输入测试假设' }]}>
                      <Input.TextArea rows={2} />
                    </Form.Item>
                    <Form.Item label="成功指标" name={[field.name, 'success_metric']} rules={[{ required: true, message: '请输入成功指标' }]}>
                      <Input />
                    </Form.Item>
                    <Button type="link" danger onClick={() => remove(field.name)}>删除</Button>
                  </div>
                ))}
              </Space>
            </Card>
          )}
        </Form.List>
        <Card size="small" title="出价策略">
          <Form.Item label="策略名称" name="bid_strategy_name" rules={[{ required: true, message: '请输入策略名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="策略理由" name="bid_strategy_rationale" rules={[{ required: true, message: '请输入策略理由' }]}>
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="约束（每行一项）" name="bid_constraints" rules={[{ required: true, message: '请输入策略约束' }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
        </Card>
        <Form.List name="risk_controls">
          {(fields, { add, remove }) => (
            <Card size="small" title="风险控制" extra={<Button onClick={() => add({ risk: '', mitigation: '' })}>增加风险</Button>}>
              <Space orientation="vertical" style={{ width: '100%' }}>
                {fields.map((field, index) => (
                  <div className="ad-form-row" key={field.key}>
                    <Form.Item label={`风险 ${index + 1}`} name={[field.name, 'risk']} rules={[{ required: true, message: '请输入风险' }]}>
                      <Input />
                    </Form.Item>
                    <Form.Item label="缓解措施" name={[field.name, 'mitigation']} rules={[{ required: true, message: '请输入缓解措施' }]}>
                      <Input.TextArea rows={2} />
                    </Form.Item>
                    <Button type="link" danger onClick={() => remove(field.name)}>删除</Button>
                  </div>
                ))}
              </Space>
            </Card>
          )}
        </Form.List>
        <Form.Item label="下一步动作（每行一项）" name="next_steps" rules={[{ required: true, message: '请输入下一步动作' }]}>
          <Input.TextArea rows={4} />
        </Form.Item>
      </Form>
    </Modal>
  )
}
