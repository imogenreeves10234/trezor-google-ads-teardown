#!/usr/bin/env python3
"""
HOMOGLYPH -> PUNYCODE  (educational / defensive)
================================================

WHAT A HOMOGLYPH IS
  A homoglyph is a character from ANOTHER alphabet that looks the same as a normal
  Latin letter. Example: Latin "a" (U+0061) vs Cyrillic "а" (U+0430). To your eye
  they are identical; to a computer they are two completely different characters.

HOW A LOOK-ALIKE DOMAIN IS MADE (3 steps)
  1. Take a real word, e.g.  ledger
  2. Swap one or more letters for a look-alike from another script/accent,
     e.g. the "g" becomes "ġ" (U+0121, a g with a dot on top)  ->  ledġer
  3. Domain names can only use plain ASCII letters, so the browser stores that
     word in a special ASCII form called PUNYCODE, which always starts with "xn--".
        ledġer   ->   xn--leder-y1a
     The address bar shows the pretty "ledġer" but the real registered domain is
     "xn--leder-y1a". This is called an IDN homograph attack.

WHY THE BROWSER ACCEPTS IT
  Non-English domains are a legitimate feature (e.g. Chinese, Arabic, accented
  European names), standardised as IDNA / Punycode (RFC 3492 / UTS-46). Attackers
  abuse that feature: they pick homoglyphs that render as the target brand.
  (Modern browsers DO defend a bit: if a label mixes scripts, or is all one
  non-Latin script that looks Latin, many browsers show the raw xn-- instead. Pure
  accent tricks like "ġ" often still render as the pretty form.)

HOW THE LETTERS ARE CHOSEN
  You need a character that (a) looks like the target letter and (b) is a valid
  IDNA character. The CONFUSABLES map below is a small hand-picked set of the best
  look-alikes (Cyrillic, Greek, Armenian, and Latin accents). Real attack tools use
  the official Unicode "confusables.txt" list, which has thousands.

DEFENCE (the important half)
  To CHECK a suspicious domain, do the reverse: decode the xn-- back to unicode and
  see if it's really your brand in disguise.  ->  decode() below.
"""
import sys
import unicodedata

# hand-picked look-alikes: latin letter -> list of valid IDNA homoglyphs
CONFUSABLES = {
    "a": ["а", "à", "á", "â", "ā", "ą"],      # а = Cyrillic U+0430
    "c": ["с", "ç", "ć"],                        # с = Cyrillic U+0441
    "d": ["ԁ", "ď"],                             # ԁ = Cyrillic U+0501
    "e": ["е", "ё", "ē", "ė", "ę", "é"],        # е = Cyrillic U+0435
    "g": ["ġ", "ğ", "ǵ", "ģ"],                  # ġ = U+0121 (the ledġer trick)
    "h": ["һ", "ĥ"],                             # һ = Cyrillic U+04BB
    "i": ["і", "í", "ï", "ī", "ı"],             # і = Cyrillic U+0456
    "j": ["ј", "ĵ"],                             # ј = Cyrillic U+0458
    "k": ["к", "ķ"],                             # к = Cyrillic U+043A
    "l": ["ӏ", "ł", "ĺ", "ļ"],                  # ӏ = Cyrillic U+04CF
    "n": ["ո", "ñ", "ń"],                        # ո = Armenian U+0578
    "o": ["о", "ο", "ø", "ō", "ö", "ó"],        # о = Cyrillic U+043E, ο = Greek
    "p": ["р", "ρ"],                             # р = Cyrillic U+0440, ρ = Greek
    "s": ["ѕ", "ś", "š"],                        # ѕ = Cyrillic U+0455
    "u": ["υ", "ս", "ü", "ū"],                  # υ = Greek, ս = Armenian
    "x": ["х", "ҳ"],                             # х = Cyrillic U+0445
    "y": ["у", "ý", "ÿ"],                        # у = Cyrillic U+0443
    "z": ["ż", "ź", "ž"],
}


def to_punycode(unicode_domain):
    """pretty unicode domain  ->  real registered xn-- form."""
    import idna
    try:
        return idna.encode(unicode_domain, uts46=True, transitional=False).decode()
    except Exception:
        # per-label fallback (idna is strict about whole domains)
        return ".".join(
            (lbl.encode("idna").decode() if not lbl.isascii() else lbl)
            for lbl in unicode_domain.split("."))


def decode(punycode_domain):
    """DEFENCE: real xn-- form  ->  the pretty unicode it hides + the plain skeleton."""
    import idna
    labels = []
    for lbl in punycode_domain.split("."):
        if lbl.startswith("xn--"):
            try:
                labels.append(idna.decode(lbl))
            except Exception:
                labels.append(lbl.encode().decode("idna"))
        else:
            labels.append(lbl)
    uni = ".".join(labels)
    # "skeleton" = strip accents/scripts back toward plain ascii, to reveal the target
    skel = "".join(_nearest_ascii(ch) for ch in uni)
    return uni, skel


_REV = {g: base for base, glist in CONFUSABLES.items() for g in glist}


def _nearest_ascii(ch):
    if ch in _REV:
        return _REV[ch]
    d = unicodedata.normalize("NFKD", ch)
    b = "".join(c for c in d if not unicodedata.combining(c))
    return b if b.isascii() and b else ch


def variants(word, tld="com", max_swaps=1, limit=40):
    """generate look-alike domains by swapping up to `max_swaps` letters."""
    out = []
    for i, ch in enumerate(word.lower()):
        for g in CONFUSABLES.get(ch, []):
            uni = word[:i] + g + word[i + 1:]
            dom = f"{uni}.{tld}"
            out.append((dom, to_punycode(dom), f"{ch}->{g} (U+{ord(g):04X}) at pos {i}"))
            if len(out) >= limit:
                return out
    return out


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "decode":
        uni, skel = decode(sys.argv[2])
        print(f"{sys.argv[2]}  reads as  {uni}   (looks like: {skel})")
    else:
        word = sys.argv[1] if len(sys.argv) > 1 else "ledger"
        tld = sys.argv[2] if len(sys.argv) > 2 else "app"
        print(f"look-alike domains for '{word}.{tld}':\n")
        for dom, puny, how in variants(word, tld):
            print(f"  {dom:16} -> {puny:22} [{how}]")
