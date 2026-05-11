# 自动回测系统 - 股票资产组合管理

## 项目结构

```
auto-backtest-system/
├── app/
│   ├── data/          # 数据获取（AKShare/Tushare/CSV）
│   ├── strategy/      # 选股策略 & 调仓策略
│   ├── portfolio/     # 组合构建 & 权重分配
│   ├── backtest/      # 回测引擎
│   └── report/        # 结果输出 & 可视化
├── config/            # 配置
├── tests/             # 测试
├── main.py            # 入口
└── requirements.txt
```

## 快速开始

```bash
pip install -r requirements.txt
python main.py
```

## 核心流程

选股 → 权重分配 → 调仓 → 回测 → 报告
