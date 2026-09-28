import puppeteer from "puppeteer-core";
import {baseUrl, chromePath, scenarios} from "./mock-browser.mjs";

if (!chromePath) throw new Error("Không tìm thấy Chrome để kiểm tra overflow.");

const browser = await puppeteer.launch({
  executablePath: chromePath,
  headless: "new",
  args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
});
const failures = [];

try {
  const widths = [360, 390, 430];
  for (const width of widths) {
    for (const theme of ["light", "dark"]) {
      for (const [scenario, tab] of scenarios) {
        const page = await browser.newPage();
        await page.setViewport({width, height: 844, deviceScaleFactor: 1, isMobile: true});
        await page.goto(`${baseUrl}/?scenario=${scenario}&tab=${tab}&theme=${theme}`, {waitUntil: "domcontentloaded", timeout: 15000});
        await page.waitForSelector(".app-shell", {timeout: 10000});
        await page.waitForFunction(() => document.fonts?.status === "loaded" || !document.fonts, {timeout: 5000}).catch(() => {});
        await new Promise((resolve) => setTimeout(resolve, 150));
        const result = await page.evaluate(() => ({
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
          clipped: Array.from(document.querySelectorAll(".bottom-tabs button, .bottom-tabs button em, .chip"))
            .filter((el) => el.scrollWidth > el.clientWidth + 1)
            .map((el) => `${el.className || el.tagName}: ${el.textContent?.trim()} (${el.scrollWidth}>${el.clientWidth})`),
          verticalText: Array.from(document.querySelectorAll(".session-row span, .session-row b, .session-row small, .session-row strong, .history-block .chip"))
            .filter((el) => {
              const text = el.textContent?.trim() || "";
              const rect = el.getBoundingClientRect();
              if (!text || rect.width === 0 || rect.height === 0) return false;
              const lineHeightRaw = window.getComputedStyle(el).lineHeight;
              const fontSize = Number.parseFloat(window.getComputedStyle(el).fontSize) || 12;
              const lineHeight = lineHeightRaw === "normal" ? fontSize * 1.25 : Number.parseFloat(lineHeightRaw);
              const tooNarrow = text.length >= 12 && rect.width < 80;
              const tooTall = lineHeight > 0 && rect.height > lineHeight * 4.2;
              return tooNarrow || tooTall;
            })
            .map((el) => `${el.tagName}.${el.className || ""}: ${el.textContent?.trim()} (${Math.round(el.getBoundingClientRect().width)}x${Math.round(el.getBoundingClientRect().height)})`),
        }));
        await page.close();
        if (result.scrollWidth !== result.clientWidth) {
          failures.push(`${width}px ${theme} ${scenario}: scroll=${result.scrollWidth}, client=${result.clientWidth}`);
        }
        if (result.clipped.length) {
          failures.push(`${width}px ${theme} ${scenario}: clipped ${result.clipped.join("; ")}`);
        }
        if (result.verticalText.length) {
          failures.push(`${width}px ${theme} ${scenario}: vertical text ${result.verticalText.join("; ")}`);
        }
      }
    }
  }

  for (const width of widths) {
    const page = await browser.newPage();
    await page.setViewport({width, height: 844, deviceScaleFactor: 1, isMobile: true});
    await page.goto(`${baseUrl}/?scenario=manager_employee_assign&tab=employees&theme=light`, {waitUntil: "domcontentloaded", timeout: 15000});
    await page.waitForSelector(".app-shell", {timeout: 10000});
    await page.waitForSelector("textarea", {timeout: 10000});
    await page.setViewport({width, height: 400, deviceScaleFactor: 1, isMobile: true});
    await page.evaluate(() => {
      document.documentElement.style.setProperty("--tg-viewport-height", "400px");
    });
    await page.focus("textarea");
    await page.evaluate(() => document.body.classList.add("keyboard-open"));
    await new Promise((resolve) => setTimeout(resolve, 350));
    const keyboardResult = await page.evaluate(() => {
      const focused = document.activeElement;
      const submit = Array.from(document.querySelectorAll("button"))
        .find((button) => button.textContent?.includes("Xác nhận") || button.textContent?.includes("XÃ¡c nháº­n"));
      const tabBar = document.querySelector(".bottom-tabs");
      const focusedRect = focused instanceof HTMLElement ? focused.getBoundingClientRect() : null;
      const submitRect = submit instanceof HTMLElement ? submit.getBoundingClientRect() : null;
      const tabStyle = tabBar ? window.getComputedStyle(tabBar) : null;
      const viewportHeight = window.visualViewport?.height || window.innerHeight;
      return {
        focusedVisible: Boolean(focusedRect && focusedRect.top >= 0 && focusedRect.bottom <= viewportHeight),
        submitVisible: Boolean(submitRect && submitRect.top >= 0 && submitRect.bottom <= viewportHeight),
        tabHidden: !tabStyle || tabStyle.visibility === "hidden" || tabStyle.pointerEvents === "none",
        focusedRect: focusedRect ? `${Math.round(focusedRect.top)}-${Math.round(focusedRect.bottom)}` : "none",
        submitRect: submitRect ? `${Math.round(submitRect.top)}-${Math.round(submitRect.bottom)}` : "none",
      };
    });
    await page.close();
    if (!keyboardResult.focusedVisible || !keyboardResult.submitVisible || !keyboardResult.tabHidden) {
      failures.push(`${width}px keyboard: focused=${keyboardResult.focusedVisible} ${keyboardResult.focusedRect}, submit=${keyboardResult.submitVisible} ${keyboardResult.submitRect}, tabHidden=${keyboardResult.tabHidden}`);
    }
  }
} finally {
  await browser.close();
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log(`No horizontal overflow: ${scenarios.length * 2 * 3} cases`);
