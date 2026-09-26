# Telegram Mini App Theming

## Overview
Telegram provides theme parameters for Mini Apps. The `useTelegram` hook applies these values to CSS custom properties for consistent light/dark theming.

## Quick Links
- [Frontend Guide](frontend-guide.md)
- [Mini Apps Overview](README.md)

## How Theming Works
In `useTelegram`, theme parameters are mapped to CSS variables:

```ts
const map: Record<string, string> = {
  bg_color: "--tg-theme-bg-color",
  text_color: "--tg-theme-text-color",
  hint_color: "--tg-theme-hint-color",
  link_color: "--tg-theme-link-color",
  button_color: "--tg-theme-button-color",
  button_text_color: "--tg-theme-button-text-color",
  secondary_bg_color: "--tg-theme-secondary-bg-color"
};
```

These variables are then available in CSS:

```css
.app {
  background: var(--tg-theme-bg-color);
  color: var(--tg-theme-text-color);
}
```

## Color Scheme
You can also use the provided `colorScheme`:

```ts
const { colorScheme } = useTelegram();
```

In `App.tsx` the scheme is applied as a class:

```tsx
<div className={`app app--${colorScheme}`}>
```

## Adding Custom Theme Tokens
Define additional variables in your CSS and set defaults:

```css
:root {
  --card-bg: #ffffff;
  --card-border: #e5e7eb;
}
```

Override them with Telegram theme params if desired.

## Common Issues

### Colors do not change
**Symptoms:** App remains in default colors.
**Cause:** Telegram theme params not applied.
**Solution:** Ensure `useTelegram()` is called and `tg.ready()` is executed.

### Low contrast
**Symptoms:** Text is hard to read in dark mode.
**Cause:** Custom colors override Telegram values.
**Solution:** Prefer Telegram tokens and test in both themes.

## Best Practices

1. DO use Telegram theme variables as the base.
2. DO test in light and dark modes.
3. DO avoid hard-coded colors for text and backgrounds.

## Next Steps
- Customize UI in [Frontend Guide](frontend-guide.md)
- Review [Security](security.md)
