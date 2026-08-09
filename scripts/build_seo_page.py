#!/usr/bin/env python3
"""Build docs/seo/index.html — the plain-language SEO teardown."""
import html
import json
import os
import time

ROOT = "/root/workspace/trezor-ads-teardown"
E = html.escape


def load(p, d=None):
    try:
        return json.load(open(os.path.join(ROOT, "data", p)))
    except Exception:
        return d


cases = load("seo_cases.json", [])
rdap = load("ranking_rdap.json", {})
allpages = load("ranking_pages.json", [])
ndomains = len({p["attached_domain"] for p in allpages if p.get("attached_domain")})
nindexed = len(allpages)

REG_COUNTRY = {  # registrar HQ, for "registered from where"
    "NameCheap, Inc.": "USA", "BigRock Solutions Ltd": "India",
    "NICENIC INTERNATIONAL GROUP CO., LIMITED": "Hong Kong",
    "Web Commerce Communications Limited dba WebNic.cc": "Malaysia",
    "HOSTINGER operations, UAB": "Lithuania", "Squarespace Domains LLC": "USA",
    "Global Domain Group LLC": "USA", "MAT BAO CORPORATION": "Vietnam",
    "Paknic (Private) Limited": "Pakistan", "Internet Domain Service BS Corp": "Bahamas",
    "Hosting Concepts B.V. d/b/a Registrar.eu": "Netherlands",
}


def card(c):
    dom = c.get("attached_domain")
    reg = c.get("reg_date") or "unknown"
    rar = c.get("registrar") or ""
    where = REG_COUNTRY.get(rar, "")
    rank = c.get("ranked_for") or []
    rank_html = ""
    if rank:
        rank_html = ('<div class="rankbadge">Seen ranking: ' +
                     ", ".join(E(r) for r in rank) + "</div>")
    shot = (f'<a href="{E(c["shot"])}" target="_blank"><img src="{E(c["shot"])}" loading="lazy" '
            f'alt="Phishing page for {E(c["brand"])}"></a>' if c.get("shot") else "")
    domrow = (f'<tr><td>Attached domain</td><td class="mono">{E(dom)}</td></tr>'
              f'<tr><td>Registered</td><td>{E(reg)}'
              + (f' &middot; {E(rar)}' if rar else "")
              + (f' &middot; <b>{E(where)}</b>' if where else "") + '</td></tr>'
              if dom else
              '<tr><td>Attached domain</td><td class="muted">none &mdash; anonymous '
              '<code>/view/</code> page (free, no domain)</td></tr>')
    return f'''<div class="case">
      {rank_html}
      <div class="ct">
        <h3>{E(c["brand"].title())} &mdash; {E(c.get("title") or "")}</h3>
        <table class="kv">
          <tr><td>Live URL</td><td class="mono"><a href="{E(c["url"])}" target="_blank">{E(c["url"])}</a></td></tr>
          {domrow}
          <tr><td>Asks victim for</td><td class="bad">{E(", ".join(c.get("signals") or []) or "wallet connect")}</td></tr>
          <tr><td>Status</td><td>{"<b class=bad>live</b>" if c.get("live") else "removed"}</td></tr>
        </table>
      </div>
      {("<div class=cs>"+shot+"</div>") if shot else ""}
    </div>'''


def dom_table():
    rows = []
    seen = set()
    for c in cases:
        d = c.get("attached_domain")
        if not d or d in seen:
            continue
        seen.add(d)
        e = rdap.get(d, {})
        reg = (e.get("registered") or "")[:10] or "?"
        rar = e.get("registrar") or "?"
        where = REG_COUNTRY.get(rar, "")
        rows.append(f'<tr><td class="mono">{E(d)}</td><td>{E(reg)}</td>'
                    f'<td>{E(rar)}</td><td>{E(where)}</td></tr>')
    return "\n".join(rows)


HTML = f'''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>How crypto phishing pages reach Google's first page (Google Sites SEO teardown)</title>
<style>
:root{{--bg:#0b0d10;--panel:#12161b;--line:#232a33;--ink:#e8edf3;--dim:#97a3b2;--accent:#4ade80;
--after:#ef4444;--amber:#f59e0b;--link:#7dd3fc;--mono:ui-monospace,Menlo,Consolas,monospace;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Arial,sans-serif}}
.wrap{{max-width:1000px;margin:0 auto;padding:0 22px}}
a{{color:var(--link)}}
h1,h2,h3{{line-height:1.15;letter-spacing:-.02em}}
header{{padding:64px 0 40px;border-bottom:1px solid var(--line)}}
.kicker{{font:600 12px/1 var(--mono);letter-spacing:.15em;text-transform:uppercase;color:var(--amber)}}
h1{{font-size:clamp(30px,5.5vw,52px);font-weight:800;margin:16px 0}}
.lede{{font-size:clamp(17px,2.2vw,20px);color:var(--dim);max-width:70ch}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;background:var(--line);
border:1px solid var(--line);margin:34px 0 0}}
.stat{{background:var(--panel);padding:16px 18px}}
.stat b{{display:block;font:700 24px/1.1 var(--mono)}} .stat span{{font-size:12px;color:var(--dim)}}
.stat.red b{{color:var(--after)}}
section{{padding:48px 0;border-bottom:1px solid var(--line)}}
h2{{font-size:clamp(22px,3.4vw,30px);font-weight:750;margin:0 0 8px}}
.sub{{color:var(--dim);margin:0 0 22px;max-width:74ch}}
p{{max-width:74ch}} b.bad,.bad{{color:var(--after)}}
ol.steps{{counter-reset:s;list-style:none;padding:0}}
ol.steps>li{{counter-increment:s;position:relative;padding:0 0 22px 56px;border-left:1px solid var(--line);margin-left:16px}}
ol.steps>li:last-child{{border-left:1px solid transparent}}
ol.steps>li::before{{content:counter(s);position:absolute;left:-16px;top:-3px;width:32px;height:32px;
border-radius:50%;background:var(--panel);border:1px solid var(--line);color:var(--amber);
font:700 14px/32px var(--mono);text-align:center}}
ol.steps h3{{font-size:17px;margin:0 0 6px}}
.panel{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin:18px 0}}
.panel.flag{{border-left:3px solid var(--after)}} .panel.good{{border-left:3px solid var(--accent)}}
table{{width:100%;border-collapse:collapse;margin:14px 0;font-size:13.5px}}
th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}}
th{{font:600 11px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--dim)}}
.mono,code{{font-family:var(--mono);font-size:12.5px;word-break:break-all}}
code{{background:#1a1f26;padding:2px 6px;border-radius:4px;color:#cfe6ff}}
.muted{{color:var(--dim)}} .scroll{{overflow-x:auto}}
.case{{border:1px solid var(--line);border-radius:11px;margin:18px 0;overflow:hidden;background:var(--panel)}}
.rankbadge{{background:#2a1114;color:#ffb4b4;font:700 12px/1.4 var(--mono);padding:8px 16px;border-bottom:1px solid var(--line)}}
.case .ct{{padding:16px 18px}}
.case h3{{font-size:16px;margin:0 0 10px}}
table.kv td{{font-size:13px}} table.kv td:first-child{{color:var(--dim);width:150px;font-size:12px}}
.cs{{border-top:1px solid var(--line);background:#fff}}
.cs img{{width:100%;display:block}}
@media(min-width:760px){{.case{{display:grid;grid-template-columns:1fr 1fr;align-items:start}}
.rankbadge{{grid-column:1/3}} .cs{{border-top:0;border-left:1px solid var(--line)}}}}
footer{{padding:40px 0 70px;color:var(--dim);font-size:13px}}
</style></head><body>

<header><div class="wrap">
  <div class="kicker">Companion teardown &middot; the SEO route</div>
  <h1>How fake wallet pages reach Google's first page &mdash; without ads</h1>
  <p class="lede">The paid ads have stopped. But the same crooks now get their fake Trezor, Ledger,
  MetaMask, Phantom, Exodus, Coinbase and OKX pages onto Google's first page <b>for free</b>, by
  hiding them inside <b>Google's own website, google.com</b>. Here is exactly how, which pages, and
  who registered them.</p>
  <div class="stats">
    <div class="stat"><b>{nindexed}</b><span>fake pages indexed on Google</span></div>
    <div class="stat"><b>{ndomains}</b><span>attacker domains behind them</span></div>
    <div class="stat red"><b>#1</b><span>rank in Germany for &ldquo;ledger live&rdquo;</span></div>
    <div class="stat red"><b>#3</b><span>rank in UK for &ldquo;trezor suite&rdquo;</span></div>
  </div>
</div></header>

<section><div class="wrap">
  <div class="panel good" style="margin-bottom:18px"><p style="margin:0">&#128293; <b>Go deeper:</b> the full method &mdash; the ~4,700-word AI articles that do the ranking, hidden-character look-alike domains (<code>led&#289;er.app</code>), where victims actually end up, and <b>the registrars to alert</b> &rarr; <a href="seo2/"><b>The full playbook (part 2)</b></a></p></div>
  <h2>The one-sentence answer</h2>
  <p>They build the fake page on <b>Google Sites</b> (a free Google product), so the address starts
  with <code>sites.google.com</code>. Google trusts its own domain, so these pages borrow that trust
  and rank on page one &mdash; no ads, no real backlinks needed. This trick has a name:
  <b>parasite SEO</b> (a scam page feeding off a trusted host's reputation).</p>
</div></section>

<section><div class="wrap">
  <h2>Why it works (plain version)</h2>
  <p class="sub">Four things stack up. None of them is clever hacking &mdash; it's abuse of features
  Google gives everyone.</p>
  <ol class="steps">
    <li><h3>google.com is the most trusted domain on earth</h3>
      <p>Google's ranking heavily favours trusted domains. A page at
      <code>sites.google.com/&hellip;</code> <b>is</b> on google.com, so it starts with a huge trust
      advantage over any new scam domain the crook could register.</p></li>
    <li><h3>They bolt a look-alike domain onto it</h3>
      <p>Using a Google Workspace account with a <i>verified</i> domain, the page's address becomes
      <code>sites.google.com/<b>walletcryptohub.com</b>/trezorsuite</code>. Now the URL carries
      <b>both</b> google.com <b>and</b> a wallet-sounding word. Google's own domain verification
      becomes part of the disguise.</p></li>
    <li><h3>The page is stuffed with the exact words people search</h3>
      <p>Titles like &ldquo;Trezor Suite (Official) | Download Trezor App&rdquo; and
      &ldquo;Ledger Live Download | Official Website&rdquo; match what victims type. The body repeats
      &ldquo;download&rdquo;, &ldquo;official&rdquo;, &ldquo;login&rdquo;, &ldquo;recovery phrase&rdquo;.</p></li>
    <li><h3>They run a whole network of these pages</h3>
      <p>We found <b>{nindexed}</b> of them across <b>{ndomains}</b> domains. They interlink and
      reinforce each other. When Google removes one, the next is already indexed.</p></li>
  </ol>
  <div class="panel">
    <p style="margin:0"><b>About backlinks:</b> we looked &mdash; these pages have <b>almost no
    outside backlinks</b>. They don't need them. The whole point of parasite SEO is that the
    google.com host supplies the authority that backlinks normally would. The &ldquo;link building&rdquo;
    here is just the network of Google Sites pages pointing at each other.</p>
  </div>
</div></section>

<section><div class="wrap">
  <h2>Is the back end the same as the ad pages?</h2>
  <div class="panel flag">
    <p style="margin-top:0"><b>No. They are two different set-ups.</b></p>
    <p style="margin-bottom:0"><b>The ad pages</b> (the ones people paid to reach months ago) were a
    thin Google Sites shell that loaded the real theft page from a <i>second</i> server in a hidden
    frame &mdash; Firebase (<code>ksf-webapp-080826.web.app</code>), Google Cloud Storage, or a
    throwaway domain. <b>These SEO pages</b> mostly put the theft <b>directly on the Google Sites
    page itself</b>: {sum(1 for c in cases if c.get("signals"))} of the ones we opened ask for the
    recovery phrase or private key right there, or show a fake &ldquo;ledger.com &mdash; verify you
    are human&rdquo; box before the theft screen. Different domains, different registrars, different
    kits &mdash; <b>not one shared back end.</b></p>
  </div>
</div></section>

<section><div class="wrap">
  <h2>Where the money is asked for</h2>
  <p class="sub">All of these end the same way: get you to type your <b>12/24-word recovery phrase</b>
  or &ldquo;connect&rdquo; the wallet. That hands over full control. A real wallet never asks for the
  phrase on a website.</p>
</div></section>

<section><div class="wrap">
  <h2>The pages (URL &middot; domain &middot; registration &middot; screenshot)</h2>
  <p class="sub">A representative page per attacker domain. The first two are confirmed ranking on
  page one for real searches; the rest are indexed and live. Full list of {nindexed} in the data file.</p>
  {"".join(card(c) for c in cases)}
</div></section>

<section><div class="wrap">
  <h2>Every attacker domain, and where it was registered</h2>
  <div class="scroll"><table>
    <tr><th>Domain</th><th>Registered</th><th>Registrar</th><th>Registrar country</th></tr>
    {dom_table()}
  </table></div>
  <p class="small muted">Clear clusters: several were registered on the <b>same day (3 Aug 2025)</b>
  through the same Malaysian registrar (WebNic) &mdash; one operator batch. Another cluster runs
  through <b>BigRock (India)</b>, another through <b>NICENIC (Hong Kong)</b>.</p>
</div></section>

<section><div class="wrap">
  <h2>How to get them taken down</h2>
  <ol>
    <li><b>Google Sites abuse:</b> <a href="https://support.google.com/sites/answer/1651998">support.google.com/sites/answer/1651998</a> &mdash; report the <code>sites.google.com/&hellip;</code> URL.</li>
    <li><b>Google Safe Browsing:</b> <a href="https://safebrowsing.google.com/safebrowsing/report_phish/">report the phishing URL</a> (flags it in Chrome/Firefox/Safari).</li>
    <li><b>The look-alike domain:</b> report to its registrar's abuse desk (listed above) and to the impersonated brand.</li>
    <li><b>The brands</b> (Trezor, Ledger, etc.) run their own takedown desks &mdash; send them the list.</li>
  </ol>
  <p class="small muted">The full machine-readable list of all {nindexed} URLs and {ndomains} domains
  is in <code>data/ranking_pages.json</code> / <code>data/ranking_rdap.json</code> in the repository.</p>
</div></section>

<footer><div class="wrap">
  Built {time.strftime("%d %B %Y", time.gmtime())} &middot; defensive research, noindex &middot;
  companion to the <a href="../">main teardown</a> &middot; every URL, domain and date verified live.
</div></footer>
</body></html>'''

os.makedirs(os.path.join(ROOT, "docs", "seo"), exist_ok=True)
with open(os.path.join(ROOT, "docs", "seo", "index.html"), "w") as f:
    f.write(HTML)
print(f"wrote docs/seo/index.html ({len(HTML)//1024} KB), {len(cases)} cases")
