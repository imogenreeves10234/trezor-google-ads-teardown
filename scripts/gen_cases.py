import json
import os

ROOT = "/root/workspace/trezor-ads-teardown"


def load(p, d=None):
    try:
        return json.load(open(os.path.join(ROOT, "data", p)))
    except Exception:
        return d


cases = load("cases.json", [])
liveverdict = load("livead_verdict.json", {})

KIND_TAG = {"ACTIVE HARVESTER": ("active", "ACTIVE HARVESTER"),
            "BROKEN SHELL": ("broken", "BROKEN SHELL — payload dead"),
            "BRAND PAGE": ("brand", "BRAND IMPERSONATION")}


def _date(s):
    return (s or "")[:10] or "unknown"


def journey(c):
    b = c["brand"]
    path = c["url"]
    if c["kind"] == "ACTIVE HARVESTER" and not c["payload"]:
        return (f"A user searches for {b} and clicks a result whose visible URL is "
                f"<b>google.com</b>. It lands on this page, hosted on Google Sites, cloned to look "
                f"like {b}. The page itself asks for the wallet <b>recovery phrase</b>; the 24 words "
                f"are sent to the operator, who then empties the wallet.")
    if c["kind"] == "ACTIVE HARVESTER" and c["payload"]:
        return (f"A user searches for {b} and clicks a result showing <b>google.com</b>. The Google "
                f"Sites page loads <code>{c['payload_domain']}</code> inside an iframe — that second "
                f"page (still framed under the google.com address) is the {b} clone that asks for the "
                f"recovery phrase. This payload host is <b>live now</b>.")
    if c["kind"] == "BROKEN SHELL":
        return (f"Same structure as the live cases: a Google Sites page framing a payload from "
                f"<code>{c['payload_domain']}</code>. That payload host is currently <b>dead "
                f"({c['payload_state']})</b>, so the page renders blank right now — but it is still a "
                f"live {b} impersonation on a google.com URL, and the operator can repoint the frame "
                f"at a new payload at any time without touching the Google Sites page.")
    return (f"A {b}-branded page on Google Sites. At probe time no active recovery-phrase harvesting "
            f"was captured; it is a brand-impersonation shell on a google.com URL.")


def ad_line(c):
    v = (liveverdict.get("per_brand") or {}).get(c["brand"], {})
    live = v.get("live_countries") or []
    parts = []
    if live:
        parts.append(f'<span class="bad"><b>Live ad confirmed today</b> in {", ".join(live)}</span>')
    elif v.get("checked"):
        parts.append(f'<span class="muted">No live ad observed in {v.get("checked")} SERP checks '
                     f'across {v.get("geos_checked", "?")} countries (see §17)</span>')
    if c["advertised"]:
        cids = sorted({x for a in c["advertised"] for x in (a.get("campaign") or [])})
        last = max((a.get("last_seen") or "") for a in c["advertised"])
        parts.append(f'<span class="amber">Was advertised — Google Ads campaign '
                     f'{", ".join(cids) or "(id not captured)"}, last seen {last}</span>')
    if not parts:
        parts.append('<span class="muted">No ad-click capture on record for this exact URL</span>')
    return "<br>".join(parts)


def E(s):
    import html
    return html.escape(str(s)) if s is not None else ""


def render():
    out = []
    n = 0
    for c in cases:
        n += 1
        cls, lab = KIND_TAG.get(c["kind"], ("brand", c["kind"]))
        cd = c["custom_domain"]
        dom_row = (f'<tr><td>Landing domain (what the URL shows)</td><td class="mono">google.com '
                   f'&mdash; via sites.google.com</td></tr>')
        cust_row = ""
        if cd:
            cust_row = (f'<tr><td>Workspace domain in the URL</td><td class="mono">{E(cd)} '
                        f'<span class="muted small">registered {E(_date(c["custom_domain_reg"]))}, '
                        f'{E(c["custom_domain_registrar"] or "")}</span></td></tr>')
        pay_row = ""
        if c["payload"]:
            pr = (f' &middot; registered {E(_date(c["payload_reg"]))}, {E(c["payload_registrar"])}'
                  if c["payload_reg"] else "")
            pay_row = (f'<tr><td>Payload / real phishing host behind it</td>'
                       f'<td class="mono">{E(c["payload_domain"])} '
                       f'<span class="{"bad" if c["payload_state"]=="LIVE" else "muted"}">'
                       f'[{E(c["payload_state"])}]</span>'
                       f'<span class="muted small">{pr}</span></td></tr>')
        shot = (f'<img src="{E(c["shot"])}" loading="lazy" alt="Landing page of {E(c["brand"])} '
                f'phishing case">' if c.get("shot") else "")
        out.append(f'''<div class="case" id="case{n}">
      <div class="case-head">
        <span class="tag tag-{cls}">{E(lab)}</span>
        <h3>{n}. {E(c["brand"])} &mdash; <span class="mono">{E(c["url"].replace("https://sites.google.com",""))}</span></h3>
      </div>
      <div class="case-body">
        <table class="kv">
          {dom_row}
          {cust_row}
          <tr><td>Full landing URL</td><td class="mono">{E(c["url"])}</td></tr>
          <tr><td>Page title</td><td>{E(c["title"] or "(none)")}</td></tr>
          {pay_row}
          <tr><td>Serves in</td><td>all {len(c["served_geos"])} countries probed
              ({E(", ".join(c["served_geos"]))})</td></tr>
          <tr><td>Advertising status</td><td>{ad_line(c)}</td></tr>
          <tr><td>Evidence in the ZIP</td><td class="mono small">evidence/{E(folder(c["url"]))}/
              &mdash; page source, headers, {c.get("shots_total", 0)} screenshots</td></tr>
        </table>
        <div class="case-journey"><b>User journey.</b> {journey(c)}</div>
        {("<figure class=case-shot>" + shot + "<figcaption>Landing page as served (one of "
          + str(c.get("shots_total", 0)) + " country captures)</figcaption></figure>") if shot else ""}
      </div>
    </div>''')
    return "\n".join(out)


def folder(u):
    import re
    return re.sub(r"[^a-zA-Z0-9]+", "_", re.sub(r"^https?://", "", u)).strip("_")[:80]


if __name__ == "__main__":
    frag = render()
    open(os.path.join(ROOT, "data", "cases_fragment.html"), "w").write(frag)
    print(f"wrote cases_fragment.html ({len(frag)} bytes, {len(cases)} cases)")
