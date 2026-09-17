import { CheckCircleOutlined, InboxOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Divider, List, Modal, Space, Tag, Typography } from 'antd'
import { useState } from 'react'
import { ApiError } from '../api/client'
import { importPerformanceRecords, previewPerformanceImport } from '../api/performanceImports'
import type { PerformanceImportPreview, PerformanceImportResult, PerformancePreviewRow } from '../types/performanceImport'

function cell(row: PerformancePreviewRow, key: string): string {
  const value = row.normalized_data?.[key]
  return value === null || value === undefined ? '—' : String(value)
}

export function PerformanceImportModal({
  open,
  productId,
  onCancel,
  onImported,
}: {
  open: boolean
  productId: number
  onCancel: () => void
  onImported: () => void
}) {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<PerformanceImportPreview | null>(null)
  const [result, setResult] = useState<PerformanceImportResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const reset = () => {
    setFile(null)
    setPreview(null)
    setResult(null)
    setError('')
    setLoading(false)
  }

  const close = () => {
    reset()
    onCancel()
  }

  const chooseFile = (value: File | null) => {
    setFile(value)
    setPreview(null)
    setResult(null)
    setError('')
  }

  const handlePreview = async () => {
    if (!file) return
    setLoading(true)
    setError('')
    try {
      setPreview(await previewPerformanceImport(productId, file))
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '文件预览失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  const handleImport = async () => {
    if (!file || !preview) return
    setLoading(true)
    setError('')
    try {
      const value = await importPerformanceRecords(productId, file)
      setResult(value)
      onImported()
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : '文件导入失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      open={open}
      title="导入经营数据"
      width={900}
      footer={null}
      onCancel={close}
      destroyOnHidden
    >
      <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
        <Alert type="info" showIcon message="预览不会写入数据库" description="确认后会重新上传原文件并重新校验，合法行允许部分成功写入。支持 .csv / .xlsx，建议不超过 5 MB、1000 行。" />
        <Space wrap>
          <label className="file-input-label">
            <InboxOutlined /> 选择文件
            <input
              type="file"
              accept=".csv,.xlsx"
              style={{ display: 'none' }}
              onChange={(event) => chooseFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <Typography.Text type="secondary">{file ? file.name : '尚未选择文件'}</Typography.Text>
          <Button type="primary" disabled={!file} loading={loading && !preview} onClick={() => void handlePreview()}>预览</Button>
          <Button type="primary" disabled={!file || !preview || loading || Boolean(result)} loading={loading && Boolean(preview) && !result} onClick={() => void handleImport()}>确认导入</Button>
        </Space>
        {error && <Alert type="error" showIcon message="导入处理失败" description={error} />}
        {preview && (
          <Card size="small" title="预览结果" extra={<Space><Tag color="blue">总计 {preview.total_rows}</Tag><Tag color="green">合法 {preview.valid_rows}</Tag><Tag color="red">错误 {preview.invalid_rows}</Tag></Space>}>
            {preview.rows.length === 0 ? <Typography.Text type="secondary">文件只有表头，没有数据行。</Typography.Text> : (
              <List
                size="small"
                dataSource={preview.rows}
                renderItem={(row) => (
                  <List.Item>
                    <Space orientation="vertical" style={{ width: '100%' }}>
                      <Space wrap><Tag color={row.status === 'valid' ? 'green' : 'red'}>第 {row.row_number} 行 · {row.status === 'valid' ? '合法' : '错误'}</Tag>{row.status === 'valid' && <Typography.Text type="secondary">曝光 {cell(row, 'impressions')} / 点击 {cell(row, 'clicks')} / 转化 {cell(row, 'conversions')} / 支出 ¥{cell(row, 'spend')} / 收入 ¥{cell(row, 'revenue')}</Typography.Text>}</Space>
                      {row.status === 'valid' && row.calculated_metrics && <Typography.Text type="secondary">系统指标：CTR {row.calculated_metrics.ctr} · CVR {row.calculated_metrics.conversion_rate} · ROI {row.calculated_metrics.roi ?? '无定义'}</Typography.Text>}
                      {row.status === 'invalid' && <List size="small" dataSource={row.errors} renderItem={(item) => <List.Item><Typography.Text type="danger">{item.field || '整行'} · {item.error_code}：{item.message}</Typography.Text></List.Item>} />}
                    </Space>
                  </List.Item>
                )}
              />
            )}
          </Card>
        )}
        {result && (
          <Card size="small" title={<Space><CheckCircleOutlined style={{ color: '#52c41a' }} />导入完成</Space>}>
            <Typography.Paragraph>共 {result.total_rows} 行，成功 {result.success_count} 条，失败 {result.failure_count} 条。</Typography.Paragraph>
            {result.successes.length > 0 && <Typography.Text>成功行：{result.successes.map((item) => `第 ${item.row_number} 行（记录 #${item.performance_record_id}）`).join('、')}</Typography.Text>}
            {result.failures.length > 0 && <><Divider /><List size="small" header="失败行" dataSource={result.failures} renderItem={(item) => <List.Item><Typography.Text type="danger">第 {item.row_number} 行：{item.errors.map((errorItem) => `${errorItem.field || '整行'} · ${errorItem.message}`).join('；')}</Typography.Text></List.Item>} /></>}
          </Card>
        )}
      </Space>
    </Modal>
  )
}

