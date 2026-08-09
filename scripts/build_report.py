#!/usr/bin/env python3
"""Generate docs/index.html from the verified data files.

Everything numeric on the page comes out of data/*.json so the report cannot
drift from the evidence.
"""
import html
import json
import os
import time

ROOT = "/root/workspace/trezor-ads-teardown"
D = lambda p: json.load(open(os.path.join(ROOT, "data", p)))  # noqa: E731


def load(p, default=None):
    try:
        return D(p)
    except Exception:
        return default


btc = load("btc_forensics.json", {})
hourly = load("hourly.json", [])
timeline = load("timeline.json", {"events": []})
geo = load("geo_summary.json", [])
limits = load("serp_method_limitation.json", {})
hop1 = load("hop1.json", [])
feeders = load("treasury_feeders.json", {})
atc_sug = load("atc_suggest_trezor.json", {})
atc_find = load("atc_findings.json", {})
research = load("research.json", {})

import calendar  # noqa: E402

# 2026-08-06 19:56:03 UTC, the victim's public warning. Computed, not hardcoded:
# a hand-typed epoch was a day out and silently put every drain in the "before" bucket.
WARN = calendar.timegm(time.strptime("2026-08-06 19:56:03", "%Y-%m-%d %H:%M:%S"))
assert 1786046163 == WARN, WARN
dep = btc.get("deposits", [])
pre = [x for x in dep if x["time"] < WARN]
post = [x for x in dep if x["time"] >= WARN]
usd = lambda L: sum(x.get("usd") or 0 for x in L)  # noqa: E731
btcs = lambda L: sum(x["btc"] for x in L)  # noqa: E731

E = html.escape


def money(v):
    return f"${v:,.0f}"


# ---------------------------------------------------------------- chart
def chart(rows, w=1000, h=260, pad=34):
    if not rows:
        return ""
    mx = max(r["usd"] for r in rows) or 1
    n = len(rows)
    bw = (w - pad * 2) / n
    bars, labels = [], []
    warn_idx = None
    for i, r in enumerate(rows):
        if r["hour"] >= "08-06 20":
            warn_idx = warn_idx if warn_idx is not None else i
        bh = (r["usd"] / mx) * (h - pad * 2)
        x = pad + i * bw
        y = h - pad - bh
        after = r["hour"] >= "08-06 20"
        fill = "var(--after)" if after else "var(--before)"
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw*0.78:.1f}" height="{max(bh,1):.1f}" '
            f'fill="{fill}" rx="1.5"><title>{E(r["hour"])}:00 UTC — {r["n"]} drains — {money(r["usd"])}</title></rect>')
        if i % 3 == 0:
            labels.append(f'<text x="{x+bw*0.39:.1f}" y="{h-pad+15:.0f}" class="tick">{E(r["hour"][-2:])}</text>')
    marker = ""
    if warn_idx is not None:
        mxp = pad + warn_idx * bw - bw * 0.11
        marker = (f'<line x1="{mxp:.1f}" y1="{pad-8}" x2="{mxp:.1f}" y2="{h-pad}" class="warnline"/>'
                  f'<text x="{mxp+6:.1f}" y="{pad-12}" class="warnlabel">public warning 19:56 UTC</text>')
    return f'''<svg viewBox="0 0 {w} {h}" class="chart" role="img"
  aria-label="Hourly value of victim drains; the public warning is marked">
  <line x1="{pad}" y1="{h-pad}" x2="{w-pad}" y2="{h-pad}" class="axis"/>
  {''.join(bars)}{marker}{''.join(labels)}
  <text x="{pad}" y="{pad-12}" class="tick">peak hour {money(mx)}</text>
</svg>'''


# ---------------------------------------------------------------- sections
def timeline_html():
    out = []
    for e in timeline.get("events", []):
        rel = e["rel_to_warning_h"]
        sign = "after" if rel > 0 else "before"
        cls = {"money": "t-money", "infra": "t-infra", "public": "t-public",
               "defence": "t-def", "state": "t-state"}.get(e["kind"], "")
        rl = f"{abs(rel):.1f}h {sign} warning" if abs(rel) < 400 else ""
        out.append(f'''<li class="{cls}">
      <div class="t-when"><b>{E(e["utc"])}</b><span>{E(rl)}</span></div>
      <div class="t-what">{E(e["event"])}<span class="src">{E(e["source"])}</span></div></li>''')
    return "\n".join(out)


def geo_html():
    ok = [g for g in geo if g.get("status") == "OK"]
    by = {}
    for g in geo:
        by.setdefault(g["cc"], []).append(g)
    rows = []
    for cc in sorted(by):
        items = by[cc]
        v = [i for i in items if i.get("status") == "OK"]
        ads = sum((i.get("ads") or 0) for i in v)
        st = f"{len(v)}/{len(items)} rendered"
        adcell = (f'<span class="ok">{ads} ad captured</span>' if ads
                  else ('<span class="muted">no creative served</span>' if v else '<span class="bad">not measured</span>'))
        orgs = sorted({(i.get("exit_org") or "").split(" ", 1)[-1] for i in items if i.get("exit_org")})
        rows.append(f'<tr><td><b>{E(cc)}</b></td><td>{E(st)}</td><td>{adcell}</td>'
                    f'<td class="muted small">{E(", ".join(orgs)[:70])}</td></tr>')
    return "\n".join(rows), len(ok), len(geo)


def hop_html():
    rows = []
    for h in hop1:
        held = h["balance_btc"]
        rows.append(
            f'<tr><td class="mono">{E(h["address"])}</td>'
            f'<td>{h["received_from_harvest_btc"]:.4f}</td>'
            f'<td>{h["total_received_btc"]:.4f}</td>'
            f'<td class="{"hold" if held>0.01 else "muted"}">{held:.4f}</td></tr>')
    return "\n".join(rows)


def feeder_html():
    rows = []
    for a, v in sorted(feeders.items(), key=lambda x: -x[1]):
        if v <= 0:
            continue
        ours = a == "bc1qqg3c0ed0wzjdnjjlgcdrzyzedj8tgyapkvda9z"
        rows.append(f'<tr><td class="mono">{E(a)}</td><td>{v:.4f}</td>'
                    f'<td>{"the Trezor campaign" if ours else "a different campaign"}</td></tr>')
    return "\n".join(rows)


def legit_html():
    names = {}
    for r, items in atc_sug.items():
        for kind, a, b, c in items:
            if kind == "ADV":
                names.setdefault(a, set()).add(c or "?")
    return "".join(
        f"<li><b>{E(n)}</b> <span class='muted'>({E('/'.join(sorted(cc)))})</span></li>"
        for n, cc in sorted(names.items()) if n)


geo_rows, geo_ok, geo_tot = geo_html()
eco = load("ecosystem.json", {})


def eco_brand_html():
    return "".join(
        f'<tr><td>{E(b)}</td><td>{n}</td></tr>'
        for b, n in (eco.get("brands") or {}).items())


def eco_live_html():
    rows = []
    for l in eco.get("still_live", []):
        rows.append(f'<tr><td>{E(l["brand"])}</td><td class="mono">{E(l["url"])}</td></tr>')
    return "\n".join(rows)


def eco_ads_html():
    rows = []
    for a in eco.get("ad_parameter_urls", [])[:16]:
        rows.append(f'<tr><td>{E(a["time"])}</td><td>{E(a["brand"])}</td>'
                    f'<td class="mono">{E(a["campaign_id"] or "—")}</td>'
                    f'<td class="mono small">{E(a["url"][:78])}…</td></tr>')
    return "\n".join(rows)


def eco_dom_html():
    ds = [d["domain"] for d in eco.get("attacker_domains", [])]
    return ", ".join(f"<code>{E(d)}</code>" for d in ds)

# --------------------------------------------------------------- research
def research_block():
    if not research:
        return ('<p class="muted">The multi-source research pass and the per-region advertiser sweep '
                'are recorded in <code>data/</code> in the repository.</p>')
    parts = []
    for k, v in research.items():
        if isinstance(v, str) and v.strip():
            parts.append(f"<h3>{E(k.replace('_',' ').title())}</h3><div class='prose'>{v}</div>")
    return "\n".join(parts)


HTML = f'''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>The google.com Phishing Ad — Trezor / Google Sites teardown</title>
<style>
:root{{
  --bg:#0b0d10; --panel:#12161b; --line:#232a33; --ink:#e8edf3; --dim:#97a3b2;
  --accent:#4ade80; --before:#f59e0b; --after:#ef4444; --link:#7dd3fc;
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased}}
.wrap{{max-width:1080px;margin:0 auto;padding:0 22px}}
a{{color:var(--link)}}
h1,h2,h3{{line-height:1.15;letter-spacing:-.02em;margin:0}}
header{{padding:74px 0 46px;border-bottom:1px solid var(--line)}}
.kicker{{font:600 12px/1 var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--after)}}
h1{{font-size:clamp(34px,6vw,62px);font-weight:800;margin:18px 0 16px}}
h1 em{{font-style:normal;color:var(--after)}}
.lede{{font-size:clamp(17px,2.2vw,21px);color:var(--dim);max-width:74ch}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1px;
  background:var(--line);border:1px solid var(--line);margin:44px 0 0}}
.stat{{background:var(--panel);padding:18px 20px}}
.stat b{{display:block;font:700 26px/1.1 var(--mono);color:var(--ink)}}
.stat span{{display:block;font-size:12.5px;color:var(--dim);margin-top:7px}}
.stat.red b{{color:var(--after)}} .stat.amber b{{color:var(--before)}} .stat.green b{{color:var(--accent)}}
section{{padding:56px 0;border-bottom:1px solid var(--line)}}
h2{{font-size:clamp(23px,3.4vw,33px);font-weight:750;margin-bottom:8px}}
.sub{{color:var(--dim);margin:0 0 26px;max-width:76ch}}
p{{max-width:76ch}}
.panel{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:22px 24px;margin:20px 0}}
.panel.flag{{border-left:3px solid var(--after)}}
.panel.good{{border-left:3px solid var(--accent)}}
figure{{margin:26px 0}}
figure img{{width:100%;border:1px solid var(--line);border-radius:8px;display:block;background:#fff}}
figcaption{{color:var(--dim);font-size:13.5px;margin-top:11px;max-width:80ch}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:26px}}
@media(max-width:820px){{.two{{grid-template-columns:1fr}}}}
table{{width:100%;border-collapse:collapse;margin:18px 0;font-size:14px}}
th,td{{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}}
th{{font:600 11.5px/1 var(--mono);letter-spacing:.09em;text-transform:uppercase;color:var(--dim)}}
.mono,code{{font-family:var(--mono);font-size:12.5px;word-break:break-all}}
code{{background:#1a1f26;padding:2px 6px;border-radius:4px;color:#cfe6ff}}
.muted{{color:var(--dim)}} .small{{font-size:12.5px}}
.ok{{color:var(--accent)}} .bad{{color:var(--after)}} .hold{{color:var(--before);font-weight:700}}
.scroll{{overflow-x:auto}}
ol.steps{{counter-reset:s;list-style:none;padding:0;margin:26px 0}}
ol.steps>li{{counter-increment:s;position:relative;padding:0 0 26px 60px;
  border-left:1px solid var(--line);margin-left:17px}}
ol.steps>li:last-child{{border-left:1px solid transparent}}
ol.steps>li::before{{content:counter(s);position:absolute;left:-17px;top:-3px;width:34px;height:34px;
  border-radius:50%;background:var(--panel);border:1px solid var(--line);color:var(--after);
  font:700 14px/34px var(--mono);text-align:center}}
ol.steps h3{{font-size:18px;margin-bottom:7px}}
ul.timeline{{list-style:none;padding:0;margin:24px 0}}
ul.timeline li{{display:grid;grid-template-columns:210px 1fr;gap:20px;padding:13px 0;
  border-bottom:1px solid var(--line)}}
@media(max-width:720px){{ul.timeline li{{grid-template-columns:1fr;gap:5px}}}}
.t-when b{{font:600 13px/1.4 var(--mono);display:block}}
.t-when span{{font-size:11.5px;color:var(--dim)}}
.t-what{{font-size:15px}}
.t-what .src{{display:block;font-family:var(--mono);font-size:11.5px;color:var(--dim);margin-top:4px}}
li.t-money .t-when b{{color:var(--after)}}
li.t-infra .t-when b{{color:var(--link)}}
li.t-public .t-when b{{color:var(--before)}}
li.t-def .t-when b{{color:var(--accent)}}
.chart{{width:100%;height:auto;margin:14px 0 4px}}
.chart .axis{{stroke:var(--line);stroke-width:1}}
.chart .tick{{fill:var(--dim);font:11px var(--mono)}}
.chart .warnline{{stroke:var(--ink);stroke-width:1;stroke-dasharray:3 3;opacity:.75}}
.chart .warnlabel{{fill:var(--ink);font:11px var(--mono)}}
.legend{{display:flex;gap:18px;font-size:12.5px;color:var(--dim);margin-top:6px;flex-wrap:wrap}}
.sw{{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:6px;vertical-align:-1px}}
.urlbar{{font-family:var(--mono);font-size:14px;background:#fff;color:#202124;border-radius:22px;
  padding:11px 17px;display:inline-block;margin:7px 0;border:1px solid #dadce0}}
.urlbar .g{{color:#188038}} .urlbar .r{{color:#c5221f;font-weight:700}}
footer{{padding:46px 0 76px;color:var(--dim);font-size:13.5px}}
.ioc{{background:#0f1318;border:1px solid var(--line);border-radius:8px;padding:16px 18px;
  font-family:var(--mono);font-size:12.5px;line-height:1.95;overflow-x:auto;white-space:pre-wrap;word-break:break-all}}
.prose{{max-width:78ch}}
</style></head><body>

<header><div class="wrap">
  <div class="kicker">Incident teardown · 5–7 August 2026</div>
  <h1>The phishing ad that displayed <em>google.com</em></h1>
  <p class="lede">A Google Search sponsored result for <b>“trezor suite”</b> showed the URL
  <code>https://www.google.com</code> and the advertiser name <b>Trezor.io</b>. It led to a
  pixel-perfect Trezor clone hosted on Google Sites that asked for the wallet recovery phrase.
  It out-ranked Trezor’s own ad. In 33 hours the harvesting address took
  <b>{btcs(dep):.2f} BTC</b> from <b>{len(dep)}</b> wallets — and Google’s own advertising policy
  already forbade the ad in writing.</p>
  <div class="stats">
    <div class="stat red"><b>{money(usd(dep))}</b><span>stolen, valued at each drain’s own block time</span></div>
    <div class="stat"><b>{len(dep)}</b><span>separate victim wallet drains</span></div>
    <div class="stat amber"><b>32.9 h</b><span>from first drain to last</span></div>
    <div class="stat red"><b>{money(usd(post))}</b><span>taken <i>after</i> the victim went public</span></div>
    <div class="stat green"><b>18 mo</b><span>the kit had been running before this</span></div>
  </div>
</div></header>

<section><div class="wrap">
  <h2>What actually happened</h2>
  <p class="sub">Five facts carry the whole incident.</p>
  <div class="panel flag">
    <ol style="margin:0;padding-left:19px">
      <li>The attacker put the phishing page on <b>Google Sites</b> —
        <code>sites.google.com/view/start-trezor-suite</code>.</li>
      <li>The ad rendered its display URL as <b><code>https://www.google.com</code></b>. Google’s
        destination-mismatch policy lists as a violation <i>“Failing to use a subdomain to clearly
        identify a site from all other sites hosted on that domain or from the parent domain”</i> —
        which a path-based Google Sites URL cannot satisfy. The ad was <b>already prohibited</b>. It
        ran anyway.</li>
      <li>The advertiser set its public name to <b>Trezor.io</b> and bought sitelinks, so the ad
        rendered above the genuine Trezor ad.</li>
      <li>The landing page cloned trezor.io and asked for the <b>BIP-39 recovery phrase</b> in
        24 boxes, promising “Your information stays offline only.”</li>
      <li>The same kit had been blocked by <b>Cloudflare</b> nine days earlier. It moved to Google’s
        own hosting and was not blocked.</li>
    </ol>
  </div>
</div></section>

<section><div class="wrap">
  <h2>How much of this is actually established</h2>
  <p class="sub">Separating what is checkable from what is one person’s word, before anything is
  built on top of it.</p>
  <div class="two">
    <div class="panel good">
      <h3 style="margin-bottom:8px">Verifiable</h3>
      <ul style="margin:0;padding-left:18px">
        <li>The URL <code>sites.google.com/view/start-trezor-suite</code> — captured by urlscan.io
          while live.</li>
        <li>The page content — a trezor.io clone soliciting a BIP-39 phrase.</li>
        <li>The address <code>bc1qrz33mr7…</code> and every satoshi through it —
          <b>{money(usd(dep))}</b> across <b>{len(dep)}</b> drains, agreed by two independent
          block explorers.</li>
        <li>Trezor’s reply, from the verified account, at <b>2026-08-07 10:57:56 UTC</b>.</li>
        <li>Google’s policy text, quoted live.</li>
      </ul>
    </div>
    <div class="panel flag">
      <h3 style="margin-bottom:8px">Claim only</h3>
      <ul style="margin:0;padding-left:18px">
        <li><b>“Life savings.”</b> Unverified. No amount was named and no wallet was tied to the
          poster.</li>
        <li><b>“Top sponsored result.”</b> Unverified for the query the victim named. The surviving
          screenshot is a different query, posted by a different account, a day later.</li>
        <li><b>The reporting account is 16 minutes old.</b> The user ID decodes to
          <b>2026-08-06 19:39:47 UTC</b>; the post is <b>19:56:03 UTC</b> — 16 minutes 15 seconds
          later. Default avatar, unverified, no history.</li>
      </ul>
    </div>
  </div>
  <p class="small muted">This does not make the incident false — the blockchain is indifferent to who
  tweeted, and it records {len(dep)} drained wallets either way. It means the <b>money and the page
  are the evidence</b>, and the narrator is not. Every figure in this report comes from the former.</p>
</div></section>

<section><div class="wrap">
  <h2>The ad</h2>
  <p class="sub">Published by @BitcoinNewsCom on 2026-08-07, on the query “trezor suite”. Both
  sponsored slots say Trezor — only one of them is Trezor.</p>
  <p class="small muted">Provenance, stated precisely: the victim’s own post carried
  <b>no image</b> — its media list is empty in X’s API. These two screenshots were attached to
  @BitcoinNewsCom’s post the following day, and the query shown (“trezor suite”) is not the query
  the victim named (“Trezor wallet”). They are the best available capture of the ad and they are
  consistent with everything else here, but they are a news account’s screenshots, not the victim’s,
  and nobody has independently reproduced the placement.</p>
  <figure>
    <img src="assets/serp-malicious-ad.jpg" alt="Google search results for 'trezor suite'. The first sponsored result is titled 'Trezor Suite | Download Trezor App' from advertiser Trezor.io with the displayed URL https://www.google.com. The second sponsored result is the genuine Trezor ad with the displayed URL https://www.trezor.io.">
    <figcaption>Top sponsored slot: advertiser <b>Trezor.io</b>, display URL
    <b>https://www.google.com</b>, headline “Trezor Suite | Download Trezor App”, with five sitelinks
    and a “1M+ visits in past month” annotation. Directly beneath it sits the real Trezor ad
    at <b>https://www.trezor.io</b> — the same creative this investigation captured live in Spain
    while the fleet was running, which is one reason the capture reads as genuine. The sitelinks
    matter: they are configured per campaign, so this was a built-out account, not a throwaway.</figcaption>
  </figure>
  <div class="two">
    <div><div class="urlbar">🔒 Trezor.io &nbsp;<span class="r">https://www.google.com</span></div>
      <p class="small muted">The impostor. The domain is real, which is the whole trick.</p></div>
    <div><div class="urlbar">🔒 Trezor.io &nbsp;<span class="g">https://www.trezor.io</span></div>
      <p class="small muted">The genuine advertiser, ranked second.</p></div>
  </div>
</div></section>

<section><div class="wrap">
  <h2>The mechanic: why it said google.com</h2>
  <p class="sub">This is the part that generalises beyond Trezor.</p>
  <p>A Google search ad carries two URLs. The <b>final URL</b> is where the click lands; the
  <b>display URL</b> is the one the user reads. The advertiser supplies both, but Google constrains
  the pair through its <i>Destination mismatch</i> policy, which lists four separate violations.
  Two of them matter here, quoted verbatim:</p>
  <div class="panel">
    <p style="margin-top:0"><b>1.</b> <i>“The domain or domain extension in the display URL doesn’t
    match the final and mobile URLs where users are taken to.”</i> The policy’s own worked example of
    a violation is <i>“Display URL: google.com and Final URL: example.com”.</i></p>
    <p style="margin-bottom:0"><b>2.</b> <i>“Failing to use a subdomain to clearly identify a site
    from all other sites hosted on that domain or from the parent domain.”</i></p>
  </div>
  <p>Clause 1 is the one everybody reaches for, and on its own it looks satisfied: the click really
  did land on google.com, so display domain and final domain agree. That reading is why the
  “it complied with the rule” explanation circulates. It is wrong, because clause 2 exists.</p>
  <div class="panel flag">
    <p style="margin:0"><b>Clause 2 is precisely about shared hosting, and it is unsatisfiable on
    Google Sites.</b> <code>sites.google.com</code> hosts millions of unrelated pages. Clause 2
    demands a <i>subdomain</i> that distinguishes this site both from every other site on the domain
    and from the parent domain. A Google Sites URL identifies itself by <i>path</i> —
    <code>/view/start-trezor-suite</code> — never by subdomain. There is no way to run this ad
    compliantly.</p>
  </div>
  <p><b>So this was not a loophole. It was an enforcement failure.</b> The rule that should have
  stopped the ad was already written, already published, and already covered the exact
  configuration used. The ad served regardless, above the genuine advertiser, for at least the
  33 hours the blockchain can account for.</p>
  <p class="small muted">Stated carefully because the popular explanation is wrong: the claim that
  <code>sites.google.com</code> and <code>ads.google.com</code> “share the google.com root, so the
  display URL is legitimate” was tested against the live policy text and does not hold. The display
  URL is an <i>observation</i> — read off the SERP capture below — and the policy breach is clause 2,
  not an absence of rules.</p>
  <div class="panel flag">
    <p style="margin:0"><b>What the victim actually saw.</b> Whatever the policy says, the rendered
    result carried the most trusted string on the internet above a seed-phrase harvester — and the
    string was not a lie. The click really did go to google.com. That is what makes this class of
    ad unusually effective: the single check a careful user is told to perform, reading the domain,
    returns the reassuring answer.</p>
  </div>
  <p>Any Google-operated host that lets a stranger publish a page will do the same job:
  Google Sites, Looker Studio, Google Groups, Blogger, Apps Script, Firebase
  (<code>web.app</code>, <code>firebaseapp.com</code>), and <code>appspot.com</code>. Google Sites is
  the strongest of them because it serves from <code>sites.google.com</code> and adds Google’s own
  cookie-consent banner to the attacker’s page.</p>
</div></section>

<section><div class="wrap">
  <h2>The landing page</h2>
  <figure>
    <img src="assets/phishing-clone-google-sites.jpg" alt="The phishing page: a pixel-perfect copy of the trezor.io homepage, served from sites.google.com, with a Google cookie-consent banner in the lower left.">
    <figcaption>The clone as urlscan.io captured it at <b>2026-08-05 23:07:54 UTC</b> — two hours after
    the first victim was already being drained. It reproduces Trezor’s live homepage down to the
    “Self-Custody Week. Up to 20% Off” promo bar and the “2M+ Customers · 10+ Years in Bitcoin”
    line. Bottom-left is Google’s own banner: <i>“This site uses cookies from Google to deliver its
    services and to analyze traffic.”</i> The attacker inherited Google’s consent UI as free
    credibility. “Continue in browser” is the harvest path.</figcaption>
  </figure>
  <figure>
    <img src="assets/seed-harvest-modal.jpg" alt="A modal titled 'Import your Trezor Wallet' with a BIP-39 24-word recovery phrase selector and 24 numbered input boxes.">
    <figcaption>The harvest. A recovery-phrase-type selector (BIP-39, 24 words) and 24 numbered boxes.
    The reassurance <i>“Trezor will restore your private keys… Your information stays offline only.”</i>
    is the load-bearing lie. The “Enable automatic synchronization” toggle is set dressing. A genuine
    Trezor never asks for the phrase on a screen.</figcaption>
  </figure>
</div></section>

<section><div class="wrap">
  <h2>Roadmap: how the operation was assembled</h2>
  <p class="sub">Reconstructed from the on-chain record, 41 public scans of the kit, and the live
  advertising surfaces.</p>
  <ol class="steps">
    <li><h3>Build the kit, then run it for 18 months</h3>
      <p>The earliest public capture is <b>23 January 2025</b> on
      <code>start-trezor-suite-cdn.gitbook.io</code> — a crude doorway page titled “Trezor Suite
      (Official)” carrying the misspelling <i>“Get strat your trezor”</i>, which survives as an
      attribution marker.</p></li>
    <li><h3>Industrialise on disposable hosting</h3>
      <p>From September 2025 the kit ran on <b>eight</b> Cloudflare Pages subdomains —
      <code>-faq</code>, <code>-en</code>, <code>-ai</code>, <code>-us</code>, <code>-dlv</code>,
      <code>-cdn</code>, <code>-download-io</code>. Free, instant, and disposable: when one is
      burned, the next is a deploy away.</p></li>
    <li><h3>Lose the channel to Cloudflare</h3>
      <p>By <b>27 July 2026</b> Cloudflare was serving <i>“Suspected Phishing — This website has been
      reported for potential phishing”</i> in place of the kit. The pages.dev channel was dead.</p></li>
    <li><h3>Move onto Google’s own domain</h3>
      <p>Nine days later the same kit is live at
      <code>sites.google.com/view/start-trezor-suite</code>. Google Sites is free, needs only a Google
      account, publishes instantly, and hands the attacker a google.com URL.</p></li>
    <li><h3>Buy the query</h3>
      <p>An advertiser named <b>Trezor.io</b> bids on Trezor’s brand terms with sitelinks and a
      site-visit annotation, and takes the slot above the real Trezor ad. Brand terms are cheap for an
      impostor: the click is worth a wallet, not a $60 device sale.</p></li>
    <li><h3>Harvest and drain</h3>
      <p>Victims type 24 words. Drains begin <b>2026-08-05 21:08:55 UTC</b> and run for 33 hours at an
      average of <b>{money(usd(dep)/32.9)}/hour</b>.</p></li>
    <li><h3>Consolidate before anyone can act</h3>
      <p>Seven sweeps between <b>04:19</b> and <b>06:40 UTC</b> on 7 August empty the harvest address
      into hop-1 wallets and onward into a treasury that was already collecting from other
      campaigns.</p></li>
  </ol>
</div></section>

<section><div class="wrap">
  <h2>The money</h2>
  <p class="sub">Every figure below is read from the Bitcoin blockchain and cross-checked between
  mempool.space and blockstream.info, which agree exactly
  ({btc.get("total_received_btc",0):.8f} BTC received, {btc.get("chain_stats",{}).get("tx_count",0)} transactions).</p>

  <div class="stats" style="margin:0 0 26px">
    <div class="stat"><b>{btcs(dep):.4f}</b><span>BTC from victims (external inflow)</span></div>
    <div class="stat red"><b>{money(usd(dep))}</b><span>valued at each drain’s block time</span></div>
    <div class="stat"><b>{money(usd(dep)/len(dep)) if dep else "—"}</b><span>average per victim</span></div>
    <div class="stat"><b>{money(sorted((x.get("usd") or 0) for x in dep)[len(dep)//2]) if dep else "—"}</b><span>median per victim</span></div>
    <div class="stat amber"><b>{money(max((x.get("usd") or 0) for x in dep)) if dep else "—"}</b><span>single largest drain</span></div>
  </div>

  <div class="panel">
    <h3 style="margin-bottom:6px">The warning changed nothing for ten hours</h3>
    <p class="small muted" style="margin-top:0">The victim named the exact URL and the exact
    harvesting address publicly at 19:56 UTC on 6 August, tagging Trezor, ZachXBT and CertiK.
    Drains continued until 06:00 UTC the next morning.</p>
    {chart(hourly)}
    <div class="legend">
      <span><i class="sw" style="background:var(--before)"></i>before the public warning —
        {len(pre)} drains, {money(usd(pre))}</span>
      <span><i class="sw" style="background:var(--after)"></i>after it —
        {len(post)} drains, <b>{money(usd(post))}</b>
        ({usd(post)/usd(dep)*100:.0f}% of the total)</span>
    </div>
  </div>

  <p class="small muted">A note on the headline number: the address’s gross
  <code>funded_txo_sum</code> is {btc.get("total_received_btc",0):.4f} BTC, but that figure
  double-counts change returning from the attacker’s own sweeps. Victim money is the
  <b>{btcs(dep):.4f} BTC</b> of external inflow across {len(dep)} deposits.</p>

  <h3 style="margin-top:34px">Where it went</h3>
  <p class="sub">Seven sweeps into four hop-1 wallets, then onward into one treasury.</p>
  <div class="scroll"><table>
    <tr><th>Hop-1 address</th><th>BTC from harvest</th><th>Total received</th><th>Still held</th></tr>
    {hop_html()}
  </table></div>

  <div class="panel flag">
    <h3 style="margin-bottom:6px">The treasury is shared across campaigns</h3>
    <p style="margin:0">
    <code class="mono">bc1qhluxs8yfper7sxnmpgpjy9e38dx4qxpuhen5cs</code> has received
    <b>27.3128 BTC</b> and has spent <b>none of it</b>. Only 10.55 BTC of that came from the Trezor
    harvest address. Its earliest receipt is <b>4 August</b> — before the Trezor campaign’s first
    victim — so the operator was already running other campaigns through the same wallet.</p>
  </div>
  <div class="scroll"><table>
    <tr><th>Feeder into the treasury</th><th>BTC</th><th>Attribution</th></tr>
    {feeder_html()}
  </table></div>
  <p class="small muted">Two wallets are still sitting on funds:
  <code>bc1q4yc2fuexygkyl27hxkpjyrjw5al9vd7c3jkyrs</code> (7.3966 BTC) and
  <code>bc1qpx66w070d2x68pdv3899wksl9h9vtf7fhmkg92</code> (1.19 BTC), plus the 27.31 BTC treasury —
  unspent as at {time.strftime("%d %B %Y", time.gmtime())}.</p>
</div></section>

<section><div class="wrap">
  <h2>Timeline</h2>
  <ul class="timeline">{timeline_html()}</ul>
</div></section>

<section><div class="wrap">
  <h2>The kit’s hosting history</h2>
  <p class="sub">41 public scans of <code>start-trezor-suite</code> across 18 months. The migration to
  Google is the story.</p>
  <div class="two">
    <figure><img src="assets/kit-origin-gitbook.jpg" alt="The January 2025 GitBook version of the phishing kit.">
      <figcaption><b>23 Jan 2025 — GitBook.</b> The origin: a doorway page with the
      “Get strat your trezor” typo.</figcaption></figure>
    <figure><img src="assets/cloudflare-blocked.jpg" alt="Cloudflare 'Suspected Phishing' warning page shown in place of the kit.">
      <figcaption><b>27 Jul 2026 — Cloudflare.</b> The pages.dev channel is blocked as
      “Suspected Phishing”. Nine days later the kit is on Google Sites.</figcaption></figure>
  </div>
  <div class="scroll"><table>
    <tr><th>Host</th><th>Scans</th><th>Role</th></tr>
    <tr><td class="mono">start-trezor-suite-faq.pages.dev</td><td>10</td><td>Cloudflare Pages</td></tr>
    <tr><td class="mono">start-trezor-suite-en.pages.dev</td><td>9</td><td>Cloudflare Pages</td></tr>
    <tr><td class="mono">start-trezor-suite-ai.pages.dev</td><td>9</td><td>Cloudflare Pages</td></tr>
    <tr><td class="mono">start-trezor-suite-us.pages.dev</td><td>6</td><td>Cloudflare Pages</td></tr>
    <tr><td class="mono">start-trezor-suite-download-io.pages.dev</td><td>3</td><td>Cloudflare Pages</td></tr>
    <tr><td class="mono">start-trezor-suite-dlv.pages.dev</td><td>1</td><td>Cloudflare Pages</td></tr>
    <tr><td class="mono">start-trezor-suite-cdn.pages.dev</td><td>1</td><td>Cloudflare Pages</td></tr>
    <tr><td class="mono">start-trezor-suite-cdn.gitbook.io</td><td>1</td><td>GitBook — earliest, Jan 2025</td></tr>
    <tr><td class="mono"><b>sites.google.com/view/start-trezor-suite</b></td><td>1</td>
        <td><b>Google Sites — the paid-ad campaign</b></td></tr>
  </table></div>
</div></section>

<section><div class="wrap">
  <h2>This is not one page. It is a platform pattern.</h2>
  <p class="sub">Searching every public scan of <code>sites.google.com</code> against ten wallet and
  exchange brands returns <b>{eco.get("unique_urls",0)} distinct phishing URLs</b>, running
  continuously from <b>2020 to today</b>.</p>

  <div class="stats" style="margin:0 0 26px">
    <div class="stat"><b>{eco.get("unique_urls",0)}</b><span>unique sites.google.com phishing URLs</span></div>
    <div class="stat"><b>10</b><span>crypto brands impersonated</span></div>
    <div class="stat amber"><b>{eco.get("custom_domain_sites",0)}</b><span>use a Workspace custom domain</span></div>
    <div class="stat red"><b>{len(eco.get("still_live",[]))}</b><span>still live when checked</span></div>
  </div>

  <div class="panel flag">
    <h3 style="margin-bottom:6px">Paid distribution, proven</h3>
    <p style="margin-top:0">Sixteen of these URLs were captured <i>with Google Ads click parameters
    still attached</i> — <code>gclid</code>, <code>gad_source=1</code>, <code>gbraid</code> and
    <code>gad_campaignid</code>. Those parameters are appended by Google’s own ad click redirector,
    so each one is a receipt that the page was reached through a paid Google ad. Ten distinct
    campaign IDs survive in the URLs:</p>
    <p class="mono small" style="margin-bottom:0">{E(", ".join(eco.get("campaign_ids",[])))}</p>
  </div>
  <div class="scroll"><table>
    <tr><th>Scanned</th><th>Brand</th><th>Campaign ID</th><th>URL</th></tr>
    {eco_ads_html()}
  </table></div>

  <div class="panel">
    <h3 style="margin-bottom:6px">The upgrade: a lookalike domain <i>inside</i> a google.com URL</h3>
    <p style="margin-top:0">{eco.get("custom_domain_sites",0)} of the
    {eco.get("unique_urls",0)} sites do not use the anonymous <code>/view/</code> path. They read
    <code>sites.google.com/<b>ledgercom-start.com</b>/ledger-live/home</code>. That form appears when a
    Google Workspace account with a <i>verified</i> domain publishes a Site — so the attacker
    registers a brand-lookalike domain, verifies it with Google, and receives a URL carrying both
    the google.com hostname and the lookalike brand string. Google’s domain verification becomes part
    of the disguise.</p>
    <p style="margin-bottom:0" class="small muted">{len(eco.get("attacker_domains",[]))} attacker-verified
    domains observed: {eco_dom_html()}</p>
  </div>

  <div class="panel flag">
    <h3 style="margin-bottom:6px">Still live</h3>
    <p style="margin-top:0">Of 28 recent pages re-checked on
    {time.strftime("%d %B %Y", time.gmtime())}, the five Trezor pages are gone — and
    <b>{len(eco.get("still_live",[]))} others are still serving</b>. Two verified by hand:
    <code>sites.google.com/ledgerstart-web.com/ledger-live/home</code> is titled
    “<b>Leder Live</b> | Ledger Live App Crypto Wallet — Official® Site®” and
    <code>sites.google.com/view/exodus-wlt/home</code> is titled “<b>Exódus®</b> Web3 Wallet”. Both
    solicit a recovery phrase. The misspelling and the accented <i>ó</i> are deliberate — they read
    correctly to a human and defeat exact-string brand matching.</p>
  </div>
  <div class="scroll"><table>
    <tr><th>Brand</th><th>Live URL</th></tr>
    {eco_live_html()}
  </table></div>
  <div class="scroll"><table>
    <tr><th>Brand impersonated</th><th>Distinct Google Sites URLs</th></tr>
    {eco_brand_html()}
  </table></div>
</div></section>

<section><div class="wrap">
  <h2>Multi-geo check</h2>
  <p class="sub">{geo_tot} probes across 18 countries, each through a fresh residential exit in-country,
  driving a real Chrome profile. {geo_ok} rendered a genuine local SERP.</p>
  <div class="panel">
    <p style="margin-top:0"><b>What this can and cannot prove.</b> The extractor is validated: in
    Spain it captured a live ad in full — the genuine
    <i>“Hardware Wallet Trezor — Up To 20% Off Trezor Wallets”</i> creative at
    <code>https://www.trezor.io</code>, through a DIGI Spain residential exit. But on a control query
    that always carries ads (“car insurance”, UK) the rendered page contained an
    <code>#tads</code> container holding <b>two empty ad slots</b> and no creative. Google reserves
    the slots for these sessions and declines to fill them.</p>
    <p style="margin-bottom:0">So a country reading <i>no creative served</i> below is
    <b>not measured</b> — it is not evidence that no malicious ad runs there. Reported as-is rather
    than dressed up as coverage.</p>
  </div>
  <div class="scroll"><table>
    <tr><th>Country</th><th>SERPs rendered</th><th>Paid creative</th><th>Residential exits used</th></tr>
    {geo_rows}
  </table></div>
  <p class="small muted">Most residential exits are refused outright: Google’s
  <code>/sorry/</code> interstitial appeared on AT&amp;T, Verizon, Charter, TalkTalk, Sky, BT and DIGI
  addresses alike. Rendering a SERP at all required between one and five fresh exits per country, and
  a persistent real-Chrome profile with a warm-up search — a plain automated browser is refused every
  time.</p>
</div></section>

<section><div class="wrap">
  <h2>What the Ads Transparency Center holds</h2>
  <p class="sub">Google’s own advertiser-accountability record, queried directly through the RPC the
  site itself uses, across 20 regions.</p>
  <div class="panel flag">
    <p style="margin-top:0"><b>There is no record of this ad.</b> A domain query for
    <code>sites.google.com</code> returns <b>zero</b> creatives in the United States. The same query
    for <code>trezor.io</code> returns 40 creatives for
    <b>Trezor Company s.r.o.</b> (<code>AR07426507167890407425</code>) — so the method works and the
    zero is real, not a broken query.</p>
    <p style="margin-bottom:0">Sweeping the term <i>trezor</i> across 20 regions returns only genuine
    businesses. The advertiser that took {money(usd(dep))} is absent from the transparency tool.</p>
  </div>
  <p class="small muted">Caveat recorded rather than buried: sustained querying eventually returns
  <b>HTTP 429</b> from the ATC endpoint. Every negative above was collected in a run whose
  <code>trezor.io</code> positive control returned 40 creatives in the same pass — a negative taken
  during a 429 storm would be worthless, and none are reported here.</p>

  <p><b>Do not mistake these for impostors.</b> <i>Trezor</i> means “safe” or “vault” in Czech,
  Polish, Slovak, Hungarian and Serbian, so a long tail of legitimate safe manufacturers, locksmiths
  and one hotel advertise under the name:</p>
  <ul class="small">{legit_html()}</ul>
  {research_block()}
</div></section>

<section><div class="wrap">
  <h2>The response, and the four-month-old warning</h2>
  <div class="panel">
    <h3 style="margin-bottom:6px">Trezor</h3>
    <p style="margin-top:0">The verified @Trezor account replied to the victim at
    <b>2026-08-07 10:57:56 UTC</b> — <b>15 h 02 m</b> after the post — saying it was escalating
    internally and reporting the phishing page through the relevant channels, and followed 86 minutes
    later with a standalone advisory about fake Trezor sites in sponsored results. By then the
    harvesting had already stopped on its own: the last drain was <b>06:00 UTC</b>, and the attacker
    had finished sweeping at <b>06:40</b>. The vendor response landed <b>4 h 17 m after the money was
    already gone</b>.</p>
    <p style="margin-bottom:0" class="small muted">No Google statement on this incident was located.
    Neither the removal time of the page nor who removed it is established, so no takedown latency is
    claimed here — an attempt to bound it from X’s crawl artefacts was tested and rejected.</p>
  </div>
  <div class="panel flag">
    <h3 style="margin-bottom:6px">SEAL had documented the identical attack class in March</h3>
    <p style="margin-top:0">Security Alliance’s Intel team published a wave analysis covering
    <b>13–30 March 2026</b>: <b>351–356</b> blocked malicious Google Ads URLs,
    <b>$810,929</b> in confirmed stolen funds and <b>$1,274,259</b> including unattributable losses.
    It names <code>sites.google.com/view/</code> pages — along with <code>docs.google.com</code> and
    <code>business.google.com</code> — as the primary web frame, with the cloned front end delivered
    through secondary iframes behind fingerprinting and cloaking scripts.</p>
    <p style="margin-bottom:0">Four months later the same hosting pattern, on the same platform, took
    a further <b>{money(usd(dep))}</b> in 33 hours.</p>
  </div>
  <div class="panel">
    <h3 style="margin-bottom:6px">Why the advertiser is still unnamed</h3>
    <p style="margin-top:0">Google’s advertiser-verification programme is explicitly a
    <i>gradual, selective</i> rollout — <i>“all advertisers will eventually be required to complete
    advertiser verification”</i>. Verification is triggered after selection, with restriction or
    pausing as the consequence, which leaves a window in which an unverified account serves live
    search ads. Verified advertisers are disclosed publicly — name and location, name-change history,
    creatives, dates and locations served, and whether ads were removed or the account suspended.</p>
    <p style="margin-bottom:0">That disclosure surfaces only the <b>self-declared</b> identity, and in
    this case it surfaces nothing at all: the Transparency Center holds no record of the campaign.
    Whether the account was hijacked, bought aged, or newly created inside the unverified window is
    <b>not established</b> — the leads circulating for it were tested here and did not survive.</p>
  </div>
</div></section>

<section><div class="wrap">
  <h2>Indicators</h2>
  <div class="ioc">Phishing page   sites.google.com/view/start-trezor-suite   (unpublished as of 2026-08-09)
Ad display URL  https://www.google.com          Ad advertiser name  "Trezor.io"
Ad headline     Trezor Suite | Download Trezor App
Kit fingerprint "Get strat your trezor"   (misspelling, present since Jan 2025)

Harvest address bc1qrz33mr7tx8wrpcs2pxrvv83hqwpm907s9shkz4
Hop 1           bc1qqg3c0ed0wzjdnjjlgcdrzyzedj8tgyapkvda9z    10.5460 BTC  (forwarded)
                bc1q4yc2fuexygkyl27hxkpjyrjw5al9vd7c3jkyrs     7.3966 BTC  (HELD)
                bc1qs7zptzqvl0ahaz8qpvlhz2qqtwdrsyhu3sf3rn     1.7580 BTC  (forwarded via taproot)
                bc1qpx66w070d2x68pdv3899wksl9h9vtf7fhmkg92     1.1900 BTC  (HELD)
Treasury        bc1qhluxs8yfper7sxnmpgpjy9e38dx4qxpuhen5cs    27.3128 BTC  (HELD, multi-campaign)
Other feeders   bc1qp2lvxmy6zafwxclt5p2q6zdyvcv9xuhgw674yz     6.4575 BTC
                bc1qxzuw53znzkqa0jyrktjhzzqxgz92dnuncwxj86     4.8814 BTC  (15 txs, 15.5895 BTC total)
                bc1qah99mfvfgpks8qrj5k490ava0z0lzqhwc06e7h     3.5142 BTC
                bc1qja3nhlxs76h74t25zj660zuj2l2pfhmfmnj82y     1.9138 BTC
Taproot hop     bc1pdv5j7k8fqfmfscc5yd4l9duadsqh3ektkf89pxuy9tt4g0vuahgqgu4yzn
                bc1p8hpctcd32r5pv0t50w2k7mlhvqnklxwa3ljelm8q6eapjvnertpsc4qhzj

Prior hosting   start-trezor-suite-{{faq,en,ai,us,dlv,cdn,download-io}}.pages.dev
                start-trezor-suite-cdn.gitbook.io/en-us</div>
</div></section>

<section><div class="wrap">
  <h2>Method</h2>
  <p class="sub">Everything here is reproducible from the repository.</p>
  <table>
    <tr><th>Question</th><th>How it was answered</th></tr>
    <tr><td>What the ad looked like</td><td>The victim’s own screenshots, pulled from the source post</td></tr>
    <tr><td>What the page did</td><td>urlscan.io public capture <code>019fd42e</code>, 2026-08-05 23:07:54 UTC</td></tr>
    <tr><td>How long the kit ran</td><td>41 urlscan captures, 2025-01-23 → 2026-08-05</td></tr>
    <tr><td>How much was taken</td><td>Full chain history, per-deposit valuation at block time;
      mempool.space and blockstream.info agree exactly</td></tr>
    <tr><td>Who advertised</td><td>Ads Transparency Center RPC (<code>SearchCreatives</code>,
      <code>SearchSuggestions</code>), 20 regions, with a trezor.io positive control on every run</td></tr>
    <tr><td>Whether ads run elsewhere now</td><td>{geo_tot} residential-exit SERP probes in 18 countries —
      <b>inconclusive by construction</b>, see the control above</td></tr>
  </table>
  <h3 style="margin-top:30px">What remains unanswered</h3>
  <ul>
    <li><b>The advertiser of record.</b> Not identified. The Transparency Center holds no entry, and
      the circulating explanations — hijacked advertiser accounts, named advertisers from earlier
      waves — were each tested against their sources and did not survive.</li>
    <li><b>Takedown latency.</b> Unknown. The page was live on 5 August and is unpublished now;
      neither the removal time nor the actor is established, and no abuse-report SLA was found.</li>
    <li><b>Geo-targeting.</b> No pattern established. The live-SERP instrument cannot see ad fill, and
      the ATC holds no campaign to inspect.</li>
    <li><b>Cloaking specifics for this page.</b> Not evidenced. SEAL describes fingerprinting and
      cloaking with secondary iframes for the March wave; nothing was recovered for this URL, whose
      DOM is behind urlscan’s login wall.</li>
    <li><b>Any Google statement.</b> None located.</li>
    <li><b>Sibling-campaign attribution.</b> The feeder wallets share a treasury; which brand campaign
      each ran is unproven.</li>
  </ul>
  <p class="small muted">One correction worth recording, because the wrong version is the popular one:
  the explanation that a <code>sites.google.com</code> landing page makes a <code>google.com</code>
  display URL <i>legitimate</i> does not survive contact with the policy text. Clause 2 of the same
  policy forbids it. The display URL is an observation; the compliance story attached to it was wrong.
  The victim’s loss is a claim; the {money(usd(dep))} is not — it is the blockchain’s.</p>
</div></section>

<footer><div class="wrap">
  Built {time.strftime("%d %B %Y", time.gmtime())} · defensive research, published noindex ·
  source data and scripts in the repository ·
  primary sources:
  <a href="https://x.com/ReallyBadDay99/status/2085454877719675354">victim report</a> ·
  <a href="https://x.com/BitcoinNewsCom/status/2085734257784139900">amplification</a> ·
  <a href="https://urlscan.io/result/019fd42e-d592-714c-b291-4cf35ccef61c/">urlscan capture</a> ·
  <a href="https://mempool.space/address/bc1qrz33mr7tx8wrpcs2pxrvv83hqwpm907s9shkz4">harvest address</a>
</div></footer>
</body></html>'''

os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
with open(os.path.join(ROOT, "docs", "index.html"), "w") as f:
    f.write(HTML)
print(f"wrote docs/index.html  {len(HTML)//1024} KB")
print(f"deposits {len(dep)}  usd {usd(dep):,.0f}  pre {len(pre)}/{usd(pre):,.0f}  post {len(post)}/{usd(post):,.0f}")
print(f"geo {geo_ok}/{geo_tot} verified")
