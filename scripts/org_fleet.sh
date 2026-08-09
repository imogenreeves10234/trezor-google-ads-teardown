#!/bin/bash
cd /root/workspace/trezor-ads-teardown
N=$(python3 -c "import json;print(len(json.load(open('data/org_jobs.json'))))")
for i in $(seq 0 $((N-1))); do
  while [ "$(jobs -rp | wc -l)" -ge 4 ]; do sleep 4; done
  ( python3 -c "import json,subprocess;x=json.load(open('data/org_jobs.json'))[$i];subprocess.run(['xvfb-run','-a','--server-args=-screen 0 2560x1440x24','python3','-u','scripts/organic_probe.py',x['brand'],x['cc'],x['query'],x['tld'],x['hl'],'8'])" >> /tmp/org_$i.log 2>&1 ) &
  sleep 4
done
wait; echo DONE
