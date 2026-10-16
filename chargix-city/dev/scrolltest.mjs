// Loads a page, scrolls the real page to a list of fractions of the film and screenshots each, like a visitor would.
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
const [,, url, w, h, outPrefix, ...fracs] = process.argv;
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: +w, height: +h } });
const errs = [];
page.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
page.on('console', (m) => { if (m.type() === 'error') errs.push('console: ' + m.text().slice(0, 200)); });
page.on('requestfailed', (r) => errs.push('failed: ' + r.url()));
const t0 = Date.now();
await page.goto(url);
await page.waitForFunction(() => document.querySelector('.cx-city.is-ready'), null, { timeout: 300000 });
console.log('ready in', ((Date.now() - t0) / 1000).toFixed(1) + 's');
for (const f of fracs) {
  await page.evaluate((f) => {
    const t = document.querySelector('[data-cx-track]').getBoundingClientRect();
    const span = t.height - innerHeight;
    scrollTo(0, scrollY + t.top + span * +f);
  }, f);
  await page.waitForTimeout(+(process.env.SETTLE || 9000));
  await page.screenshot({ path: `${outPrefix}${f}.png` });
  console.log('shot', f);
}
console.log(errs.length ? errs.join('\n') : 'no errors');
await browser.close();
