export function elapsedSeconds(fromIso: string, now: Date = new Date()): number {
  return Math.max(0, Math.floor((now.getTime() - new Date(fromIso).getTime()) / 1000));
}

export function elapsedMinutes(fromIso: string, now: Date = new Date()): number {
  return Math.floor(elapsedSeconds(fromIso, now) / 60);
}

export function rawAmountForMinutes(minutes: number, ratePerHour: number): number {
  return Math.floor((minutes * ratePerHour) / 60);
}

export function roundedDayAmount(rawAmount: number): number {
  if (rawAmount <= 0) return 0;
  return Math.ceil(rawAmount / 1000) * 1000;
}

export function temporarySalary(minutes: number, ratePerHour: number): number {
  return roundedDayAmount((minutes * ratePerHour) / 60);
}
