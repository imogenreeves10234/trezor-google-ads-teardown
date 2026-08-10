# trezor-ads-teardown — Google Sites phishing ad postmortem

**Status: DELIVERED 2026-08-09.** Report LIVE (noindex) at
**https://imogenreeves10234.github.io/trezor-google-ads-teardown/**
Repo: `imogenreeves10234/trezor-google-ads-teardown` (Pages from `/docs`, public repo, **no team
collaborators** — sensitive security research stays on the isolated account, same rule as
`lunaya-cloaking-teardown` and `ad-cloak-teardown`).

## What this was

Bob sent `x.com/BitcoinNewsCom/status/2085734257784139900` and asked for a complete teardown: what
happened, how the attackers positioned a **google.com** domain, similar ads across geos via
residential proxies, and which advertiser ran them. Everything on git, no fluff.

## The answer, in one line

A Google Search sponsored ad showed display URL **`https://www.google.com`** and advertiser name
**Trezor.io**, landing on a trezor.io clone at `sites.google.com/view/start-trezor-suite` that
harvested BIP-39 phrases. **73 wallets, 20.93 BTC, $1,349,952, in 32.9 hours.**

## Findings that matter

- **⭐ It was an ENFORCEMENT FAILURE, not a loophole.** Google's destination-mismatch policy lists as
  a violation: *"Failing to use a subdomain to clearly identify a site from all other sites hosted on
  that domain or from the parent domain."* Google Sites identifies by **path**, never subdomain, so
  that clause is **unsatisfiable** there — the ad was already prohibited in writing and ran anyway.
  🛑 **Do NOT repeat the popular explanation** ("sites.google.com and ads.google.com share the
  google.com root so the display URL is legitimate") — it was tested against the live policy in every
  formulation and **refuted 0-3**. I published that version first and had to correct it.
- **$439,226 (33%) was stolen in the 10 hours AFTER** the victim publicly named the URL and address.
  Trezor replied 15h02m later — **4h17m after the last drain and the final sweep**.
- **Treasury `bc1qhluxs8yfper7sxnmpgpjy9e38dx4qxpuhen5cs` holds 27.31 BTC unspent**, with receipts
  predating this campaign → shared across multiple campaigns. Two more wallets hold 8.59 BTC unspent.
- **18-month kit lineage**: GitBook (2025-01-23, typo *"Get strat your trezor"*) → 8 Cloudflare Pages
  subdomains → **Cloudflare blocked it 2026-07-27 as "Suspected Phishing"** → Google Sites 9 days
  later, not blocked. Cloudflare caught what Google hosted.
- **Platform pattern: 185 distinct `sites.google.com` phishing URLs, 10 crypto brands, 2020→2026.**
  **16 captured with Google Ads click params still attached → 10 campaign IDs recovered.**
  **86 use Workspace-verified lookalike domains** (`sites.google.com/ledgercom-start.com/…`) — 62
  attacker domains. **10 were still live on 2026-08-09** (Ledger, Exodus, Uniswap, Coinbase, MetaMask);
  captured "Leder Live … Official® Site®" and "Exódus®" — misspellings/homoglyphs beat brand matching.
- **The advertiser is NOT identified** and cannot be: ATC holds **zero** record. Verified with a
  passing `trezor.io` positive control (40 creatives) in the same run.
- **Source credibility**: the reporting account was **16m15s old** when it posted. "Life savings" and
  "top sponsored" are claim-only; the SERP screenshots are **@BitcoinNewsCom's, not the victim's**
  (victim's post had no media) and show a different query. The money and the page are the evidence.
- SEAL documented the same class 13–30 Mar 2026: 351–356 blocked ad URLs, $810,929 confirmed /
  $1,274,259 total.

## Tooling built (reusable)

- **`scripts/atc.py`** — Ads Transparency Center RPC client. Endpoints + field map reverse-engineered
  by capturing the live SPA's own traffic. `SearchCreatives` payload:
  `{"2":40,"3":{"8":[<geoId>],"12":{"1":"<domain>","2":true}},"7":{"1":1,"2":0,"3":-1}}`.
  Response: `1`=advertiser AR-id, `2`=creative CR-id, `4`=format, `6.1`/`7.1`=first/last shown epoch,
  `12`=advertiser name, `14`=verified domain. ⚠ **429s under sustained use** — always run the
  `trezor.io` positive control in the same pass or a negative is worthless.
- **`scripts/serp_probe.py`** — the only config that gets past Google's bot wall from this box:
  **patchright + `channel="chrome"` + `launch_persistent_context` + `no_viewport` + a benign warm-up
  search**, through a fresh Gonzo residential exit, retrying on `/sorry/`. Plain Playwright/headless
  is refused 100%. Even so ~60-75% of residential exits get `/sorry/` regardless of ISP.
- **`scripts/btc_forensics.py`**, `fleet.py`, `ad_diag.py`, `build_report.py`.

## ⚠ Traps hit (don't repeat)

- **A hand-typed epoch was a day out** and silently put all 73 drains in the "before warning" bucket.
  Compute epochs, assert them. `build_report.py` now does.
- **`ads=0` from a SERP probe is NOT "no ads".** Control query "car insurance" (UK) rendered an
  `#tads` container with **two empty slots** — Google reserves slots and declines to fill them for
  these sessions. The extractor is fine (it caught the genuine Trezor ad in ES). Report *not measured*.
- urlscan **full results are login-gated** (`/api/v1/result/` → 403) but
  **`/screenshots/<uuid>.png` is still open** — that's how the live phishing page was recovered.
- X is 402 to WebFetch; **`api.fxtwitter.com` / `api.vxtwitter.com` work** and return quoted-tweet
  media lists (that's how the screenshot provenance error was caught).

## 12-region ATC sweep — COMPLETE (61 agents, 0 control failures)

- ⭐ **`sites.google.com` returns ZERO advertisers in all 18 regions tested**, and so do 12 more
  Google-owned hosting domains. Only `google.com` (Google LLC + Business-Profile local ads) and
  `googleusercontent.com` (creative-hosting artifact) return anything — **no crypto advertiser on
  either, in any region**. The attackers' own verified lookalike domains are absent too.
- ⭐ **Two CONFIRMED advertiser-account takeovers found** — proof the mechanism is real and visible:
  **NORM REEVES INC** `AR13216877914810744833` (real Honda dealership; intruder ran a Binance
  brand-bid + 8 cloaked display creatives with **16.5h overlap with live dealer ads**, ~40h window,
  suspended) and **VISA EUROPE LTD** `AR02700591065387237377` (the real Visa Europe, 4-day takeover).
  ⚠ **Neither is connected to the Trezor campaign** (11 months earlier, different brands) — say so.
- ⚠ **Nine flagged advertisers were REFUTED — do not defame them.** The three that appear on
  `trezor.io` searches render, once the creative PNG is downloaded, as an **`affil.trezor.io`** ad
  (Trezor's own affiliate subdomain), a **Bybit** ad and an **MEXC** ad.

## ⭐ Rev 2 (2026-08-09, Bob asked for the exact advertised URLs + clearer segmentation)

- **Report RESTRUCTURED**: 17 numbered sections in document order, sticky contents bar, and an
  **"Answers, up front"** Q&A block. Bob's complaint was segmentation, not content.
- ⭐ **§10 — 16 URLs with a click-parameter RECEIPT, 11 campaign IDs, 4 still live.** Method: urlscan
  `page.domain:sites.google.com AND page.url:"gclid"|"gad_source"|"gbraid"|"gad_campaignid"` crossed
  with brand terms. Google's click redirector appends those params, so their presence proves the page
  was reached **through a paid ad**. ⚠ **~9,900 Google Sites URLs carry them in total and MOST ARE
  LEGITIMATE small businesses** — always state the crypto subset, never the raw 9,900.
  ⭐ Campaign **22897044940** ran **three** different Uniswap landing pages as each was killed —
  taking down a page does not touch the ad account.
  ⚠ **No Trezor URL is on this list** — the start-trezor-suite capture was a direct submission, not
  an ad click. Say so; the table proves the technique, not that page.
- ⭐ **§11 — `sites.google.com/ledgerstart-web.com/ledger-live/home`: NO EVIDENCE of advertising.**
  Page is LIVE and malicious. ATC 0 in US/GB/DE (control passed, routed via residential exit);
  3 urlscan captures, none with ad params; does not rank organically (Google autocorrects the "Leder"
  misspelling away). US paid check **not measured** — 6/6 exits got `/sorry/`. Verdict = dormant
  portfolio asset. ⚠ ATC-zero is WEAK evidence here — it was also zero for the Trezor campaign.
- **`scripts/atc_res.py` NEW** — ATC via curl through a Gonzo residential exit. **This is the fix for
  the 429**: the datacenter IP stays blocked for hours, a fresh residential exit works immediately.

## Open

- Advertiser of record, takedown latency, geo-targeting pattern, cloaking specifics for this URL — all
  unestablished and labelled as such on the page. 17 of 25 tested claims were killed in verification.
- US sweep had a partial blackout (HTTP 302 for 25+ min after ~70 calls), leaving 4 enrichment gaps.

See memory [[trezor-google-sites-ad-teardown]], [[google-sites-phishing-pattern]].

## ⭐ Rev 5-6 (2026-08-09/10): SEO parasite teardown + homoglyph tool + expanded sweep

- **/seo** (docs/seo/) — plain-language: how fake wallet pages rank ORGANICALLY on Google via
  parasite SEO on sites.google.com. 71 indexed pages / 22 attacker domains, per-page cards w/ reg
  dates. **/seo2** (docs/seo2/) — deep method: AI "white content" (~4,700-word ChatGPT articles,
  proven per-page markers), IDN homographs, cloaking, registrar clusters + abuse contacts + KYC ask.
- ⭐ **CRITICAL, user-caught: ledġer.app (xn--leder-y1a.app) cloaks — bare root 302s to REAL
  ledger.com; phishing lives ONLY on device paths /stax.php /nanos.php /nanox.php** (Ledger models).
  Loads ethers.js = live wallet-DRAINER, obfuscated (3.5k+ \x escapes). Registrar NICENIC (HK),
  reg 2026-05-10, Cloudflare. ⚠ LESSON: test the device/param PATHS, not just root — root cloaks.
- ⭐ **Backend answer: SEO pages harvest INLINE (30/31); ad pages iframe external payload. Not one
  backend.** Bare attacker domains = mostly dead Workspace-verification tokens (19/25).
- ⭐ **OSINT sweep (wf 21 agents): +300 look-alike domains, 91 live, 32 IDN homographs** (mostly
  trezor via NICENIC; also Dynadot, Registrar.eu). Registrar.eu 410-Gone park cluster = takedown in
  progress. Several homograph variants registered-but-not-serving (pre-positioned). Data:
  data/osint_expanded.json, data/osint_synthesis.md, data/registrar_clusters.json.
- ⭐ **Homoglyph educational tool** — homoglyph/homoglyph.py (word↔xn-- + decode/defence) + gated CF
  Worker (3 users, Basic Auth) at homoglyph-tool.fleet-fefsba.workers.dev. ⚠ worker.js gitignored
  (holds pwds); creds in /root/.config/homoglyph-tool/creds.json. See memory [[homoglyph-idn-attack]].
- Registrar abuse desks: NICENIC abuse@nicenic.net, WebNic compliance@web.cc, BigRock abuse@bigrock.com,
  Registrar.eu/Openprovider abuse@openprovider.eu.
