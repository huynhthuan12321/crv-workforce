let offsetMs: number | null = null;

export function syncServerClock(serverNowIso: string): void {
  const serverMs = new Date(serverNowIso).getTime();
  if (Number.isFinite(serverMs)) {
    offsetMs = serverMs - performance.now();
  }
}

export function serverNow(): Date {
  if (offsetMs === null) return new Date();
  return new Date(offsetMs + performance.now());
}

export function resetServerClockForTest(): void {
  offsetMs = null;
}
