import json
from pathlib import Path
import pandas as pd
import numpy as np

from app.data.fetcher import get_multi_stock_history, get_index_history
from app.strategy.strategy import BaseStrategy, MomentumStrategy
from app.portfolio.portfolio import EqualWeightPortfolio
from app.report.reporter import ReportGenerator

CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.json"


class BacktestEngine:
    def __init__(self, config: dict | None = None):
        if config is None:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
        self.config = config
        self.initial_capital = config.get("initial_capital", 1_000_000)
        self.commission_rate = config.get("commission_rate", 0.0003)
        self.slippage = config.get("slippage", 0.001)
        self.rebalance_freq = config.get("rebalance_freq", "M")

    def run(
        self,
        symbols: list[str],
        strategy: BaseStrategy,
        start: str,
        end: str,
        benchmark: str = "000300",
    ) -> pd.DataFrame:
        print(f"加载数据: {len(symbols)} 只股票, {start} ~ {end}")
        data = get_multi_stock_history(symbols, start.replace("-", ""), end.replace("-", ""))

        all_dates = set()
        for df in data.values():
            all_dates.update(df.index)
        all_dates = sorted(all_dates)
        start_dt = pd.Timestamp(start)
        end_dt = pd.Timestamp(end)
        all_dates = [d for d in all_dates if start_dt <= d <= end_dt]

        portfolio = EqualWeightPortfolio()
        cash = self.initial_capital
        holdings: dict[str, float] = {}
        records = []

        rebalance_dates = pd.date_range(start_dt, end_dt, freq=self.rebalance_freq)

        for date in all_dates:
            if date in rebalance_dates:
                selected = strategy.select(date, data)
                weights = portfolio.allocate(selected, date, data)

                for s, shares in list(holdings.items()):
                    if s in data and date in data[s].index:
                        price = data[s].loc[date, "close"]
                        cash += shares * price * (1 - self.commission_rate)
                holdings.clear()

                for s, w in weights.items():
                    if s in data and date in data[s].index:
                        price = data[s].loc[date, "close"] * (1 + self.slippage)
                        invest = cash * w
                        shares = invest / price
                        holdings[s] = shares
                        cash -= invest * (1 + self.commission_rate)

            total_value = cash
            for s, shares in holdings.items():
                if s in data and date in data[s].index:
                    total_value += shares * data[s].loc[date, "close"]

            records.append({"date": date, "portfolio_value": total_value, "cash": cash, "holdings": len(holdings)})

        result = pd.DataFrame(records).set_index("date")
        print(f"回测完成: {len(result)} 个交易日")
        return result
