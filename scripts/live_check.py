#!/usr/bin/env python3
"""Liveness check for sites.google.com pages.
LIVE      = 200 and not a Google sign-in page
REMOVED   = redirects to accounts.google.com (unpublished/deleted)
NOTFOUND  = 404
Also extracts <title> and any iframe/embed src pointing off Google Sites' own embed infra.
"""
import json, re, sys, subprocess, concurrent.futures as cf

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# Google Sites' own sandboxed embed infrastructure (not attacker infra)
GOOGLE_EMBED = re.compile(
    r"(atari-embeds\.googleusercontent\.com|gstatic\.com/atari|"
    r"^https?://(www\.)?(google|gstatic|googleusercontent|googleapis)\.com)")


def check(url):
    r = {"url": url}
    try:
        p = subprocess.run(
            ["curl", "-sL", "-m", "35", "-A", UA, "-w",
             "\n@@@%{http_code}|%{url_effective}|%{size_download}", url],
            capture_output=True, text=True, timeout=60)
        body, _, tail = p.stdout.rpartition("\n@@@")
        code, eff, size = (tail.split("|") + ["", "", ""])[:3]
        r["code"] = code
        r["final_url"] = eff
        r["bytes"] = size
        t = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
        r["title"] = re.sub(r"\s+", " ", t.group(1)).strip()[:200] if t else ""
        if "accounts.google.com" in eff:
            r["status"] = "REMOVED"
        elif code == "404":
            r["status"] = "NOTFOUND"
        elif code == "200":
            r["status"] = "LIVE"
        else:
            r["status"] = "HTTP" + code
        # secondary payload frames
        srcs = re.findall(r'(?:src|data-src)=["\'](https?://[^"\']+)', body)
        ext = []
        for s in srcs:
            host = s.split("/")[2]
            if host.endswith(("googleusercontent.com", "gstatic.com", "google.com",
                              "googleapis.com", "ggpht.com", "youtube.com")):
                continue
            ext.append(s)
        # also grab urls buried in the Sites JSON blob
        for m in re.findall(r'"(https?://[^"\\]{10,300})"', body):
            host = m.split("/")[2]
            if host.endswith(("googleusercontent.com", "gstatic.com", "google.com",
                              "googleapis.com", "ggpht.com", "youtube.com", "schema.org",
                              "w3.org", "youtu.be", "googleblog.com")):
                continue
            ext.append(m)
        r["external"] = sorted(set(ext))[:25]
    except Exception as e:
        r["status"] = "ERROR"
        r["err"] = str(e)[:120]
    return r


if __name__ == "__main__":
    urls = [l.strip() for l in open(sys.argv[1]) if l.strip()]
    out = []
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for res in ex.map(check, urls):
            out.append(res)
            print(f"{res['status']:9} {res.get('code','?'):4} {res['url']}  :: {res.get('title','')[:70]}",
                  flush=True)
    json.dump(out, open(sys.argv[2], "w"), indent=1)
