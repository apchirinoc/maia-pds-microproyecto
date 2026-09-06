export function formatNumber(value: number, locale: string): string {
  return new Intl.NumberFormat(locale, { useGrouping: 'always' }).format(value)
}

export function formatPercent(value: number, locale: string, fractionDigits = 1): string {
  return new Intl.NumberFormat(locale, {
    style: 'percent',
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(value / 100)
}

const DATE_ONLY_PATTERN = /^\d{4}-\d{2}-\d{2}$/

function parseDate(value: string | Date): Date {
  if (value instanceof Date) return value
  if (DATE_ONLY_PATTERN.test(value)) {
    const [year, month, day] = value.split('-').map(Number)
    return new Date(year, month - 1, day)
  }
  return new Date(value)
}

export function formatDate(value: string | Date, locale: string): string {
  const date = parseDate(value)
  return new Intl.DateTimeFormat(locale, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date)
}

export function formatDateTime(value: string | Date, locale: string): string {
  const date = parseDate(value)
  return new Intl.DateTimeFormat(locale, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

export function formatBytes(megabytes: number): string {
  if (megabytes < 1024) return `${megabytes.toFixed(0)} MB`
  return `${(megabytes / 1024).toFixed(1)} GB`
}
