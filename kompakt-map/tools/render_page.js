// Full-page screenshot of a local HTML file. Usage: node tools/render_page.js page.html out.png [width]
const path = require("path");
const { chromium } = require("/opt/node22/lib/node_modules/playwright");
(async () => {
  const [inp, out, width] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: +(width || 2800), height: 1000 } });
  await page.goto("file://" + path.resolve(inp));
  await page.waitForTimeout(800);
  await page.screenshot({ path: out, fullPage: true });
  await browser.close();
})();
