# Market Pulse

Inspired Money's public property market pages at https://market.inspiredmoney.com.au

- `/` Perth Market Pulse: weekly Perth figures from REIWA's market snapshots (`data/perth_market_weekly.json`).
- `/australia/` Australia Market Pulse: prices, sales, home loans, building approvals and unemployment for every state and territory from the ABS Data API (`data/australia.json`).

Both refresh themselves on GitHub's servers:

- `.github/workflows/refresh.yml` runs Tuesdays 7:33am Perth. It pulls REIWA with API Anything (pinned version, sharing off), cross-checks the newest week against REIWA's page, and publishes only a new, matching week.
- `.github/workflows/abs.yml` runs Thursdays 9:13am Perth. It pulls the ABS series and publishes only when they change.

If a run fails, GitHub emails the account owner and the page keeps showing the last good data.

Sources: Real Estate Institute of Western Australia (REIWA); Australian Bureau of Statistics, used under CC BY 4.0. General information only, not advice. FML Financial Solutions Pty Ltd ACN 148 937 222 trading as Inspired Money, Corporate Authorised Representative of Inspired Financial Group, AFSL 494196.
