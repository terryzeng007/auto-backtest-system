import numpy as np
import pandas as pd


def calc_stats(values: list[float]) -> dict:
    if len(values) < 2:
        return _empty_stats()
    s = pd.Series(values)
    returns = s.pct_change().dropna()
    if returns.empty:
        return _empty_stats()

    total_return = s.iloc[-1] / s.iloc[0] - 1
    n_days = len(s)
    n_years = max(n_days / 252, 0.01)
    annual_return = (1 + total_return) ** (1 / n_years) - 1
    annual_vol = returns.std() * np.sqrt(252)
    sharpe = (annual_return - 0.03) / annual_vol if annual_vol > 0 else 0
    cummax = s.cummax()
    drawdown = (s - cummax) / cummax
    max_drawdown = drawdown.min()
    calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
    win_rate = (returns > 0).sum() / len(returns)

    return {
        "total_return": round(total_return, 4),
        "annual_return": round(annual_return, 4),
        "annual_volatility": round(annual_vol, 4),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown": round(max_drawdown, 4),
        "calmar_ratio": round(calmar, 2),
        "win_rate": round(win_rate, 4),
    }


def calc_radar_scores(stats: dict, benchmark_stats: dict | None = None) -> dict:
    def normalize(val, min_v, max_v):
        if max_v == min_v:
            return 50
        return max(0, min(100, (val - min_v) / (max_v - min_v) * 100))

    ret_score = normalize(stats.get("annual_return", 0), -0.2, 0.5)
    vol_score = normalize(-stats.get("annual_volatility", 0.3), -0.5, 0)
    sharpe_score = normalize(stats.get("sharpe_ratio", 0), -1, 3)
    dd_score = normalize(-stats.get("max_drawdown", -0.2), -0.5, 0)
    win_score = normalize(stats.get("win_rate", 0.5), 0.3, 0.7)
    calmar_score = normalize(stats.get("calmar_ratio", 0), -1, 5)

    portfolio_scores = [ret_score, vol_score, sharpe_score, dd_score, win_score, calmar_score]

    if benchmark_stats:
        b_ret = normalize(benchmark_stats.get("annual_return", 0), -0.2, 0.5)
        b_vol = normalize(-benchmark_stats.get("annual_volatility", 0.3), -0.5, 0)
        b_sharpe = normalize(benchmark_stats.get("sharpe_ratio", 0), -1, 3)
        b_dd = normalize(-benchmark_stats.get("max_drawdown", -0.2), -0.5, 0)
        b_win = normalize(benchmark_stats.get("win_rate", 0.5), 0.3, 0.7)
        b_calmar = normalize(benchmark_stats.get("calmar_ratio", 0), -1, 5)
        benchmark_scores = [b_ret, b_vol, b_sharpe, b_dd, b_win, b_calmar]
    else:
        benchmark_scores = [40, 55, 35, 45, 50, 30]

    return {
        "indicators": ["收益率", "波动率", "夏普比率", "最大回撤", "胜率", "卡尔玛比率"],
        "portfolio": [round(x, 1) for x in portfolio_scores],
        "benchmark": [round(x, 1) for x in benchmark_scores],
    }


def _empty_stats() -> dict:
    return {
        "total_return": 0,
        "annual_return": 0,
        "annual_volatility": 0,
        "sharpe_ratio": 0,
        "max_drawdown": 0,
        "calmar_ratio": 0,
        "win_rate": 0,
    }
