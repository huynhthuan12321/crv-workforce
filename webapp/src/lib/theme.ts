type ThemeParams = NonNullable<Window["Telegram"]>["WebApp"]["themeParams"];

const lightTheme = {
  bg_color: "#f4f7fb",
  text_color: "#17202a",
  hint_color: "#6f7c8a",
  button_color: "#0d6efd",
  button_text_color: "#ffffff",
  secondary_bg_color: "#ffffff",
};

const darkTheme = {
  bg_color: "#0f1720",
  text_color: "#edf5ff",
  hint_color: "#9aa8b6",
  button_color: "#2d8cff",
  button_text_color: "#ffffff",
  secondary_bg_color: "#17212b",
};

const cssMap: Record<keyof typeof lightTheme, string> = {
  bg_color: "--tg-theme-bg-color",
  text_color: "--tg-theme-text-color",
  hint_color: "--tg-theme-hint-color",
  button_color: "--tg-theme-button-color",
  button_text_color: "--tg-theme-button-text-color",
  secondary_bg_color: "--tg-theme-secondary-bg-color",
};

function setColorVars(params: Partial<typeof lightTheme>) {
  const root = document.documentElement;
  Object.entries(cssMap).forEach(([key, cssVar]) => {
    const value = params[key as keyof typeof lightTheme];
    if (value) root.style.setProperty(cssVar, value);
  });
}

export function applyTelegramTheme(colorScheme?: "light" | "dark", themeParams?: ThemeParams) {
  const fallback = colorScheme === "dark" ? darkTheme : lightTheme;
  document.documentElement.dataset.crvTheme = colorScheme || "light";
  setColorVars({...fallback, ...themeParams});
}

export function applyMockTheme(theme: "light" | "dark") {
  applyTelegramTheme(theme, theme === "dark" ? darkTheme : lightTheme);
}

export function mockThemeFromUrl(): "light" | "dark" {
  const value = new URLSearchParams(window.location.search).get("theme");
  if (value === "dark" || value === "light") return value;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
