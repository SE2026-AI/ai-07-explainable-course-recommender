// Real-browser check of the web MVP against the live backend (run evidence for T-10).
import puppeteer from "puppeteer-core";
import fs from "node:fs";

const OUT = process.argv[2];
const URL = "http://localhost:5173/";
const log = [];
const record = (id, ok, detail) => { log.push({ id, ok, detail }); console.log(ok ? "PASS" : "FAIL", id, detail); };

const browser = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true });
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 900 });
await page.goto(URL, { waitUntil: "networkidle0" });
await page.evaluate(() => localStorage.clear());
await page.reload({ waitUntil: "networkidle0" });

const clickButton = async (text) => {
  const handles = await page.$$("button");
  for (const h of handles) if ((await h.evaluate((b) => b.textContent)).includes(text)) return h.click();
  throw new Error(`button ${text} not found`);
};
const shot = (name) => page.screenshot({ path: `${OUT}/${name}`, fullPage: true });

// Keyboard: the primary action is reachable with Tab.
let tabs = 0, focused = "";
for (; tabs < 60; tabs++) {
  await page.keyboard.press("Tab");
  focused = await page.evaluate(() => document.activeElement?.textContent ?? "");
  if (focused.includes("Gợi ý môn học")) break;
}
record("KBD-1 primary button reachable by Tab", focused.includes("Gợi ý môn học"), `${tabs + 1} Tab presses`);
await page.keyboard.press("Enter");

// AC-1 BASE live
await page.waitForSelector('[data-testid="eligible-ST201"]', { timeout: 10000 });
const eligible = await page.$$eval('[data-testid^="eligible-"]', (els) => els.map((e) => e.dataset.testid.replace("eligible-", "")));
const ai = await page.$eval('[data-testid="ineligible-AI301"]', (e) => e.textContent);
record("AC-1 BASE eligible set", JSON.stringify(eligible) === JSON.stringify(["ST201", "SE201"]), `eligible=${eligible.join(",")}`);
record("AC-1 AI301 blocked by ST201", /ST201/.test(ai) && !eligible.includes("AI301"), ai.trim().slice(0, 120));
await shot("01-base-results-1280.png");

// AC-2 what-if via slider (React listens to input events)
// Baseline = card order + baseline rank + baseline score (what-if badges may be added to cards by design).
const baselineOf = () => page.$$eval('[data-testid^="eligible-"]', (els) => els.map((e) => [e.dataset.testid, e.querySelector(".rank")?.textContent, e.querySelector(".score")?.textContent].join("|")));
const before = await baselineOf();
await page.evaluate(() => {
  const el = [...document.querySelectorAll('input[type="range"]')][0];
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
  setter.call(el, "0.1");
  el.dispatchEvent(new Event("input", { bubbles: true }));
  const wl = [...document.querySelectorAll('input[type="range"]')][3];
  setter.call(wl, "0.8");
  wl.dispatchEvent(new Event("input", { bubbles: true }));
});
await page.waitForSelector('[data-testid="change-ST201"]', { timeout: 10000 });
await new Promise((r) => setTimeout(r, 600));
const rows = await page.$$eval('[data-testid^="change-"]', (els) => els.map((e) => e.textContent));
const after = await baselineOf();
record("AC-2 what-if comparison from /v1/simulations", rows.length === 2, rows.join(" | "));
record("AC-2 baseline list unchanged during what-if", JSON.stringify(before) === JSON.stringify(after), after.join(" ; "));
await shot("02-whatif-1280.png");
await clickButton("Hoàn tác");

// Narrow viewport
await page.setViewport({ width: 400, height: 900 });
await new Promise((r) => setTimeout(r, 300));
const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
record("UI-1 no horizontal overflow at 400px", overflow <= 0, `overflow=${overflow}px`);
await shot("03-narrow-400.png");
await page.setViewport({ width: 1280, height: 900 });

// AC-3 invalid grade
const grade = (await page.$$('input[type="number"]'))[0];
await grade.click({ clickCount: 3 });
await grade.type("11");
await clickButton("Gợi ý môn học");
await page.waitForSelector(".field-error", { timeout: 10000 });
const fieldErr = await page.$eval(".field-error", (e) => e.textContent);
record("AC-3 invalid grade shows field error", /CS101/.test(fieldErr), fieldErr);
await shot("04-invalid-grade.png");
await grade.click({ clickCount: 3 });
await grade.type("8");

// Degraded and unavailable via fault injection (backend started with AI07_ALLOW_FAULTS=1)
await page.select(".fault select", "ranking_failure");
await clickButton("Gợi ý môn học");
await page.waitForSelector('[data-testid="degraded-banner"]', { timeout: 10000 });
record("ERR-1 ranking failure shown as degraded", true, await page.$eval('[data-testid="degraded-banner"]', (e) => e.textContent.slice(0, 140)));
await shot("05-degraded.png");

await page.select(".fault select", "catalog_unavailable");
await new Promise((r) => setTimeout(r, 500));
await clickButton("Gợi ý môn học");
await page.waitForSelector('[data-testid="error-banner"]', { timeout: 10000 });
const banner = await page.$eval('[data-testid="error-banner"]', (e) => e.textContent);
const gradeKept = await page.$$eval('input[type="number"]', (els) => els[0].value);
record("AC-6 catalog outage shows 503 status and keeps draft", /503|không khả dụng/i.test(banner) && gradeKept === "8", `${banner.slice(0, 120)} | grade=${gradeKept}`);
await shot("06-unavailable.png");

// AC-5 mock mode label
await page.select(".fault select", "");
const radios = await page.$$('input[name="mode"]');
await radios[1].click();
await page.waitForSelector('[data-testid="mock-badge"]');
record("AC-5 mock mode is labeled", true, await page.$eval('[data-testid="mock-badge"]', (e) => e.textContent));

fs.writeFileSync(`${OUT}/browser-checks.json`, JSON.stringify({ date: new Date().toISOString(), browser: await browser.version(), url: URL, checks: log }, null, 2));
await browser.close();
process.exit(log.every((c) => c.ok) ? 0 : 1);
