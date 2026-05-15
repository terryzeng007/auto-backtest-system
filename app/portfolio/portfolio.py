import pandas as pd


class BasePortfolio:
    def allocate(self, selected: list[str], date: str, data: dict) -> dict[str, float]:
        raise NotImplementedError


class EqualWeightPortfolio(BasePortfolio):
    def allocate(self, selected: list[str], date: str, data: dict) -> dict[str, float]:
        if not selected:
            return {}
        weight = 1.0 / len(selected)
        return {s: round(weight, 6) for s in selected}


class MarketCapWeightPortfolio(BasePortfolio):
    def allocate(self, selected: list[str], date: str, data: dict) -> dict[str, float]:
        if not selected:
            return {}
        caps = {}
        for s in selected:
            if s in data:
                cap = data[s].get("total_mv", 0) or data[s].get("circ_mv", 0)
                if cap and cap > 0:
                    caps[s] = cap
        if not caps:
            return EqualWeightPortfolio().allocate(selected, date, data)
        total = sum(caps.values())
        return {s: round(v / total, 6) for s, v in caps.items()}


PORTFOLIO_MAP = {
    "equal_weight": EqualWeightPortfolio,
    "market_cap_weight": MarketCapWeightPortfolio,
}


def get_portfolio(method: str = "market_cap_weight") -> BasePortfolio:
    cls = PORTFOLIO_MAP.get(method, MarketCapWeightPortfolio)
    return cls()
