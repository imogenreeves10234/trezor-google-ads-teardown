#!/usr/bin/env python3
"""Re-verify the Google-hosted-domain negatives on a clean path.

The whole point: an empty result only means "no ads" if a positive control
run on the SAME path at the SAME time returns data. This pairs every
google-hosted zero with a fresh trezor.io control.
"""
import json
import os
import sys

sys.path.insert(0, '/root/workspace/trezor-ads-teardown/scripts')
import atc_curl  # noqa: F401
import atc  # noqa: E402

OUT = '/tmp/claude-0/-root-workspace/b565dfe0-0382-4576-91e8-11ca027cf6bf/scratchpad'
atc_curl.MIN_GAP = 2.0

GOOGLE_HOSTS = [
    "sites.google.com", "script.google.com", "docs.google.com", "drive.google.com",
    "groups.google.com", "lookerstudio.google.com", "datastudio.google.com",
    "firebaseapp.com", "web.app", "appspot.com", "blogspot.com",
    "googleusercontent.com", "storage.googleapis.com", "translate.goog", "google.com",
]

res = {}
for region in ("GB", "IE"):
    pf = f'{OUT}/proxy_{region}.txt'
    atc_curl.PROXY = open(pf).read().strip() if os.path.exists(pf) else None
    r = {}

    # control BEFORE
    try:
        c = atc.parse_creatives(atc.search_creatives('trezor.io', region))
        r['control_before'] = len(c)
    except Exception as e:
        r['control_before'] = f"ERR {str(e)[:80]}"
    print(f"[{region}] control_before = {r['control_before']}", flush=True)

    r['hosts'] = {}
    for d in GOOGLE_HOSTS:
        try:
            rows = atc.parse_creatives(atc.search_creatives(d, region))
            advs = sorted({(x['advertiser_name'], x['advertiser_id']) for x in rows})
            r['hosts'][d] = {'n': len(rows), 'advertisers': advs, 'error': None}
        except Exception as e:
            r['hosts'][d] = {'n': None, 'advertisers': [], 'error': str(e)[:100]}
        print(f"[{region}] {d:26s} n={r['hosts'][d]['n']} err={r['hosts'][d]['error']}", flush=True)

    # control AFTER — proves the path was still alive through the zeros
    try:
        c = atc.parse_creatives(atc.search_creatives('trezor.io', region))
        r['control_after'] = len(c)
    except Exception as e:
        r['control_after'] = f"ERR {str(e)[:80]}"
    print(f"[{region}] control_after = {r['control_after']}", flush=True)
    res[region] = r

json.dump(res, open(f'{OUT}/verify_negatives.json', 'w'), ensure_ascii=False, indent=1)
print("VERIFY DONE", flush=True)
