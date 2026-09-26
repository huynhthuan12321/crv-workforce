import {afterEach, describe, expect, it, vi} from "vitest";
import {getCurrentLocation} from "./location";

function setTelegramManager(manager: unknown) {
  Object.defineProperty(window, "Telegram", {
    configurable: true,
    value: {WebApp: {LocationManager: manager}},
  });
}

function setNavigatorGeo(geo: unknown) {
  Object.defineProperty(navigator, "geolocation", {
    configurable: true,
    value: geo,
  });
}

describe("location", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    Object.defineProperty(window, "Telegram", {configurable: true, value: undefined});
  });

  it("gets location from Telegram LocationManager when granted", async () => {
    setTelegramManager({
      isInited: true,
      isLocationAvailable: true,
      isAccessGranted: true,
      getLocation: (callback: (location: unknown) => void) => callback({latitude: 10.1, longitude: 106.2, accuracy: 12}),
    });

    await expect(getCurrentLocation()).resolves.toEqual({lat: 10.1, lng: 106.2, accuracy_m: 12});
  });

  it("falls back when Telegram LocationManager is denied", async () => {
    setTelegramManager({
      isInited: true,
      isLocationAvailable: true,
      isAccessGranted: false,
      getLocation: (callback: (location: unknown) => void) => callback(null),
    });
    setNavigatorGeo({
      getCurrentPosition: (ok: (position: GeolocationPosition) => void) => ok({
        coords: {latitude: 11, longitude: 107, accuracy: 20} as GeolocationCoordinates,
      } as GeolocationPosition),
    });

    await expect(getCurrentLocation()).resolves.toEqual({lat: 11, lng: 107, accuracy_m: 20});
  });

  it("uses navigator when Telegram LocationManager is unsupported", async () => {
    setTelegramManager(undefined);
    setNavigatorGeo({
      getCurrentPosition: (ok: (position: GeolocationPosition) => void) => ok({
        coords: {latitude: 12, longitude: 108, accuracy: 30} as GeolocationCoordinates,
      } as GeolocationPosition),
    });

    await expect(getCurrentLocation()).resolves.toEqual({lat: 12, lng: 108, accuracy_m: 30});
  });
});
