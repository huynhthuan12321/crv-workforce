type HapticKind = "success" | "error" | "warning";

export function hapticImpact(style: "light" | "medium" | "heavy" = "light") {
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred?.(style);
}

export function hapticNotify(kind: HapticKind) {
  window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred?.(kind);
}
