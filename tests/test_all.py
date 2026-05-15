import pytest
import json
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np


class TestScreener:
    def test_screen_with_filters(self):
        from app.strategy.screener import screen_stocks
        mock_df = pd.DataFrame({
            "ts_code": ["000001.SZ", "000002.SZ", "000003.SZ"],
            "pe": [8, 15, 25],
            "pb": [0.5, 1.2, 3.0],
            "roe": [15, 10, 5],
            "total_mv": [10000, 5000, 2000],
        })
        with patch("app.strategy.screener.get_fundamental_all", return_value=mock_df):
            result = screen_stocks([{"field": "pe", "op": "<", "value": 20}], "20250101")
            assert "000001.SZ" in result
            assert "000002.SZ" in result
            assert "000003.SZ" not in result

    def test_screen_empty_filters(self):
        from app.strategy.screener import screen_stocks
        assert screen_stocks([], "20250101") == []

    def test_screen_no_match(self):
        from app.strategy.screener import screen_stocks
        mock_df = pd.DataFrame({"ts_code": ["000001.SZ"], "pe": [100]})
        with patch("app.strategy.screener.get_fundamental_all", return_value=mock_df):
            result = screen_stocks([{"field": "pe", "op": "<", "value": 10}], "20250101")
            assert result == []

    def test_screen_empty_df(self):
        from app.strategy.screener import screen_stocks
        with patch("app.strategy.screener.get_fundamental_all", return_value=pd.DataFrame()):
            result = screen_stocks([{"field": "pe", "op": "<", "value": 10}], "20250101")
            assert result == []

    def test_screen_multiple_filters(self):
        from app.strategy.screener import screen_stocks
        mock_df = pd.DataFrame({
            "ts_code": ["000001.SZ", "000002.SZ"],
            "pe": [8, 15],
            "roe": [20, 5],
        })
        with patch("app.strategy.screener.get_fundamental_all", return_value=mock_df):
            result = screen_stocks([
                {"field": "pe", "op": "<", "value": 20},
                {"field": "roe", "op": ">", "value": 10},
            ], "20250101")
            assert result == ["000001.SZ"]


class TestPortfolio:
    def test_equal_weight(self):
        from app.portfolio.portfolio import EqualWeightPortfolio
        p = EqualWeightPortfolio()
        w = p.allocate(["A", "B", "C"], "20250101", {})
        assert abs(sum(w.values()) - 1.0) < 0.01
        assert abs(w["A"] - 1 / 3) < 0.01

    def test_equal_weight_empty(self):
        from app.portfolio.portfolio import EqualWeightPortfolio
        p = EqualWeightPortfolio()
        assert p.allocate([], "20250101", {}) == {}

    def test_market_cap_weight(self):
        from app.portfolio.portfolio import MarketCapWeightPortfolio
        p = MarketCapWeightPortfolio()
        data = {"A": {"total_mv": 3000}, "B": {"total_mv": 1000}}
        w = p.allocate(["A", "B"], "20250101", data)
        assert abs(sum(w.values()) - 1.0) < 0.01
        assert w["A"] > w["B"]

    def test_market_cap_fallback_equal(self):
        from app.portfolio.portfolio import MarketCapWeightPortfolio
        p = MarketCapWeightPortfolio()
        w = p.allocate(["A", "B"], "20250101", {})
        assert abs(sum(w.values()) - 1.0) < 0.01

    def test_get_portfolio(self):
        from app.portfolio.portfolio import get_portfolio, EqualWeightPortfolio, MarketCapWeightPortfolio
        assert isinstance(get_portfolio("equal_weight"), EqualWeightPortfolio)
        assert isinstance(get_portfolio("market_cap_weight"), MarketCapWeightPortfolio)
        assert isinstance(get_portfolio("unknown"), MarketCapWeightPortfolio)


class TestStats:
    def test_calc_stats_basic(self):
        from app.report.stats import calc_stats
        values = [10000, 10500, 10200, 11000, 10800, 12000]
        stats = calc_stats(values)
        assert stats["total_return"] == 0.2
        assert "sharpe_ratio" in stats
        assert "max_drawdown" in stats

    def test_calc_stats_too_short(self):
        from app.report.stats import calc_stats
        stats = calc_stats([10000])
        assert stats["total_return"] == 0

    def test_calc_radar(self):
        from app.report.stats import calc_radar_scores
        stats = {"annual_return": 0.15, "annual_volatility": 0.2, "sharpe_ratio": 1.5,
                 "max_drawdown": -0.1, "win_rate": 0.55, "calmar_ratio": 1.5}
        radar = calc_radar_scores(stats)
        assert len(radar["indicators"]) == 6
        assert len(radar["portfolio"]) == 6

    def test_calc_radar_with_benchmark(self):
        from app.report.stats import calc_radar_scores
        stats = {"annual_return": 0.15, "annual_volatility": 0.2, "sharpe_ratio": 1.5,
                 "max_drawdown": -0.1, "win_rate": 0.55, "calmar_ratio": 1.5}
        bm = {"annual_return": 0.08, "annual_volatility": 0.18, "sharpe_ratio": 0.5,
              "max_drawdown": -0.15, "win_rate": 0.5, "calmar_ratio": 0.5}
        radar = calc_radar_scores(stats, bm)
        assert len(radar["benchmark"]) == 6


class TestParser:
    def test_rule_parse_pe(self):
        from app.ai.parser import _rule_parse
        result = _rule_parse("PE>10的股票组合表现")
        assert result is not None
        assert any(f["field"] == "pe" for f in result["filters"])

    def test_rule_parse_roe(self):
        from app.ai.parser import _rule_parse
        result = _rule_parse("ROE>15的白马股")
        assert result is not None
        assert any(f["field"] == "roe" for f in result["filters"])

    def test_rule_parse_cashflow(self):
        from app.ai.parser import _rule_parse
        result = _rule_parse("现金流为正的股票")
        assert result is not None
        assert any(f["field"] == "cashflow" for f in result["filters"])

    def test_rule_parse_period(self):
        from app.ai.parser import _rule_parse
        result = _rule_parse("PE>10过去3年表现")
        assert result is not None
        assert result["period_years"] == 3

    def test_rule_parse_no_match(self):
        from app.ai.parser import _rule_parse
        result = _rule_parse("今天天气怎么样")
        assert result is None

    def test_parse_fallback_to_rule(self):
        from app.ai.parser import parse_question
        with patch("app.ai.parser._try_llm_parse", return_value=None):
            result = parse_question("PE>10的股票")
            assert "error" not in result or result.get("error") is None or "filters" in result


class TestQuestions:
    def test_default_questions(self):
        from app.data.questions import _default_questions
        qs = _default_questions()
        assert len(qs) == 5
        assert all("question" in q for q in qs)

    def test_get_hot_questions(self):
        from app.data.questions import get_hot_questions
        with patch("app.data.questions._load", return_value=[
            {"id": 1, "question": "test", "click_count": 100, "is_active": True, "priority": 0},
            {"id": 2, "question": "test2", "click_count": 50, "is_active": False, "priority": 0},
        ]):
            qs = get_hot_questions(5)
            assert len(qs) == 1

    def test_add_question(self):
        from app.data.questions import add_question
        mock_qs = [{"id": 1, "question": "old", "click_count": 0, "is_active": True, "priority": 0, "created_at": ""}]
        with patch("app.data.questions._load", return_value=mock_qs), \
             patch("app.data.questions._save") as mock_save:
            q = add_question("new question")
            assert q["question"] == "new question"
            mock_save.assert_called_once()

    def test_click_question(self):
        from app.data.questions import click_question
        mock_qs = [{"id": 1, "question": "test", "click_count": 10, "is_active": True, "priority": 0}]
        with patch("app.data.questions._load", return_value=mock_qs), \
             patch("app.data.questions._save") as mock_save:
            ok = click_question(1)
            assert ok is True
            mock_save.assert_called_once()

    def test_delete_question(self):
        from app.data.questions import delete_question
        mock_qs = [{"id": 1, "question": "test", "click_count": 0, "is_active": True, "priority": 0}]
        with patch("app.data.questions._load", return_value=mock_qs), \
             patch("app.data.questions._save") as mock_save:
            ok = delete_question(1)
            assert ok is True


class TestConfig:
    def test_config_loads(self):
        from app.core.config import PROJECT_ROOT, DATA_DIR, CONFIG_PATH
        assert PROJECT_ROOT.exists()
        assert CONFIG_PATH.exists()


class TestFlaskAPI:
    @pytest.fixture
    def client(self):
        from app.api.server import create_app
        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json["status"] == "ok"

    def test_parse_missing_question(self, client):
        r = client.post("/api/parse", json={})
        assert r.status_code == 400

    def test_parse_valid(self, client):
        r = client.post("/api/parse", json={"question": "PE>10的股票"})
        assert r.status_code == 200

    def test_hot_questions(self, client):
        r = client.get("/api/hot-questions")
        assert r.status_code == 200

    def test_backtest_no_filters(self, client):
        r = client.post("/api/backtest", json={"start_date": "2020-01-01", "end_date": "2025-01-01"})
        assert r.status_code == 400

    def test_backtest_no_dates(self, client):
        r = client.post("/api/backtest", json={"filters": [{"field": "pe", "op": "<", "value": 20}]})
        assert r.status_code == 400

    def test_add_question(self, client):
        r = client.post("/api/hot-questions", json={"question": "测试问题"})
        assert r.status_code == 201

    def test_admin_questions(self, client):
        r = client.get("/api/admin/questions")
        assert r.status_code == 200
