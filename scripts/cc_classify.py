#!/usr/bin/env python3
"""Classify Common Crawl sites.google.com records as crypto-brand-impersonation candidates.

STRONG brands are unambiguous strings that essentially never appear in a legitimate
Google Sites path by accident.  AMBIGUOUS brands are ordinary English words that happen to
be wallet names (glow, core, casa, argent, rainbow, passport, frame, jupiter, jade, lace,
slope, curve, orca, ethos, blur, brave, compound, gemini, sparrow, leather ...) and are only
counted when a crypto/wallet context token also appears in the same path.
"""
import json, re, sys, collections

STRONG = {
    "trezor", "metamask", "coinbase", "binance", "uniswap", "okx", "bybit", "bitget", "kucoin",
    "safepal", "keepkey", "bitbox", "tangem", "myetherwallet", "solflare", "coinomi", "jaxx",
    "electrum", "tonkeeper", "xverse", "unisat", "imtoken", "tokenpocket", "bitkeep", "zerion",
    "enkrypt", "keplr", "cosmostation", "yoroi", "daedalus", "eternl", "tronlink", "klever",
    "talisman", "subwallet", "suiet", "freighter", "lobstr", "xumm", "xaman", "mycelium",
    "pancakeswap", "sushiswap", "1inch", "dydx", "opensea", "rarible", "looksrare",
    "walletconnect", "magiceden", "bitfinex", "bitstamp", "huobi", "mexc", "gateio", "bingx",
    "bitmart", "poloniex", "upbit", "bithumb", "coincheck", "bitflyer", "wazirx", "coindcx",
    "coinspot", "swyftx", "cryptocom", "cashapp", "bitpay", "guarda", "rabby", "ngrave",
    "cypherock", "gridplus", "coolwallet", "coldcard", "seedsigner", "ellipal", "onekey",
    "trustwallet", "atomicwallet", "phantomwallet", "plasmawallet", "pontem", "nunchuk",
    "ledgerlive", "trezorsuite", "exoduswallet", "krakenlogin", "cryptowallet",
}
AMBIGUOUS = {
    "ledger", "exodus", "phantom", "kraken", "gemini", "atomic", "sparrow", "leather", "petra",
    "martian", "hiro", "albedo", "rabet", "nami", "taho", "luno", "bitso", "aave", "lido",
    "ronin", "glow", "core", "casa", "rainbow", "passport", "frame", "argent", "compound",
    "jupiter", "jade", "lace", "slope", "curve", "orca", "ethos", "stargate", "blur", "brave",
    "specter", "edge", "gmx", "raydium", "rocketpool", "crypto", "blockchain",
}
# context that turns an ambiguous word into a crypto signal
CTX = {
    "wallet", "wallets", "walet", "walett", "wallett", "crypto", "cryptocurrency", "bitcoin",
    "btc", "ethereum", "eth", "solana", "web3", "defi", "nft", "token", "coin", "coins",
    "blockchain", "seed", "seedphrase", "recovery", "restore", "unlock", "login", "signin",
    "connect", "suite", "extension", "bridge", "staking", "airdrop", "dapp", "hardware",
    "keystore", "privatekey", "app", "start", "desktop", "download", "live",
}
LURE = {
    "seedphrase", "recoveryphrase", "privatekey", "keystore", "walletconnect", "walletrecovery",
    "walletrestore", "restorewallet", "recoverwallet", "validatewallet", "walletvalidation",
    "syncwallet", "walletsync", "unlockwallet", "walletunlock", "web3login", "dappconnect",
    "connectwallet", "walletlogin", "cryptologin", "seedrecovery",
}
SPLIT = re.compile(r"[^a-z0-9]+")


def classify(url):
    if "sites.google.com" not in url:
        return None
    tail = url.split("sites.google.com", 1)[1].lstrip("/")
    if not tail:
        return None
    seg1 = tail.split("/")[0]
    toks = set(t for t in SPLIT.split(tail.lower()) if t)
    flat = re.sub(r"[^a-z0-9]", "", tail.lower())

    strong = sorted(b for b in STRONG if b in toks or (len(b) >= 6 and b in flat))
    if strong:
        return ("BRAND", strong, seg1)

    amb = sorted(b for b in AMBIGUOUS if b in toks or (len(b) >= 7 and b in flat))
    if amb and (toks & CTX):
        return ("BRAND_CTX", amb, seg1)

    lure = sorted(l for l in LURE if l in flat)
    if lure:
        return ("LURE", lure, seg1)
    return None


def main():
    files, outp = sys.argv[1:-1], sys.argv[-1]
    seen, n = {}, 0
    for f in files:
        for line in open(f, errors="replace"):
            n += 1
            try:
                r = json.loads(line)
            except Exception:
                continue
            u = r.get("url", "")
            c = classify(u)
            if not c:
                continue
            key = u.split("?")[0].rstrip("/")
            e = seen.setdefault(key, {"url": key, "verdict": c[0], "brands": c[1],
                                      "seg1": c[2], "ts": [], "status": r.get("status")})
            e["ts"].append(r.get("timestamp"))
    for e in seen.values():
        e["ts"] = sorted(set(e["ts"]))[-1]
    rows = sorted(seen.values(), key=lambda x: x["url"])
    json.dump(rows, open(outp, "w"), indent=1)
    print("records", n, "candidates", len(rows))
    print("verdicts", collections.Counter(r["verdict"] for r in rows))
    bc = collections.Counter()
    for r in rows:
        for b in r["brands"]:
            bc[b] += 1
    print("brands", bc.most_common(40))
    doms = sorted({r["seg1"] for r in rows if "." in r["seg1"]})
    print("custom-domain hosts", len(doms))


if __name__ == "__main__":
    main()
