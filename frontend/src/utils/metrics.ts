export function formatRatio(value: string | null): string {
  if (value === null) return '无定义'
  const number = Number(value)
  return Number.isFinite(number) ? `${(number * 100).toFixed(2)}%` : '无定义'
}
