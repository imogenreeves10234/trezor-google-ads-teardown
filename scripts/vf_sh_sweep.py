#!/usr/bin/env python3
"""Adversarial sweep for the STAR HONOUR / ledger.com claim.

Everything routes through the residential shim (datacenter IP is 429'd).
Positive control (trezor.io US -> 40 creatives, Trezor Company s.r.o.) runs in the SAME pass.
"""
import datetime
import json
import os
import sys

sys.path.insert(0, '/root/workspace/trezor-ads-teardown/scripts')
import vf_atc  # noqa: F401  (monkeypatches atc._post onto the residential curl transport)
import atc  # noqa: E402

OUT = '/tmp/claude-0/-root-workspace/b565dfe0-0382-4576-91e8-11ca027cf6bf/scratchpad'
STATE = f'{OUT}/sh_sweep.json'
vf_atc.MIN_GAP = 1.6

SH_A = 'AR16387915955222609921'
SH_B = 'AR05598834575821242369'


def ts(e):
    return datetime.datetime.utcfromtimestamp(int(e)).strftime('%Y-%m-%d') if e else None


def pages(fn, *a, max_pages=6, **kw):
    rows, cursor = [], None
    for _ in range(max_pages):
        r = fn(*a, cursor=cursor, **kw)
        rows.extend(atc.parse_creatives(r))
        cursor = r.get("2")
        if not cursor or not r.get("1"):
            break
    return rows


def agg(rows):
    d = {}
    for r in rows:
        k = f"{r['advertiser_id']}|{r['advertiser_name']}|{r['domain']}"
        e = d.setdefault(k, {'n': 0, 'first': None, 'last': None, 'formats': set(),
                             'creatives': []})
        e['n'] += 1
        e['formats'].add(str(r['format']))
        if r['first_shown'] and (e['first'] is None or r['first_shown'] < e['first']):
            e['first'] = r['first_shown']
        if r['last_shown'] and (e['last'] is None or r['last_shown'] > e['last']):
            e['last'] = r['last_shown']
        if len(e['creatives']) < 8:
            e['creatives'].append(r['creative_id'])
    for e in d.values():
        e['formats'] = sorted(e['formats'])
        e['first'] = ts(e['first'])
        e['last'] = ts(e['last'])
    return d


def run(state, key, fn, *a, **kw):
    if key in state and not state[key].get('error'):
        print(f"[skip] {key}")
        return
    try:
        rows = pages(fn, *a, **kw)
        state[key] = {'count': len(rows), 'agg': agg(rows), 'error': None}
    except Exception as e:
        state[key] = {'count': None, 'agg': {}, 'error': str(e)[:200]}
    print(f"{key}: n={state[key]['count']} err={state[key]['error']}")
    for k, v in state[key]['agg'].items():
        print(f"    {k}  n={v['n']} fmt={v['formats']} {v['first']}..{v['last']}")
    json.dump(state, open(STATE, 'w'), ensure_ascii=False, indent=1)


def main():
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    todo = sys.argv[1] if len(sys.argv) > 1 else 'all'

    # --- positive control, same pass ---
    run(state, 'CONTROL|trezor.io|US', atc.search_creatives, 'trezor.io', 'US')

    if todo in ('all', 'adv'):
        # every creative these two advertiser IDs ever ran, in many regions
        for aid, tag in ((SH_A, 'SH_A'), (SH_B, 'SH_B')):
            for reg in ('TR', 'US', 'GB', 'DE', 'FR', 'IN', 'SG', 'ID', 'VN', 'PH',
                        'TH', 'BR', 'JP', 'KR', 'AE', 'NL', 'PL', 'ES', 'IT', 'RU'):
                run(state, f'ADV|{tag}|{aid}|{reg}', atc.search_by_advertiser, aid, reg)

    if todo in ('all', 'dom'):
        for reg in ('TR', 'US', 'GB', 'FR', 'DE', 'IN', 'SG', 'VN', 'ID', 'NL',
                    'BR', 'JP', 'AE', 'PL', 'ES'):
            run(state, f'DOM|ledger.com|{reg}', atc.search_creatives, 'ledger.com', reg)

    if todo in ('all', 'ctrl2'):
        # Does a duplicate advertiser NAME across IDs also happen for uncontested brands?
        for dom in ('coinbase.com', 'binance.com', 'shop.ledger.com', 'trezor.io'):
            for reg in ('TR', 'US'):
                run(state, f'DOM|{dom}|{reg}', atc.search_creatives, dom, reg)

    print("DONE")


if __name__ == '__main__':
    main()
