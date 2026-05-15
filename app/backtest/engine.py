import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

from app.core.config import CONFIG_PATH
from app.strategy.screener import screen_stocks, get_holdings_detail
from app.portfolio.portfolio import get_portfolio, BasePortfolio
from app.data.fetcher import (
    get_daily_batch, get_index_daily, get_rebalance_dates, get_fundamental_all
)


class BacktestEngine:
    def __init__(self, config: dict | None = None):
        if config is None:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
        self.config = config
        self.initial_capital = config.get("initial_capital", 10000)
        self.commission_rate = config.get("commission_rate", 0.0003)
        self.benchmark_code = config.get("benchmark", "000300")

    def run(
        self,
        filters: list[dict],
        start_date: str,
        end_date: str,
        rebalance_freq: str = "M",
        portfolio_method: str = "market_cap_weight",
    ) -> dict:
        portfolio = get_portfolio(portfolio_method)
        start_fmt = start_date.replace("-", "")
        end_fmt = end_date.replace("-", "")

        rebalance_dates = get_rebalance_dates(start_fmt, end_fmt, rebalance_freq)
        if not rebalance_dates:
            return {"error": "No trading days found in range"}

        benchmark_code = self.benchmark_code
        if "." not in benchmark_code:
            if benchmark_code.startswith("0"):
                benchmark_code = f"{benchmark_code}.SH"
            else:
                benchmark_code = f"{benchmark_code}.SZ"
        benchmark_df = get_index_daily(benchmark_code, start_fmt, end_fmt)
        if benchmark_df.empty:
            alt = f"{self.benchmark_code}.SZ" if benchmark_code.endswith(".SH") else f"{self.benchmark_code}.SH"
            benchmark_df = get_index_daily(alt, start_fmt, end_fmt)

        all_symbols = set()
        holdings_by_date: dict[str, dict] = {}
        weights_by_date: dict[str, dict] = {}
        fund_cache: dict[str, pd.DataFrame] = {}

        for rd in rebalance_dates:
            selected = screen_stocks(filters, rd)
            if not selected:
                continue
            all_symbols.update(selected)

            if rd not in fund_cache:
                fund_cache[rd] = get_fundamental_all(rd)
            fund_df = fund_cache[rd]
            cap_data = {}
            if not fund_df.empty:
                for _, row in fund_df[fund_df["ts_code"].isin(selected)].iterrows():
                    cap_data[row["ts_code"]] = {"total_mv": row.get("total_mv", 0), "circ_mv": row.get("circ_mv", 0)}
            weights = portfolio.allocate(selected, rd, cap_data)
            weights_by_date[rd] = weights

        if not all_symbols:
            return {"error": "No stocks matched the filter criteria. Try relaxing conditions."}

        price_data = get_daily_batch(list(all_symbols), start_fmt, end_fmt)

        rebalance_set = set(rebalance_dates)
        cash = float(self.initial_capital)
        holdings: dict[str, float] = {}
        records = []
        all_dates = sorted(set(d for df in price_data.values() for d in df.index))
        last_prices: dict[str, float] = {}

        for date in all_dates:
            date_str = date.strftime("%Y%m%d")
            if date_str in rebalance_set and date_str in weights_by_date:
                for s, shares in list(holdings.items()):
                    price = self._get_price(s, date, price_data, last_prices)
                    if price > 0:
                        cash += shares * price * (1 - self.commission_rate)
                holdings.clear()

                weights = weights_by_date[date_str]
                for s, w in weights.items():
                    price = self._get_price(s, date, price_data, last_prices)
                    if price <= 0:
                        continue
                    invest = cash * w
                    shares = invest / (price * (1 + self.commission_rate))
                    holdings[s] = shares
                    cash -= invest

                holdings_by_date[date_str] = {s: round(sh, 4) for s, sh in holdings.items()}

            total_value = cash
            for s, shares in holdings.items():
                price = self._get_price(s, date, price_data, last_prices)
                total_value += shares * price

            bm_val = 0
            if not benchmark_df.empty and date in benchmark_df.index:
                bm_val = benchmark_df.loc[date, "close"]

            records.append({
                "date": date.strftime("%Y-%m-%d"),
                "portfolio_value": round(total_value, 2),
                "cash": round(cash, 2),
                "holdings_count": len(holdings),
                "benchmark_close": round(bm_val, 2) if bm_val else None,
            })

        result_df = pd.DataFrame(records)
        return {
            "records": records,
            "holdings_by_date": holdings_by_date,
            "weights_by_date": weights_by_date,
            "total_trading_days": len(records),
        }

    @staticmethod
    def _get_price(symbol: str, date, price_data: dict, last_prices: dict) -> float:
        if symbol not in price_data:
            return last_prices.get(symbol, 0)
        df = price_data[symbol]
        if date in df.index:
            price = float(df.loc[date, "close"])
            last_prices[symbol] = price
            return price
        return last_prices.get(symbol, 0)

    def get_holdings_for_date(self, holdings_by_date: dict, date_str: str) -> list[dict]:
        if date_str not in holdings_by_date:
            sorted_dates = sorted(holdings_by_date.keys(), reverse=True)
            for d in sorted_dates:
                if d <= date_str:
                    date_str = d
                    break
            else:
                return []
        ts_codes = list(holdings_by_date.get(date_str, {}).keys())
        if not ts_codes:
            return []
        details = get_holdings_detail(ts_codes, date_str)
        for d in details:
            d["date"] = date_str
            d["shares"] = holdings_by_date.get(date_str, {}).get(d.get("ts_code", ""), 0)
        return details
