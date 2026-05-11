import json
from pathlib import Path
from app.backtest.engine import BacktestEngine
from app.strategy.strategy import MomentumStrategy
from app.report.reporter import ReportGenerator


def main():
    with open(Path(__file__).parent / "config" / "config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    symbols = ["000001", "000002", "000063", "000333", "000651",
               "000858", "002415", "002714", "300059", "300750",
               "600036", "600104", "600276", "600309", "600519",
               "600887", "601012", "601166", "601318", "603259"]

    strategy = MomentumStrategy(lookback=20, top_n=10)
    engine = BacktestEngine(config)

    result = engine.run(
        symbols=symbols,
        strategy=strategy,
        start="2023-01-01",
        end="2025-12-31",
        benchmark=config.get("benchmark", "000300"),
    )

    reporter = ReportGenerator()
    reporter.generate(result, title="动量策略 - 股票组合回测")


if __name__ == "__main__":
    main()
