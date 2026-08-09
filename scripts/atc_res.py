#!/usr/bin/env python3
"""Transport shim: route atc.py through a Gonzo residential exit via curl.

The box's datacenter IP is 429/`/sorry/`-blocked at adstransparency.google.com.
Everything else about atc.py (payload shapes, GEO map, parse_creatives) is unchanged.
"""
import json
import random
import string
import subprocess
import sys
import time

sys.path.insert(0, '/root/workspace/trezor-ads-teardown/scripts')
import atc  # noqa: E402

CC = 'US'          # residential exit country (independent of the ATC region filter)
MIN_GAP = 1.5
_LAST = [0.0]


def _rnd(n=8):
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))


def _px():
    return (f'http://GonzosdyOUxO_c_{CC}_s_{_rnd()}_ttl_30m:ZuBnaGgs'
            f'@connect.gonzoproxy.app:10000')


def _post(endpoint, payload, proxy=None, timeout=60, retries=4):
    gap = time.time() - _LAST[0]
    if gap < MIN_GAP:
        time.sleep(MIN_GAP - gap)
    body = "f.req=" + json.dumps(payload, separators=(",", ":"))
    last = None
    for attempt in range(retries):
        _LAST[0] = time.time()
        cmd = ["curl", "-sS", "--compressed", "-m", str(timeout), "--proxy", _px(),
               "-X", "POST", atc.BASE + endpoint,
               "-H", "Content-Type: application/x-www-form-urlencoded;charset=UTF-8",
               "-H", "x-same-domain: 1",
               "-H", "Origin: https://adstransparency.google.com",
               "-H", "Referer: https://adstransparency.google.com/",
               "-H", "Accept-Language: en-US,en;q=0.9",
               "-H", f"User-Agent: {atc.UA}",
               "-w", "\n__HTTP__%{http_code}", "--data-urlencode", body]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 25)
            out, code = p.stdout, ""
            if "__HTTP__" in out:
                out, code = out.rsplit("__HTTP__", 1)
                code = code.strip()
            if code == "200":
                return json.loads(out.strip() or "{}")
            last = f"HTTP {code}: {out[:150]}"
        except Exception as e:   # transport failure -> retry, never "no ads"
            last = repr(e)
        time.sleep(2 + attempt * 3)
    raise RuntimeError(f"{endpoint} failed after {retries}: {last}")


atc._post = _post
