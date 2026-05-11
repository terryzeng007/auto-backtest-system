import pandas as pd
import numpy as np


class EqualWeightPortfolio:
    def allocate(self, selected: list[str], date: pd.Timestamp, data: dict[str, pd.DataFrame]) -> dict[str, float]:
        if not selected:
            return {}
        weight = 1.0 / len(selected)
        return {s: weight for s in selected}


class MarketCapWeightPortfolio:
    def allocate(self, selected: list[str], date: pd.Timestamp, data: dict[str, pd.DataFrame]) -> dict[str, float]:
        if not selected:
            return {}
        volumes = {}
        for s in selected:
            if s in data and date in data[s].index:
                volumes[s] = data[s].loc[date, "volume"]
        total = sum(volumes.values())
        if total == 0:
            return {s: 1.0 / len(selected) for s in selected}
        return {s: v / total for s, v in volumes.items()}
