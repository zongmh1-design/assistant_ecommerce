import { CheckOutlined, CloseOutlined, EditOutlined, FlagOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { Button, Descriptions, Drawer, Space, Tag, Typography } from 'antd'
import type { GeneratedAsset } from '../types/asset'
import type { AdExperiment, AdExperimentStatus } from '../types/adExperiment'
import type { AdRecommendation } from '../types/adRecommendation'
import type { PromotionLink } from '../types/promotionLink'

const statusLabels: Record<AdExperimentStatus, string> = {
  draft: '草稿', confirmed: '已确认', running: '实验执行中', finished: '实验已结束', cancelled: '已取消',
}
const statusColors: Record<AdExperimentStatus, string> = {
  draft: 'default', confirmed: 'blue', running: 'processing', finished: 'green', cancelled: 'red',
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString('zh-CN')
}

function recommendationLabel(id: number, recommendations: AdRecommendation[]): string {
  const recommendation = recommendations.find((item) => item.id === id)
  return recommendation ? `#${id} · ${recommendation.summary_text}` : `投放建议 #${id}`
}

export function AdExperimentDetailDrawer({
  experiment,
  open,
  canWrite,
  recommendations,
  assets,
  links,
  onClose,
  onEdit,
  onStatus,
}: {
  experiment: AdExperiment | null
  open: boolean
  canWrite: boolean
  recommendations: AdRecommendation[]
  assets: GeneratedAsset[]
  links: PromotionLink[]
  onClose: () => void
  onEdit: () => void
  onStatus: (status: AdExperimentStatus) => void
}) {
  const asset = experiment?.related_asset_id ? assets.find((item) => item.id === experiment.related_asset_id) : undefined
  const link = experiment?.related_link_id ? links.find((item) => item.id === experiment.related_link_id) : undefined
  return (
    <Drawer open={open} onClose={onClose} size="large" title={experiment ? `实验计划详情 · #${experiment.id}` : '实验计划详情'}>
      {experiment && (
        <Space orientation="vertical" size="large" style={{ width: '100%' }}>
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="实验名称" span={2}>{experiment.experiment_name}</Descriptions.Item>
            <Descriptions.Item label="状态"><Tag color={statusColors[experiment.experiment_status]}>{statusLabels[experiment.experiment_status]}</Tag></Descriptions.Item>
            <Descriptions.Item label="生成时间">{formatDate(experiment.created_at)}</Descriptions.Item>
            <Descriptions.Item label="实验目标" span={2}>{experiment.target_text}</Descriptions.Item>
            <Descriptions.Item label="目标人群" span={2}>{experiment.audience_text}</Descriptions.Item>
            <Descriptions.Item label="预算金额">{experiment.budget_amount}</Descriptions.Item>
            <Descriptions.Item label="成功指标">{experiment.success_metric_text}</Descriptions.Item>
            <Descriptions.Item label="实验假设" span={2}>{experiment.hypothesis_text}</Descriptions.Item>
            <Descriptions.Item label="来源投放建议" span={2}>{recommendationLabel(experiment.ad_recommendation_id, recommendations)}</Descriptions.Item>
            <Descriptions.Item label="关联素材" span={2}>{asset ? `${asset.asset_type === 'image' ? '图片' : '视频'} v${asset.version_no}${asset.usage_scene ? ` · ${asset.usage_scene}` : ''}` : '未绑定'}</Descriptions.Item>
            <Descriptions.Item label="关联推广链接" span={2}>{link ? `${link.link_name}${link.scene_text ? ` · ${link.scene_text}` : ''}` : '未绑定'}</Descriptions.Item>
          </Descriptions>
          {canWrite && experiment.experiment_status === 'draft' && <Button icon={<EditOutlined />} onClick={onEdit}>编辑实验计划</Button>}
          {canWrite && (
            <Space wrap>
              {experiment.experiment_status === 'draft' && <><Button type="primary" icon={<CheckOutlined />} onClick={() => onStatus('confirmed')}>确认实验</Button><Button danger icon={<CloseOutlined />} onClick={() => onStatus('cancelled')}>取消实验</Button></>}
              {experiment.experiment_status === 'confirmed' && <><Button type="primary" icon={<PlayCircleOutlined />} onClick={() => onStatus('running')}>开始执行</Button><Button danger icon={<CloseOutlined />} onClick={() => onStatus('cancelled')}>取消实验</Button></>}
              {experiment.experiment_status === 'running' && <><Button type="primary" icon={<FlagOutlined />} onClick={() => onStatus('finished')}>标记已结束</Button><Button danger icon={<CloseOutlined />} onClick={() => onStatus('cancelled')}>取消实验</Button></>}
            </Space>
          )}
          {experiment.experiment_status === 'running' && <Typography.Text type="secondary">实验执行中仅表示运营人员人工维护的业务状态，不代表系统已调用广告平台。</Typography.Text>}
          {experiment.experiment_status === 'finished' && <Typography.Text type="secondary">实验已结束，可前往经营数据模块录入实际表现。</Typography.Text>}
        </Space>
      )}
    </Drawer>
  )
}
