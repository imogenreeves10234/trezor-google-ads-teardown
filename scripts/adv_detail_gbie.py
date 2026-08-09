#!/usr/bin/env python3
"""Pull full creative lists for suspect advertisers in GB / IE."""
import datetime
import json
import os
import sys

sys.path.insert(0, '/root/workspace/trezor-ads-teardown/scripts')
import atc_curl  # noqa: F401
import atc  # noqa: E402

OUT = '/tmp/claude-0/-root-workspace/b565dfe0-0382-4576-91e8-11ca027cf6bf/scratchpad'
atc_curl.MIN_GAP = 2.0
_pf = f'{OUT}/proxy_GB.txt'
if os.path.exists(_pf):
    atc_curl.PROXY = open(_pf).read().strip()
    print("[proxy] residential exit", flush=True)

SUSPECTS = json.loads(sys.argv[1]) if len(sys.argv) > 1 else []
STATE = f'{OUT}/adv_detail.json'


def ts(e):
    return datetime.datetime.utcfromtimestamp(int(e)).strftime('%Y-%m-%d') if e else None


def pull(aid, region, max_pages=8):
    rows, cursor, err = [], None, None
    for _ in range(max_pages):
        try:
            r = (atc.search_by_advertiser(aid, region, cursor=cursor) if cursor
                 else atc.search_by_advertiser(aid, region))
        except Exception as e:
            err = str(e)[:150]
            break
        rows.extend(atc.parse_creatives(r))
        cursor = r.get("2")
        if not cursor or not r.get("1"):
            break
    return rows, err


def main():
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    for aid, region in SUSPECTS:
        k = f"{aid}|{region}"
        if k in state and state[k].get('error') is None:
            continue
        rows, err = pull(aid, region)
        firsts = [r['first_shown'] for r in rows if r['first_shown']]
        lasts = [r['last_shown'] for r in rows if r['last_shown']]
        doms = sorted({r['domain'] for r in rows if r['domain']})
        names = sorted({r['advertiser_name'] for r in rows if r['advertiser_name']})
        state[k] = {
            'advertiser_id': aid, 'region': region, 'count': len(rows), 'error': err,
            'names': names, 'domains': doms,
            'first_shown': ts(min(firsts)) if firsts else None,
            'last_shown': ts(max(lasts)) if lasts else None,
            'atc_url': f"https://adstransparency.google.com/advertiser/{aid}?region={region}",
            'sample_creatives': [
                {'creative_id': r['creative_id'], 'format': r['format'],
                 'first': ts(r['first_shown']), 'last': ts(r['last_shown']),
                 'body': r['body'][:600]} for r in rows[:6]],
        }
        print(f"{region} {aid} n={len(rows)} names={names} doms={doms} "
              f"{state[k]['first_shown']}->{state[k]['last_shown']} err={err}", flush=True)
        json.dump(state, open(STATE, 'w'), ensure_ascii=False, indent=1)
    print("ADV DETAIL DONE", flush=True)


if __name__ == '__main__':
    main()
