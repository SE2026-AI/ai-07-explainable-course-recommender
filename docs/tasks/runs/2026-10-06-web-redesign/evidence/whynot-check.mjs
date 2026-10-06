import puppeteer from "puppeteer-core";
const b = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: true });
const p = await b.newPage();
await p.goto("http://localhost:5173/", { waitUntil: "networkidle0" });
for (const id of ["AI301", "CS101", "SE201"]) {
  const chips = await p.$$('[aria-label="Chọn môn học"] button');
  for (const c of chips) if ((await c.evaluate((e) => e.textContent)) === id) { await c.click(); break; }
  await p.waitForFunction((id) => document.querySelector('[data-testid="whynot-result"]')?.textContent.startsWith(id), {}, id);
  console.log(id, "→", (await p.$eval('[data-testid="whynot-result"]', (e) => e.textContent)).slice(0, 110));
}
await b.close();
