// usage: node dev/batch.mjs W H out1.png "url1" out2.png "url2" ...
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
const [,, w, h, ...rest] = process.argv;
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: +w, height: +h } });
page.on('pageerror', (e) => console.log('pageerror:', e.message));
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log('console:', m.text().slice(0, 200)); });
for (let i = 0; i < rest.length; i += 2) {
  const [out, url] = [rest[i], rest[i + 1]];
  const t0 = Date.now();
  await page.goto(url);
  await page.waitForFunction(() => document.title.startsWith('done'), null, { timeout: +(process.env.T || 200000) }).catch((e) => console.log('timeout', e.message));
  await page.waitForTimeout(+(process.env.SETTLE || 1500));
  await page.screenshot({ path: out, timeout: 150000 }).catch((e) => console.log('shot failed', out, e.message.split('\n')[0]));
  console.log(out, ((Date.now() - t0) / 1000).toFixed(1) + 's', await page.title());
}
await browser.close();
