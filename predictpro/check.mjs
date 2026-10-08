// PredictPro browser check for the os-bloom fork (see PREDICTPRO.md).
//
//   node check.mjs <BASE>            e.g. node check.mjs http://127.0.0.1:8000
//   SHOT_DIR=/some/dir node check.mjs <BASE>   also saves <tab>-<width>.png
//
// Needs playwright-core next to this file (not a dependency of the fork) and
// system Chrome. Run it after the collector has finished its first fetch round,
// with the test feed from PREDICTPRO.md listed under `feeds:`.
// Prints PASS/FAIL per check and exits 1 on any FAIL.
import { chromium } from "playwright-core";

const BASE = (process.argv[2] || "").replace(/\/+$/, "");
if (!BASE) {
  console.error("usage: node check.mjs <BASE>");
  process.exit(2);
}
const SHOT_DIR = process.env.SHOT_DIR;
const CHROME = process.env.CHROME_PATH
  || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

// Third-party copyrighted series (ICE, ISM, CBOE, UMich, AAII) and every
// FRED-backed id from the upstream config.
const REMOVED_IDS = [
  "ig-oas", "hy-oas", "eu-hy-oas", "bbb-oas", "ccc-oas", "ism-pmi", "ism-svc",
  "vix", "vxn", "pc-total", "pc-equity", "umich", "aaii-spread",
  "usrec", "claims", "jolts", "trucks", "m2-yoy", "m2-velocity", "breakeven-10y",
  "infl-5y5y", "real-10y", "usd-broad", "t10y3m", "t10y2y", "nfci", "bank-lending",
  "corp-profits",
  "us-cpi-yoy", "us-core-cpi-yoy", "us-pce-yoy", "us-nfp", "us-unemployment", "us-gdp",
  "us-retail", "us-fed-rate", "ez-hicp-yoy", "ez-unemployment", "ez-gdp", "ez-ecb-rate",
];
const CYCLE_TABS = ["risk", "econ", "pos"];

let failed = 0;
const report = (ok, name, detail = "") => {
  if (!ok) failed++;
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`);
};

const browser = await chromium.launch({ executablePath: CHROME, headless: true });
try {
  for (const width of [390, 448]) {
    const ctx = await browser.newContext({ viewport: { width, height: 844 }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    await page.goto(`${BASE}/#/mkt`, { waitUntil: "load" });
    // the first dashboard poll has rendered once the clock is filled in
    await page.waitForFunction(() => document.getElementById("clock")?.textContent.trim(), null, { timeout: 30000 });
    await page.waitForTimeout(500);

    const tabs = await page.$$eval("nav.tab-row a[data-tab-link]", (as) =>
      as.map((a) => ({ id: a.dataset.tabLink, href: a.getAttribute("href") })));
    report(tabs.length > 0, `${width}px tab links found`, tabs.map((t) => t.id).join(","));

    for (const [i, tab] of tabs.entries()) {
      const link = page.locator(`nav.tab-row a[data-tab-link="${tab.id}"]`);
      await link.click();
      await page.waitForFunction((h) => location.hash === h, tab.href, { timeout: 5000 })
        .catch(() => {});
      const hash = await page.evaluate(() => location.hash);
      if (i === tabs.length - 1) {
        report(hash === tab.href, `${width}px last tab (${tab.id}) scrolls into view and opens`, `hash=${hash}`);
      }
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(300);
      const { sw, iw } = await page.evaluate(() => ({
        sw: document.documentElement.scrollWidth, iw: window.innerWidth,
      }));
      report(sw <= iw, `${width}px ${tab.id}: page not wider than screen`, `scrollWidth=${sw} innerWidth=${iw}`);
      if (SHOT_DIR) await page.screenshot({ path: `${SHOT_DIR}/${tab.id}-${width}.png`, fullPage: true });

      if (tab.id === "defi") {
        const links = await page.locator("#panel-defi a[href]").count();
        report(links === 0, `${width}px defi: no links in the DeFi panel`, `a[href] count=${links}`);
        const apy = await page.evaluate(() => {
          const body = document.querySelector("#panel-defi .panel-body");
          const th = [...body.querySelectorAll("th")].find((t) => t.textContent.trim() === "APY");
          if (!th) return { ok: false, why: "no APY header (no DeFi data?)" };
          window.scrollTo(0, window.scrollY);
          body.scrollLeft = body.scrollWidth; // slide the table, never the page
          const r = th.getBoundingClientRect();
          const ok = r.left >= 0 && r.right <= window.innerWidth + 0.5 && window.scrollX === 0;
          return { ok, why: `th left=${Math.round(r.left)} right=${Math.round(r.right)} scrollX=${window.scrollX} body sw/cw=${body.scrollWidth}/${body.clientWidth}` };
        });
        report(apy.ok, `${width}px defi: APY column reachable inside the panel`, apy.why);
      }

      if (tab.id === "mkt") {
        const news = await page.evaluate(() => {
          const p = document.getElementById("panel-news");
          return {
            img: p.querySelector("img") !== null,
            text: p.innerText.includes("<img"),
            jsLink: [...p.querySelectorAll("a[href]")].some((a) => !/^https?:\/\//i.test(a.getAttribute("href"))),
          };
        });
        report(!news.img && news.text, `${width}px mkt: headline markup shown as text`,
          `img element=${news.img} literal "<img" visible=${news.text}`);
        report(!news.jsLink, `${width}px mkt: news links are http(s) only`, `non-http link=${news.jsLink}`);
      }

      if (CYCLE_TABS.includes(tab.id)) {
        const empty = await page.evaluate((id) =>
          [...document.querySelectorAll(`#cycle-${id} tr.release`)]
            .filter((tr) => tr.children[1]?.textContent.trim() === "—")
            .map((tr) => tr.children[0].textContent.trim()), tab.id);
        report(empty.length === 0, `${width}px ${tab.id}: no empty rows`, empty.join("; "));
      }
    }
    await ctx.close();
  }

  const res = await fetch(`${BASE}/api/dashboard`);
  const text = await res.text();
  const present = REMOVED_IDS.filter((id) => text.includes(`"${id}"`));
  report(present.length === 0, "/api/dashboard has none of the removed ids", present.join(","));
  const fred = /"(?:actual_)?source"\s*:\s*"[^"]*fred/i.test(text);
  report(!fred, "/api/dashboard has no fred source", `fred source=${fred}`);
} finally {
  await browser.close();
}
console.log(failed ? `\n${failed} check(s) FAILED` : "\nALL PASS");
process.exit(failed ? 1 : 0);
