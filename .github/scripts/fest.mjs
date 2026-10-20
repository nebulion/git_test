// Crawl a festival site in Chrome: follow lineup/map/info links, save page text, JSON API responses,
// and images that look like maps or lineup posters. Usage: node fest.mjs <name> <start-url> [more urls...]
import { chromium } from "playwright";
import fs from "fs";
import path from "path";
const [name, ...starts] = process.argv.slice(2);
const out = `fests/${name}`;
fs.mkdirSync(out + "/img", { recursive: true });
fs.mkdirSync(out + "/json", { recursive: true });
const seen = new Set(), log = [];
const browser = await chromium.launch({ channel: "chrome" });
const page = await (await browser.newContext({ viewport: { width: 1400, height: 1000 }, locale: "en-US" })).newPage();
let n = 0;
page.on("response", async (res) => {
  const url = res.url(), type = res.headers()["content-type"] || "";
  log.push(`${res.status()} ${type} ${url}`);
  if (seen.has(url)) return;
  try {
    if (/json/.test(type) && /line|artist|program|schedule|stage|map|event|perform|act/i.test(url)) {
      seen.add(url);
      fs.writeFileSync(path.join(out, "json", `${String(++n).padStart(3, "0")}.json`), await res.body());
      log.push(`SAVED json ${n} ${url}`);
    } else if (/image|pdf/.test(type) && /map|plano|mapa|plan|lineup|line-up|cartel|poster|stage|site/i.test(url)) {
      seen.add(url);
      const fn = decodeURIComponent(new URL(url).pathname).split("/").filter(Boolean).slice(-1)[0].slice(-100);
      fs.writeFileSync(path.join(out, "img", fn), await res.body());
    }
  } catch (e) {}
});
const host = new URL(starts[0]).host;
const queue = [...starts], visited = new Set();
while (queue.length && visited.size < 14) {
  const url = queue.shift();
  if (visited.has(url)) continue;
  visited.add(url);
  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 }); await page.waitForTimeout(9000);
    for (let i = 0; i < 30; i++) { await page.mouse.wheel(0, 1000); await page.waitForTimeout(200); }
    const slug = new URL(url).pathname.replace(/\//g, "_").replace(/^_|_$/g, "") || "home";
    fs.writeFileSync(path.join(out, slug + ".txt"), await page.evaluate(() => document.body.innerText));
    fs.writeFileSync(path.join(out, slug + ".html"), await page.content());
    const links = await page.evaluate(() => [...document.querySelectorAll("a[href]")].map(a => a.href));
    for (const l of links) {
      try {
        const u = new URL(l);
        if (u.host === host && /line-?up|artists|map|mapa|plano|venue|info|faq|schedule|program/i.test(u.pathname) && !visited.has(u.href.split("#")[0]))
          queue.push(u.href.split("#")[0]);
      } catch (e) {}
    }
  } catch (e) { log.push("ERR " + url + " " + e.message); }
}
fs.writeFileSync(path.join(out, "network.log"), log.join("\n"));
fs.writeFileSync(path.join(out, "visited.txt"), [...visited].join("\n"));
await browser.close();
