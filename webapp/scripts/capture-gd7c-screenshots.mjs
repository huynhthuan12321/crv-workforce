import {mkdirSync} from "node:fs";
import {resolve} from "node:path";
import puppeteer from "puppeteer-core";
import {baseUrl, chromePath, managerScenarios} from "./mock-browser.mjs";

if (!chromePath) throw new Error("Không tìm thấy Chrome để chụp ảnh.");

const root = resolve(import.meta.dirname, "..", "..");
const outDir = resolve(root, "docs", "screenshots", "gd7c");
mkdirSync(outDir, {recursive: true});

const browser = await puppeteer.launch({executablePath: chromePath, headless: true});

try {
  for (const [scenario, tab, name] of managerScenarios) {
    for (const theme of ["light", "dark"]) {
      const page = await browser.newPage();
      await page.setViewport({width: 390, height: 844, deviceScaleFactor: 1, isMobile: true});
      page.on("dialog", (dialog) => dialog.accept());
      await page.goto(`${baseUrl}/?scenario=${scenario}&tab=${tab}&theme=${theme}`, {waitUntil: "networkidle0"});
      if (scenario === "manager_already_handled") {
        await page.$$eval("button", (buttons) => {
          const target = buttons.find((button) => button.textContent?.includes("Đã xem"));
          target?.click();
        });
        await page.waitForNetworkIdle({idleTime: 300, timeout: 3000}).catch(() => {});
      }
      if (scenario === "manager_lock_open") {
        await page.$$eval("button.switch.on", (buttons) => buttons[0]?.click());
        await page.waitForNetworkIdle({idleTime: 300, timeout: 3000}).catch(() => {});
      }
      await page.screenshot({path: resolve(outDir, `${name}_${theme}.png`)});
      await page.close();
    }
  }
} finally {
  await browser.close();
}

console.log(`Captured ${managerScenarios.length * 2} screenshots to ${outDir}`);
