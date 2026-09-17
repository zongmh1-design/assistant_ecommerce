import { Pagination } from 'antd'

export function PaginationControls({
  page,
  pageSize,
  total,
  onChange,
}: {
  page: number
  pageSize: number
  total: number
  onChange: (page: number) => void
}) {
  if (total <= pageSize) return null
  return (
    <div className="pagination-row">
      <Pagination current={page} pageSize={pageSize} total={total} onChange={onChange} showSizeChanger={false} />
    </div>
  )
}
