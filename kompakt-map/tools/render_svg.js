// Rasterize an SVG (with its relative fonts) to PNG using the preinstalled Chromium.
// Usage: node tools/render_svg.js in.svg out.png [scale]
const path = require("path");
const { chromium } = require("/opt/node22/lib/node_modules/playwright");

(async () => {
  const [inp, out, scale] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage({ deviceScaleFactor: +(scale || 1) });
  await page.goto("file://" + path.resolve(inp));
  await page.waitForTimeout(500);
  const box = await page.evaluate(() => {
    const s = document.querySelector("svg");
    return [s.width.baseVal.value, s.height.baseVal.value];
  });
  await page.setViewportSize({ width: Math.ceil(box[0]), height: Math.ceil(box[1]) });
  await page.screenshot({ path: out, clip: { x: 0, y: 0, width: box[0], height: box[1] } });
  await browser.close();
})();
