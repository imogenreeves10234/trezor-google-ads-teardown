#!/usr/bin/env python3
"""ATC queries through a fresh Gonzo residential exit.

The datacenter IP gets HTTP 429 after sustained use; a residential exit resets
the bucket. Uses curl because urllib is the thing Cloudflare/Google 429s hardest.
"""
import json, subprocess, sys, time, urllib.parse, urllib.request

KEY = open('/root/.config/gonzo/key').read().strip()
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
GEO = {"US":2840,"GB":2826,"DE":2276,"FR":2250,"NL":2528,"CA":2124,"AU":2036,
       "IN":2356,"BR":2076,"JP":2392,"ES":2724,"IT":2380,"PL":2616,"CZ":2203,
       "TR":2792,"MX":2484,"SG":2702,"AE":2784,"KR":2410,"IE":2372}

def exit_proxy(cc="US"):
    req = urllib.request.Request(
        "https://api.gonzoproxy.app/functions/v1/proxy-api/generate",
        data=json.dumps({"country":cc,"ttl":72,"ttl_unit":"h",
                         "format":"ip:port:user:pass","count":1}).encode(),
        headers={"x-api-key":KEY,"Content-Type":"application/json"})
    p = json.load(urllib.request.urlopen(req,timeout=45))["proxies"][0]
    h,pt,u,pw = p.split(":")
    return f"http://{u}:{pw}@{h}:{pt}"

def call(endpoint, payload, proxy, tries=3):
    body = urllib.parse.urlencode({"f.req":json.dumps(payload,separators=(",",":"))})
    for i in range(tries):
        r = subprocess.run(["curl","-sS","--max-time","50","-x",proxy,
            "-H","Content-Type: application/x-www-form-urlencoded;charset=UTF-8",
            "-H",f"User-Agent: {UA}","-H","x-same-domain: 1",
            "-H","Origin: https://adstransparency.google.com",
            "-H","Referer: https://adstransparency.google.com/",
            "--data",body,
            f"https://adstransparency.google.com/anji/_/rpc/{endpoint}"],
            capture_output=True,text=True)
        t = (r.stdout or "").strip()
        if t.startswith("{") or t.startswith("["):
            return json.loads(t)
        time.sleep(3+i*4)
    return {"_error": (r.stdout or r.stderr or "")[:200]}

def creatives(term, region, proxy):
    return call("SearchService/SearchCreatives",
        {"2":40,"3":{"8":[GEO[region]],"12":{"1":term,"2":True}},
         "7":{"1":1,"2":0,"3":-1}}, proxy)

def rows(resp):
    out=[]
    for it in (resp or {}).get("1",[]) or []:
        def ep(k):
            v=it.get(k)
            return int(v["1"]) if isinstance(v,dict) and v.get("1") else None
        out.append({"advertiser_id":it.get("1"),"creative_id":it.get("2"),
                    "advertiser_name":it.get("12"),"domain":it.get("14"),
                    "first":ep("6"),"last":ep("7"),
                    "body":json.dumps(it.get("3",{}),ensure_ascii=False)[:2500]})
    return out

def d(ts):
    return time.strftime("%Y-%m-%d",time.gmtime(ts)) if ts else "?"

if __name__=="__main__":
    proxy = exit_proxy("US")
    print("exit:", subprocess.run(["curl","-sS","--max-time","30","-x",proxy,
          "https://ipinfo.io/json"],capture_output=True,text=True).stdout[:150])
    ctl = rows(creatives("trezor.io","US",proxy))
    print(f"CONTROL trezor.io US -> {len(ctl)} creatives", ctl[0]['advertiser_name'] if ctl else "FAIL")
    if not ctl:
        sys.exit("control failed, aborting")
    for term in sys.argv[1:]:
        for reg in ["US","GB","DE"]:
            r = rows(creatives(term,reg,proxy))
            if r:
                print(f"  HIT {term} [{reg}] {len(r)}:")
                for x in r[:6]:
                    print(f"      {x['advertiser_name']} ({x['advertiser_id']}) dom={x['domain']} {d(x['first'])}->{d(x['last'])}")
            else:
                print(f"  {term} [{reg}]: 0")
            time.sleep(1.2)
