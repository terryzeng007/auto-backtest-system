import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


class ReportGenerator:
    def __init__(self, output_dir: str = "results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate(self, result: pd.DataFrame, benchmark: pd.DataFrame | None = None, title: str = "回测报告"):
        stats = self._calc_stats(result)
        self._print_stats(stats, title)
        self._plot_equity(result, benchmark, title)
        self._export_excel(result, stats, title)
        return stats

    def _calc_stats(self, result: pd.DataFrame) -> dict:
        values = result["portfolio_value"]
        returns = values.pct_change().dropna()
        total_return = values.iloc[-1] / values.iloc[0] - 1
        n_years = (values.index[-1] - values.index[0]).days / 365
        annual_return = (1 + total_return) ** (1 / max(n_years, 0.01)) - 1
        annual_vol = returns.std() * np.sqrt(252)
        sharpe = (annual_return - 0.03) / annual_vol if annual_vol > 0 else 0
        cummax = values.cummax()
        drawdown = (values - cummax) / cummax
        max_drawdown = drawdown.min()
        calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        win_rate = (returns > 0).sum() / len(returns) if len(returns) > 0 else 0

        return {
            "总收益率": f"{total_return:.2%}",
            "年化收益率": f"{annual_return:.2%}",
            "年化波动率": f"{annual_vol:.2%}",
            "夏普比率": f"{sharpe:.2f}",
            "最大回撤": f"{max_drawdown:.2%}",
            "卡尔玛比率": f"{calmar:.2f}",
            "胜率": f"{win_rate:.2%}",
            "交易天数": len(values),
        }

    def _print_stats(self, stats: dict, title: str):
        print(f"\n{'='*40}")
        print(f"  {title}")
        print(f"{'='*40}")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        print(f"{'='*40}\n")

    def _plot_equity(self, result: pd.DataFrame, benchmark: pd.DataFrame | None, title: str):
        fig, ax = plt.subplots(figsize=(12, 6))
        (result["portfolio_value"] / result["portfolio_value"].iloc[0]).plot(ax=ax, label="组合", linewidth=1.5)
        if benchmark is not None and not benchmark.empty:
            aligned = benchmark.reindex(result.index).ffill()
            (aligned / aligned.iloc[0]).plot(ax=ax, label="基准", linewidth=1, alpha=0.7)
        ax.set_title(title)
        ax.set_ylabel("净值")
        ax.legend()
        ax.grid(True, alpha=0.3)
        path = self.output_dir / "equity_curve.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"净值曲线已保存: {path}")

    def _export_excel(self, result: pd.DataFrame, stats: dict, title: str):
        path = self.output_dir / "backtest_result.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            pd.DataFrame(list(stats.items()), columns=["指标", "值"]).to_excel(writer, sheet_name="统计", index=False)
            result.to_excel(writer, sheet_name="每日净值")
        print(f"Excel 已保存: {path}")
