import { EditOutlined } from '@ant-design/icons'
import { Button, Descriptions, Drawer, Space, Tag, Typography } from 'antd'
import type { AdExperiment } from '../types/adExperiment'
import type { CreativePlan } from '../types/creativePlan'
import type { GeneratedAsset } from '../types/asset'
import type { PerformanceRecord } from '../types/performanceRecord'
import type { PromotionLink } from '../types/promotionLink'
import { formatRatio } from '../utils/metrics'

function formatDate(value: string): string {
  return new Date(value).toLocaleString('zh-CN')
}

export function PerformanceRecordDetailDrawer({
  record,
  open,
  canWrite,
  creativePlans,
  assets,
  links,
  experiments,
  onClose,
  onEdit,
}: {
  record: PerformanceRecord | null
  open: boolean
  canWrite: boolean
  creativePlans: CreativePlan[]
  assets: GeneratedAsset[]
  links: PromotionLink[]
  experiments: AdExperiment[]
  onClose: () => void
  onEdit: () => void
}) {
  const creativePlan = record?.creative_plan_id ? creativePlans.find((item) => item.id === record.creative_plan_id) : undefined
  const asset = record?.generated_asset_id ? assets.find((item) => item.id === record.generated_asset_id) : undefined
  const link = record?.promotion_link_id ? links.find((item) => item.id === record.promotion_link_id) : undefined
  const experiment = record?.experiment_id ? experiments.find((item) => item.id === record.experiment_id) : undefined
  return (
    <Drawer open={open} onClose={onClose} size="large" title={record ? `经营数据详情 · #${record.id}` : '经营数据详情'}>
      {record && (
        <Space orientation="vertical" size="large" style={{ width: '100%' }}>
          <div className="section-heading">
            <div>
              <Typography.Title level={5}>统计周期</Typography.Title>
              <Typography.Text>{formatDate(record.period_start)} - {formatDate(record.period_end)}</Typography.Text>
            </div>
            {canWrite && <Button icon={<EditOutlined />} onClick={onEdit}>编辑记录</Button>}
          </div>
          <Descriptions bordered column={2} size="small" title="原始经营指标">
            <Descriptions.Item label="曝光">{record.impressions}</Descriptions.Item>
            <Descriptions.Item label="点击">{record.clicks}</Descriptions.Item>
            <Descriptions.Item label="转化">{record.conversions}</Descriptions.Item>
            <Descriptions.Item label="支出">¥{record.spend}</Descriptions.Item>
            <Descriptions.Item label="收入">¥{record.revenue}</Descriptions.Item>
            <Descriptions.Item label="备注">{record.notes || '—'}</Descriptions.Item>
          </Descriptions>
          <Descriptions bordered column={3} size="small" title="系统计算指标">
            <Descriptions.Item label="CTR"><Tag color="blue">{formatRatio(record.ctr)}</Tag></Descriptions.Item>
            <Descriptions.Item label="CVR"><Tag color="blue">{formatRatio(record.conversion_rate)}</Tag></Descriptions.Item>
            <Descriptions.Item label="ROI"><Tag color={record.roi !== null && Number(record.roi) < 0 ? 'red' : 'green'}>{formatRatio(record.roi)}</Tag></Descriptions.Item>
          </Descriptions>
          <Descriptions bordered column={1} size="small" title="业务关联">
            <Descriptions.Item label="创意方案">{creativePlan?.title || (record.creative_plan_id ? `方案 #${record.creative_plan_id}` : '未关联')}</Descriptions.Item>
            <Descriptions.Item label="素材">{asset ? `${asset.asset_type} v${asset.version_no}` : (record.generated_asset_id ? `素材 #${record.generated_asset_id}` : '未关联')}</Descriptions.Item>
            <Descriptions.Item label="推广链接">{link?.link_name || (record.promotion_link_id ? `链接 #${record.promotion_link_id}` : '未关联')}</Descriptions.Item>
            <Descriptions.Item label="实验">{experiment?.experiment_name || (record.experiment_id ? `实验 #${record.experiment_id}` : '未关联')}</Descriptions.Item>
          </Descriptions>
        </Space>
      )}
    </Drawer>
  )
}
