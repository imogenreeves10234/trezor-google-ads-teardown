#!/usr/bin/env python3
"""Adversarial verification of the TCMMO ADVERTISEMENT COMPANY LIMITED / ledger.com / KR claim.

Claim under test: AR08003813925671927809 ("TCMMO ADVERTISEMENT COMPANY LIMITED", domain
ledger.com, region KR) is an IMPERSONATOR / malicious.

Every negative is paired with the trezor.io positive control in the SAME pass.
No pagination cursor exists in this RPC (top-level 4/5 are counts), so pagesize=200.
"""
import json
import os
import sys
import time

sys.path.insert(0, '/root/workspace/trezor-ads-teardown/scripts')
import vf_atc  # noqa: F401  curl + residential transport
import atc  # noqa: E402

vf_atc.MIN_GAP = 1.4
OUT = '/tmp/claude-0/-root-workspace/b565dfe0-0382-4576-91e8-11ca027cf6bf/scratchpad'
STATE = f'{OUT}/tcmmo_vf.json'

TARGET = 'AR08003813925671927809'
LEDGER_SAS = 'AR07032089618040225793'
SH_A = 'AR16387915955222609921'
SH_B = 'AR05598834575821242369'

state = json.load(open(STATE)) if os.path.exists(STATE) else {}


def step(key, fn):
    if key in state:
        return state[key]
    try:
        state[key] = fn()
    except Exception as e:
        state[key] = {'ERROR': str(e)[:200]}
    json.dump(state, open(STATE, 'w'), indent=1, ensure_ascii=False)
    return state[key]


PAGE = 100  # >100 silently returns an EMPTY response, not an error. Verified 2026-08-09.


def _pages(fn, maxpages=5):
    rows, cursor, n = [], None, 0
    while n < maxpages:
        r = fn(cursor)
        rows += atc.parse_creatives(r)
        cursor = r.get('2')          # key '2' = next-page cursor (absent on last page)
        n += 1
        if not isinstance(cursor, str) or not cursor:
            break
    return rows


def by_domain(term, region):
    return _pages(lambda c: atc.search_creatives(term, region, pagesize=PAGE, cursor=c))


def by_adv(aid, region):
    return _pages(lambda c: atc.search_by_advertiser(aid, region, pagesize=PAGE, cursor=c))


def d(e):
    return time.strftime('%Y-%m-%d', time.gmtime(e)) if e else '?'


def show(label, rows):
    if isinstance(rows, dict):
        print(f'\n### {label}: ERROR {rows.get("ERROR")}')
        return
    agg = {}
    for r in rows:
        agg.setdefault((r['advertiser_id'], r['advertiser_name'], r['domain']), []).append(r)
    print(f'\n### {label}: {len(rows)} creatives, {len(agg)} advertiser(s)')
    for (aid, name, dom), rs in sorted(agg.items(), key=lambda x: -len(x[1])):
        fs = [x['first_shown'] for x in rs if x['first_shown']]
        ls = [x['last_shown'] for x in rs if x['last_shown']]
        mark = '   <== TARGET' if aid == TARGET else ''
        print(f'  {name!r} [{aid}] dom={dom} n={len(rs)} '
              f'{d(min(fs)) if fs else "?"} -> {d(max(ls)) if ls else "?"}{mark}')


# ------------------------------------------------------------ positive control
ctl = step('CONTROL_trezor_US', lambda: by_domain('trezor.io', 'US'))
show('POSITIVE CONTROL trezor.io US', ctl)
assert isinstance(ctl, list) and len(ctl) > 0, 'CONTROL FAILED — negatives worthless'
ctl2 = step('CONTROL_trezor_KR', lambda: by_domain('trezor.io', 'KR'))
show('CONTROL trezor.io KR', ctl2)

# ------------------------------- 1. who advertises ledger.com, per region
REGIONS = ['KR', 'US', 'GB', 'JP', 'SG', 'VN', 'TH', 'ID', 'PH', 'IN',
           'DE', 'FR', 'BR', 'TR', 'AU', 'MX', 'CA', 'NL']
for reg in REGIONS:
    show(f'ledger.com {reg}', step(f'dom_ledger_{reg}', lambda r=reg: by_domain('ledger.com', r)))

# ------------------------------- 2. the target advertiser everywhere
for reg in REGIONS:
    show(f'ADV TCMMO {reg}', step(f'adv_tcmmo_{reg}', lambda r=reg: by_adv(TARGET, r)))

# ------------------------------- 3. comparators
for reg in ['KR', 'US', 'FR', 'JP', 'BR']:
    show(f'ADV LedgerSAS {reg}', step(f'adv_sas_{reg}', lambda r=reg: by_adv(LEDGER_SAS, r)))

json.dump(state, open(STATE, 'w'), indent=1, ensure_ascii=False)

# ------------------------------- 4. every domain the target has ever verified
doms, crs = set(), set()
for k, v in state.items():
    if k.startswith('adv_tcmmo_') and isinstance(v, list):
        for r in v:
            doms.add(r['domain'])
            crs.add(r['creative_id'])
print('\n### TCMMO verified domains observed :', sorted(x for x in doms if x))
print('### TCMMO distinct creative ids      :', sorted(crs))
print('\nsaved ->', STATE)
