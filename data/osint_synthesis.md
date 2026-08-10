# Wallet-Brand Phishing Domain Teardown — Defensive Report

Scope: 212 enriched rows across Ledger, Trezor, MetaMask, Phantom (+1 ChatGPT-phish tied to a MetaMask cluster). Every row below is NEW — none appear in the 22-domain KNOWN list. "Measured" = from the RDAP/HTTP row; abuse contacts are each registrar's published ICANN abuse desk (the rows carried registrar names, not abuse handles), flagged as such.

---

## 1. REGISTRAR CLUSTERS (by volume)

**#1 — Hosting Concepts B.V. d/b/a Registrar.eu / Openprovider (IANA 1647) — 25 domains**
Ledger 13, Trezor 5, MetaMask 2, Phantom 4, +chatgpt-connect.top.
Examples: ledgerlivewallet.download + ledgerlivedesktop.us (both 2026-04-08, paired same-day), ledgerwalletrelease.com (2026-06-08), metemask.com.co (2026-04-29) + metemask.com.mx (2026-06-02), phantum.biz (2026-02-18), phantomwalletverificationweb3.com (2025-08-18).
Pattern: this registrar's ...web3 / ...verification / ...device Ledger+Phantom domains cluster on IP **185.53.179.136** (Team Internet park range) returning **410 Gone (server: Caddy)** — a deliberate tombstone/takedown state. ~12 domains already sit there (also trezoriostat.com, metemask.com.co/.mx, phantomwalletweb3.com). Take-down is already happening on this IP; the LIVE ones (phantum.biz, trezorosuite.com) are the priority.
Abuse: abuse@openprovider.eu / abuse@registrar.eu.

**#2 — NICENIC International Group Co., Ltd (IANA 3765, Hong Kong) — 17 domains** (also the KNOWN 2025-08-03 cluster registrar)
Ledger 8, Trezor 8 (7 of them IDN homographs), MetaMask 1.
Examples: ledger-secure-access.com (2026-08-09, freshest), metamaskssupport.com (2026-08-07, LIVE), ledgercyber.net (2026-07-28, LIVE), and the bulk of the Trezor homograph set (xn--trezr-3ta / xn--trzor-jza / xn--trzor-o51b / xn--trezr-9dc / xn--trezr-581b / xn--trzor-7za / xn--trezo-9bb.io).
Pattern: steady drip through 2025-11 → 2026-08; **NICENIC is the dominant issuer of Trezor IDN homographs** and re-appears constantly — the single most-cited registrar across both this batch and the prior 22.
Abuse: abuse@nicenic.net.

**#3 — HOSTINGER operations, UAB (IANA 1636) — 7 domains**
ledgerpro.store (2026-07-30, LIVE), ledgerwallet.cloud (2026-05-10, LIVE), phantomwallet.co.in (2026-08-06), phantomwalletbr.site, phantomwallet.in, treezora.com, xn--trezo-9bb.com. Several already on clientHold/serverHold (Hostinger self-suspends).
Abuse: abuse@hostinger.com.

**#4 — GoDaddy.com, LLC (IANA 146) — 7 registered + parent host for 3 subdomain phish**
ledgersupport.pro (2026-08-04, LIVE), ledgeraapp.com, xn--trezor-gva.com (LIVE homograph), trezoroinvest.com, phantomblaze.online (LIVE), phantomwallet.uk (serverHold), phantomwallet.com (2016, cloaks off-brand). Also fronts godaddysites.com + peopleagainstsocialism.com subdomain lures.
Abuse: abuse@godaddy.com / supportcenter.godaddy.com/AbuseReport.

**#5 — NameSilo, LLC (IANA 1479) — 6**
phantom333.com (2026-08-02, LIVE, private NS), metamaks-info.com (LIVE, **open directory listing** exposing attacker files), metamaks.io, phantomwallet.help (Sedo park), ledger--live.com, ledgerwallets.cfd (pendingDelete/dead).
Abuse: abuse@namesilo.com.

**#6 — Dynadot Inc (IANA 472) — 6**
ledgerwalletcn.com + ledgerwaliet.com (both 2026-03-23, LIVE), ledgerliveapp.lol, xn--trzor-csa.io (LIVE, parasite redirect), xn--trezr-mua.io (suspended), phantumwallet.com (for-sale park).
Abuse: abuse@dynadot.com.

**#7 — PDR Ltd d/b/a PublicDomainRegistry.com (IANA 303) — 5**
phantomextension.app (2026-07-22, LIVE), phantom-web3apps.com (suspended-domain NS), phanton.pro, ledgre.live, metamaksio.info (clientHold).
Abuse: abuse@publicdomainregistry.com.

**#8 — Spaceship, Inc. (IANA 3862) — 5**
trezor-crypto-tips.com + trezor-model-t-tips.com (**both 2026-04-09, same IP 89.167.86.140, minutes apart = one operator**), trezorio-bridge.live (LIVE, mimics "Trezor Bridge"), phantomarcanebay.link (LIVE), ledgerlive.claims.
Abuse: abuse@spaceship.com.

**Smaller but notable clusters / same-operator pairs:**
- **West263 International (IANA 1915):** metmask.org + metmask.top (both 2025-07-29, registered **1 second apart**, same IPs). Abuse: abuse@west263.com.
- **Chengdu West Dimension / west.cn:** ledgero.cc + ledgerc.cc (both 2026-05-17, 36s apart, same IP 162.209.140.179) + ledgerwallet.com.cn. Abuse: abuse@west.cn.
- **Xin Net / Beijing Xinnet (IANA 120):** ledgerwallet-app.cn + trezor-app.cn (both 2026-04-29, onclouddns) + ledgerwallet.icu. Abuse: supervision@xinnet.com.
- **Gname.com (IANA 1923):** metamask--wallet.shop paired with **Vantage of Convergence Chengdu (IANA 3869)** metamask--wallet.com — both 2025-06-28 (paired across two registrars). Abuse: abuse@gname.com.
- **Sav.com, LLC:** phantom-backup.com + phanthom.net (shared ns1/ns2.all-harmless.domains). Abuse: abuse@sav.com.
- **WebNic (IANA 460, Malaysia — KNOWN 2025-08-03 registrar):** metamaksk.io, metamaska.com.cn. Abuse: abuse@web.cc / compliance@webnic.cc.
- Singles worth a report each: Ultahost (leedger-firmware-update.com, trezorusersupport.com) abuse@ultahost.com; OwnRegistrar (trezor-connect.com 2026-08-09, trezoronlineupdate.com); Global Domain Group (ledgre.link, ledger-helphub.com, phanton.biz); Key-Systems (trezoractivate.io, metamasksupport.help) abuse@key-systems.net; Porkbun (ledger-device-protection.info) abuse@porkbun.com; IONOS (ledgerlive-deny/portal.com, Sedo-parked) abuse@ionos.com; Galcomm (ledgerwallet.live) abuse@galcomm.com; Internet.bs Corp (two ledgerwallet...web3, shared courtney/guy CF NS) abuse@internet.bs; Cloudflare-registrar (ledgrcdn.com, ledger--stats.com) abuse.cloudflare.com.

**Platform/hosting abuse (not registrar-actionable) — report to the host:** Cloudflare Pages (7 Trezor/MetaMask *.pages.dev), GitBook (metamskdwnld / metamaskextensionnn — STILL LIVE), Cloudflare Workers (trzr3545cnct.iolanda21.workers.dev), Canva, Weebly, WordPress.com (metamskinlogin — LIVE), Blogspot (metmasksignin — LIVE), Vercel, Zapier, DuckDNS→DigitalOcean. **Two abused/compromised legitimate sites:** cadenceireland.kinsta.cloud (Kinsta WordPress → abuse@kinsta.com) and metamaks-recovery.miguelamorim.pt (compromised personal .pt site → notify owner + DNS.PT).

---

## 2. IDN HOMOGRAPHS (every xn-- domain)

All mimic **Trezor** except the last, which mimics **Ledger**. The campaign is systematically registering a diacritic on each letter of "trezor."

| Punycode | Decoded | Diacritic | Registrar | Reg date | State |
|---|---|---|---|---|---|
| xn--trezr-3ta.com | trezór.com | ó U+00F3 | NICENIC | 2026-07-10 | resolves, CF 522 |
| xn--trzor-jza.com | trēzor.com | ē U+0113 | NICENIC | 2026-02-07 | resolves, CF 522 |
| xn--trezor-gva.com | trezoré.com | é appended | GoDaddy | 2025-10-28 | **LIVE** (AWS, 200) |
| xn--trzor-csa.io | trézor.io | é U+00E9 | Dynadot | 2026-05-06 | **LIVE, 301→snl-github.io (parasite)** |
| xn--trezo-9bb.com | trezoŗ.com | ŗ U+0157 | Hostinger | 2025-07-12 | registered, no A |
| xn--trezo-9bb.io | trezoŗ.io | ŗ | NICENIC | 2026-02-02 | registered, no A |
| xn--trzor-7za.com | trėzor.com | ė U+0117 | NICENIC | 2025-11-25 | registered, no A |
| xn--trezr-581b.com | trezọr.com | ọ U+1ECD | NICENIC | 2025-12-04 | registered, no A |
| xn--trezr-9dc.com | trezȯr.com | ȯ U+022F | NICENIC | 2025-12-09 | registered, no A |
| xn--trzor-k0a.com | tręzor.com | ę U+0119 | Dominet HK | 2025-10-04 | registered, no A |
| xn--trezr-j9a.com | trezōr.com | ō U+014D | Registrar.eu | 2026-04-16 | registered, EdgeOne, not serving |
| xn--treor-kib.org | treżor.org | ż U+017C | Registrar.eu | 2026-05-30 | registered, EdgeOne, not serving |
| xn--trzor-o51b.com | trẹzor.com | ẹ U+1EB9 | NICENIC | 2025-12-01 | **SUSPENDED (clientHold)** |
| xn--trezr-mua.io | trezör.io | ö U+00F6 | Dynadot | 2025-07-15 | **SUSPENDED (clientHold)** |
| xn--trezo-9bb.app | trezoŗ.app | ŗ | — | — | NOT registered (gap) |
| xn--trezo-9bb.org | trezoŗ.org | ŗ | — | — | NOT registered |
| xn--trzor-7za.online | trėzor.online | ė | — | — | NOT registered |
| xn--trzor-csa.cc | trézor.cc | é | — | — | NOT registered |
| xn--trezr-mua.com | trezör.com | ö | — | — | NOT registered |
| xn--trezr-gua.com | trezõr.com | õ U+00F5 | — | — | NOT registered |
| xn--trezr-yua.com | trezør.com | ø U+00F8 | — | — | NOT registered |
| xn--trezr-xta.com | trezòr.com | ò U+00F2 | — | — | NOT registered |
| xn--trezr-9ta.com | trezôr.com | ô U+00F4 | — | — | NOT registered |
| xn--trzor-w0a.net | trězor.net | ě U+011B | — | — | NOT registered |
| xn--trezo-bp1b.com | trezoṙ.com | ṙ U+1E59 | — | — | NOT registered |
| xn--trezor-o-i2a.com | trezor-ío.com | í | — | — | NOT registered |
| **xn--leder-y1a.app** | **ledġer.app** | ġ U+0121 | NICENIC | 2026-05-10 | **LIVE, CLOAKS to ledger.com** (see §3) |

Live IDN threats now: xn--trezor-gva.com, xn--trzor-csa.io, xn--leder-y1a.app. The 12 "NOT registered" rows are open registrable gaps in the same scheme — candidates for defensive registration / watchlisting.

---

## 3. CLOAKING TELLS (redirect-based evasion)

Per the brief's definition (bare root 30x-redirects to the **real** brand = cloaking to defeat casual inspection):

- **xn--leder-y1a.app (ledġer.app)** — https 302 → https://ledger.com → www.ledger.com. **Reproduced twice.** This is the textbook cloak: the homograph bounces visitors to the genuine Ledger site so the domain looks harmless to a scanner, while the operator serves the phish selectively (device/geo/UA-gated) — a browser fleet is needed to capture the malicious variant.
- **xn--trzor-csa.io (trézor.io)** — https 301 → https://snl-github.io/ . Redirect-cloak to a **GitHub Pages parasite host** (not the real brand). Parasite-host tell.
- **phantomwallet.com (GoDaddy, 2016)** — https 301 → https://store.fantomwallet.com . Brand-bleed cloak to a **different** "fantomwallet" store; does NOT reach real phantom.app.

**Distinct — self-redirects, NOT cloaking to real brand (do not misclassify):** ledger-device-protection.info (301→self), trezoronlineupdate.com (301→self, expired cert), phantomhoods.xyz (308→www self). **Broken self-redirects:** ledger-live-update.com + ledger-live-login.com (both 302 → www.www.<self>, NXDOMAIN dead-end; sisters, same CF NS, same minute 2026-01-22). These force HTTPS on their own host — evasion posture, but not the real-brand cloak.

---

## 4. NEW DOMAINS — MOST SUSPICIOUS FIRST

Ranking = fresh registration × currently LIVE × software/support/recovery lure × sketchy signal (misspelling, IDN, private/abuse NS). All are new vs the KNOWN list.

**Tier 1 — fresh + LIVE + high-harm (act first):**
1. **trezor-connect.com** — reg **2026-08-09 (today)**, LIVE 200 (Cloudflare), OwnRegistrar. Impersonates "Trezor Connect," a real Trezor software name. Freshest live domain in the set.
2. **metamaskssupport.com** — 2026-08-07, LIVE 200 ("Site Under Maintenance"), NICENIC, NS ml1/ml2.**darkhost.pro**. Support-desk lure, staging state.
3. **ledger-secure-access.com** — 2026-08-09 (today), NICENIC, Cloudflare (403 to us = live-behind-CF, not a negative).
4. **trezorusersupport.com** — 2026-08-08, Ultahost, live-behind-CF (403). Support lure.
5. **phantom333.com** — 2026-08-02, LIVE 200, NameSilo, **custom private NS (misteri88390.com)** = operator-run infra.
6. **metmask-backup-token-recovery-authkey.cadenceireland.kinsta.cloud** — LIVE (WordPress on a **compromised Kinsta site**). **Seed-phrase recovery lure = highest data-theft harm.** Report to Kinsta.
7. **metamaks-recovery.miguelamorim.pt** — LIVE on a **compromised legitimate .pt site**; page header base64-decodes to "apocas@github." Recovery lure.

**Tier 2 — fresh + LIVE:**
8. **ledgre.link** — 2026-08-04, LIVE (Vercel), misspelling "ledgre," Global Domain Group.
9. **ledgersupport.pro** — 2026-08-04, LIVE, GoDaddy. Support lure.
10. **ledger-helphub.com** — 2026-08-03, LIVE (Cloudflare), Global Domain Group.
11. **phantomextension.app** — 2026-07-22, LIVE (Bluehost). Extension lure (matches KNOWN phantom-extension.app scheme).
12. **phanton.biz** — 2026-07-24, LIVE (Cloudflare), misspelling "phanton," Global Domain Group.
13. **ledgerpro.store** — 2026-07-30, LIVE (Render).
14. **phantomhoods.xyz** — 2026-08-05, LIVE (Vercel).
15. **trezoractivate.io** — 2026-07-19, LIVE (Hostwinds).
16. **trezorosuite.com** — 2026-07-17, resolves (CF, timing out to us), mimics "Trezor Suite."
17. **metamaks-info.com** — 2026-05-21, LIVE with an **open directory listing** (attacker files exposed), NameSilo, misspelling.
18. **metamskdwnld.gitbook.io** & **metamaskextensionnn.gitbook.io** — STILL LIVE (307), GitBook download lures.
19. **metamskinlogin.wordpress.com** / **metmasksignin.blogspot.com** — LIVE 200 on free blog platforms.

**Tier 3 — live IDN homographs (see §2):** xn--leder-y1a.app (cloaks to ledger.com), xn--trezor-gva.com, xn--trzor-csa.io.

**Tier 4 — large registered footprint, currently parked/refused (one naming scheme, watch for re-activation):**
- **.ph cluster on 45.79.222.138 (Linode/dotPH-ParkLogic):** metamask-logincentral-{bg,my,oz}.ph, metamask-walletaccess-{nl,ph}.ph, metamask-walletauth-{asia,eu}.ph, metamask-account-recovery-key.ph, metamask-activate.ph, metamask-payment.ph, metamask-confirmaccess10.ph, metamask-verify-1111wincardbet.ph, metamask-verify-1111baccaratblazeryzyxz.ph (**last two tie the MetaMask lure to gambling brands**), plus ledger-wallet.ph, ledgerwallet.com.ph, trezoriosecure.ph, trezor-{vhod,billing}.ph, trezorrbionline.ph, phantom-wallet.ph, phantom-activate.ph. `.ph` has no RDAP; measured via CT + DNS. Currently ParkLogic-parked / registry-suspended, but the geo-suffixed naming (bg/my/oz/nl/eu/asia) is one operator's kit.

**Tier 5 — already neutralized (low priority, confirm they stay down):** ~12 Registrar.eu domains at 185.53.179.136 (410 Gone); clientHold/serverHold suspensions (metamaksk.io, metamaks.org, metamaksio.info, xn--trzor-o51b.com, xn--trezr-mua.io, phantomwallet.uk, phantom-web3apps.com, phantomwalletbr.site); redemption/pendingDelete (metamask--wallet.com/.shop, phanthom.net, phantom-alert-final-bot.com, ledgerwallets.cfd); taken-down platform subdomains (7 *.pages.dev 403, webflow/wixstudio/typedream/godaddysites/github.io 404).

**Registrable gaps to defensively register/watchlist:** the 12 unregistered Trezor homographs in §2, plus metamaks.xyz, metamakscrypto.com, metamakse.click, metamaksvip.top, metamask--portfoliio-dapp.xyz, metamask--por4folio-dapp.xyz, phantummm.com.

---

## 5. RECOMMENDATION TO REGISTRARS

Two registrars are issuing wallet-brand-lookalike domains at volume: **Hosting Concepts B.V./Registrar.eu/Openprovider (IANA 1647, 25 domains)** and **NICENIC International Group (IANA 3765, 17 domains, Hong Kong)**, with **NICENIC also the dominant issuer of Trezor IDN homographs** and a recurring name in the prior 2025-08-03 WebNic/NICENIC burst. Hostinger, GoDaddy, NameSilo, Dynadot, PDR, and Spaceship each carry 5–7. The concentration is not random: same-day paired registrations (Spaceship trezor-crypto-tips.com + trezor-model-t-tips.com; West263 metmask.org + metmask.top one second apart; Chengdu West Dimension ledgero.cc + ledgerc.cc), shared nameserver/IP infrastructure, and a systematic diacritic-per-letter sweep of the "trezor"/"ledger" homograph space all indicate a small number of operators registering in bulk. These strings — a hardware-wallet brand name plus "support/recovery/backup/activate/firmware/suite/connect," or the same brand rendered with a combining diacritic — have no plausible legitimate registrant other than the brand owner, and several already serve credential/seed-phrase capture (including one that cloaks to ledger.com to evade inspection). Under the ICANN Registrar Accreditation Agreement's abuse obligations (RAA §3.18 and the DNS-Abuse amendment), registrars must publish an abuse contact and take reasonable, prompt action on well-founded reports of DNS abuse such as phishing. Given the measured volume and the low-false-positive nature of these strings, extra pre-registration KYC/verification on **wallet-brand + support/recovery lookalikes and on IDN homographs of known wallet brands** is warranted and proportionate; the unregistered homograph gaps in §2 show the sweep is ongoing, so a registration-time screen would prevent the next batch rather than only remediate it after live phishing.

---
*Measured from the provided RDAP/HTTP enrichment. "Live-behind-CF" 403s and 521/522/timeouts are resolving domains our datacenter IP cannot see, not clean negatives — confirm content via the browser fleet. Abuse emails are each registrar's standard ICANN-required abuse desk, not values carried in the RDAP rows.*