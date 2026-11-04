#!/usr/bin/env python3
"""Build the Perth Market Pulse dataset from REIWA weekly snapshots.

Runs reiwa_month.py for every month from April 2026 to the current month (Perth time),
merges the weeks, and writes perth_market_weekly.json: one row per week, oldest first.
Fails (exit 1) rather than writing a file with gaps in the core figures.
"""
import calendar, csv, datetime as dt, json, os, subprocess, sys
from zoneinfo import ZoneInfo

START = (2026, 4)
HERE = os.path.dirname(os.path.abspath(__file__))
URL = "https://reiwa.com.au/news/perth-weekly-market-snapshot-for-the-week-ending-{}/"
CORE = {"sales": "Sales transactions", "forSale": "For sale (listings)",
        "forRent": "For rent (listings)", "leased": "Leased"}


def months(today):
    y, m = START
    while (y, m) <= (today.year, today.month):
        yield f"{y}-{m:02d}"
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def num(s):
    return int(s.replace(",", "").split()[0])


def main():
    today = dt.datetime.now(ZoneInfo("Australia/Perth")).date()
    rows, issues = [], []
    for ym in months(today):
        subprocess.run([sys.executable, os.path.join(HERE, "reiwa_month.py"), ym],
                       cwd=HERE, check=True, capture_output=True, timeout=600)
        issues += [l for l in open(os.path.join(HERE, f"reiwa_{ym}.md")).read().split("## Pull issues")[1].splitlines()
                   if l.startswith("- ") and "HTTP 404" not in l]
        for r in csv.DictReader(open(os.path.join(HERE, f"reiwa_{ym}.csv"))):
            d = dt.datetime.strptime(r["Week ending"], "%d/%m/%Y").date()
            slug = f"{d.day}-{calendar.month_name[d.month].lower()}-{d.year}"
            try:
                core = {k: num(r[v]) for k, v in CORE.items()}
            except (ValueError, IndexError):
                sys.exit(f"Week ending {r['Week ending']}: a core figure is missing; not writing the file.")
            rows.append({"week": d.isoformat(), **core,
                         "highestSale": r["Highest sale"], "lowestSale": r["Lowest sale"],
                         "source": URL.format(slug)})
    rows.sort(key=lambda r: r["week"])
    out = os.path.join(os.path.dirname(HERE), "data", "perth_market_weekly.json")
    json.dump(rows, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"{len(rows)} weeks, {rows[0]['week']} to {rows[-1]['week']} -> {out}")
    for l in issues:
        if "differs between" in l or "identical" in l:
            print(l)


if __name__ == "__main__":
    main()
