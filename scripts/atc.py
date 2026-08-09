#!/usr/bin/env python3
"""Direct client for the Google Ads Transparency Center internal RPC.

Endpoints (verified 2026-08-09 by capturing the live SPA's own traffic):
  POST /anji/_/rpc/SearchService/SearchCreatives    body: f.req=<json>
  POST /anji/_/rpc/SearchService/SearchSuggestions
  POST /anji/_/rpc/LookupService/GetCreativeById

SearchCreatives request shape:
  {"2": <pagesize>, "3": {"8": [<geo criteria ids>], "12": {"1": "<domain or term>", "2": true}},
   "7": {"1":1, "2":0, "3":-1}}
Advertiser-scoped variant uses "3":{"12":{"1":"<AR-id>"}} via the advertiser param.
"""
import json
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://adstransparency.google.com/anji/_/rpc/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

# Google geo "criteria IDs" used by ATC region filter.
GEO = {
    "US": 2840, "GB": 2826, "DE": 2276, "FR": 2250, "NL": 2528, "CA": 2124,
    "AU": 2036, "IN": 2356, "BR": 2076, "JP": 2392, "ES": 2724, "IT": 2380,
    "PL": 2616, "CZ": 2203, "TR": 2792, "MX": 2484, "ZA": 2710, "SG": 2702,
    "AE": 2784, "CH": 2756, "AT": 2040, "SE": 2752, "NO": 2578, "DK": 2208,
    "FI": 2246, "BE": 2056, "PT": 2620, "IE": 2372, "NZ": 2554, "RU": 2643,
    "UA": 2804, "RO": 2642, "HU": 2348, "GR": 2300, "IL": 2376, "KR": 2410,
    "ID": 2360, "PH": 2608, "TH": 2764, "VN": 2704, "NG": 2566, "AR": 2032,
    "CL": 2152, "CO": 2170, "SK": 2703, "BG": 2100, "HR": 2191, "SI": 2705,
}


def _post(endpoint, payload, proxy=None, timeout=45, retries=3):
    data = urllib.parse.urlencode({"f.req": json.dumps(payload, separators=(",", ":"))}).encode()
    req = urllib.request.Request(
        BASE + endpoint, data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "User-Agent": UA,
            "x-same-domain": "1",
            "Origin": "https://adstransparency.google.com",
            "Referer": "https://adstransparency.google.com/",
            "Accept-Language": "en-US,en;q=0.9",
        })
    opener = urllib.request.build_opener()
    if proxy:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    last = None
    for attempt in range(retries):
        try:
            with opener.open(req, timeout=timeout) as r:
                return json.loads(r.read().decode() or "{}")
        except Exception as e:  # transport failures retry; never treated as "no ads"
            last = e
            time.sleep(2 + attempt * 3)
    raise RuntimeError(f"{endpoint} failed after {retries}: {last!r}")


def search_creatives(term, region="US", pagesize=40, proxy=None, cursor=None):
    """term = a domain (e.g. trezor.io) or an advertiser id (AR...)."""
    payload = {"2": pagesize,
               "3": {"8": [GEO[region]], "12": {"1": term, "2": True}},
               "7": {"1": 1, "2": 0, "3": -1}}
    if cursor:
        payload["4"] = cursor
    return _post("SearchService/SearchCreatives", payload, proxy=proxy)


def search_by_advertiser(advertiser_id, region="US", pagesize=40, proxy=None, cursor=None):
    payload = {"2": pagesize,
               "3": {"8": [GEO[region]], "13": {"1": [advertiser_id]}},
               "7": {"1": 1, "2": 0, "3": -1}}
    if cursor:
        payload["4"] = cursor
    return _post("SearchService/SearchCreatives", payload, proxy=proxy)


def suggestions(term, region="US", proxy=None):
    payload = {"1": term, "2": 10, "3": 10, "4": [GEO[region]], "5": {"1": 1}}
    return _post("SearchService/SearchSuggestions", payload, proxy=proxy)


FORMAT = {1: "image", 2: "html5/display", 3: "video", 4: "text"}


def parse_creatives(resp):
    """Flatten a SearchCreatives response into rows.

    Field map verified 2026-08-09 against the trezor.io positive control:
      1=advertiser id (AR..)  2=creative id (CR..)  3=creative body
      4=format  6={1:first-shown epoch}  7={1:last-shown epoch}
      12=advertiser display name  14=advertiser verified domain
    """
    out = []
    for item in (resp or {}).get("1", []) or []:
        def epoch(k):
            v = item.get(k)
            if isinstance(v, dict) and v.get("1"):
                try:
                    return int(v["1"])
                except (TypeError, ValueError):
                    return None
            return None

        body = json.dumps(item.get("3", {}), ensure_ascii=False)
        out.append({
            "advertiser_id": item.get("1"),
            "creative_id": item.get("2"),
            "advertiser_name": item.get("12"),
            "domain": item.get("14"),
            "format": FORMAT.get(item.get("4"), item.get("4")),
            "first_shown": epoch("6"),
            "last_shown": epoch("7"),
            "body": body[:4000],
        })
    return out


def creative_url(advertiser_id, creative_id, region="US"):
    return (f"https://adstransparency.google.com/advertiser/{advertiser_id}"
            f"/creative/{creative_id}?region={region}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "domain"
    term = sys.argv[2] if len(sys.argv) > 2 else "trezor.io"
    region = sys.argv[3] if len(sys.argv) > 3 else "US"
    if mode == "suggest":
        r = suggestions(term, region)
    elif mode == "advertiser":
        r = search_by_advertiser(term, region)
    else:
        r = search_creatives(term, region)
    print(json.dumps(r, ensure_ascii=False)[:6000])
    if mode != "suggest":
        rows = parse_creatives(r)
        print(f"\n-- {len(rows)} creatives --", file=sys.stderr)
