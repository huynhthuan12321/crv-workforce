import {useEffect} from "react";

const FOCUSABLE_SELECTOR = "input, textarea, select";
const KEYBOARD_CLASS = "keyboard-open";

function setViewportVars() {
  const tg = window.Telegram?.WebApp;
  const stableHeight = tg?.viewportStableHeight || window.visualViewport?.height || window.innerHeight;
  const height = tg?.viewportHeight || window.visualViewport?.height || window.innerHeight;
  document.documentElement.style.setProperty("--tg-viewport-stable-height", `${Math.round(stableHeight)}px`);
  document.documentElement.style.setProperty("--tg-viewport-height", `${Math.round(height)}px`);
}

function isEditableElement(target: EventTarget | null): target is HTMLElement {
  return target instanceof HTMLElement && target.matches(FOCUSABLE_SELECTOR);
}

function hasFocusedField() {
  return isEditableElement(document.activeElement);
}

function isTelegramViewportShrunk() {
  const tg = window.Telegram?.WebApp;
  if (!tg?.viewportHeight || !tg.viewportStableHeight) return false;
  return tg.viewportStableHeight - tg.viewportHeight > 80;
}

function isVisualViewportShrunk() {
  if (!window.visualViewport) return false;
  return window.innerHeight - window.visualViewport.height > 80;
}

function updateKeyboardClass(force?: boolean) {
  setViewportVars();
  const open = force ?? (hasFocusedField() || isTelegramViewportShrunk() || isVisualViewportShrunk());
  document.body.classList.toggle(KEYBOARD_CLASS, open);
}

function scrollFocusedIntoView() {
  const element = document.activeElement;
  if (!isEditableElement(element)) return;
  window.setTimeout(() => {
    element.scrollIntoView({block: "center", inline: "nearest", behavior: "smooth"});
  }, 300);
}

function handleReturnKey(event: KeyboardEvent) {
  if (!(event.target instanceof HTMLInputElement || event.target instanceof HTMLSelectElement)) return;
  if (event.key !== "Enter") return;
  event.preventDefault();
  const fields = Array.from(document.querySelectorAll<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(
    `${FOCUSABLE_SELECTOR}:not([disabled]):not([readonly])`,
  ));
  const index = fields.indexOf(event.target);
  const next = fields[index + 1];
  if (next) next.focus();
  else event.target.blur();
}

export function initKeyboardAvoidance() {
  setViewportVars();
  const tg = window.Telegram?.WebApp;
  const onFocusIn = (event: FocusEvent) => {
    if (!isEditableElement(event.target)) return;
    document.body.classList.add(KEYBOARD_CLASS);
    scrollFocusedIntoView();
  };
  const onFocusOut = () => {
    window.setTimeout(() => {
      if (!hasFocusedField()) updateKeyboardClass(false);
    }, 80);
  };
  const onViewportChanged = () => {
    updateKeyboardClass();
    scrollFocusedIntoView();
  };

  document.addEventListener("focusin", onFocusIn);
  document.addEventListener("focusout", onFocusOut);
  document.addEventListener("keydown", handleReturnKey);
  window.visualViewport?.addEventListener("resize", onViewportChanged);
  window.visualViewport?.addEventListener("scroll", onViewportChanged);
  window.addEventListener("resize", onViewportChanged);
  tg?.onEvent?.("viewportChanged", onViewportChanged);

  return () => {
    document.removeEventListener("focusin", onFocusIn);
    document.removeEventListener("focusout", onFocusOut);
    document.removeEventListener("keydown", handleReturnKey);
    window.visualViewport?.removeEventListener("resize", onViewportChanged);
    window.visualViewport?.removeEventListener("scroll", onViewportChanged);
    window.removeEventListener("resize", onViewportChanged);
    tg?.offEvent?.("viewportChanged", onViewportChanged);
    document.body.classList.remove(KEYBOARD_CLASS);
  };
}

export function useKeyboardAvoidance() {
  useEffect(() => initKeyboardAvoidance(), []);
}
