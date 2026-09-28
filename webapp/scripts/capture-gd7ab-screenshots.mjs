import {mkdirSync} from "node:fs";
import {resolve} from "node:path";
import puppeteer from "puppeteer-core";
import {baseUrl, chromePath, employeeScenarios} from "./mock-browser.mjs";

if (!chromePath) throw new Error("Không tìm thấy Chrome để chụp ảnh.");

const root = resolve(import.meta.dirname, "..", "..");
const outDir = resolve(root, "docs", "screenshots", "gd7ab");
mkdirSync(outDir, {recursive: true});

const browser = await puppeteer.launch({
  executablePath: chromePath,
  headless: "new",
  args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
});

try {
  for (const [scenario, tab, name] of employeeScenarios) {
    for (const theme of ["light", "dark"]) {
      const page = await browser.newPage();
      await page.setViewport({width: 390, height: 844, deviceScaleFactor: 1, isMobile: true});
      await page.goto(`${baseUrl}/?scenario=${scenario}&tab=${tab}&theme=${theme}`, {waitUntil: "domcontentloaded", timeout: 15000});
      await page.waitForSelector(".app-shell", {timeout: 10000});
      await page.waitForFunction(() => document.fonts?.status === "loaded" || !document.fonts, {timeout: 5000}).catch(() => {});
      await new Promise((resolve) => setTimeout(resolve, 350));
      await page.screenshot({path: resolve(outDir, `${name}_${theme}.png`)});
      await page.close();
    }
  }
} finally {
  await browser.close();
}

  console.log(`Captured ${employeeScenarios.length * 2} screenshots to ${outDir}`);
