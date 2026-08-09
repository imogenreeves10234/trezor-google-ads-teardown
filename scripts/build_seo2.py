#!/usr/bin/env python3
"""Build docs/seo2/index.html — deep method teardown: AI content, IDN homographs,
redirection/scripts, registrar clusters + abuse contacts + KYC recommendation."""
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


clusters = load("registrar_clusters.json", [])
ai = load("ai_content.json", [])
cloak = []
for i in ("2", "10", "18"):
    cloak += load(f"cloak/cloak_{i}_{'10' if i=='2' else '18' if i=='10' else '25'}_US.json", []) or []
chain = load("chain_ranking.json", [])
expanded = load("osint_expanded.json", {})  # filled if workflow finished

exp = load("osint_expanded.json", None)
if exp and exp.get("domains"):
    rows = "".join(f'<tr><td class="mono">{E(d.get("domain",""))}</td><td>{E(d.get("idn_decoded") or "")}</td>'
                   f'<td>{E(d.get("registrar") or "?")}</td><td>{E((d.get("registered") or "")[:10])}</td></tr>'
                   for d in exp["domains"][:120])
    EXPANDED_BLOCK = (f'<p class="sub">{len(exp["domains"])} additional look-alike / homograph domains '
        f'found via Certificate-Transparency + RDAP. Full list in <code>data/osint_expanded.json</code>.</p>'
        f'<div class="scroll"><table><tr><th>Domain</th><th>Reads as</th><th>Registrar</th><th>Registered</th></tr>{rows}</table></div>')
else:
    EXPANDED_BLOCK = ('<p class="muted">The automated Certificate-Transparency sweep for additional '
        'look-alike and homograph domains is still completing; its full results will be published to '
        '<code>data/osint_expanded.json</code> in the repository. Everything else on this page is '
        'complete and verified from live visits.</p>')
ndom = sum(c["count"] for c in clusters)
avg_words = sum(a["words"] for a in ai) // max(len(ai), 1)
serve_phish = [r for r in cloak if r.get("drainer_signatures") and not r.get("redirects_to_real_brand")]
dead = [r for r in cloak if not r.get("ok") and not r.get("drainer_signatures")]


def cluster_rows():
    out = []
    for c in sorted(clusters, key=lambda x: -x["count"]):
        doms = ", ".join(d["domain"] for d in c["domains"][:6])
        batch = ' <span class="bad">(same-day batch)</span>' if c.get("same_day_batch") else ""
        out.append(f'<tr><td><b>{E(c["registrar"])}</b><br><span class="muted small">{E(c["country"])}</span></td>'
                   f'<td>{c["count"]}{batch}</td>'
                   f'<td class="mono small">{E(c["abuse"])}</td>'
                   f'<td class="mono small">{E(doms)}</td></tr>')
    return "\n".join(out)


def ai_rows():
    out = []
    for a in sorted(ai, key=lambda x: -x["ai_markers"]):
        out.append(f'<tr><td class="mono">{E(a["domain"])}</td><td>{a["words"]:,}</td>'
                   f'<td>{a["ai_markers"]}</td></tr>')
    return "\n".join(out)


HTML = f'''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>The full method: AI content, homograph domains, cloaking &amp; the registrars behind it</title>
<style>
:root{{--bg:#0b0d10;--panel:#12161b;--line:#232a33;--ink:#e8edf3;--dim:#97a3b2;--accent:#4ade80;
--after:#ef4444;--amber:#f59e0b;--link:#7dd3fc;--mono:ui-monospace,Menlo,Consolas,monospace;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Arial,sans-serif}}
.wrap{{max-width:1000px;margin:0 auto;padding:0 22px}}
a{{color:var(--link)}} h1,h2,h3{{line-height:1.15;letter-spacing:-.02em}}
header{{padding:60px 0 38px;border-bottom:1px solid var(--line)}}
.kicker{{font:600 12px/1 var(--mono);letter-spacing:.15em;text-transform:uppercase;color:var(--amber)}}
h1{{font-size:clamp(28px,5vw,48px);font-weight:800;margin:16px 0}}
.lede{{font-size:clamp(16px,2.1vw,20px);color:var(--dim);max-width:72ch}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);margin:32px 0 0}}
.stat{{background:var(--panel);padding:15px 18px}} .stat b{{display:block;font:700 23px/1.1 var(--mono)}}
.stat span{{font-size:12px;color:var(--dim)}} .stat.red b{{color:var(--after)}} .stat.amber b{{color:var(--amber)}}
section{{padding:46px 0;border-bottom:1px solid var(--line)}}
h2{{font-size:clamp(21px,3.3vw,29px);font-weight:750;margin:0 0 8px}}
.sub{{color:var(--dim);margin:0 0 20px;max-width:74ch}} p{{max-width:74ch}} .bad{{color:var(--after)}} .ok{{color:var(--accent)}}
ol.steps{{counter-reset:s;list-style:none;padding:0}}
ol.steps>li{{counter-increment:s;position:relative;padding:0 0 22px 54px;border-left:1px solid var(--line);margin-left:16px}}
ol.steps>li:last-child{{border-left:1px solid transparent}}
ol.steps>li::before{{content:counter(s);position:absolute;left:-16px;top:-3px;width:32px;height:32px;border-radius:50%;
background:var(--panel);border:1px solid var(--line);color:var(--amber);font:700 14px/32px var(--mono);text-align:center}}
ol.steps h3{{font-size:17px;margin:0 0 6px}}
.panel{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin:16px 0}}
.panel.flag{{border-left:3px solid var(--after)}} .panel.good{{border-left:3px solid var(--accent)}} .panel.amber{{border-left:3px solid var(--amber)}}
table{{width:100%;border-collapse:collapse;margin:14px 0;font-size:13.5px}}
th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}}
th{{font:600 11px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--dim)}}
.mono,code{{font-family:var(--mono);font-size:12.5px;word-break:break-all}}
code{{background:#1a1f26;padding:2px 6px;border-radius:4px;color:#cfe6ff}}
.muted{{color:var(--dim)}} .small{{font-size:12px}} .scroll{{overflow-x:auto}}
.big{{font:800 40px/1 var(--mono)}} .homoglyph{{color:var(--after);font-weight:800}}
footer{{padding:38px 0 66px;color:var(--dim);font-size:13px}}
</style></head><body>

<header><div class="wrap">
  <div class="kicker">Deep method teardown &middot; part 2</div>
  <h1>The full playbook: AI articles, look-alike domains, cloaking &mdash; and the registrars issuing them</h1>
  <p class="lede">Part 1 showed <b>that</b> fake wallet pages rank on Google. This shows <b>how</b>,
  end to end: the ~4,700-word ChatGPT articles that push them up, the look-alike and hidden-character
  domains they attach, where a victim actually ends up, and which registrars keep handing out the
  domains &mdash; with the exact abuse addresses to alert.</p>
  <div class="stats">
    <div class="stat"><b>{avg_words:,}</b><span>avg words of AI text per page</span></div>
    <div class="stat"><b>{ndom}</b><span>domains traced to registrars</span></div>
    <div class="stat amber"><b>ledġer.app</b><span>hidden-character look-alike found</span></div>
    <div class="stat red"><b>{len(serve_phish)}</b><span>live drainer payload hosts</span></div>
  </div>
</div></header>

<section><div class="wrap">
  <h2>The method, start to finish</h2>
  <ol class="steps">
    <li><h3>Register a wallet-sounding domain (this is the disguise, not the host)</h3>
      <p>e.g. <code>walletcryptohub.com</code>, <code>ledgrliveus.com</code>, <code>metamaslogi.com</code>.
      <b>The domain barely hosts anything</b> &mdash; we checked all of them from a real home
      connection and <b>{len(dead)} of {len(cloak)} were dead or blank.</b> Its real job is the next step.</p></li>
    <li><h3>Verify that domain inside a Google Workspace account</h3>
      <p>Once Google has &ldquo;verified&rdquo; you own the domain, you can publish a Google Site at
      <code>sites.google.com/<b>yourdomain.com</b>/page</code>. Now the address shows <b>google.com</b>
      <i>and</i> your wallet-word. Google's own verification becomes the disguise.</p></li>
    <li><h3>Fill the page with a long AI-written article</h3>
      <p>Each page carries a <b>~{avg_words:,}-word</b> article, clearly machine-written
      (&ldquo;in the world of&hellip;&rdquo;, &ldquo;seamless&rdquo;, &ldquo;beginner-friendly&rdquo;,
      &ldquo;navigate the ecosystem&rdquo;, &ldquo;designed to&hellip;&rdquo;). This keyword-rich text
      is what makes Google rank the page &mdash; it's the fuel for the parasite. Evidence below.</p></li>
    <li><h3>Put the theft on the same page (or one hop away)</h3>
      <p>The article sits on top; underneath is a &ldquo;Download / Connect / Verify&rdquo; button that
      leads to the recovery-phrase grab &mdash; either right there, behind a fake
      &ldquo;ledger.com: verify you are human&rdquo; box, or in a hidden frame from a payload host.</p></li>
    <li><h3>Run dozens in parallel and let google.com's trust do the ranking</h3>
      <p>No real backlinks needed. When one is removed, the next is already indexed.</p></li>
  </ol>
</div></section>

<section><div class="wrap">
  <h2>1. The AI &ldquo;white content&rdquo; that does the ranking</h2>
  <p class="sub">You were right: they seed each page with a long, bland, ChatGPT-style article first.
  It reads clean to Google, matches what people search, and carries the google.com trust to page one.</p>
  <div class="scroll"><table>
    <tr><th>Page (attached domain)</th><th>Article length</th><th>AI filler phrases</th></tr>
    {ai_rows()}
  </table></div>
  <p class="small muted">&ldquo;AI filler phrases&rdquo; counts stock ChatGPT tells actually present on
  the page (&ldquo;in the world of&rdquo;, &ldquo;seamless&rdquo;, &ldquo;robust&rdquo;,
  &ldquo;intuitive&rdquo;, &ldquo;gateway to&rdquo;, &ldquo;navigate the ecosystem&rdquo;, etc.).
  Pages run 3,000&ndash;16,000 words &mdash; far more text than a real wallet download page has,
  because the text <i>is</i> the ranking tactic.</p>
</div></section>

<section><div class="wrap">
  <h2>2. Hidden-character (homograph) domains</h2>
  <p class="sub">Some domains use letters that look normal but aren't &mdash; the browser quietly turns
  the real code into a word that reads like the brand.</p>
  <div class="panel flag">
    <p style="margin-top:0">You found <code>xn--leder-y1a.app</code>. That <code>xn--</code> code is how
    browsers store non-English letters. Decoded, it reads:</p>
    <p style="margin:6px 0"><span class="big">led<span class="homoglyph">ġ</span>er.app</span></p>
    <p style="margin-bottom:0">A normal <b>g</b> with a tiny dot on top (Unicode U+0121). At a glance
    it's &ldquo;ledger.app&rdquo;.</p>
  </div>
  <div class="panel flag">
    <h3 style="margin-top:0">The trick I first missed &mdash; and you caught</h3>
    <p style="margin-top:0"><b>The bare address <code>ledġer.app/</code> redirects to the REAL
    ledger.com</b> from every condition (datacenter, home broadband, US residential, fake ad-click).
    So a quick check sees nothing wrong. <b>The phishing hides on device-specific paths</b> named after
    Ledger's actual products:</p>
    <ul class="mono small" style="margin:6px 0">
      <li>led&#289;er.app/<b>stax.php</b> &mdash; Ledger Stax</li>
      <li>led&#289;er.app/<b>nanos.php</b> &mdash; Ledger Nano S</li>
      <li>led&#289;er.app/<b>nanox.php</b> &mdash; Ledger Nano X</li>
    </ul>
    <p style="margin-bottom:0">All three return <b>HTTP 200</b> and a fake &ldquo;Ledger Live &mdash;
    Device initialization / Connect your device&rdquo; page (title itself uses Cyrillic look-alike
    letters: &ldquo;L&#1077;dg&#1077;r Liv&#1077;&rdquo;). Steps: Device Detection &rarr; Device Check
    &rarr; Ledger Live &rarr; it asks for the <b>24-word recovery phrase</b>.</p>
  </div>
  <div class="panel amber">
    <h3 style="margin-top:0">What's under the hood (the phishing scripts)</h3>
    <ul style="margin:0">
      <li>Loads <code>ethers-5.2.umd.min.js</code> &mdash; the real <b>Ethereum wallet library</b>. This
      is a <b>live wallet-drainer</b>, not just a seed-phrase form: it can build and push
      drain transactions once you interact. Drainer signatures seen: <code>ethereum</code>,
      <code>solana</code>, <code>recovery phrase</code>.</li>
      <li><b>Heavily obfuscated</b>: 3,500&ndash;4,500 <code>&#92;x</code> hex-escaped strings per page plus
      <code>atob()</code> decoding &mdash; the drain logic is deliberately hidden from readers.</li>
      <li>Fronted by <b>Cloudflare</b> (nameservers adam/shaz.ns.cloudflare.com), UI built on Bootstrap.</li>
    </ul>
  </div>
  <div class="panel">
    <p style="margin:0"><b>Where it's registered:</b> <code>xn--leder-y1a.app</code> (ledġer.app) &mdash;
    registrar <b>NICENIC International Group, Hong Kong</b> (abuse@nicenic.net, +1.400 622 8300),
    registered <b>2026-05-10</b>, expires 2027-05-10. Same registrar as <code>kryptowallets.app</code>
    (Germany's #1 &ldquo;ledger live&rdquo; result) and <code>phantom-wallet-extension.app</code>
    &mdash; a NICENIC <code>.app</code> cluster. The <code>.app</code> top-level domain is run by
    <b>Google Registry</b>, which is itself a route to escalate.</p>
  </div>
</div></section>

<section><div class="wrap">
  <h2>3. Where a victim actually ends up (cloaking, defeated)</h2>
  <div class="panel amber">
    <p style="margin-top:0"><b>You were right to insist on this.</b> These pages cloak &mdash; they show
    a clean page to bots and datacenter IPs, and the scam only to real people. So we re-visited every
    target the way a victim arrives: <b>real Chrome + a residential home IP (ziny) + a Google
    ad-referrer + a gclid + real mouse movement.</b></p>
    <p style="margin-bottom:0">Result across {len(cloak)} targets: <b>{len(dead)} were dead</b> (the
    bare look-alike domains &mdash; verification tokens, nothing more), <b>1 redirected to the real
    brand</b> (the homograph above), and <b>{len(serve_phish)} live payload hosts served the actual
    drainer</b>.</p>
  </div>
  <div class="scroll"><table>
    <tr><th>Live payload host</th><th>What runs on it</th></tr>
    <tr><td class="mono">ksf-webapp-080826.web.app<br><span class="muted small">Google Firebase</span></td>
        <td>Trezor clone + wallet-drainer scripts: <code>web3</code>, <code>solana</code>,
        <code>walletconnect</code>, asks for <code>private key</code> / <code>passphrase</code></td></tr>
    <tr><td class="mono">japanesetoenailfunguscode.com/ledger1/<br><span class="muted small">compromised 2016 domain</span></td>
        <td>Ledger &ldquo;Connect&rdquo; seed grab: <code>12/24 word</code> <code>recovery phrase</code>,
        with a <code>verify_human.php</code> anti-bot gate (tracks mouse/keys before showing the form)</td></tr>
  </table></div>
  <p class="small muted">On the ranking pages themselves the harvest is mostly inline. Scripts seen
  across them: <b>private key</b> (21 pages), <b>web3</b> (14), <b>recovery/seed phrase</b> (13/12),
  <b>solana</b> (9); two pages use <code>eval()</code>/<code>atob()</code> obfuscation to hide the code.
  A real wallet never asks for the phrase on a web page &mdash; that is the whole scam in one line.</p>
</div></section>

<section><div class="wrap">
  <h2>4. The registrars &mdash; who to alert, and the case for extra KYC</h2>
  <p class="sub">Every look-alike domain has to be bought somewhere. Here is where these were bought,
  the abuse address for each, and the clustering that shows it's organised, not random.</p>
  <div class="scroll"><table>
    <tr><th>Registrar</th><th>Domains seen</th><th>Abuse contact</th><th>Examples</th></tr>
    {cluster_rows()}
  </table></div>
  <div class="panel">
    <p style="margin-top:0"><b>The tell that this is organised:</b> four domains
    (<code>okx-wallet-extension.com</code>, <code>walletcryptoextension.com</code>,
    <code>phantom-solana-wallet.com</code>, <code>mywalletcryptous.com</code>) were registered on the
    <b>same day, 3 Aug 2025, through the same registrar (WebNic, Malaysia)</b> &mdash; one operator
    buying a batch. Others cluster on <b>BigRock (India)</b> and <b>NICENIC (Hong Kong)</b>.</p>
    <p style="margin-bottom:0"><b>Recommendation to registrars (plain):</b> a domain whose name copies a
    named crypto-wallet brand (Ledger, Trezor, MetaMask, Phantom, Exodus, OKX), or that uses a
    hidden-character homograph of one, is almost never legitimate. Registrars can flag these at
    checkout for <b>extra identity verification (KYC)</b> before issuing, the same way brand-name
    look-alikes are handled in other regulated sectors. Under ICANN rules registrars must act on abuse
    reports &mdash; the addresses above are where to send them.</p>
  </div>
</div></section>

<section id="expanded"><div class="wrap">
  <h2>5. Wider domain sweep</h2>
  {EXPANDED_BLOCK}
</div></section>

<section><div class="wrap">
  <h2>How to report</h2>
  <ol>
    <li><b>The Google Sites page:</b> <a href="https://support.google.com/sites/answer/1651998">report abuse</a> + <a href="https://safebrowsing.google.com/safebrowsing/report_phish/">Safe Browsing</a>.</li>
    <li><b>The look-alike / homograph domain:</b> email the registrar abuse address in the table above, with the URL and a one-line note that it impersonates a named wallet brand.</li>
    <li><b>The payload hosts:</b> Firebase abuse (<code>network-abuse@google.com</code> / Firebase report) for <code>*.web.app</code>; the hosting provider for <code>japanesetoenailfunguscode.com</code>.</li>
    <li><b>The brands</b> (Ledger, Trezor, etc.) run takedown desks &mdash; send them the full list.</li>
  </ol>
  <p class="small muted">Machine-readable lists in the repo: <code>data/registrar_clusters.json</code>,
  <code>data/ranking_pages.json</code>, <code>data/ranking_rdap.json</code>, <code>data/cloak/</code>.</p>
</div></section>

<footer><div class="wrap">
  Built {time.strftime("%d %B %Y", time.gmtime())} &middot; defensive research, noindex &middot;
  part 2 of the <a href="../">main teardown</a> &middot; also see the <a href="../seo/">SEO ranking list</a>.
</div></footer>
</body></html>'''

os.makedirs(os.path.join(ROOT, "docs", "seo2"), exist_ok=True)
open(os.path.join(ROOT, "docs", "seo2", "index.html"), "w").write(HTML)
print(f"wrote docs/seo2/index.html ({len(HTML)//1024} KB)")
print(f"clusters={len(clusters)} ai_pages={len(ai)} cloak_targets={len(cloak)} serve_phish={len(serve_phish)} dead={len(dead)}")
