import pandas as pd


class BaseStrategy:
    def select(self, date: pd.Timestamp, data: dict[str, pd.DataFrame]) -> list[str]:
        raise NotImplementedError


class MomentumStrategy(BaseStrategy):
    def __init__(self, lookback: int = 20, top_n: int = 10):
        self.lookback = lookback
        self.top_n = top_n

    def select(self, date: pd.Timestamp, data: dict[str, pd.DataFrame]) -> list[str]:
        returns = {}
        for symbol, df in data.items():
            if date not in df.index:
                continue
            loc = df.index.get_loc(date)
            if loc < self.lookback:
                continue
            ret = df["close"].iloc[loc] / df["close"].iloc[loc - self.lookback] - 1
            returns[symbol] = ret

        sorted_stocks = sorted(returns.items(), key=lambda x: x[1], reverse=True)
        return [s for s, _ in sorted_stocks[: self.top_n]]
