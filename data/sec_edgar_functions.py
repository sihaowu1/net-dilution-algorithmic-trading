import os
import pandas as pd
import requests
from typing import Optional, Dict, Tuple, Any
from sec_edgar_config import SEC_HEADERS

def match_ticker_to_cik(tckr: str) -> str:
    ticker = tckr.upper().replace(".", "-")

    ticker_json = requests.get(
        "https://www.sec.gov/files/company_tickers.json", headers=SEC_HEADERS
    )
    ticker_json.raise_for_status()
    data = ticker_json.json()

    for company in data.values():
        if company["ticker"] == ticker:
            cik = str(company["cik_str"]).zfill(10)
            return cik
    
    raise ValueError(f"{ticker} not found.")

def get_stock_based_compensation(ticker: str, period: str = "annual") -> pd.DataFrame:
    cik = match_ticker_to_cik(ticker)
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    r = requests.get(url, headers=SEC_HEADERS)
    r.raise_for_status()
    company_facts = r.json()

    facts = company_facts.get("facts", {}).get("us-gaap", {})

    # Prefer the canonical expense concept first
    candidate_tags = [
        "StockBasedCompensation",
        # fallback options (only if needed)
        "ShareBasedCompensation",
    ]

    def fp_ok(fp: str | None) -> bool:
        if period == "annual":
            return fp == "FY"
        return isinstance(fp, str) and fp.startswith("Q")

    series = {}

    for tag in candidate_tags:
        concept = facts.get(tag)
        if not concept:
            continue

        units = concept.get("units", {})
        usd_items = units.get("USD", [])  # companyfacts almost always uses "USD"
        if not usd_items:
            continue

        for item in usd_items:
            if not fp_ok(item.get("fp")):
                continue

            # Optional: filter to primary forms
            form = item.get("form")
            if period == "annual" and form not in (None, "10-K", "10-K/A"):
                continue
            if period != "annual" and form not in (None, "10-Q", "10-Q/A"):
                continue

            end = item.get("end")
            val = item.get("val")
            if end is None or val is None:
                continue

            # If duplicates exist for same end, prefer latest filed date
            filed = item.get("filed")  # YYYY-MM-DD
            prev = series.get(end)
            if prev is None or (filed and filed > prev["filed"]):
                series[end] = {"val": float(val), "filed": filed or ""}

        # if we found data in this preferred tag, stop searching fallbacks
        if series:
            break

    if not series:
        raise ValueError(f"No stock-based compensation data found for CIK {cik}")

    # flatten to end -> value
    data = {"Stock-Based Compensation": {end: d["val"] for end, d in series.items()}}
    df = pd.DataFrame(data).T.sort_index(axis=1, ascending=False).fillna(0)
    return df

def get_cashflow_sbc(ticker: str, period: str = "annual") -> pd.DataFrame:
    cik = match_ticker_to_cik(ticker)

    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    r = requests.get(url, headers=SEC_HEADERS)
    r.raise_for_status()
    facts = r.json().get("facts", {}).get("us-gaap", {})

    # Cash flow add-back is most commonly tagged this way
    preferred_tags = ["ShareBasedCompensation", "StockBasedCompensation"]

    def fp_ok(fp: str | None) -> bool:
        if period == "annual":
            return fp == "FY"
        return isinstance(fp, str) and fp.startswith("Q")

    allowed_forms = {"10-K", "10-K/A"} if period == "annual" else {"10-Q", "10-Q/A"}

    series = {}  # end -> (filed, val)

    for tag in preferred_tags:
        concept = facts.get(tag)
        if not concept:
            continue

        usd_items = concept.get("units", {}).get("USD", [])
        if not usd_items:
            continue

        for item in usd_items:
            if not fp_ok(item.get("fp")):
                continue

            form = item.get("form")
            if form and form not in allowed_forms:
                continue

            end = item.get("end")
            val = item.get("val")
            filed = item.get("filed") or ""

            if end is None or val is None:
                continue

            # Prefer latest filed if duplicates exist
            prev = series.get(end)
            if prev is None or filed > prev[0]:
                series[end] = (filed, float(val))

        if series:
            break

    if not series:
        raise ValueError(f"No cash-flow SBC data found for CIK {cik}")

    data = {"Cash Flow SBC": {end: v for end, (_, v) in series.items()}}
    df = pd.DataFrame(data).T.sort_index(axis=1, ascending=False).fillna(0)
    return df

def get_shares_repurchase(ticker: str, period: str = "annual") -> pd.DataFrame:
    cik = match_ticker_to_cik(ticker)

    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    r = requests.get(url, headers=SEC_HEADERS)
    r.raise_for_status()
    company_facts = r.json()

    facts = company_facts.get("facts", {}).get("us-gaap", {})

    repurchase_concepts = [
        "PaymentsForRepurchaseOfCommonStock",
        "PaymentsForRepurchaseOfEquity",
        "RepurchaseOfCommonStock",
        "StockRepurchasedDuringPeriodValue",
    ]

    def fp_ok(fp: str | None) -> bool:
        if period == "annual":
            return fp == "FY"
        return isinstance(fp, str) and fp.startswith("Q")

    repurchase_data = {"Share Repurchase": {}}

    for concept_name in repurchase_concepts:
        for key, concept in facts.items():
            if concept_name.lower() in key.lower():
                units = concept.get("units", {})
                for unit_type, periods_list in units.items():
                    if unit_type != "USD":
                        continue
                    for item in periods_list:
                        if fp_ok(item.get("fp")):
                            end = item.get("end")
                            val = item.get("val")
                            if end is None or val is None:
                                continue
                            # avoid silent overwrite: keep the latest filed if present
                            prev = repurchase_data["Share Repurchase"].get(end)
                            if prev is None:
                                repurchase_data["Share Repurchase"][end] = val
                            else:
                                # if duplicates, keep max (simple heuristic)
                                repurchase_data["Share Repurchase"][end] = max(prev, val)

    # remove empty label
    if not repurchase_data["Share Repurchase"]:
        raise ValueError(f"No share repurchase data found for CIK {cik}")

    df = pd.DataFrame(repurchase_data).T
    df = df.sort_index(axis=1, ascending=False).fillna(0)
    return df

def get_diluted_shares_outstanding(
    ticker: str,
    period: str = "quarterly",
) -> pd.DataFrame:
    """
    Fetch *period-end shares outstanding* from SEC companyfacts.
    This is NOT weighted-average shares (basic or diluted).

    Important note:
    SEC/XBRL generally does not provide a standardized tag for "fully diluted shares outstanding"
    (i.e., basic shares + in-the-money options/RSUs at period end). The closest, consistently
    tagged measure of "shares outstanding" at period end is:
      1) dei:EntityCommonStockSharesOutstanding (cover page)
      2) us-gaap:CommonStockSharesOutstanding

    Args:
        ticker: e.g., "NVDA"
        period: "annual" or "quarterly" (default "quarterly")

    Returns:
        DataFrame with one row ("Shares Outstanding (Period-End)") and period end dates as columns.
    """
    cik = match_ticker_to_cik(ticker)

    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    r = requests.get(url, headers=SEC_HEADERS, timeout=30)
    r.raise_for_status()
    j = r.json()

    # Prefer cover page shares outstanding (dei) then fall back to us-gaap.
    dei = j.get("facts", {}).get("dei", {}) or {}
    gaap = j.get("facts", {}).get("us-gaap", {}) or {}

    # Candidate tags for *period-end* shares outstanding
    # (NOT weighted-average shares tags like WeightedAverageNumberOfDilutedSharesOutstanding)
    candidate_paths = [
        ("dei", "EntityCommonStockSharesOutstanding"),
        ("us-gaap", "CommonStockSharesOutstanding"),
    ]

    def fp_ok(fp: Optional[str]) -> bool:
        if period == "annual":
            return fp == "FY"
        return isinstance(fp, str) and fp.startswith("Q")

    allowed_forms = {"10-K", "10-K/A"} if period == "annual" else {"10-Q", "10-Q/A"}

    # Keep best per end date: prefer latest filed
    best: Dict[str, Tuple[str, float]] = {}  # end -> (filed, val)

    def ingest(concept: Dict[str, Any]) -> None:
        units = concept.get("units", {}) or {}
        # Shares are commonly under "shares"
        items = units.get("shares", [])
        for item in items:
            end = item.get("end")
            val = item.get("val")
            filed = item.get("filed") or ""
            form = item.get("form")

            if end is None or val is None:
                continue

            # Some dei facts may not have fp/form; be permissive for dei.
            # For us-gaap, it's often present; for dei, fp can be missing.
            if form and form not in allowed_forms:
                continue

            fp = item.get("fp")
            if fp is not None and not fp_ok(fp):
                # only enforce fp if present
                continue

            prev = best.get(end)
            if prev is None or filed > prev[0]:
                best[end] = (filed, float(val))

    found_any = False
    for namespace, tag in candidate_paths:
        concept = (dei if namespace == "dei" else gaap).get(tag)
        if concept:
            ingest(concept)
            if best:
                found_any = True
                # If we found data in the preferred (dei) tag, we can stop early.
                if namespace == "dei":
                    break

    if not found_any or not best:
        raise ValueError(f"No period-end shares outstanding found for ticker={ticker}, CIK={cik}")

    series = {end: v for end, (_, v) in best.items()}
    df = pd.DataFrame({"Shares Outstanding (Period-End)": series}).T
    df = df.sort_index(axis=1, ascending=False).fillna(0)
    return df