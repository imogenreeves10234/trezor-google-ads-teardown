/*
 * Google SERP sponsored-result probe through a Gonzo residential exit.
 *
 * Usage: node serp_probe.js <CC> "<query>" <outdir> [tld] [hl]
 * Emits <outdir>/<CC>__<slug>.json  and a .png screenshot.
 *
 * Captures, for every ad slot: rank, headline, the DISPLAYED url (cite), the
 * real destination pulled out of the /aclk?...&adurl= wrapper, and the raw href.
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const https = require('https');

const CC = (process.argv[2] || 'US').toUpperCase();
const QUERY = process.argv[3] || 'trezor wallet';
const OUTDIR = process.argv[4] || '/tmp/serp';
const TLD = process.argv[5] || 'com';
const HL = process.argv[6] || 'en';

const LOCALE = { US: 'en-US', GB: 'en-GB', DE: 'de-DE', FR: 'fr-FR', NL: 'nl-NL', ES: 'es-ES', IT: 'it-IT', CA: 'en-CA', AU: 'en-AU', IN: 'en-IN', BR: 'pt-BR', JP: 'ja-JP', PL: 'pl-PL', CZ: 'cs-CZ', TR: 'tr-TR', MX: 'es-MX', ZA: 'en-ZA', SG: 'en-SG', AE: 'en-AE', CH: 'de-CH', AT: 'de-AT', SE: 'sv-SE', NO: 'nb-NO', DK: 'da-DK', FI: 'fi-FI', BE: 'nl-BE', PT: 'pt-PT', IE: 'en-IE', NZ: 'en-NZ', UA: 'uk-UA', RO: 'ro-RO', HU: 'hu-HU', GR: 'el-GR', IL: 'he-IL', KR: 'ko-KR', ID: 'id-ID', PH: 'en-PH', TH: 'th-TH', VN: 'vi-VN', NG: 'en-NG', AR: 'es-AR', CL: 'es-CL', CO: 'es-CO' }[CC] || 'en-US';
const TZ = { US: 'America/New_York', GB: 'Europe/London', DE: 'Europe/Berlin', FR: 'Europe/Paris', NL: 'Europe/Amsterdam', ES: 'Europe/Madrid', IT: 'Europe/Rome', CA: 'America/Toronto', AU: 'Australia/Sydney', IN: 'Asia/Kolkata', BR: 'America/Sao_Paulo', JP: 'Asia/Tokyo', PL: 'Europe/Warsaw', CZ: 'Europe/Prague', TR: 'Europe/Istanbul', MX: 'America/Mexico_City', ZA: 'Africa/Johannesburg', SG: 'Asia/Singapore', AE: 'Asia/Dubai', CH: 'Europe/Zurich', AT: 'Europe/Vienna', SE: 'Europe/Stockholm', NO: 'Europe/Oslo', DK: 'Europe/Copenhagen', FI: 'Europe/Helsinki', BE: 'Europe/Brussels', PT: 'Europe/Lisbon', IE: 'Europe/Dublin', NZ: 'Pacific/Auckland', UA: 'Europe/Kyiv', RO: 'Europe/Bucharest', HU: 'Europe/Budapest', GR: 'Europe/Athens', IL: 'Asia/Jerusalem', KR: 'Asia/Seoul', ID: 'Asia/Jakarta', PH: 'Asia/Manila', TH: 'Asia/Bangkok', VN: 'Asia/Ho_Chi_Minh', NG: 'Africa/Lagos', AR: 'America/Argentina/Buenos_Aires', CL: 'America/Santiago', CO: 'America/Bogota' }[CC] || 'America/New_York';

function gonzo(cc) {
  const key = fs.readFileSync('/root/.config/gonzo/key', 'utf8').trim();
  const body = JSON.stringify({ country: cc, ttl: 72, ttl_unit: 'h', format: 'ip:port:user:pass', count: 1 });
  return new Promise((resolve, reject) => {
    const req = https.request('https://api.gonzoproxy.app/functions/v1/proxy-api/generate',
      { method: 'POST', headers: { 'x-api-key': key, 'Content-Type': 'application/json' }, timeout: 45000 },
      res => { let d = ''; res.on('data', c => d += c); res.on('end', () => { try { resolve(JSON.parse(d)); } catch (e) { reject(new Error('bad json: ' + d.slice(0, 200))); } }); });
    req.on('error', reject); req.on('timeout', () => req.destroy(new Error('timeout')));
    req.write(body); req.end();
  });
}

const slug = s => s.replace(/[^a-z0-9]+/gi, '-').toLowerCase().slice(0, 50);

(async () => {
  fs.mkdirSync(OUTDIR, { recursive: true });
  const out = { cc: CC, query: QUERY, tld: TLD, hl: HL, ts: new Date().toISOString(), ok: false };

  let proxyStr;
  try {
    const g = await gonzo(CC);
    proxyStr = (g.proxies || [])[0];
    if (!proxyStr) throw new Error('no proxy returned: ' + JSON.stringify(g).slice(0, 200));
  } catch (e) { out.error = 'gonzo: ' + e.message; fs.writeFileSync(path.join(OUTDIR, `${CC}__${slug(QUERY)}.json`), JSON.stringify(out, null, 2)); console.log(JSON.stringify(out)); return; }

  const [host, port, user, pass] = proxyStr.split(':');
  out.proxy_user = user;

  const browser = await chromium.launch({
    headless: false,
    proxy: { server: `http://${host}:${port}`, username: user, password: pass },
    args: ['--no-sandbox', '--disable-blink-features=AutomationControlled', '--disable-dev-shm-usage'],
  });
  try {
    const ctx = await browser.newContext({
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
      viewport: { width: 1440, height: 1000 }, locale: LOCALE, timezoneId: TZ,
    });
    await ctx.addInitScript(() => { Object.defineProperty(navigator, 'webdriver', { get: () => undefined }); });
    const page = await ctx.newPage();

    // confirm the exit really is in-country
    try {
      const ipr = await page.goto('https://ipinfo.io/json', { timeout: 45000 });
      const j = JSON.parse(await ipr.text());
      out.exit = { ip: j.ip, country: j.country, city: j.city, org: j.org };
    } catch (e) { out.exit = { error: e.message }; }

    const url = `https://www.google.${TLD}/search?q=${encodeURIComponent(QUERY)}&hl=${HL}&gl=${CC.toLowerCase()}&num=20&pws=0`;
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 75000 });
    await page.waitForTimeout(2500);

    // EU/consent interstitial
    for (const sel of ['button:has-text("Accept all")', 'button:has-text("Alle akzeptieren")', 'button:has-text("Tout accepter")', 'button:has-text("Alles accepteren")', 'button:has-text("Aceptar todo")', 'button:has-text("Accetta tutto")', 'button:has-text("Zaakceptuj wszystko")', 'button:has-text("I agree")', '#L2AGLb']) {
      try { const b = await page.$(sel); if (b) { await b.click({ timeout: 4000 }); await page.waitForTimeout(2500); break; } } catch (e) { /* next */ }
    }
    await page.waitForTimeout(1500);
    await page.mouse.move(500, 400); await page.mouse.move(700, 620); // human signal
    await page.waitForTimeout(1200);

    out.final_url = page.url();
    const body = await page.evaluate(() => document.body.innerText.slice(0, 2500));
    out.blocked = /unusual traffic|not a robot|systems have detected/i.test(body);
    out.page_text_head = body.slice(0, 600);

    out.ads = await page.evaluate(() => {
      const seen = new Set(); const res = [];
      const anchors = Array.from(document.querySelectorAll('a[href]'));
      for (const a of anchors) {
        const href = a.href || '';
        if (!/aclk|googleadservices\.com\/pagead\/aclk|\/url\?.*adurl/i.test(href)) continue;
        // climb to the ad block
        let block = a; for (let i = 0; i < 8 && block.parentElement; i++) { block = block.parentElement; if (block.innerText && block.innerText.length > 60) break; }
        const text = (block.innerText || '').trim().slice(0, 600);
        const key = text.slice(0, 120);
        if (seen.has(key) || !text) continue; seen.add(key);
        let dest = null;
        try { const u = new URL(href); dest = u.searchParams.get('adurl') || u.searchParams.get('url') || null; } catch (e) { }
        const cite = block.querySelector('cite');
        res.push({
          headline: (block.querySelector('[role="heading"], h3, span[class]') || {}).innerText || text.split('\n')[0],
          displayed_url: cite ? cite.innerText.trim() : null,
          destination: dest,
          href_head: href.slice(0, 500),
          block_text: text,
          top_of_page: block.getBoundingClientRect().top < 900,
        });
      }
      return res;
    });
    out.ad_count = out.ads.length;
    out.ok = !out.blocked;
    await page.screenshot({ path: path.join(OUTDIR, `${CC}__${slug(QUERY)}.png`), fullPage: false });
  } catch (e) {
    out.error = (out.error ? out.error + ' | ' : '') + e.message;
  } finally { await browser.close(); }

  fs.writeFileSync(path.join(OUTDIR, `${CC}__${slug(QUERY)}.json`), JSON.stringify(out, null, 2));
  console.log(JSON.stringify({ cc: out.cc, q: out.query, exit: out.exit, blocked: out.blocked, ads: out.ad_count, err: out.error }, null, 1));
})();
