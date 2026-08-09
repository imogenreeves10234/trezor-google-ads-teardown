#!/bin/bash
cd /root/workspace/trezor-ads-teardown
N=$(python3 -c "import json;print(len(json.load(open('data/fp_jobs.json'))))")
MAXPAR=4
for i in $(seq 0 $((N-1))); do
  while [ "$(jobs -rp | wc -l)" -ge "$MAXPAR" ]; do sleep 4; done
  ( j=$(python3 -c "import json;x=json.load(open('data/fp_jobs.json'))[$i];print(x['brand'],x['cc'],repr(x['query']),x['tld'],x['hl'])")
    b=$(echo "$j"|cut -d' ' -f1); c=$(echo "$j"|cut -d' ' -f2)
    python3 -c "import json,sys;x=json.load(open('data/fp_jobs.json'))[$i];import subprocess;subprocess.run(['xvfb-run','-a','--server-args=-screen 0 2560x1440x24','python3','-u','scripts/fp_probe.py',x['brand'],x['cc'],x['query'],x['tld'],x['hl'],'8'])" >> /tmp/fp_$i.log 2>&1 ) &
  sleep 4
done
wait
echo "FP FLEET DONE"
