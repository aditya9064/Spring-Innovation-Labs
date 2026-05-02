// Capture before/after screenshots of two personas on the same region
// to prove the persona toggle now produces visible UI change.
import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";

const BASE = "http://localhost:3000";
const OUT = "out";
const VIEWPORT = { width: 1440, height: 900 };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function snap(page, persona, file) {
  await page.locator(`button:has-text("${persona}")`).first().click();
  await sleep(2000);
  await page.screenshot({ path: `${OUT}/${file}`, fullPage: false });
  console.log("  saved", file);
}

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: VIEWPORT, deviceScaleFactor: 2 });
const page = await ctx.newPage();
await mkdir(OUT, { recursive: true });

console.log("→ load + switch to UK");
await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
await page.locator('select[aria-label="City selector"]').selectOption("uk");
await sleep(4000);

console.log("→ snapshots");
await snap(page, "INS", "persona_ins.png");
await snap(page, "RES", "persona_res.png");
await snap(page, "BUY", "persona_buy.png");
await snap(page, "BIZ", "persona_biz.png");
await snap(page, "PLN", "persona_pln.png");

await ctx.close();
await browser.close();
console.log("✓ done");
