export function fmtMoney(value = 0): string {
  return `${new Intl.NumberFormat("vi-VN").format(Math.round(value))}đ`;
}

export function fmtKg(value = 0): string {
  return `${new Intl.NumberFormat("vi-VN", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value)} kg`;
}

export function totalKg<T extends {bags?: number; quantity?: number; kg?: number | null; total_kg?: number | null; kg_per_bag?: number | null; kg_per_unit?: number | null}>(items: T[]): number {
  return items.reduce((sum, item) => {
    const quantity = item.quantity ?? item.bags ?? 0;
    const kgPerUnit = item.kg_per_unit ?? item.kg_per_bag ?? 0;
    return sum + (item.total_kg ?? item.kg ?? quantity * kgPerUnit);
  }, 0);
}
