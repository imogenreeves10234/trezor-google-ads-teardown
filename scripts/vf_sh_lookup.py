#!/usr/bin/env python3
"""Try LookupService endpoints for creative + advertiser detail on the STAR HONOUR IDs."""
import json
import sys

sys.path.insert(0, '/root/workspace/trezor-ads-teardown/scripts')
import vf_atc  # noqa: F401
import atc  # noqa: E402

vf_atc.MIN_GAP = 1.8

CASES = [
    ("SH_B ledger", "AR05598834575821242369", "CR11164072603193180161", "TR"),
    ("SH_A ledger", "AR16387915955222609921", "CR09020505346891841537", "TR"),
    ("Ledger SAS", "AR07032089618040225793", None, "US"),
    ("Adcore East", "AR15863532213959131137", None, "US"),
]

for label, aid, cid, reg in CASES:
    if cid:
        for shape in (
            {"1": aid, "2": cid, "5": {"1": 1, "2": atc.GEO[reg]}},
            {"1": aid, "2": cid, "3": {"1": [atc.GEO[reg]]}},
            {"1": aid, "2": cid},
        ):
            try:
                r = atc._post("LookupService/GetCreativeById", shape)
                print(f"\n=== {label} GetCreativeById shape={list(shape)} ===")
                print(json.dumps(r, ensure_ascii=False)[:2500])
                break
            except Exception as e:
                print(f"  {label} shape {list(shape)} -> {e}"[:160])
    for ep, shape in (
        ("LookupService/GetAdvertiserById", {"1": aid}),
        ("SearchService/SearchAdvertisers", {"1": aid, "2": 5, "4": [atc.GEO[reg]]}),
    ):
        try:
            r = atc._post(ep, shape)
            print(f"\n=== {label} {ep} ===")
            print(json.dumps(r, ensure_ascii=False)[:1500])
        except Exception as e:
            print(f"  {label} {ep} -> {e}"[:160])
