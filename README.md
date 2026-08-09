# The phishing ad that displayed `google.com`

Teardown of the Google Search sponsored result that impersonated Trezor, landed on a phishing page
hosted on **Google Sites**, and harvested hardware-wallet recovery phrases — 5–7 August 2026.

**Report → https://imogenreeves10234.github.io/trezor-google-ads-teardown/**

---

## Headline findings

| | |
|---|---|
| Stolen | **$1,349,952** — 20.9324 BTC across **73** victim wallet drains, valued at each drain's own block time |
| Window | **32.9 hours**, 2026-08-05 21:08:55 → 2026-08-07 06:00:44 UTC |
| After the public warning | **$439,226** (25 drains, 33% of the total) taken in the 10 hours *after* the victim named the URL and the address publicly |
| Display URL shown in the ad | `https://www.google.com` — advertiser name `Trezor.io`, out-ranking the genuine Trezor ad |
| Kit age | **18 months** — GitBook (Jan 2025) → 8 Cloudflare Pages subdomains → Google Sites (Aug 2026) |
| Platform pattern | **185** distinct `sites.google.com` phishing URLs across **10** crypto brands, 2020→2026; **10 still live** when checked |
| Paid distribution | **16** of those URLs captured with Google Ads click parameters attached; **10** campaign IDs recovered |
| Transparency record | **Zero.** `sites.google.com` returns no creatives in the Ads Transparency Center |

## The mechanic

Google's *Destination mismatch* policy defines the violation as *"The domain or domain extension in
the display URL doesn't match the final and mobile URLs where users are taken to"*, and its own
worked example of a violation is literally *"Display URL: google.com and Final URL: example.com"*.

By hosting the phishing page **on Google's own domain**, the attacker made display domain and final
domain genuinely identical. The ad was not evading the destination rule — it was complying with it.

Two variants observed:

- `sites.google.com/view/<name>` — anonymous, free, needs only a Google account (98 of 185)
- `sites.google.com/<attacker-domain>.com/<page>` — a **Google Workspace** Site published under a
  *verified* lookalike domain, so the URL carries google.com **and** a brand-lookalike string
  (86 of 185, across 62 attacker-verified domains such as `trzrio.com`, `ledgercom-start.com`,
  `metamsklgin.com`)

## Repository layout

```
scripts/
  atc.py                 Ads Transparency Center RPC client (endpoints + field map reverse-engineered
                         from the live SPA's own traffic; includes a positive-control mode)
  atc_capture.js         Captures the real ATC RPC request/response shapes from a headful browser
  atc_capture2.js        Same, for a direct results URL (SearchCreatives shape)
  btc_forensics.py       Full chain history, deposits vs sweeps, per-deposit USD at block time
  serp_probe.py          Google SERP probe: patchright + real Chrome persistent profile through a
                         Gonzo residential exit, with fresh-exit retry
  serp_probe.js          First (blocked) Playwright attempt, kept for the record
  ad_diag.py             Distinguishes "selector missed the ads" from "Google served no ads"
  fleet.py               Runs the probe across geo x query under a hard concurrency cap
  build_report.py        Renders docs/index.html from data/*.json

data/
  btc_forensics.json     73 deposits, 7 sweeps, counterparties, USD at receipt
  hop1.json              Hop-1 consolidation wallets
  treasury_feeders.json  The shared treasury's feeder addresses (other campaigns)
  timeline.json          Master timeline, each event stamped relative to the public warning
  urlscan_search.json    All 41 public captures of the kit
  gsites_crypto_scan.json / gsites_unique.json / gsites_liveness.json
  ecosystem.json         185 URLs, campaign IDs, attacker domains, liveness
  atc_suggest_trezor.json   ATC advertiser autocomplete across 20 regions
  geo_summary.json       36 SERP probes across 18 countries
  serp_method_limitation.json / atc_rate_limit.json   what the instruments could NOT measure
  phishing_page_20260805.png, tweet_img*.jpg          evidence images

geo/    per-probe JSON + screenshots
docs/   the published report
```

## Reproducing

```bash
python3 scripts/btc_forensics.py                      # on-chain, no key needed
python3 scripts/atc.py domain trezor.io US            # positive control: must return ~40 creatives
python3 scripts/atc.py domain sites.google.com US     # returns {} — no record of the attack
xvfb-run -a python3 scripts/serp_probe.py US "trezor wallet" ./geo com en 5
python3 scripts/build_report.py
```

`scripts/serp_probe.py` needs a Gonzo residential-proxy key at `/root/.config/gonzo/key`.

## Measurement honesty

Two instruments could not answer what they were pointed at, and the report says so rather than
presenting the gap as coverage:

- **Live SERP probing cannot measure ad presence.** The extractor is validated — it captured the
  genuine Trezor ad in full through a Spanish residential exit. But on a control query that always
  carries ads ("car insurance", UK), the rendered page held an `#tads` container with **two empty ad
  slots**. Google reserves the slots for these sessions and declines to fill them. Every `ads=0`
  reading is therefore *not measured*, not *no ad running*.
- **The ATC rate-limits to HTTP 429** under sustained querying. Every ATC negative reported was
  collected in a run whose `trezor.io` positive control returned 40 creatives in the same pass.

Also unresolved: the Google Ads account behind the ad was never identified, because Google's own
transparency tool holds no record of it. Attribution of the sibling feeder wallets to specific
brand campaigns is unproven beyond their shared treasury.

## Primary sources

- Victim report — https://x.com/ReallyBadDay99/status/2085454877719675354
- Amplification — https://x.com/BitcoinNewsCom/status/2085734257784139900
- urlscan capture of the live phishing page — https://urlscan.io/result/019fd42e-d592-714c-b291-4cf35ccef61c/
- Harvest address — https://mempool.space/address/bc1qrz33mr7tx8wrpcs2pxrvv83hqwpm907s9shkz4
- Google Ads *Destination mismatch* policy — https://support.google.com/adspolicy/answer/16428020

Defensive research. Report published `noindex`.
