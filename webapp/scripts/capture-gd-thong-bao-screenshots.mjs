import {mkdirSync} from "node:fs";
import {resolve} from "node:path";
import puppeteer from "puppeteer-core";
import {baseUrl, chromePath} from "./mock-browser.mjs";

if (!chromePath) throw new Error("Không tìm thấy Chrome để chụp ảnh.");
const root = resolve(import.meta.dirname, "..", "..");
const outDir = resolve(root, "docs", "screenshots", "gd-thong-bao");
mkdirSync(outDir, {recursive: true});
const browser = await puppeteer.launch({
  executablePath: chromePath,
  headless: "new",
  args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
});
try {
  for (const [scenario, name] of [["manager_messages", "01_quan_ly_tin_nhan"], ["director_messages", "02_giam_doc_tin_nhan"]]) {
    for (const theme of ["light", "dark"]) {
      const page = await browser.newPage();
      await page.setViewport({width: 390, height: 844, deviceScaleFactor: 1, isMobile: true});
      await page.goto(`${baseUrl}/?scenario=${scenario}&tab=messages&theme=${theme}`, {waitUntil: "domcontentloaded", timeout: 15000});
      await page.waitForSelector(".app-shell", {timeout: 10000});
      await new Promise((resolve) => setTimeout(resolve, 300));
      await page.screenshot({path: resolve(outDir, `${name}_${theme}.png`), fullPage: true});
      await page.close();
    }
  }
} finally {
  await browser.close();
}
console.log(`Captured screenshots to ${outDir}`);
