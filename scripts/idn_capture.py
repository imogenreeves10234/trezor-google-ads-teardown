import json,os,random,re,string,sys
sys.path.insert(0,os.path.dirname(__file__))
from serp_probe import slug
from patchright.sync_api import sync_playwright
ROOT="/root/workspace/trezor-ads-teardown"
Z=json.load(open("/root/.config/ziny/creds.json"))["residential"]
U="Dominic_Butler_2330"
DR=["eth_requestaccounts","web3","ethereum","walletconnect","personal_sign","eth_sendtransaction",
"solana","recovery phrase","seed phrase","mnemonic","private key","24 word","24-word","passphrase",
"verify_human","connect wallet","setapprovalforall","permit(","increaseallowance"]
def px():
    s="".join(random.choices(string.ascii_letters+string.digits,k=8))
    return f"http://{Z['endpoint']}:{Z['http_port']}",U,f"{Z['proxy_key']}_country-US_session-{s}"
targets=json.load(open(f"{ROOT}/data/idn_targets.json"))
out=[]
with sync_playwright() as p:
  for u in targets:
    for attempt in range(4):
      srv,usr,pw=px(); prof=f"/tmp/idn-{random.randint(1000,9999)}"; os.makedirs(prof,exist_ok=True)
      scripts=set(); xhr=set(); rec={"url":u,"attempt":attempt+1}
      try:
        ctx=p.chromium.launch_persistent_context(user_data_dir=prof,channel="chrome",headless=False,no_viewport=True,
          proxy={"server":srv,"username":usr,"password":pw},locale="en-US",
          args=["--no-sandbox","--disable-dev-shm-usage","--start-maximized"])
        def onreq(r):
          try:
            rt=r.resource_type
            if rt=="script": scripts.add(str(r.url).split("?")[0][:150])
            elif rt in ("xhr","fetch"): xhr.add(str(r.method)+" "+str(r.url).split("?")[0][:150])
          except: pass
        pg=ctx.pages[0] if ctx.pages else ctx.new_page(); pg.on("request",onreq)
        try:
          pg.goto("https://ipinfo.io/json",timeout=40000); rec["exit"]=json.loads(pg.inner_text("pre")).get("ip")
        except: pass
        pg.set_extra_http_headers({"Referer":"https://www.google.com/"})
        r=pg.goto(u+"?gclid=Cj0KCQtest123",wait_until="domcontentloaded",timeout=60000,referer="https://www.google.com/")
        for _ in range(4): pg.mouse.move(random.randint(200,900),random.randint(200,700)); pg.wait_for_timeout(700)
        pg.wait_for_timeout(4000)
        html=pg.content(); low=html.lower()
        rec["http"]=r.status if r else None; rec["final_url"]=pg.url
        rec["title"]=(pg.title() or "")[:100]
        rec["drainer"]=sorted({s for s in DR if s in low})
        rec["seed_inputs"]=len(re.findall(r'<input',low))
        rec["post_endpoints"]=sorted(set(re.findall(r"(?:fetch|xmlhttprequest|\.post)\(\s*['\"]([^'\"]+)",html,re.I)))[:8]
        rec["external_scripts"]=sorted({s for s in scripts if not re.search(r"gstatic|google|jquery|cloudflare",s)})[:12]
        rec["xhr"]=sorted(xhr)[:10]
        rec["telegram"]=bool(re.search(r"api\.telegram\.org|bot[0-9]+:",html))
        rec["obf"]={"eval":low.count("eval("),"atob":low.count("atob("),"hex":len(re.findall(r"\\x[0-9a-f]{2}",html))}
        sh=f"{ROOT}/idnshots/{slug(u)[:40]}.png"; os.makedirs(os.path.dirname(sh),exist_ok=True)
        pg.screenshot(path=sh,full_page=True); rec["screenshot"]=os.path.basename(sh)
        rec["ok"]=r and r.status==200 and len(html)>2000
        ctx.close()
        if rec["ok"]: break
      except Exception as e:
        rec["error"]=str(e)[:120]
        try: ctx.close()
        except: pass
    print(f"  {u}  http={rec.get('http')} drainer={rec.get('drainer')} tg={rec.get('telegram')} post={rec.get('post_endpoints')}",flush=True)
    out.append(rec)
json.dump(out,open(f"{ROOT}/data/idn_capture.json","w"),indent=2)
