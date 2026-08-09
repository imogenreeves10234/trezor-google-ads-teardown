"""Verification transport: atc.py unchanged, _post routed through curl + Gonzo residential exit."""
import json, random, string, subprocess, sys, time
sys.path.insert(0, '/root/workspace/trezor-ads-teardown/scripts')
import atc

MIN_GAP = 1.5
LAST = [0.0]
CC = 'NL'

def rnd(n=8):
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))

def _px():
    return (f'http://GonzosdyOUxO_c_{CC}_s_{rnd()}_ttl_30m:ZuBnaGgs'
            f'@connect.gonzoproxy.app:10000')

def _post(endpoint, payload, proxy=None, timeout=60, retries=3):
    gap = time.time() - LAST[0]
    if gap < MIN_GAP:
        time.sleep(MIN_GAP - gap)
    body = "f.req=" + json.dumps(payload, separators=(",", ":"))
    last = None
    for attempt in range(retries):
        LAST[0] = time.time()
        cmd = ["curl","-sS","--compressed","-m",str(timeout),"--proxy",_px(),
               "-X","POST", atc.BASE + endpoint,
               "-H","Content-Type: application/x-www-form-urlencoded;charset=UTF-8",
               "-H","x-same-domain: 1",
               "-H","Origin: https://adstransparency.google.com",
               "-H","Referer: https://adstransparency.google.com/",
               "-H","Accept-Language: en-US,en;q=0.9",
               "-w","\n__HTTP__%{http_code}",
               "--data-urlencode", body]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+20)
            out, code = p.stdout, ""
            if "__HTTP__" in out:
                out, code = out.rsplit("__HTTP__", 1); code = code.strip()
            if code == "200":
                return json.loads(out.strip() or "{}")
            last = f"HTTP {code}: {out[:150]}"
        except Exception as e:
            last = repr(e)
        time.sleep(3 + attempt * 4)
    raise RuntimeError(f"{endpoint} failed after {retries}: {last}")

atc._post = _post
