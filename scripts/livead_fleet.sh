#!/bin/bash
cd /root/workspace/trezor-ads-teardown
N=$(python3 -c "import json;print(len(json.load(open('data/livead_jobs.json'))))")
MAXPAR=4
for i in $(seq 0 $((N-1))); do
  while [ "$(jobs -rp | wc -l)" -ge "$MAXPAR" ]; do sleep 4; done
  ( timeout 900 xvfb-run -a --server-args="-screen 0 1920x1080x24" \
      python3 -u scripts/livead_probe.py "$i" >> /tmp/livead.log 2>&1 ) &
  sleep 3
done
wait
echo "LIVEAD FLEET COMPLETE"
