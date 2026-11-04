#!/usr/bin/env python3
"""Build data/australia.json from the ABS Data API (free to republish under CC BY 4.0).

Series, by state and territory:
  meanPrice     Mean price of residential dwellings ($'000), quarterly           RES_DWELL_ST
  houseMedian   Median price of established house transfers ($'000), capitals    RES_DWELL
  transfers     Established house + attached dwelling transfers, capitals        RES_DWELL
  loansOO       New owner-occupier dwelling loan commitments (number, seas. adj.)  LEND_HOUSING
  loansInv      New investor dwelling loan commitments (number), quarterly       LEND_HOUSING
  loansFHB      New first home buyer (owner-occupier) commitments (number)       LEND_HOUSING
  approvals     Residential dwelling units approved (number), monthly            BA_GCCSA
  unemployment  Unemployment rate (%), seasonally adjusted, monthly              LF
Fails (exit 1) rather than writing a file with a series missing.
"""
import csv, datetime as dt, io, json, os, sys, urllib.request

API = "https://data.api.abs.gov.au/rest/data/ABS,{flow}/{key}?startPeriod={start}"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "data", "australia.json")

STATES = ["1", "2", "3", "4", "5", "6", "7", "8", "AUS"]
NAMES = {"1": "NSW", "2": "VIC", "3": "QLD", "4": "SA", "5": "WA", "6": "TAS", "7": "NT", "8": "ACT", "AUS": "Australia"}
CAPS = {"1GSYD": "NSW", "2GMEL": "VIC", "3GBRI": "QLD", "4GADE": "SA", "5GPER": "WA", "6GHOB": "TAS", "7GDAR": "NT", "8ACTE": "ACT"}
S = "+".join(STATES)


def fetch(flow, key, start):
    url = API.format(flow=flow, key=key, start=start)
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.sdmx.data+csv"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode("utf-8"))))


def series(rows, region_map=None, keep=lambda r: True, scale=1.0):
    out = {}
    for r in rows:
        if not keep(r) or r["OBS_VALUE"] == "":
            continue
        reg = (region_map or NAMES).get(r["REGION"])
        if reg is None:
            continue
        out.setdefault(reg, {})[r["TIME_PERIOD"]] = round(float(r["OBS_VALUE"]) * scale, 2)
    return {k: sorted(v.items()) for k, v in out.items()}


def main():
    data = {}
    rows = fetch("RES_DWELL_ST,1.0.0", f"5.{S}.Q", "2019-Q1")
    data["meanPrice"] = series(rows)

    caps = "+".join(CAPS)
    rows = fetch("RES_DWELL,1.0.0", f"1+2+3.{caps}.Q", "2019-Q1")
    data["houseMedian"] = series([r for r in rows if r["MEASURE"] == "3"], CAPS)
    sums = {}
    for r in rows:
        if r["MEASURE"] in ("1", "2") and r["OBS_VALUE"]:
            k = (CAPS[r["REGION"]], r["TIME_PERIOD"])
            sums[k] = sums.get(k, 0) + float(r["OBS_VALUE"])
    tr = {}
    for (reg, per), v in sums.items():
        tr.setdefault(reg, []).append((per, round(v)))
    data["transfers"] = {k: sorted(v) for k, v in tr.items()}

    rows = fetch("LEND_HOUSING,1.1", f"FIN_NUM.NEWCOMMITS.DV8368.TOTDWELL.TOT.DV5167+DV5168.20.{S}.Q", "2019-Q1")
    data["loansOO"] = series(rows, keep=lambda r: r["HOUSING_PURPOSE"] == "DV5167")
    data["loansInv"] = series(rows, keep=lambda r: r["HOUSING_PURPOSE"] == "DV5168")
    rows = fetch("LEND_HOUSING,1.1", f"FIN_NUM.NEWCOMMITS.DV8368.TOTHOUS.TOT.DV5167_FHB.20.{S}.Q", "2019-Q1")
    data["loansFHB"] = series(rows)

    rows = fetch("BA_GCCSA,1.0.0", f"1.1.9.TOT.100.10.{S}.M", "2019-01")
    data["approvals"] = series(rows)

    # Seasonally adjusted where the ABS publishes it; NT and ACT only have trend estimates.
    rows = fetch("LF,1.0.0", f"M13.3.1599.20+30.{S}.M", "2019-01")
    sa = series(rows, keep=lambda r: r["TSEST"] == "20")
    tr = series(rows, keep=lambda r: r["TSEST"] == "30")
    data["unemployment"] = {k: sa.get(k) or tr[k] for k in tr}
    trend_only = sorted(k for k in tr if k not in sa)

    for name, s in data.items():
        need = 8 if name in ("houseMedian", "transfers") else 9
        if len(s) < need or any(len(v) < 8 for v in s.values()):
            sys.exit(f"{name}: expected {need} regions with history, got {[(k, len(v)) for k, v in s.items()]}; not writing the file.")

    out = {"source": "Australian Bureau of Statistics, used under CC BY 4.0", "series": data,
           "unemploymentTrendOnly": trend_only,
           "latest": {k: max(p for v in s.values() for p, _ in v) for k, s in data.items()}}
    json.dump(out, open(OUT, "w"), separators=(",", ":"))
    print("Wrote", OUT, out["latest"])


if __name__ == "__main__":
    main()
