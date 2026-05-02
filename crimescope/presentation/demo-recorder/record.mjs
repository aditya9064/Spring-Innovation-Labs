// CrimeScope demo recorder — drives the running app at http://localhost:3000
// and saves a silent .webm video. Run `npm run encode` afterwards for .mp4.
//
// Assumes:
//   - Backend on http://127.0.0.1:8000 (uvicorn)
//   - Frontend on http://localhost:3000 (next dev)
//
// Output:
//   out/video.webm  (raw Playwright recording)
//   out/demo.mp4    (after `npm run encode`)

import { chromium } from "playwright";
import { mkdir, rm, readdir, rename } from "node:fs/promises";
import path from "node:path";

const BASE = "http://localhost:3000";
const OUT = path.resolve("out");
const VIEWPORT = { width: 1440, height: 900 };

// ── tiny helpers ────────────────────────────────────────────────────────────
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function step(label, fn) {
  const t0 = Date.now();
  process.stdout.write(`  • ${label} ... `);
  try {
    await fn();
    console.log(`ok (${Date.now() - t0}ms)`);
  } catch (e) {
    console.log(`FAIL (${Date.now() - t0}ms)`);
    throw e;
  }
}

// Click a button/link by visible text inside a region. Tolerant of layout.
async function clickText(page, text, opts = {}) {
  const loc = page.getByText(text, { exact: opts.exact ?? true }).first();
  await loc.waitFor({ state: "visible", timeout: 8000 });
  await loc.click();
}

async function navTo(page, label) {
  // Left-rail nav uses the label text (DASH, REPORT, COMPARE, ...)
  await page.locator(`a[title="${label}"]`).first().click();
}

// ── warm-up: compile every route in Next dev so the recording is smooth ────
async function warmup(page) {
  const routes = ["/", "/live", "/compare", "/simulator", "/reports", "/alerts", "/blindspots", "/audit", "/analyst"];
  for (const r of routes) {
    await page.goto(BASE + r, { waitUntil: "networkidle", timeout: 60000 }).catch(() => {});
    await sleep(200);
  }
  await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
}

// ── main demo flow ─────────────────────────────────────────────────────────
async function runDemo(page) {
  // Open dashboard
  await step("open dashboard", async () => {
    await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForSelector("text=CRIMESCOPE", { timeout: 10000 });
    await sleep(2000);
  });

  // Switch city to UK (England & Wales — MSOA)
  await step("switch city → England & Wales", async () => {
    const select = page.locator('select[aria-label="City selector"]');
    await select.selectOption("uk");
    await sleep(3500); // map fly + scores reload
  });

  // Linger on KPI strip + platform pills
  await step("show KPIs / platform pills", async () => {
    await sleep(2500);
  });

  // Persona walkthrough — INS → BUY (real-estate) → PLN (planner) → INS
  await step("persona: BUY (buyer / real-estate)", async () => {
    await page.locator('button:has-text("BUY")').first().click();
    await sleep(2000);
  });
  await step("persona: PLN (urban planner)", async () => {
    await page.locator('button:has-text("PLN")').first().click();
    await sleep(2000);
  });
  await step("persona: INS (insurer, primary)", async () => {
    await page.locator('button:has-text("INS")').first().click();
    await sleep(1500);
  });

  // View-mode walkthrough — VERIFIED → BLENDED → LIVE
  await step("view mode: VERIFIED", async () => {
    await page.locator('button:has-text("VERIFIED")').first().click();
    await sleep(1800);
  });
  await step("view mode: LIVE", async () => {
    await page.locator('button:has-text("LIVE")').first().click();
    await sleep(1800);
  });
  await step("view mode: BLENDED", async () => {
    await page.locator('button:has-text("BLENDED")').first().click();
    await sleep(1500);
  });

  // Reports — auto-loads default region for current city (E02000001)
  await step("nav → REPORT (City of London 001)", async () => {
    await navTo(page, "REPORT");
    await page.waitForLoadState("networkidle", { timeout: 30000 });
    await sleep(3000);
  });
  await step("scroll report down (drivers / pricing)", async () => {
    await page.mouse.wheel(0, 600);
    await sleep(2200);
    await page.mouse.wheel(0, 600);
    await sleep(2200);
    await page.mouse.wheel(0, -1200);
    await sleep(1500);
  });

  // Compare two regions side-by-side
  await step("nav → COMPARE", async () => {
    await navTo(page, "COMPARE");
    await page.waitForLoadState("networkidle", { timeout: 30000 });
    await sleep(3500);
  });

  // Counterfactual / simulator
  await step("nav → SIM (counterfactual)", async () => {
    await navTo(page, "SIM");
    await page.waitForLoadState("networkidle", { timeout: 30000 });
    await sleep(3000);
  });

  // Audit trail — Persistent + compliance buy-word
  await step("nav → AUDIT (decision audit trail)", async () => {
    await navTo(page, "AUDIT");
    await page.waitForLoadState("networkidle", { timeout: 30000 });
    await sleep(3000);
  });

  // Analyst tab — Genie / NL surface
  await step("nav → ANALYST (NL surface)", async () => {
    await navTo(page, "ANALYST");
    await page.waitForLoadState("networkidle", { timeout: 30000 });
    await sleep(3500);
  });

  // Back to dashboard, open AI Analyst side-panel chat
  await step("back to DASH", async () => {
    await navTo(page, "DASH");
    await page.waitForLoadState("networkidle", { timeout: 30000 });
    await sleep(2000);
  });
  await step("open AI ANALYST panel", async () => {
    await page.locator('button:has-text("AI ANALYST")').first().click();
    await sleep(2500);
  });

  // Final hold on the dashboard
  await step("hold final frame", async () => {
    await sleep(3000);
  });
}

// ── orchestrator ───────────────────────────────────────────────────────────
async function main() {
  await rm(OUT, { recursive: true, force: true });
  await mkdir(OUT, { recursive: true });

  console.log("→ launching chromium");
  const browser = await chromium.launch({ headless: true });

  console.log("→ warmup pass (compiles every Next.js route)");
  const warmCtx = await browser.newContext({ viewport: VIEWPORT });
  const warmPage = await warmCtx.newPage();
  await warmup(warmPage);
  await warmCtx.close();

  console.log("→ recording pass");
  const ctx = await browser.newContext({
    viewport: VIEWPORT,
    recordVideo: { dir: OUT, size: VIEWPORT },
    deviceScaleFactor: 2,
  });
  const page = await ctx.newPage();

  const t0 = Date.now();
  try {
    await runDemo(page);
  } finally {
    const video = page.video();
    await ctx.close();
    if (video) {
      // rename whatever Playwright dropped to a stable name
      const files = await readdir(OUT);
      const webm = files.find((f) => f.endsWith(".webm"));
      if (webm && webm !== "video.webm") {
        await rename(path.join(OUT, webm), path.join(OUT, "video.webm"));
      }
    }
    await browser.close();
  }

  const seconds = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`\n✓ recording complete (${seconds}s of footage) → out/video.webm`);
  console.log("  next: npm run encode    # produces out/demo.mp4");
}

main().catch((e) => {
  console.error("\n✗ recording failed:", e);
  process.exit(1);
});
