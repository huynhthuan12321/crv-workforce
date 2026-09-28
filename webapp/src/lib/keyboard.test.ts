import {afterEach, describe, expect, it, vi} from "vitest";
import {initKeyboardAvoidance} from "./keyboard";

describe("keyboard avoidance", () => {
  afterEach(() => {
    document.body.innerHTML = "";
    document.body.className = "";
    document.documentElement.style.removeProperty("--tg-viewport-height");
    document.documentElement.style.removeProperty("--tg-viewport-stable-height");
    vi.useRealTimers();
  });

  it("adds keyboard-open on input focus and scrolls the field into view", () => {
    vi.useFakeTimers();
    document.body.innerHTML = `<input id="reason" /><button id="save">Lưu</button>`;
    const input = document.getElementById("reason") as HTMLInputElement;
    const scrollIntoView = vi.fn();
    input.scrollIntoView = scrollIntoView;
    const cleanup = initKeyboardAvoidance();

    input.focus();
    input.dispatchEvent(new FocusEvent("focusin", {bubbles: true}));
    expect(document.body.classList.contains("keyboard-open")).toBe(true);

    vi.advanceTimersByTime(310);
    expect(scrollIntoView).toHaveBeenCalledWith({block: "center", inline: "nearest", behavior: "smooth"});
    cleanup();
  });

  it("moves Enter from one-line input to the next field", () => {
    document.body.innerHTML = `<input id="first" /><input id="second" />`;
    const first = document.getElementById("first") as HTMLInputElement;
    const second = document.getElementById("second") as HTMLInputElement;
    const cleanup = initKeyboardAvoidance();

    first.focus();
    first.dispatchEvent(new KeyboardEvent("keydown", {key: "Enter", bubbles: true, cancelable: true}));
    expect(document.activeElement).toBe(second);
    cleanup();
  });
});
