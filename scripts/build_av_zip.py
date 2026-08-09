#!/usr/bin/env python3
"""Build the antivirus-submission package.

Unlike the public evidence ZIP (which stores source as .txt on purpose), this one
restores REAL extensions (.html/.js/.css) and includes the offline-working mirror
copies, so an AV engine ingests the actual code and classifies it. The whole
archive is encrypted with the password "infected" — the universal convention for
sharing live malware samples so the sender's own AV does not quarantine it first.
"""
import json
import os
import re
import shutil
import subprocess
import hashlib
import time

ROOT = "/root/workspace/trezor-ads-teardown"
EV = os.path.join(ROOT, "evidence")
MIR = os.path.join(ROOT, "mirror")
STAGE = os.path.join(ROOT, "av-samples")
OUTZIP = os.path.join(ROOT, "docs", "trezor-google-sites-phishing-SAMPLES-pw-infected.zip")
PW = "infected"


def sniff_ext(txt):
    t = txt.lstrip()[:400].lower()
    if "<!doctype html" in t or "<html" in t or "<meta" in t:
        return ".html"
    if t.startswith("{") or t.startswith("["):
        return ".json"
    if "function" in t or "var " in t or "=>" in t:
        return ".js"
    return ".html"


def folder(u):
    return re.sub(r"[^a-zA-Z0-9]+", "_", re.sub(r"^https?://", "", u)).strip("_")[:80]


def main():
    if os.path.exists(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE)
    cases = json.load(open(os.path.join(ROOT, "data", "cases.json")))
    by = {folder(c["url"]): c for c in cases}
    manifest = []

    for name in sorted(os.listdir(EV)):
        src = os.path.join(EV, name)
        if not os.path.isdir(src):
            continue
        c = by.get(name, {})
        dst = os.path.join(STAGE, name)
        os.makedirs(dst, exist_ok=True)
        # restore real extensions on the captured source
        for fn in os.listdir(src):
            fp = os.path.join(src, fn)
            if fn.endswith(".source.txt"):
                base = fn[:-len(".source.txt")]
                ext = sniff_ext(open(fp, encoding="utf-8", errors="ignore").read())
                shutil.copy2(fp, os.path.join(dst, base + ext))
            elif fn.endswith(".headers.txt") or fn == "EVIDENCE.txt":
                shutil.copy2(fp, os.path.join(dst, fn))
        # attach the offline-working mirror if we have one
        m = os.path.join(MIR, name)
        if os.path.isdir(m):
            shutil.copytree(m, os.path.join(dst, "working_copy"))
        # per-sample sheet
        with open(os.path.join(dst, "SAMPLE.txt"), "w") as f:
            f.write(f"brand           {c.get('brand')}\n")
            f.write(f"classification  {c.get('kind')}\n")
            f.write(f"landing URL     {c.get('url')}\n")
            f.write(f"displayed as    google.com (via sites.google.com)\n")
            if c.get("payload"):
                f.write(f"payload host    {c.get('payload_domain')} [{c.get('payload_state')}]\n")
                if c.get("payload_reg"):
                    f.write(f"payload reg     {c['payload_reg'][:10]} ({c.get('payload_registrar')})\n")
            if c.get("custom_domain"):
                f.write(f"workspace dom   {c.get('custom_domain')} "
                        f"(reg {(c.get('custom_domain_reg') or '?')[:10]})\n")
            f.write(f"serves in       {', '.join(c.get('served_geos', []))}\n")
            f.write(f"files           landing_page.html + assets, working_copy/ renders offline\n")
        manifest.append({"folder": name, "brand": c.get("brand"), "kind": c.get("kind"),
                         "payload_state": c.get("payload_state")})

    # the two live standalone payload kits — freshly fetched, full content, real extension
    lp = os.path.join(STAGE, "LIVE_PAYLOAD_KITS")
    os.makedirs(lp, exist_ok=True)
    for src, dst, desc in [
        ("av_payloads/ksf-webapp-080826_trezor_payload.html",
         "trezor__ksf-webapp-080826.web.app.html",
         "Trezor Suite clone, Firebase Hosting, LIVE"),
        ("av_payloads/japanesetoenailfunguscode_ledger_payload.html",
         "ledger__japanesetoenailfunguscode.com_ledger1_v5.html",
         "Ledger Connect kit w/ anti-bot + BIP-39 wordlist, LIVE"),
    ]:
        sp = os.path.join(ROOT, src)
        if os.path.exists(sp) and os.path.getsize(sp) > 1000:
            shutil.copy2(sp, os.path.join(lp, dst))
    with open(os.path.join(lp, "README.txt"), "w") as f:
        f.write("The two payload kits that were LIVE at capture time, full content, real .html\n"
                "extension. These are the highest-value detection samples in this package.\n")

    if os.path.exists(os.path.join(EV, "INDICATORS.txt")):
        shutil.copy2(os.path.join(EV, "INDICATORS.txt"), os.path.join(STAGE, "INDICATORS.txt"))

    with open(os.path.join(STAGE, "README.txt"), "w") as f:
        f.write(f"""ANTIVIRUS SUBMISSION PACKAGE — Google Sites crypto phishing
Built {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}

PASSWORD: infected
  The archive is encrypted with the standard malware-sample password so your own
  endpoint AV does not delete the files before you can submit them.

WHAT THIS IS
  Live crypto wallet / exchange phishing pages hosted on Google Sites, plus the
  second-stage payload pages they load. Provided for detection-signature work.
  Unlike the public evidence archive, source files here keep their REAL extensions
  (.html/.js/.css) so your engine classifies the code directly.

LAYOUT
  <case folder>/
      landing_page.html         the sites.google.com page (real extension restored)
      payload_N.html            the embedded second-stage kit(s), if captured
      *.headers.txt             HTTP response headers as served
      working_copy/             browser-rendered copy + assets/ that opens offline
      SAMPLE.txt                brand, classification, payload host, geos
  standalone_payload__*/        the two live payload kits, fully mirrored
  INDICATORS.txt                all URLs, payload hosts, BTC addresses, campaign IDs

NOTE
  Several landing pages render sparse offline because their harvesting UI is loaded
  cross-origin from a payload host; the payload's own HTML/JS is included separately
  where it was reachable. The two files under standalone_payload__* are the complete,
  self-contained kits and are the highest-value samples.

  All content is unmodified response bytes. Nothing is weaponised or armed; these
  are captures, not runnable installers.
""")

    json.dump(manifest, open(os.path.join(ROOT, "data", "av_manifest.json"), "w"), indent=2)

    if os.path.exists(OUTZIP):
        os.remove(OUTZIP)
    # zip -P uses ZipCrypto — universally readable, the AV-vault convention
    subprocess.run(["zip", "-r", "-q", "-9", "-P", PW, OUTZIP, "."],
                   cwd=STAGE, check=True)
    size = os.path.getsize(OUTZIP)
    md5 = hashlib.md5(open(OUTZIP, "rb").read()).hexdigest()
    meta = {"file": os.path.basename(OUTZIP), "password": PW, "bytes": size,
            "mb": round(size / 1048576, 2), "md5": md5,
            "cases": len(manifest),
            "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(meta, open(os.path.join(ROOT, "data", "av_zip_meta.json"), "w"), indent=2)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
