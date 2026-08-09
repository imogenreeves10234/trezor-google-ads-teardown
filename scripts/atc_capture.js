// Capture the real Ads Transparency Center RPC request/response shapes.
// Opens ATC, searches an advertiser/domain term, records every /anji/_/rpc/ call.
const { chromium } = require('playwright');
const fs = require('fs');

const TERM = process.argv[2] || 'trezor';
const REGION = process.argv[3] || 'US';
const OUT = process.argv[4] || '/tmp/atc_capture.json';

(async () => {
  const browser = await chromium.launch({ headless: false, args: ['--no-sandbox', '--disable-blink-features=AutomationControlled'] });
  const ctx = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    viewport: { width: 1440, height: 900 }, locale: 'en-US',
  });
  const calls = [];
  ctx.on('request', req => {
    const u = req.url();
    if (u.includes('/anji/_/rpc/')) {
      calls.push({ dir: 'req', url: u, method: req.method(), postData: req.postData() });
    }
  });
  ctx.on('response', async res => {
    const u = res.url();
    if (u.includes('/anji/_/rpc/')) {
      let body = null;
      try { body = await res.text(); } catch (e) { body = 'ERR:' + e.message; }
      calls.push({ dir: 'res', url: u, status: res.status(), body: body ? body.slice(0, 200000) : null });
    }
  });

  const page = await ctx.newPage();
  const url = `https://adstransparency.google.com/?region=${REGION}`;
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(4000);

  // type into the search box
  try {
    const box = await page.waitForSelector('input[aria-label*="Search"], input[type="text"], input', { timeout: 20000 });
    await box.click();
    await box.type(TERM, { delay: 120 });
    await page.waitForTimeout(3500); // let suggest RPC fire
    await page.keyboard.press('Enter');
  } catch (e) {
    console.error('search box fail:', e.message);
  }
  await page.waitForTimeout(9000);
  // scroll to trigger creative load
  for (let i = 0; i < 3; i++) { await page.mouse.wheel(0, 1600); await page.waitForTimeout(2500); }

  fs.writeFileSync(OUT, JSON.stringify({ term: TERM, region: REGION, finalUrl: page.url(), calls }, null, 2));
  console.log('final URL:', page.url());
  console.log('captured RPC calls:', calls.length);
  for (const c of calls) {
    if (c.dir === 'req') console.log('REQ', c.url.split('/rpc/')[1].split('?')[0], '|', (c.postData || '').slice(0, 400));
    else console.log('RES', c.url.split('/rpc/')[1].split('?')[0], c.status, 'len', (c.body || '').length);
  }
  await browser.close();
})();
