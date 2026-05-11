import pandas as pd
import akshare as ak


def get_stock_history(symbol: str, start: str, end: str) -> pd.DataFrame:
    df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start, end_date=end, adjust="qfq")
    df = df.rename(columns={
        "日期": "date", "开盘": "open", "收盘": "close",
        "最高": "high", "最低": "low", "成交量": "volume",
    })
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df[["open", "high", "low", "close", "volume"]]


def get_index_history(symbol: str, start: str, end: str) -> pd.DataFrame:
    df = ak.index_zh_a_hist(symbol=symbol, period="daily", start_date=start, end_date=end)
    df = df.rename(columns={
        "日期": "date", "开盘": "open", "收盘": "close",
        "最高": "high", "最低": "low", "成交量": "volume",
    })
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df[["open", "high", "low", "close", "volume"]]


def get_multi_stock_history(symbols: list[str], start: str, end: str) -> dict[str, pd.DataFrame]:
    result = {}
    for s in symbols:
        try:
            result[s] = get_stock_history(s, start, end)
        except Exception as e:
            print(f"[WARN] {s} 数据获取失败: {e}")
    return result
