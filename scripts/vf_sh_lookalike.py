#!/usr/bin/env python3
"""Adversarial test: do the STAR HONOUR advertiser IDs ever appear on a known
Ledger/crypto LOOKALIKE (attacker) domain? Positive control runs in the same pass."""
import json
import os
import sys

sys.path.insert(0, '/root/workspace/trezor-ads-teardown/scripts')
import vf_atc  # noqa: F401
import atc  # noqa: E402

OUT = '/tmp/claude-0/-root-workspace/b565dfe0-0382-4576-91e8-11ca027cf6bf/scratchpad'
STATE = f'{OUT}/sh_lookalike.json'
vf_atc.MIN_GAP = 1.6

SH = {'AR16387915955222609921', 'AR05598834575821242369'}

DOMAINS = ['ledgercom-start.com', 'ledgerstart-web.com', 'ledgrstrt.com',
           'app-download-ledger.com', 'ledger-live.com', 'ledgerlive.com',
           'sites.google.com', 'trezor.io', 'trezorwallet.io', 'suite-trezor.com']
REGIONS = ['US', 'TR', 'DE']

state = json.load(open(STATE)) if os.path.exists(STATE) else {}

# positive control in the same pass
if 'CONTROL' not in state:
    r = atc.search_creatives('trezor.io', 'US')
    rows = atc.parse_creatives(r)
    state['CONTROL'] = {'n': len(rows),
                        'names': sorted({x['advertiser_name'] for x in rows})}
print('CONTROL trezor.io US:', state['CONTROL'])
assert state['CONTROL']['n'] > 0, 'POSITIVE CONTROL FAILED - all negatives worthless'

for dom in DOMAINS:
    for reg in REGIONS:
        k = f'{dom}|{reg}'
        if k in state:
            continue
        try:
            rows = atc.parse_creatives(atc.search_creatives(dom, reg))
            advs = sorted({(x['advertiser_id'], x['advertiser_name']) for x in rows})
            state[k] = {'n': len(rows), 'advertisers': advs,
                        'STAR_HONOUR_PRESENT': any(a[0] in SH for a in advs)}
        except Exception as e:
            state[k] = {'error': str(e)[:150]}
        print(k, json.dumps(state[k], ensure_ascii=False)[:400])
        json.dump(state, open(STATE, 'w'), ensure_ascii=False, indent=1)

hits = [k for k, v in state.items() if isinstance(v, dict) and v.get('STAR_HONOUR_PRESENT')]
print('\nSTAR HONOUR on a lookalike/attacker domain:', hits or 'NONE')
