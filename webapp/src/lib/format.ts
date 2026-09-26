export function fmtMoney(value = 0): string {
  return `${new Intl.NumberFormat("vi-VN").format(Math.round(value))}đ`;
}

export function fmtKg(value = 0): string {
  return `${new Intl.NumberFormat("vi-VN", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value)} kg`;
}

export function totalKg<T extends {bags: number; kg?: number; kg_per_bag?: number}>(items: T[]): number {
  return items.reduce((sum, item) => sum + (item.kg ?? item.bags * (item.kg_per_bag ?? 0)), 0);
}
