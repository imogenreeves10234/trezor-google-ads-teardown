#!/usr/bin/env python3
"""Pull raw creative bodies for STAR HONOUR advertiser IDs and extract image/preview URLs."""
import json
import re
import sys

sys.path.insert(0, '/root/workspace/trezor-ads-teardown/scripts')
import vf_atc  # noqa: F401
import atc  # noqa: E402

OUT = '/tmp/claude-0/-root-workspace/b565dfe0-0382-4576-91e8-11ca027cf6bf/scratchpad'
vf_atc.MIN_GAP = 1.6

AID = sys.argv[1]
REGIONS = sys.argv[2].split(',')

allrows = []
for reg in REGIONS:
    cursor = None
    for _ in range(4):
        r = atc.search_by_advertiser(AID, reg, cursor=cursor)
        rows = atc.parse_creatives(r)
        for x in rows:
            x['region'] = reg
        allrows.extend(rows)
        cursor = r.get("2")
        if not cursor or not r.get("1"):
            break
    print(f"{reg}: {len(allrows)} cumulative", flush=True)

json.dump(allrows, open(f'{OUT}/sh_bodies_{AID}.json', 'w'), ensure_ascii=False, indent=1)

simgad, previews = set(), []
for x in allrows:
    for m in re.finditer(r'https://tpc\.googlesyndication\.com/archive/simgad/\d+', x['body']):
        simgad.add((m.group(0), x['creative_id'], x['region']))
    for m in re.finditer(r'creativeId=(\d+)&[^"]*?adGroupId=(\d+)', x['body']):
        previews.append((x['creative_id'], m.group(1), m.group(2), x['region']))
    for m in re.finditer(r'obfuscatedCustomerId=(\d+)', x['body']):
        previews.append(('CUSTID', m.group(1), x['creative_id'], x['region']))

print(f"\nsimgad images: {len(simgad)}")
for s in sorted(simgad)[:60]:
    print(' ', s)
print(f"\ncustomer ids: {sorted({p[1] for p in previews if p[0]=='CUSTID'})}")
