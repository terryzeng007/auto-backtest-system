import time
import pandas as pd
import tushare as ts
from pathlib import Path
from app.core.config import TUSHARE_TOKEN, DATA_DIR
from app.core.retry import retry

pro = None

def _get_pro():
    global pro
    if pro is None:
        if not TUSHARE_TOKEN:
            raise ValueError("TUSHARE_TOKEN not configured. Set it in .env file.")
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()
    return pro


@retry(max_retries=3, base_delay=1.0, exceptions=(Exception,))
def get_stock_list() -> pd.DataFrame:
    df = _get_pro().stock_basic(
        exchange="", list_status="L",
        fields="ts_code,symbol,name,area,industry,market,list_date"
    )
    df = df[df["list_date"].notna()].copy()
    df["list_date"] = pd.to_datetime(df["list_date"])
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=60)
    df = df[df["list_date"] <= cutoff]
    df = df[~df["name"].str.contains("ST", na=False)]
    df = df.reset_index(drop=True)
    _save_cache(df, "stock_list")
    return df


@retry(max_retries=3, base_delay=1.5, exceptions=(Exception,))
def get_daily(ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    df = _get_pro().daily(
        ts_code=ts_code, start_date=start_date, end_date=end_date,
        fields="ts_code,trade_date,open,high,low,close,vol,amount"
    )
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns={"trade_date": "date", "vol": "volume"})
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").set_index("date")
    return df[["open", "high", "low", "close", "volume", "amount"]]


@retry(max_retries=3, base_delay=2.0, exceptions=(Exception,))
def get_daily_batch(ts_codes: list[str], start_date: str, end_date: str) -> dict[str, pd.DataFrame]:
    result = {}
    for i, code in enumerate(ts_codes):
        try:
            df = get_daily(code, start_date, end_date)
            if not df.empty:
                result[code] = df
        except Exception as e:
            print(f"[WARN] {code} daily failed: {e}")
        if (i + 1) % 200 == 0:
            time.sleep(0.5)
    return result


@retry(max_retries=3, base_delay=2.0, exceptions=(Exception,))
def get_index_daily(ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    df = _get_pro().index_daily(
        ts_code=ts_code, start_date=start_date, end_date=end_date,
        fields="ts_code,trade_date,open,high,low,close,vol,amount"
    )
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns={"trade_date": "date", "vol": "volume"})
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").set_index("date")
    return df[["open", "high", "low", "close", "volume", "amount"]]


@retry(max_retries=3, base_delay=2.0, exceptions=(Exception,))
def get_fundamental(ts_code: str, period: str = "") -> pd.DataFrame:
    fields = "ts_code,trade_date,pe,pb,roe,roa,debt_to_assets,netprofit_margin,grossprofit_margin,cfps,dv_ratio,total_mv,circ_mv"
    df = _get_pro().daily_basic(
        ts_code=ts_code, trade_date=period,
        fields=fields
    )
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns={
        "debt_to_assets": "debt_ratio",
        "netprofit_margin": "profit_margin",
        "cfps": "cashflow_per_share",
        "dv_ratio": "dividend_yield",
        "total_mv": "total_mv",
        "circ_mv": "circ_mv",
    })
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


@retry(max_retries=3, base_delay=3.0, exceptions=(Exception,))
def get_fundamental_all(trade_date: str) -> pd.DataFrame:
    df = _get_pro().daily_basic(
        trade_date=trade_date,
        fields="ts_code,trade_date,pe,pb,roe,debt_to_assets,cfps,dv_ratio,total_mv,circ_mv"
    )
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns={
        "debt_to_assets": "debt_ratio",
        "cfps": "cashflow_per_share",
        "dv_ratio": "dividend_yield",
    })
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


@retry(max_retries=3, base_delay=2.0, exceptions=(Exception,))
def get_rebalance_dates(start_date: str, end_date: str, freq: str = "M") -> list[str]:
    if freq == "M":
        df = _get_pro().trade_cal(exchange="SSE", start_date=start_date, end_date=end_date, is_open="1")
    elif freq == "Q":
        df = _get_pro().trade_cal(exchange="SSE", start_date=start_date, end_date=end_date, is_open="1")
    else:
        df = _get_pro().trade_cal(exchange="SSE", start_date=start_date, end_date=end_date, is_open="1")
    if df is None or df.empty:
        return []
    df["cal_date"] = pd.to_datetime(df["cal_date"])
    df = df.sort_values("cal_date")
    if freq == "M":
        df["ym"] = df["cal_date"].dt.to_period("M")
        first_days = df.groupby("ym").first()["cal_date"]
    elif freq == "Q":
        df["q"] = df["cal_date"].dt.to_period("Q")
        first_days = df.groupby("q").first()["cal_date"]
    else:
        df["y"] = df["cal_date"].dt.year
        first_days = df.groupby("y").first()["cal_date"]
    return [d.strftime("%Y%m%d") for d in first_days]


def _save_cache(df: pd.DataFrame, name: str):
    path = DATA_DIR / f"{name}.parquet"
    df.to_parquet(path, index=False)


def _load_cache(name: str) -> pd.DataFrame | None:
    path = DATA_DIR / f"{name}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return None


