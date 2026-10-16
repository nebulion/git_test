// Load iiipoints.com pages in Chrome, interact with the festival map and save every map-like image response.
import { chromium } from "playwright";
import fs from "fs";
import path from "path";

const out = "kompakt-map/source/map";
fs.mkdirSync(out, { recursive: true });
const seen = new Set();
const log = [];
const browser = await chromium.launch({ channel: "chrome" });
const ctx = await browser.newContext({ viewport: { width: 1600, height: 1200 }, deviceScaleFactor: 3 });
const page = await ctx.newPage();
page.on("response", async (res) => {
  const url = res.url();
  const type = res.headers()["content-type"] || "";
  log.push(`${res.status()} ${type} ${url}`);
  if (!/image|pdf|svg/.test(type) || seen.has(url)) return;
  if (!/map|plan|grounds|layout|site|festival|campaign/i.test(url)) return;
  seen.add(url);
  try {
    const body = await res.body();
    const name = decodeURIComponent(new URL(url).pathname).replace(/^\/+/, "").replace(/[\/]/g, "__");
    fs.writeFileSync(path.join(out, "cap__" + name), body);
  } catch (e) {}
});
for (const p of ["/", "/experience/", "/guide/", "/tables/", "/vip-plus/", "/venue-travel/"]) {
  try {
    await page.goto("https://www.iiipoints.com" + p, { waitUntil: "networkidle", timeout: 60000 });
    for (let i = 0; i < 30; i++) { await page.mouse.wheel(0, 900); await page.waitForTimeout(250); }
    // try to open / zoom any map widget
    for (const sel of ['img[src*="map"]', '[class*="map"] img', '[aria-label*="map" i]', 'button:has-text("MAP")']) {
      const els = await page.$$(sel);
      for (const el of els.slice(0, 3)) {
        try { await el.scrollIntoViewIfNeeded(); await el.click({ timeout: 3000 }); await page.waitForTimeout(1500);
              await el.dblclick({ timeout: 3000 }); await page.waitForTimeout(1500); } catch (e) {}
      }
    }
    fs.writeFileSync(path.join(out, "dom" + p.replace(/\//g, "_") + ".html"), await page.content());
  } catch (e) { log.push("ERR " + p + " " + e.message); }
}
fs.writeFileSync(path.join(out, "network.log"), log.join("\n"));
await browser.close();
