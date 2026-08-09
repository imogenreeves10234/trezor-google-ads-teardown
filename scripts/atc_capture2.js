// Navigate straight to an ATC results URL and capture the SearchCreatives RPC shape.
const { chromium } = require('playwright');
const fs = require('fs');

const TARGET = process.argv[2]; // full ATC url
const OUT = process.argv[3] || '/tmp/atc_capture2.json';

(async () => {
  const browser = await chromium.launch({ headless: false, args: ['--no-sandbox', '--disable-blink-features=AutomationControlled'] });
  const ctx = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    viewport: { width: 1440, height: 900 }, locale: 'en-US',
  });
  const calls = [];
  ctx.on('request', req => {
    if (req.url().includes('/anji/_/rpc/')) calls.push({ dir: 'req', url: req.url(), postData: req.postData() });
  });
  ctx.on('response', async res => {
    if (res.url().includes('/anji/_/rpc/')) {
      let body = null; try { body = await res.text(); } catch (e) { body = 'ERR'; }
      calls.push({ dir: 'res', url: res.url(), status: res.status(), body: body ? body.slice(0, 400000) : null });
    }
  });
  const page = await ctx.newPage();
  await page.goto(TARGET, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(7000);
  for (let i = 0; i < 4; i++) { await page.mouse.wheel(0, 2000); await page.waitForTimeout(2500); }
  const text = await page.evaluate(() => document.body.innerText.slice(0, 4000));
  fs.writeFileSync(OUT, JSON.stringify({ target: TARGET, finalUrl: page.url(), pageText: text, calls }, null, 2));
  console.log('final:', page.url());
  console.log('--- page text ---'); console.log(text.slice(0, 1500));
  for (const c of calls) {
    if (c.dir === 'req') console.log('REQ', c.url.split('/rpc/')[1].split('?')[0], '|', decodeURIComponent(c.postData || '').slice(0, 500));
    else console.log('RES', c.url.split('/rpc/')[1].split('?')[0], c.status, 'len', (c.body || '').length);
  }
  await browser.close();
})();
