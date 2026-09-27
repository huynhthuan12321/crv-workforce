export function fmtHours(minutes: number) {
  return `${(minutes / 60).toFixed(1).replace(".", ",")} giờ`;
}

export function fmtKg(value: number) {
  return `${value.toLocaleString("vi-VN", {minimumFractionDigits: 1, maximumFractionDigits: 1})} kg`;
}
