export function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(' ');
}

export function formatNumber(value: unknown, digits = 2): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '-';
  }
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

export function formatPercent(value: unknown, digits = 2): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '-';
  }
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatList(value: unknown): string {
  if (!Array.isArray(value) || value.length === 0) {
    return '-';
  }
  return value.join(', ');
}

export function formatTimestamp(value: unknown): string {
  if (typeof value !== 'string' || !value) {
    return '-';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}
