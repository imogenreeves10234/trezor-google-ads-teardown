#!/bin/bash
# Run geo_matrix across countries, max 3 concurrent (14GB RAM, no swap).
cd /root/workspace/trezor-ads-teardown
MAXPAR=3
for CC in "$@"; do
  while [ "$(jobs -rp | wc -l)" -ge "$MAXPAR" ]; do sleep 5; done
  ( timeout 1500 xvfb-run -a --server-args="-screen 0 1920x1080x24" \
      python3 -u scripts/geo_matrix.py "$CC" ./geoshots > "/tmp/geo_$CC.log" 2>&1
    echo "[done] $CC $(grep -c SERVED /tmp/geo_$CC.log 2>/dev/null) served" ) &
  sleep 4
done
wait
echo "ALL GEOS COMPLETE"
