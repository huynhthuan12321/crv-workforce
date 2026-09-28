import type {LocationPayload} from "../types/api";

export type LocationState = "idle" | "loading" | "denied" | "unsupported";

type TelegramLocation = {
  latitude?: number;
  longitude?: number;
  accuracy?: number;
  accuracy_m?: number;
  horizontal_accuracy?: number | null;
};

function normalizeAccuracy(value: unknown): number | null {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) && numberValue > 0 ? numberValue : null;
}

function fromTelegramLocation(data: TelegramLocation): LocationPayload {
  return {
    lat: Number(data.latitude),
    lng: Number(data.longitude),
    accuracy_m: normalizeAccuracy(data.horizontal_accuracy ?? data.accuracy ?? data.accuracy_m),
  };
}

async function getFromTelegram(): Promise<LocationPayload | null> {
  const manager = window.Telegram?.WebApp?.LocationManager;
  if (!manager) return null;

  await new Promise<void>((resolve) => {
    if (manager.init && !manager.isInited) manager.init(resolve);
    else resolve();
  });

  if (manager.isLocationAvailable === false) return null;

  return await new Promise<LocationPayload>((resolve, reject) => {
    manager.getLocation((location?: TelegramLocation | null) => {
      if (!location) {
        reject(new Error("LOCATION_DENIED"));
        return;
      }
      resolve(fromTelegramLocation(location));
    });
  });
}

async function getFromNavigator(): Promise<LocationPayload> {
  return await new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("LOCATION_UNSUPPORTED"));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({
        lat: position.coords.latitude,
        lng: position.coords.longitude,
        accuracy_m: normalizeAccuracy(position.coords.accuracy),
      }),
      () => reject(new Error("LOCATION_DENIED")),
      {enableHighAccuracy: true, timeout: 15000, maximumAge: 0},
    );
  });
}

export async function getCurrentLocation(): Promise<LocationPayload> {
  try {
    const telegramLocation = await getFromTelegram();
    if (telegramLocation) return telegramLocation;
  } catch {
    // Fall back to navigator.geolocation below.
  }
  return getFromNavigator();
}

export function canOpenTelegramLocationSettings(): boolean {
  return Boolean(window.Telegram?.WebApp?.LocationManager?.openSettings);
}

export function openTelegramLocationSettings() {
  window.Telegram?.WebApp?.LocationManager?.openSettings?.();
}
