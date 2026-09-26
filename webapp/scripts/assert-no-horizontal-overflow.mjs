import puppeteer from "puppeteer-core";
import {baseUrl, chromePath, scenarios} from "./mock-browser.mjs";

if (!chromePath) throw new Error("Không tìm thấy Chrome để kiểm tra overflow.");

const browser = await puppeteer.launch({executablePath: chromePath, headless: true});
const failures = [];

try {
  for (const width of [360, 390]) {
    for (const theme of ["light", "dark"]) {
      for (const [scenario, tab] of scenarios) {
        const page = await browser.newPage();
        await page.setViewport({width, height: 844, deviceScaleFactor: 1, isMobile: true});
        await page.goto(`${baseUrl}/?scenario=${scenario}&tab=${tab}&theme=${theme}`, {waitUntil: "networkidle0"});
        const result = await page.evaluate(() => ({
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
        }));
        await page.close();
        if (result.scrollWidth !== result.clientWidth) {
          failures.push(`${width}px ${theme} ${scenario}: scroll=${result.scrollWidth}, client=${result.clientWidth}`);
        }
      }
    }
  }
} finally {
  await browser.close();
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log(`No horizontal overflow: ${scenarios.length * 2 * 2} cases`);
