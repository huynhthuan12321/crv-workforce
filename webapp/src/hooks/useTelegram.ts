import { useCallback, useEffect, useState } from "react";
import {applyMockTheme, applyTelegramTheme, mockThemeFromUrl} from "../lib/theme";

export const useTelegram = () => {
  const [isReady, setIsReady] = useState(false);
  const tg = window.Telegram?.WebApp;

  useEffect(() => {
    if (tg) {
      tg.ready();
      tg.expand();
      setIsReady(true);
    }
  }, [tg]);

  useEffect(() => {
    if (import.meta.env.DEV && import.meta.env.VITE_MOCK === "1") {
      const apply = () => applyMockTheme(mockThemeFromUrl());
      apply();
      window.addEventListener("crv-mock-theme", apply);
      return () => window.removeEventListener("crv-mock-theme", apply);
    }
    if (!tg) {
      applyMockTheme(mockThemeFromUrl());
      return;
    }
    const apply = () => applyTelegramTheme(tg.colorScheme, tg.themeParams);
    apply();
    tg.onEvent?.("themeChanged", apply);
    return () => tg.offEvent?.("themeChanged", apply);
  }, [tg]);

  const user = tg?.initDataUnsafe?.user;
  const colorScheme = tg?.colorScheme || "light";
  const themeParams = tg?.themeParams || {};

  const close = useCallback(() => {
    tg?.close();
  }, [tg]);

  const sendData = useCallback(
    (data: object) => {
      tg?.sendData(JSON.stringify(data));
    },
    [tg]
  );

  const showMainButton = useCallback(
    (text: string, onClick: () => void) => {
      if (tg?.MainButton) {
        tg.MainButton.setText(text);
        tg.MainButton.onClick(onClick);
        tg.MainButton.show();
      }
    },
    [tg]
  );

  const hideMainButton = useCallback(() => {
    tg?.MainButton?.hide();
  }, [tg]);

  const hapticFeedback = useCallback(
    (type: "success" | "error" | "warning") => {
      tg?.HapticFeedback?.notificationOccurred(type);
    },
    [tg]
  );

  return {
    tg,
    user,
    isReady,
    colorScheme,
    themeParams,
    close,
    sendData,
    showMainButton,
    hideMainButton,
    hapticFeedback
  };
};
