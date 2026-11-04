#!/usr/bin/env python3
"""Check the newest week in the data file against REIWA's own page.

Compares sales (from the page's pull-quote lead), homes for sale, homes for rent and leased.
Exits 1 on any mismatch so the refresh stops before publishing a wrong figure.
"""
import html, json, re, sys, urllib.request

rows = json.load(open(sys.argv[1]))
r = rows[-1]
req = urllib.request.Request(r["source"], headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/130 Safari/537.36"})
raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw)))
q = re.search(r'class="quote"[^>]*>(.*?)</', raw, re.S)
lead = html.unescape(re.sub(r"<[^>]+>", " ", q.group(1))) if q else ""


def grab(rx, s):
    m = re.search(rx, s)
    return int(m.group(1).replace(",", "")) if m else None


page = {
    "sales": grab(r"reporting ([\d,]+) transactions", lead) or grab(r"reporting ([\d,]+) transactions", text),
    "forSale": grab(r"There were ([\d,]+) properties for sale", text),
    "forRent": grab(r"there were ([\d,]+) properties for rent", text),
    "leased": grab(r"reported ([\d,]+) properties leased", text),
}
bad = {k: (r[k], v) for k, v in page.items() if v != r[k]}
if bad:
    print(f"MISMATCH week {r['week']}: " + ", ".join(f"{k} file {a} page {b}" for k, (a, b) in bad.items()))
    sys.exit(1)
print(f"Cross-check passed for week ending {r['week']}: {page}")
