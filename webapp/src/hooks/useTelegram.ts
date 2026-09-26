import { useCallback, useEffect, useState } from "react";

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
    if (!tg?.themeParams) return;
    const root = document.documentElement;
    const params = tg.themeParams;
    const map: Record<string, string> = {
      bg_color: "--tg-theme-bg-color",
      text_color: "--tg-theme-text-color",
      hint_color: "--tg-theme-hint-color",
      link_color: "--tg-theme-link-color",
      button_color: "--tg-theme-button-color",
      button_text_color: "--tg-theme-button-text-color",
      secondary_bg_color: "--tg-theme-secondary-bg-color"
    };

    Object.entries(map).forEach(([key, cssVar]) => {
      const value = params[key as keyof typeof params];
      if (value) {
        root.style.setProperty(cssVar, value);
      }
    });
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
