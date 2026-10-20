// Render movementfestival.com pages in Chrome; save DOM, text, and every image that looks like a map or lineup.
import { chromium } from "playwright";
import fs from "fs";
import path from "path";
const out = "movement/raw";
fs.mkdirSync(out + "/img", { recursive: true });
const seen = new Set(), log = [];
const browser = await chromium.launch({ channel: "chrome" });
const page = await (await browser.newContext({ viewport: { width: 1400, height: 1000 } })).newPage();
page.on("response", async (res) => {
  const url = res.url(), type = res.headers()["content-type"] || "";
  log.push(`${res.status()} ${type} ${url}`);
  if (seen.has(url) || !/image|pdf/.test(type)) return;
  if (!/map|lineup|line-up|schedule|set.?time|stage|site|layout|grid/i.test(url)) return;
  seen.add(url);
  try {
    const name = decodeURIComponent(new URL(url).pathname).split("/").filter(Boolean).slice(-2).join("__");
    fs.writeFileSync(path.join(out, "img", name.slice(-120)), await res.body());
  } catch (e) {}
});
const pages = ["/", "/lineup", "/start-here", "/experience-page/experience", "/map", "/festival-map", "/schedule",
               "/set-times", "/faq", "/tickets", "/info"];
for (const p of pages) {
  try {
    await page.goto("https://movementfestival.com" + p, { waitUntil: "networkidle", timeout: 60000 });
    for (let i = 0; i < 25; i++) { await page.mouse.wheel(0, 900); await page.waitForTimeout(200); }
    const slug = p === "/" ? "home" : p.replace(/\//g, "_").replace(/^_/, "");
    fs.writeFileSync(path.join(out, slug + ".html"), await page.content());
    fs.writeFileSync(path.join(out, slug + ".txt"), await page.evaluate(() => document.body.innerText));
    const links = await page.evaluate(() => [...document.querySelectorAll("a[href], img[src]")].map(e => e.href || e.src));
    fs.writeFileSync(path.join(out, slug + ".links.txt"), [...new Set(links)].join("\n"));
  } catch (e) { log.push("ERR " + p + " " + e.message); }
}
fs.writeFileSync(path.join(out, "network.log"), log.join("\n"));
await browser.close();
