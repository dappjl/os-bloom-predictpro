from pathlib import Path

from collector.config import load_config

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_load_real_config():
    cfg = load_config(REPO_ROOT / "config.yaml")
    assert len(cfg.indexes) == 10
    spx = cfg.indexes[0]
    assert (spx.symbol, spx.yahoo) == ("SPX", "^GSPC")
    assert spx.yahoo == "^GSPC"
    # PredictPro fork: no FRED, so no US bond rows
    assert {b.country for b in cfg.bonds} == {"DE"}
    assert not any(b.fred for b in cfg.bonds) and cfg.cb_rates == []
    de = next(b for b in cfg.bonds if b.country == "DE")
    assert de.bundesbank == "D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A"
    assert not any(b.country == "UK" for b in cfg.bonds)  # no keyless gilt source
    assert cfg.cadences["equity"] == 300
    assert cfg.max_news == 15
    assert cfg.series == []        # PredictPro fork: every macro chart series was FRED
    assert cfg.calendar_map == []
    assert cfg.feeds[0].name == "FT"


def test_env_overrides_db_path(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", "/data/bloom.db")
    cfg = load_config(REPO_ROOT / "config.yaml")
    assert cfg.db_path == "/data/bloom.db"


def test_defi_config():
    cfg = load_config(REPO_ROOT / "config.yaml")
    assert cfg.zyfai_base == "https://defiapi.zyf.ai/api/v2/opportunities"
    assert cfg.midnight_base == "https://api.morpho.org/v0/midnight"
    assert cfg.cadences["defi"] == 900 and cfg.cadences["midnight"] == 900
    assert cfg.defi.asset == "USDC"
    # strategy order is the dedupe priority: most conservative first
    assert [(s.id, s.label) for s in cfg.defi.strategies] == [
        ("safe", "Conservative"), ("degen", "Moderate"), ("async", "Dynamic"),
    ]
    assert [(c.id, c.name) for c in cfg.defi.chains] == [
        (8453, "Base"), (1, "Ethereum"), (42161, "Arbitrum"),
    ]
    base = cfg.defi.chains[0]
    # addresses are normalized to lowercase at load so fetchers compare directly
    assert base.usdc == "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
    assert cfg.defi.midnight_chains == [8453]
    assert cfg.defi.token_symbols["0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf"] == "cbBTC"
    assert cfg.defi.morpho_graphql == "https://blue-api.morpho.org/graphql"
    assert cfg.defi.morpho_first == 25
    assert cfg.cadences["morpho"] == 900


def test_refs_config():
    cfg = load_config(REPO_ROOT / "config.yaml")
    assert cfg.cadences["refs"] == 900 and cfg.cadences["refs_history"] == 86400

    aave = cfg.refs.aave
    assert [(a.chain, a.symbol) for a in aave] == [
        ("BASE", "USDC"), ("ETH", "USDC"), ("ETH", "USDT"), ("ARB", "USDC"), ("ARB", "USDT"),
    ]  # Base USDT deliberately absent: not listed on Aave v3 Base
    base = aave[0]
    assert base.rpc == "https://mainnet.base.org"
    # addresses are normalized to lowercase at load so fetchers compare directly
    assert base.pool == "0xa238dd80c259a72e81d7e4664a9801593f98d1c5"
    assert base.asset == "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
    assert (base.supply_id, base.supply_label) == ("aave-base-usdc-supply", "AAVE USDC BASE SUP")
    assert (base.borrow_id, base.borrow_label) == ("aave-base-usdc-borrow", "AAVE USDC BASE BOR")
    assert aave[1].pool == aave[2].pool  # ETH markets share the v3 core pool

    # every aave market has a supply-side llama backfill entry
    assert [c.series for c in cfg.refs.llama_chart] == [a.supply_id for a in aave]
    assert cfg.refs.llama_chart[0].pool == "7e0661bf-8cf3-45e6-9424-31916d4c7b84"

    assert len(cfg.refs.pendle) == 1
    pendle = cfg.refs.pendle[0]
    assert pendle.chain_id == 8453
    assert pendle.address == "0xa97bb0de338b23c088dba9bf8c948da726e49033"
    assert (pendle.implied_id, pendle.implied_label) == ("pendle-pt-cbbtc-usdc", "PENDLE PT")
    assert (pendle.underlying_id, pendle.underlying_label) == (
        "pendle-underlying-cbbtc-usdc", "PENDLE UNDERLY",
    )

    assert len(cfg.refs.funding) == 1
    funding = cfg.refs.funding[0]
    assert (funding.symbol, funding.id, funding.label) == ("BTCUSDT", "funding-binance-btc", "BTC FUND ANN")


def test_cycle_config():
    cfg = load_config(REPO_ROOT / "config.yaml")
    assert cfg.cadences["cycle"] == 86400
    by_id = {s.id: s for s in cfg.cycle_series}
    # PredictPro fork: no FRED series and none of the third-party series
    removed = {"usrec", "vix", "vxn", "pc-total", "pc-equity", "aaii-spread", "ism-pmi", "ism-svc",
               "umich", "ig-oas", "hy-oas", "eu-hy-oas", "bbb-oas", "ccc-oas", "m2-yoy", "usd-broad"}
    assert not removed & set(by_id)
    assert not any(s.fred or s.dbnomics or s.cboe or s.aaii for s in cfg.cycle_series)
    assert by_id["oecd-cli-us"].oecd.endswith("/USA.M.LI...AA...H")
    assert by_id["cot-vix"].cftc == "1170E1"
    assert by_id["spw-spx"].yahoo_ratio == ["RSP", "SPY"]
    assert by_id["cot-vix"].transform == "none"  # default
    # every source entry has exactly one source key
    for s in cfg.cycle_series:
        sources = [s.fred, s.dbnomics, s.oecd, s.cftc, s.cboe, s.aaii, s.yahoo_ratio]
        assert sum(x is not None for x in sources) == 1, s.id
    # every tab row references an existing series; overlays too
    tabs = {t.id: t for t in cfg.cycle_tabs}
    assert list(tabs) == ["risk", "econ", "pos"]  # PredictPro fork: CREDIT / PROFIT were all FRED
    for t in cfg.cycle_tabs:
        assert t.label == t.id.upper()
        for p in t.panels:
            for r in p.rows:
                assert r.series in by_id, r.series
                assert r.overlay is None or r.overlay in by_id, r.overlay
                assert not by_id[r.series].hidden


def test_actuals_rules():
    cfg = load_config(REPO_ROOT / "config.yaml")
    assert cfg.cadences["actuals"] == 600
    rules = cfg.actuals
    assert len(rules) == 4  # PredictPro fork: only the Eurostat rules remain
    assert all(r.fred is None for r in rules)
    for r in rules:
        assert (r.fred is None) != (r.eurostat is None), r.match
        assert r.calc in ("level", "pct_prev", "pct_yoy", "diff_k")
        assert r.fmt in ("pct1", "pct2", "k") and r.freq in ("m", "q", "d")
    # first match wins, so the core rules must precede the headline ones
    names = [(r.country, r.match) for r in rules]
    assert names.index(("EUR", "Core CPI Flash Estimate y/y")) < names.index(("EUR", "CPI Flash Estimate y/y"))
    eu_gdp = next(r for r in rules if r.country == "EUR" and r.match == "GDP q/q")
    assert "German" in eu_gdp.exclude and eu_gdp.freq == "q"
    eu_unemp = next(r for r in rules if r.country == "EUR" and r.match == "Unemployment Rate")
    assert eu_unemp.lag == 2 and eu_unemp.eurostat.startswith("une_rt_m?")


def test_fx_and_sectors_config():
    cfg = load_config(REPO_ROOT / "config.yaml")
    assert len(cfg.fx) == 11
    dxy = cfg.fx[0]
    assert (dxy.symbol, dxy.name, dxy.yahoo) == ("DXY", "US Dollar Index", "DX-Y.NYB")
    eurusd = next(f for f in cfg.fx if f.symbol == "EURUSD")
    assert eurusd.yahoo == "EURUSD=X"
    assert cfg.cadences["fx"] == 300

    assert len(cfg.sectors) == 2
    us, eu = cfg.sectors
    assert us.title == "US SECTORS" and len(us.rows) == 11
    assert us.rows[0].symbol == "XLK" and us.rows[0].yahoo == "XLK"
    assert eu.title == "EUROPE SECTORS" and len(eu.rows) == 19
    assert eu.rows[0].symbol == "EXV3" and eu.rows[0].yahoo == "EXV3.DE"
    assert cfg.cadences["sectors"] == 900


def test_config_without_fx_sectors_keys_defaults_empty(tmp_path):
    import yaml

    raw = yaml.safe_load((REPO_ROOT / "config.yaml").read_text())
    raw.pop("fx", None)
    raw.pop("sectors", None)
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump(raw))
    cfg = load_config(p)
    assert cfg.fx == []
    assert cfg.sectors == []


def test_duplicate_symbol_across_indexes_and_fx_raises(tmp_path):
    import yaml

    import pytest

    raw = yaml.safe_load((REPO_ROOT / "config.yaml").read_text())
    raw["fx"].append({"symbol": "SPX", "name": "dup", "yahoo": "SPX=X"})
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError):
        load_config(p)


def test_duplicate_symbol_across_fx_and_sectors_raises(tmp_path):
    import yaml

    import pytest

    raw = yaml.safe_load((REPO_ROOT / "config.yaml").read_text())
    raw["sectors"][0]["rows"].append({"symbol": "EURUSD", "name": "dup", "yahoo": "EURUSD=X"})
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError):
        load_config(p)


def test_actuals_rule_rejects_ambiguous_source():
    import pytest

    from collector.config import ActualRuleCfg

    with pytest.raises(ValueError):
        ActualRuleCfg(country="USD", match="x", fred="A", eurostat="b?c=d")
    with pytest.raises(ValueError):
        ActualRuleCfg(country="USD", match="x", fred="A", calc="nope")
    with pytest.raises(ValueError):
        ActualRuleCfg(country="USD", match="x", fred="A", fmt="nope")
    with pytest.raises(ValueError):
        ActualRuleCfg(country="USD", match="x", fred="A", freq="w")
    with pytest.raises(ValueError):
        ActualRuleCfg(country="GBP", match="x", fred="A")
    with pytest.raises(ValueError):
        ActualRuleCfg(country="USD", match="x", fred="A", lag=-1)
    with pytest.raises(ValueError):
        ActualRuleCfg(country="USD", match="x", fred="A", exclude=[""])
