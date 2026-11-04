#!/usr/bin/env python3
"""Pull REIWA Perth weekly market snapshots for one month via API Anything.

Usage:  python3 reiwa_month.py 2026-10
Output: reiwa_<YYYY-MM>.md (figures table + source links) and reiwa_<YYYY-MM>.csv

Pilot rules: public pages only, no logins, sharing off (api-anything setup --no-share).
REIWA retains copyright: use figures with attribution in commentary, never republish the snapshot text.
"""
import calendar, csv, json, re, subprocess, sys, datetime as dt

URL = "https://reiwa.com.au/news/perth-weekly-market-snapshot-for-the-week-ending-{}/"

# Each figure: (label, regex on the joined snapshot text). Group 1 is the value.
FIGURES = [
    ("Sales transactions", r"reporting ([\d,]+) transactions"),
    ("Sales vs prior week", r"Sales transactions in Perth last week were (?:(up|down) ([\d.]+) per cent|(unchanged))"),
    ("For sale (listings)", r"There were ([\d,]+)\s*properties for sale"),
    ("For sale vs prior week", r"properties for sale in Perth at the end of last week, which is ([\d.]+) per cent (higher|lower)"),
    ("For sale vs 4 weeks ago", r"available for sale is ([\d.]+) per cent (higher|lower) than four weeks ago"),
    ("For sale vs a year ago", r"four weeks ago and ([\d.]+) per cent (higher|lower) than levels seen a year ago"),
    ("For rent (listings)", r"there were ([\d,]+)\s*properties for rent"),
    ("For rent vs a year ago", r"rental listings figure is [\d.]+ per cent \w+ than four weeks ago,? (?:and|but) ([\d.]+) per cent (higher|lower) than a year ago"),
    ("Leased", r"reported ([\d,]+) properties leased"),
    ("Highest sale", r"highest sale price:\s*(.+?)(?:$|\n)"),
    ("Lowest sale", r"lowest sale price:\s*(.+?)(?:$|\n)"),
]


def week_slug(d: dt.date) -> str:
    return f"{d.day}-{calendar.month_name[d.month].lower()}-{d.year}"


def sundays(year: int, month: int):
    d = dt.date(year, month, 1)
    while d.weekday() != 6:
        d += dt.timedelta(days=1)
    while d.month == month:
        yield d
        d += dt.timedelta(days=7)


def pull(slug: str):
    out = subprocess.run(["api-anything", "call", "reiwa", "weeklySnapshot", f"week={slug}"],
                         capture_output=True, text=True, timeout=120)
    res = json.loads(out.stdout or "{}")
    if not res.get("ok") or not res.get("data"):
        return None, res.get("reason") or res.get("class") or out.stderr.strip()[:200]
    return res["data"][0], None


def signed(m):
    """Turn a regex match into a display value, e.g. ('up','4.5') -> +4.5%."""
    g = [x for x in m.groups() if x]
    if g == ["unchanged"]:
        return "0.0%"
    words = {"up": "+", "higher": "+", "down": "-", "lower": "-"}
    sign = next((words[x] for x in g if x in words), None)
    nums = [x for x in g if x not in words]
    if sign:
        return f"{sign}{nums[0]}%"
    return nums[0].strip()


def extract(snapshot):
    text = "\n".join(snapshot.get("paragraphs", []))
    row = {}
    for label, rx in FIGURES:
        m = re.search(rx, text, flags=re.I)
        row[label] = signed(m) if m else ""
    return row


def main():
    ym = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().strftime("%Y-%m")
    year, month = map(int, ym.split("-"))
    rows, notes, prev = [], [], None
    for d in sundays(year, month):
        slug = week_slug(d)
        snap, err = pull(slug)
        label = d.strftime("%d/%m/%Y")
        if err:
            notes.append(f"- Week ending {label}: not pulled ({err}). Check {URL.format(slug)}")
            continue
        row = {"Week ending": label, **extract(snap)}
        # The page lead (the pull-quote at the top) carries the headline sales figures. In at least one
        # week (25/10/2026) REIWA's body text repeated the previous week's sales paragraph while the lead
        # was correct, so the lead wins and any disagreement with the body is flagged.
        lead = extract({"paragraphs": [snap.get("lead") or ""]})
        for k in ("Sales transactions", "Sales vs prior week"):
            if lead[k] and lead[k] != row[k]:
                notes.append(f"- Week ending {label}: {k} differs between REIWA's page lead ({lead[k]}) and body "
                             f"({row[k] or 'none'}). Using the lead; body text looks like a copy of an earlier week")
                row[k] = lead[k]
        sales_para = next((p for p in snap.get("paragraphs", []) if "transactions" in p), "")
        if prev and sales_para and sales_para == prev[1]:
            notes.append(f"- Week ending {label}: REIWA's body sales paragraph is identical to week ending {prev[0]} "
                         "(source error at REIWA)")
        prev = (label, sales_para)
        missing = [k for k, v in row.items() if not v]
        if missing:
            notes.append(f"- Week ending {label}: wording changed, missing {', '.join(missing)}. Check {URL.format(slug)}")
        rows.append((row, URL.format(slug)))

    cols = ["Week ending"] + [f[0] for f in FIGURES]
    with open(f"reiwa_{ym}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r, _ in rows:
            w.writerow(r)

    name = f"{calendar.month_name[month]} {year}"
    md = [f"# REIWA Perth weekly figures, {name}", "",
          f"Pulled {dt.datetime.now().strftime('%d/%m/%Y %I:%M %p')} via API Anything (pilot). "
          "Source: REIWA weekly market snapshots. Attribute to REIWA; do not republish their text.", ""]
    for r, url in rows:
        md.append(f"## Week ending {r['Week ending']}")
        md += [f"- {k}: {v or '—'}" for k, v in r.items() if k != "Week ending"]
        md += [f"- Source: {url}", ""]
    md += ["## Pull issues", *(notes or ["- None"]), ""]
    open(f"reiwa_{ym}.md", "w").write("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
