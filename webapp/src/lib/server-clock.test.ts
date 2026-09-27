import {afterEach, describe, expect, it, vi} from "vitest";
import {resetServerClockForTest, serverNow, syncServerClock} from "./server-clock";

describe("server-clock", () => {
  afterEach(() => {
    vi.useRealTimers();
    resetServerClockForTest();
  });

  it("uses server offset when device clock is 10 minutes fast", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2024-04-24T09:50:00+07:00"));
    syncServerClock("2024-04-24T09:40:00+07:00");
    expect(serverNow().toISOString()).toBe("2024-04-24T02:40:00.000Z");
  });

  it("keeps countdown stable when device clock is 10 minutes slow", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2024-04-24T09:30:00+07:00"));
    syncServerClock("2024-04-24T09:40:00+07:00");
    const remaining = Math.floor((new Date("2024-04-24T09:45:00+07:00").getTime() - serverNow().getTime()) / 1000);
    expect(remaining).toBe(300);
  });
});
