#!/usr/bin/env python3
"""Triage the liveness results: drop residual false positives by title/host, classify the
survivors, and pull out every non-Google payload host the live pages reference."""
import json, re, sys, collections

# Residual FPs: ordinary Google Sites whose path tripped a wallet word
FP_HOST_SEG = {
    "chula.ac.th", "lorenaisd.net", "prof.cursog9.com", "umich.edu",
}
FP_PATH_SUBSTR = [
    "areasnaturalesyguardaparques", "freedomcolorguard", "pknkleverskerke", "rrg-kleverland-ev",
    "guardaraia", "jennyguardado", "naresi1968", "brava-gente-brasileira", "composguitar2",
    "drtbalusotolaryngology", "ciekudsak", "victoria-spiegl", "coastguardauxiliary",
    "associazionekeyhole", "jdtrammellmyceliumcaskets", "flyingravensart", "myblogzone",
    "talismania-casinofr", "handboek-voor-crypto", "crypto-monnaies", "capsulesurocarefloraguardau",
    "decentralised-news", "brandon-graves",
]
# Brand tokens that make a page a brand-impersonation candidate
BRANDS = ["trezor", "ledger", "metamask", "exodus", "phantom", "coinbase", "kraken", "binance",
          "uniswap", "okx", "bybit", "bitget", "kucoin", "tangem", "atomic", "rabby", "solflare",
          "pancakeswap", "1inch", "opensea", "raydium", "curve", "lido", "bitstamp", "bitmart",
          "coincheck", "crypto.com", "cryptocom", "trust", "rainbow", "solscan", "bitcoin core",
          "cash app", "cashapp", "coinbas"]


def is_fp(u):
    seg = u.split("sites.google.com/", 1)[1].split("/")[0]
    if seg in FP_HOST_SEG:
        return True
    return any(f in u for f in FP_PATH_SUBSTR)


def main():
    rows = json.load(open(sys.argv[1]))
    live = [r for r in rows if r["status"] == "LIVE" and not is_fp(r["url"])]
    payload = collections.Counter()
    for r in live:
        seg = r["url"].split("sites.google.com/", 1)[1].split("/")[0]
        r["seg1"] = seg
        r["custom_domain"] = seg if "." in seg else None
        t = (r.get("title") or "").lower()
        r["brand"] = sorted({b for b in BRANDS if b in t or b in r["url"].lower()})
        # sub-classify
        if re.search(r"slot|toto|judi|casino|rajabet|bet\d", t):
            r["kind"] = "HIJACKED_TO_GAMBLING_SPAM"
        elif re.search(r"support|customer service|refund|contact|helpline|number|taxes|pending|failed", t):
            r["kind"] = "SUPPORT_SCAM_SEO"
        else:
            r["kind"] = "BRAND_CLONE"
        for e in r.get("external", []):
            try:
                h = e.split("/")[2]
            except Exception:
                continue
            payload[h] += 1
    json.dump(live, open(sys.argv[2], "w"), indent=1)
    print("LIVE after FP strip:", len(live))
    print(collections.Counter(r["kind"] for r in live))
    cd = sorted({r["custom_domain"] for r in live if r["custom_domain"]})
    print("live custom-domain hosts:", len(cd))
    for d in cd:
        print("  ", d)
    print("\nNON-GOOGLE HOSTS REFERENCED BY LIVE PAGES:")
    for h, c in payload.most_common(60):
        print(f"  {c:4d}  {h}")


if __name__ == "__main__":
    main()
