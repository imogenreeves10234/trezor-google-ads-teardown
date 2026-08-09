#!/usr/bin/env python3
"""Merge Common Crawl candidate sets + the existing 185-URL scan, drop known false
positives, and emit a deduplicated master list plus the URL file for liveness checking."""
import json, glob, sys, collections

# Manually reviewed false positives — ordinary sites that tripped a brand word
FP_HOSTS = {
    "ab-ed.org",            # "key-worker-system" -> onekey
    "aeaag.pt",             # Guarda, Portugal (school)
    "crawfordschools.org",  # "color-guard" -> guarda
    "deocs.com",            # daedalus (unrelated)
    "gtrainerdemo.attechedu.com",  # "ingrave" -> ngrave
    "mortgagequote.ca",     # MQCC blockchain-standards site, not a wallet clone
    "site",                 # legacy /site/ classic-Sites namespace, handled per-URL
}
FP_URL_SUBSTR = [
    "/view/verticalfreighter", "/view/co-op-blockchain", "/view/london-crypto-day",
    "/view/crypto-casino-bonus", "/site/joaorib94", "/site/orionbeardedcollies",
    "/site/walkinonmusicnotes", "/site/ismageorgianbayhuronialodge15",
    "/view/fuzedcraftsstudio", "/view/mentoroftrading", "/view/thihaelec",
    "privatelender.org",
]


def seg1(u):
    return u.split("sites.google.com/", 1)[1].split("/")[0] if "sites.google.com/" in u else ""


def keep(u):
    s = seg1(u)
    if s in FP_HOSTS and s != "site":
        return False
    for f in FP_URL_SUBSTR:
        if f in u:
            return False
    return True


def main():
    rows = {}
    for f in sys.argv[1:]:
        src = f.split("/")[-1].replace("_cands.json", "")
        for x in json.load(open(f)):
            u = x["url"].replace("http://", "https://").rstrip("/")
            if not keep(u):
                continue
            e = rows.setdefault(u, {"url": u, "brands": set(), "src": set(), "ts": x.get("ts")})
            e["brands"].update(x["brands"])
            e["src"].add(src)
            if x.get("ts") and (not e["ts"] or x["ts"] > e["ts"]):
                e["ts"] = x["ts"]
    out = []
    for u, e in sorted(rows.items()):
        out.append({"url": u, "brands": sorted(e["brands"]), "src": sorted(e["src"]),
                    "cc_last_seen": e["ts"], "seg1": seg1(u)})
    json.dump(out, open("/root/workspace/trezor-ads-teardown/data/sib/cc_master.json", "w"), indent=1)
    doms = sorted({r["seg1"] for r in out if "." in r["seg1"]})
    print("urls", len(out), "custom-domain hosts", len(doms))
    open("/root/workspace/trezor-ads-teardown/data/sib/cc_urls.txt", "w").write(
        "\n".join(r["url"] for r in out) + "\n")
    json.dump(doms, open("/root/workspace/trezor-ads-teardown/data/sib/cc_domains.json", "w"), indent=1)


if __name__ == "__main__":
    main()
