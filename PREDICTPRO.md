# PredictPro fork of os-bloom

This is `dappjl/os-bloom-predictpro`, branch `predictpro`, a fork of
[cleyfe/os-bloom](https://github.com/cleyfe/os-bloom) (MIT). It is based on upstream
commit `9f1fb83` (2026-09-28, "Merge pull request #3 from cleyfe/fx-sectors").

PredictPro runs it on its own dashboard server and shows it full-page inside its member
app, in a phone page 390–448 px wide. That is why there are four changes. They are
listed below, with the reason for each, so they can be carried onto a newer upstream.

## The four changes

### 1. Phone layout (`ui/css/terminal.css`)

Applies only inside the existing `@media (max-width: 1000px)` block. Desktop is unchanged.

- The tab strip scrolls sideways by itself (`.tab-row { overflow-x: auto }`, tabs `flex: none`).
- The grid column is `minmax(0, 1fr)`, so a panel is never wider than the screen.
- `.panel-body { overflow-x: auto }`: a wide table scrolls sideways inside its own panel.

Why: on upstream at 390 px and 448 px, every tab was 652 px wide (the tab strip pushed
it out). The whole page could be dragged sideways. At 390 px, DEFI's APY column was off
the screen, and so were SECTORS' YTD and 1Y columns.

### 2. News is plain text (`ui/js/panels/news.js`)

Headline and feed name are escaped with the same `esc()` helper `defi.js` uses. A
headline is a link only when its URL is `http(s)://`. Otherwise it is shown as plain text.

Why: upstream inserted the RSS title and link into the page unchanged. A feed could put
markup into the page, or a `javascript:` link that runs when a member taps it.

### 3. DeFi pool names are not links (`ui/js/panels/defi.js`)

The pool name is plain escaped text, and `ZYFAI_URL` is deleted.

Why: upstream linked every pool to Zyfai's product site (www.zyf.ai). PredictPro does
not send members to a third-party yield product. The DEFI data itself stays.

### 4. No FRED and no third-party copyrighted series (`config.yaml`, `ui/index.html`, `ui/js/tabs.js`)

Removed:

- All FRED data:
  - the US `bonds` rows
  - all `cb_rates` (now `[]`)
  - `series` (now `[]`)
  - `calendar_map` (now `[]`, because every target was FRED)
  - the USD `actuals` rules and the ECB rate rule
  - every FRED `cycle_series`, including the hidden `usrec` recession bands
- These third-party series:
  - ICE: `ig-oas`, `hy-oas`, `eu-hy-oas`, `bbb-oas`, `ccc-oas`
  - ISM: `ism-pmi`, `ism-svc`
  - CBOE: `vix`, `vxn`, `pc-total`, `pc-equity`
  - University of Michigan: `umich`
  - AAII: `aaii-spread`
- The RISK panel "VOLATILITY & HEDGING".
- The CREDIT and PROFIT tabs. They are gone from `cycle_tabs`, from the tab links and
  `<main>` blocks in `index.html`, and from `TABS` in `tabs.js`. Keys 1–6 now select the
  six tabs.
- Overlays that pointed at removed ids:
  - `cot-vix` no longer overlays `vix`
  - `cot-usd` no longer overlays `usd-broad`
  - the `ism-pmi` and `t10y2y` overlays went away with their panels
- Panels that became empty: ECON "ACTIVITY & MONEY" and "INFLATION & RATES". An empty
  panel is removed rather than left showing "—".

Kept:

- The Eurostat `actuals` rules: euro-area HICP flash, core HICP flash, unemployment and GDP.
- DE 10Y (Bundesbank) and DE 3M (ECB).
- RISK has the Yahoo rotation ratios. Its panel is renamed from "SENTIMENT & ROTATION" to
  "ROTATION", because the sentiment row (AAII) is gone.
- ECON has the two OECD CLI rows. Its panel is renamed from "SURVEYS & LEADING" to
  "LEADING INDICATORS", because the survey rows (ISM, UMich) are gone.
- POS has CFTC, unchanged.

What changes on screen:

- The WORLD BONDS CB column shows "—". Removing that column would need a code change,
  which this fork does not make.
- Macro calendar rows no longer open a chart.
- Charts have no recession shading.

Why: FRED's terms (https://fred.stlouisfed.org/legal/) forbid commercial use without
written consent, and forbid storing, caching or archiving its content. os-bloom stores
everything in SQLite. PredictPro decided not to use a FRED key at all. Data owned by
someone else needs that owner's licence: ICE BofA spreads, CBOE VIX and put/call,
University of Michigan sentiment, ISM PMIs and AAII sentiment.

No collector code was changed. The FRED fetchers still exist, but nothing in the config
uses them, so no FRED request is ever made. With no key, startup still logs
`FRED_API_KEY not set …`, which is harmless. In `/healthz`, the `macro_history` job still
reports `active_source: "fred"` and `actuals` reports `"fred+eurostat"`. These labels are
hard-coded in the fetchers, and neither job makes a FRED call.

To bring FRED back later: restore those config entries and the two tabs, put
`FRED_API_KEY` in `.env`, and restart.

## Tests changed

The upstream pytest suite checks the repo's `config.yaml`. Only the tests that read that
config and asserted removed entries were changed. No test was deleted or skipped.

- `collector/tests/test_config.py::test_load_real_config`: bonds are `{"DE"}` with no
  FRED source and empty `cb_rates`. This replaces the US/DGS10 check. `series` and
  `calendar_map` are empty. This replaces the `us-cpi-yoy` and "Core CPI first" checks.
- `collector/tests/test_config.py::test_cycle_config`:
  - The `vix`, `usrec`, `ism-pmi`, `pc-total`, `aaii-spread` and `m2-yoy` lookups are
    replaced. The test now checks that none of the removed ids is present, and that no
    series uses fred, dbnomics, cboe or aaii.
  - The default-transform check moved from `vix` to `cot-vix`.
  - The tab list is `["risk", "econ", "pos"]`.
  - The checks that every row and overlay exists are unchanged.
- `collector/tests/test_config.py::test_actuals_rules`: there are 4 rules, none of them
  FRED. The assertions about USD rules (core before headline CPI and retail, NFP, CPI
  SA/NSA, Fed funds) are dropped. The EUR assertions are unchanged.
- `collector/tests/test_api.py::test_dashboard_shape_on_empty_store`: the cycle tab list
  is `["risk", "econ", "pos"]`.
- `collector/tests/test_api.py`: three tests exercise `/api/series` for kinds of series
  that the new config no longer has. They are
  `test_series_endpoint_applies_transform_and_range` (macro series with yoy),
  `test_series_endpoint_serves_bond_and_cb_ids` (US 3M yield and the FED CB rate) and
  `test_cycle_series_endpoint_applies_transform` (`m2-yoy`). They now load a temporary
  copy of the config with the upstream rows added back (`UPSTREAM_FRED_ROWS`, through
  `make_client(tmp_path, upstream_fred_rows=True)`). Their assertions are unchanged, so
  the endpoint behaviour is still tested.

## Browser check: `predictpro/check.mjs`

The check uses playwright-core and system Chrome. Neither is a dependency of this repo.
Copy the file next to a `node_modules/playwright-core` and run `node check.mjs <BASE>`.
Set `SHOT_DIR=<dir>` to also save full-page screenshots.

At 390 px and 448 px, for every tab link in `nav.tab-row`, it checks:

- The page is not wider than the screen.
- The last tab can be scrolled to and opened.
- DEFI has no `#panel-defi a[href]`. The VAULTS/MARKETS toggle anchors have no `href`,
  so they are not links. The APY header comes into view by sliding the panel body, not
  the page.
- MKT: a headline containing markup creates no element, and its text `<img` is visible.
  The news panel has no non-http(s) link.
- RISK, ECON and POS: no row shows "—" in "Now".

It also checks that `/api/dashboard` contains none of the removed ids and no
`fred` source.

Test fixture: serve this file with `python3 -m http.server 8765` and add
`- { name: TEST, url: "http://127.0.0.1:8765/test.xml" }` under `feeds:` in a copy of
the config:

```xml
<rss version="2.0"><channel><title>Test feed</title><link>http://127.0.0.1:8765/</link><description>t</description>
<item><title>Test &lt;img src=x onerror=alert(1)&gt;</title><link>javascript:alert(1)</link><pubDate>Fri, 01 Jan 2027 00:00:00 GMT</pubDate></item>
</channel></rss>
```

Run the collector without Docker, as in the README, against that config and an empty
`DB_PATH`. Wait until `/healthz` lists all 14 fetchers, then run the check.

### Result on upstream `9f1fb83` (2026-10-09): 28 checks FAIL

```
PASS  390px tab links found — mkt,sectors,defi,risk,econ,credit,profit,pos
FAIL  390px mkt: page not wider than screen — scrollWidth=652 innerWidth=390
FAIL  390px mkt: headline markup shown as text — img element=true literal "<img" visible=false
FAIL  390px mkt: news links are http(s) only — non-http link=true
FAIL  390px sectors: page not wider than screen — scrollWidth=652 innerWidth=390
FAIL  390px defi: page not wider than screen — scrollWidth=652 innerWidth=390
FAIL  390px defi: no links in the DeFi panel — a[href] count=46
FAIL  390px defi: APY column reachable inside the panel — th left=387 right=427 scrollX=0 body sw/cw=569/569
FAIL  390px risk: page not wider than screen — scrollWidth=652 innerWidth=390
FAIL  390px risk: no empty rows — VIX ⇄; VXN (Nasdaq vol)
FAIL  390px econ: page not wider than screen — scrollWidth=652 innerWidth=390
FAIL  390px econ: no empty rows — UMich consumer sentiment; Initial jobless claims; Job openings (JOLTS); Heavy truck sales; M2 YoY; M2 velocity; USD broad index; 10Y breakeven; 5y5y fwd inflation; 10Y real rate (TIPS)
FAIL  390px credit: page not wider than screen — scrollWidth=652 innerWidth=390
FAIL  390px profit: page not wider than screen — scrollWidth=652 innerWidth=390
PASS  390px last tab (pos) scrolls into view and opens — hash=#/pos
FAIL  390px pos: page not wider than screen — scrollWidth=652 innerWidth=390
PASS  390px pos: no empty rows
PASS  448px tab links found — mkt,sectors,defi,risk,econ,credit,profit,pos
FAIL  448px mkt: page not wider than screen — scrollWidth=652 innerWidth=448
FAIL  448px mkt: headline markup shown as text — img element=true literal "<img" visible=false
FAIL  448px mkt: news links are http(s) only — non-http link=true
FAIL  448px sectors: page not wider than screen — scrollWidth=652 innerWidth=448
FAIL  448px defi: page not wider than screen — scrollWidth=652 innerWidth=448
FAIL  448px defi: no links in the DeFi panel — a[href] count=46
PASS  448px defi: APY column reachable inside the panel — th left=387 right=427 scrollX=0 body sw/cw=569/569
FAIL  448px risk: page not wider than screen — scrollWidth=652 innerWidth=448
FAIL  448px risk: no empty rows — VIX ⇄; VXN (Nasdaq vol)
FAIL  448px econ: page not wider than screen — scrollWidth=652 innerWidth=448
FAIL  448px econ: no empty rows — UMich consumer sentiment; Initial jobless claims; Job openings (JOLTS); Heavy truck sales; M2 YoY; M2 velocity; USD broad index; 10Y breakeven; 5y5y fwd inflation; 10Y real rate (TIPS)
FAIL  448px credit: page not wider than screen — scrollWidth=652 innerWidth=448
FAIL  448px profit: page not wider than screen — scrollWidth=652 innerWidth=448
PASS  448px last tab (pos) scrolls into view and opens — hash=#/pos
FAIL  448px pos: page not wider than screen — scrollWidth=652 innerWidth=448
PASS  448px pos: no empty rows
FAIL  /api/dashboard has none of the removed ids — ig-oas,hy-oas,eu-hy-oas,bbb-oas,ccc-oas,ism-pmi,ism-svc,vix,vxn,pc-total,pc-equity,umich,aaii-spread,claims,jolts,trucks,m2-yoy,m2-velocity,breakeven-10y,infl-5y5y,real-10y,usd-broad,t10y3m,t10y2y,nfci,bank-lending,corp-profits
PASS  /api/dashboard has no fred source — fred source=false

28 check(s) FAILED
```

### Result on this branch (2026-10-09): ALL PASS

```
PASS  390px tab links found — mkt,sectors,defi,risk,econ,pos
PASS  390px mkt: page not wider than screen — scrollWidth=390 innerWidth=390
PASS  390px mkt: headline markup shown as text — img element=false literal "<img" visible=true
PASS  390px mkt: news links are http(s) only — non-http link=false
PASS  390px sectors: page not wider than screen — scrollWidth=390 innerWidth=390
PASS  390px defi: page not wider than screen — scrollWidth=390 innerWidth=390
PASS  390px defi: no links in the DeFi panel — a[href] count=0
PASS  390px defi: APY column reachable inside the panel — th left=190 right=230 scrollX=0 body sw/cw=569/372
PASS  390px risk: page not wider than screen — scrollWidth=390 innerWidth=390
PASS  390px risk: no empty rows
PASS  390px econ: page not wider than screen — scrollWidth=390 innerWidth=390
PASS  390px econ: no empty rows
PASS  390px last tab (pos) scrolls into view and opens — hash=#/pos
PASS  390px pos: page not wider than screen — scrollWidth=390 innerWidth=390
PASS  390px pos: no empty rows
PASS  448px tab links found — mkt,sectors,defi,risk,econ,pos
PASS  448px mkt: page not wider than screen — scrollWidth=448 innerWidth=448
PASS  448px mkt: headline markup shown as text — img element=false literal "<img" visible=true
PASS  448px mkt: news links are http(s) only — non-http link=false
PASS  448px sectors: page not wider than screen — scrollWidth=448 innerWidth=448
PASS  448px defi: page not wider than screen — scrollWidth=448 innerWidth=448
PASS  448px defi: no links in the DeFi panel — a[href] count=0
PASS  448px defi: APY column reachable inside the panel — th left=248 right=288 scrollX=0 body sw/cw=569/430
PASS  448px risk: page not wider than screen — scrollWidth=448 innerWidth=448
PASS  448px risk: no empty rows
PASS  448px econ: page not wider than screen — scrollWidth=448 innerWidth=448
PASS  448px econ: no empty rows
PASS  448px last tab (pos) scrolls into view and opens — hash=#/pos
PASS  448px pos: page not wider than screen — scrollWidth=448 innerWidth=448
PASS  448px pos: no empty rows
PASS  /api/dashboard has none of the removed ids
PASS  /api/dashboard has no fred source — fred source=false

ALL PASS
```

## Deploying

`predictpro/compose.yml` runs the two images built from this branch:
`osbloom-collector:predictpro-<commit>` and `osbloom-ui:predictpro-<commit>`.

- Only the UI is published, on `127.0.0.1:3130`.
- Both containers are read-only, run with `no-new-privileges`, and have memory limits
  (256 MB for the collector, 64 MB for the UI).
- Logs are capped at 3 × 10 MB.
- `user:` and the image tags are placeholders. Fill them in for the target box.
- The images are built on the build machine and loaded onto the box. Nothing is
  compiled on the box.

## Upgrading to a newer upstream

1. `git fetch upstream && git checkout -b predictpro-next upstream/main`
2. Re-apply the four changes above, starting with the config section. Upstream may add
   new FRED or third-party series; remove those too.
3. Run `cd collector && .venv/bin/pytest -q`. Change only the assertions that pin
   removed config, and list them here.
4. Run `predictpro/check.mjs` against the new branch with the test feed. Every check
   must PASS.
5. Push, rebuild the images with the new commit in their tags, and update
   `predictpro/compose.yml`.
