import pandas as pd
from app.data.fetcher import get_fundamental_all, get_stock_list

FIELD_MAP = {
    "pe": "pe",
    "pb": "pb",
    "roe": "roe",
    "roa": None,
    "revenue_growth": None,
    "profit_growth": None,
    "cashflow": "cashflow_per_share",
    "dividend_yield": "dividend_yield",
    "market_cap": "total_mv",
    "debt_ratio": "debt_ratio",
}

OP_MAP = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def screen_stocks(filters: list[dict], trade_date: str) -> list[str]:
    if not filters:
        return []

    df = get_fundamental_all(trade_date)
    if df is None or df.empty:
        return []

    for f in filters:
        field = FIELD_MAP.get(f["field"])
        if field is None or field not in df.columns:
            continue
        op_fn = OP_MAP.get(f["op"])
        if op_fn is None:
            continue
        value = f["value"]
        df = df[op_fn(df[field], value)].copy()

    if df.empty:
        return []

    codes = df["ts_code"].tolist()
    return codes


def get_stock_info(ts_codes: list[str]) -> pd.DataFrame:
    try:
        all_stocks = get_stock_list()
        return all_stocks[all_stocks["ts_code"].isin(ts_codes)][["ts_code", "name", "industry", "market"]]
    except Exception:
        return pd.DataFrame(columns=["ts_code", "name", "industry", "market"])


def get_holdings_detail(ts_codes: list[str], trade_date: str) -> list[dict]:
    if not ts_codes:
        return []
    df = get_fundamental_all(trade_date)
    if df is None or df.empty:
        return []
    df = df[df["ts_code"].isin(ts_codes)]
    stock_info = get_stock_info(ts_codes)
    if not stock_info.empty:
        df = df.merge(stock_info, on="ts_code", how="left")
    else:
        df["name"] = ""
        df["industry"] = ""
    results = []
    for _, row in df.iterrows():
        results.append({
            "ts_code": row.get("ts_code", ""),
            "name": row.get("name", ""),
            "market_cap": round(row.get("total_mv", 0) / 10000, 2) if pd.notna(row.get("total_mv")) else 0,
            "industry": row.get("industry", ""),
            "pe": round(row.get("pe", 0), 2) if pd.notna(row.get("pe")) else None,
        })
    return results
