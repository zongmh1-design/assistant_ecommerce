import { Alert, Empty, Spin } from 'antd'

export function PageLoading() {
  return (
    <div className="page-state" aria-label="正在加载">
      <Spin size="large" />
    </div>
  )
}

export function PageError({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Alert
      type="error"
      showIcon
      message="加载失败"
      description={message}
      action={onRetry ? <a onClick={onRetry}>重试</a> : undefined}
    />
  )
}

export function PageEmpty({ description }: { description: string }) {
  return <Empty description={description} />
}
