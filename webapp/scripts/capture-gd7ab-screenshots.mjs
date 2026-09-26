import {mkdirSync} from "node:fs";
import {resolve} from "node:path";
import puppeteer from "puppeteer-core";
import {baseUrl, chromePath, scenarios} from "./mock-browser.mjs";

if (!chromePath) throw new Error("Không tìm thấy Chrome để chụp ảnh.");

const root = resolve(import.meta.dirname, "..", "..");
const outDir = resolve(root, "docs", "screenshots", "gd7ab");
mkdirSync(outDir, {recursive: true});

const browser = await puppeteer.launch({executablePath: chromePath, headless: true});

try {
  for (const [scenario, tab, name] of scenarios) {
    for (const theme of ["light", "dark"]) {
      const page = await browser.newPage();
      await page.setViewport({width: 390, height: 844, deviceScaleFactor: 1, isMobile: true});
      await page.goto(`${baseUrl}/?scenario=${scenario}&tab=${tab}&theme=${theme}`, {waitUntil: "networkidle0"});
      await page.screenshot({path: resolve(outDir, `${name}_${theme}.png`)});
      await page.close();
    }
  }
} finally {
  await browser.close();
}

console.log(`Captured ${scenarios.length * 2} screenshots to ${outDir}`);
