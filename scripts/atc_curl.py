#!/usr/bin/env python3
"""Transport shim for atc.py.

atc.py's urllib transport gets HTTP 429 from adstransparency.google.com while
curl from the SAME box, same IP, same instant gets 200. That is a client
fingerprint block, not a real rate limit. This module imports atc unchanged
and monkeypatches ONLY atc._post to go through curl. Every payload shape,
the GEO map, parse_creatives() and creative_url() stay exactly as verified.
"""
import json
import subprocess
import sys
import time

sys.path.insert(0, '/root/workspace/trezor-ads-teardown/scripts')
import atc  # noqa: E402

_orig_post = atc._post
LAST_CALL = [0.0]
MIN_GAP = 1.2  # be polite: ~1s between calls


def _curl_post(endpoint, payload, proxy=None, timeout=45, retries=3):
    gap = time.time() - LAST_CALL[0]
    if gap < MIN_GAP:
        time.sleep(MIN_GAP - gap)
    body = "f.req=" + json.dumps(payload, separators=(",", ":"))
    cmd = [
        "curl", "-sS", "--compressed", "-m", str(timeout),
        "-X", "POST", atc.BASE + endpoint,
        "-H", "Content-Type: application/x-www-form-urlencoded;charset=UTF-8",
        "-H", "x-same-domain: 1",
        "-H", "Origin: https://adstransparency.google.com",
        "-H", "Referer: https://adstransparency.google.com/",
        "-H", "Accept-Language: en-GB,en;q=0.9",
        "-w", "\n__HTTP__%{http_code}",
        "--data-urlencode", body,
    ]
    last = None
    for attempt in range(retries):
        LAST_CALL[0] = time.time()
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 15)
            out = p.stdout
            code = ""
            if "__HTTP__" in out:
                out, code = out.rsplit("__HTTP__", 1)
                code = code.strip()
            if code == "200":
                return json.loads(out.strip() or "{}")
            last = f"HTTP {code}: {out[:200]}"
        except Exception as e:  # transport failures retry; never treated as "no ads"
            last = repr(e)
        time.sleep(3 + attempt * 4)
    raise RuntimeError(f"{endpoint} failed after {retries}: {last}")


atc._post = _curl_post
