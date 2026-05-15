import requests
import streamlit as st
import streamlit_echarts as se

API_BASE = "http://localhost:5000"

COLOR_UP = "#ff3b30"
COLOR_DOWN = "#34c759"
COLOR_BLUE = "#0071e3"
COLOR_GRAY = "#86868b"
COLOR_BG = "#f5f5f7"
COLOR_TEXT = "#1d1d1f"
COLOR_TEXT_WEAK = "#86868b"

st.set_page_config(page_title="Auto Backtest", page_icon="📊", layout="wide")

st.markdown(f"""
<style>
    .block-container {{ padding-top: 2rem; padding-bottom: 2rem; max-width: 1200px; }}
    .stTextInput > div > div > input {{
        border-radius: 16px; border: 1px solid #d2d2d7; font-size: 15px; padding: 12px 16px;
    }}
    .stat-card {{ background: {COLOR_BG}; border-radius: 16px; padding: 20px 24px; text-align: center; }}
    .stat-value {{ font-family: SimHei, "Heiti SC", sans-serif; font-size: 20px; font-weight: 700; }}
    .stat-label {{ font-size: 11px; color: {COLOR_TEXT_WEAK}; margin-top: 4px; }}
    .hot-item {{ padding: 8px 0; border-bottom: 1px solid #e5e5ea; cursor: pointer; font-size: 14px; }}
    .hot-item:hover {{ background: {COLOR_BG}; }}
</style>
""", unsafe_allow_html=True)


def fetch_hot_questions():
    try:
        r = requests.get(f"{API_BASE}/api/hot-questions", timeout=3)
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


def run_backtest(question: str):
    try:
        r_parse = requests.post(f"{API_BASE}/api/parse", json={"question": question}, timeout=10)
        if r_parse.status_code != 200:
            return None, "解析失败"
        parsed = r_parse.json()
        if parsed.get("error"):
            return None, parsed.get("message", "解析失败")

        from datetime import datetime, timedelta
        period = parsed.get("period_years", 5)
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=period * 365)).strftime("%Y-%m-%d")

        r_bt = requests.post(f"{API_BASE}/api/backtest", json={
            "filters": parsed.get("filters", []),
            "start_date": start_date,
            "end_date": end_date,
            "rebalance": parsed.get("rebalance", "M"),
            "portfolio_method": parsed.get("portfolio_method", "market_cap_weight"),
        }, timeout=60)
        if r_bt.status_code != 200:
            return None, r_bt.json().get("error", "回测失败")
        return r_bt.json(), None
    except Exception as e:
        return None, str(e)


def render_chart(portfolio_curve, benchmark_curve, method="market_cap_weight"):
    if not portfolio_curve:
        return
    dates = [p[0] for p in portfolio_curve]
    p_vals = [p[1] for p in portfolio_curve]
    b_vals = [b[1] for b in benchmark_curve] if benchmark_curve else []

    option = {
        "backgroundColor": "#ffffff",
        "animation": True,
        "animationDuration": 800,
        "animationEasing": "cubicOut",
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "#fff",
            "borderColor": "#e5e5ea",
            "borderWidth": 1,
            "borderRadius": 12,
            "textStyle": {"color": COLOR_TEXT, "fontSize": 13},
            "formatter": None,
        },
        "legend": {
            "data": ["组合", "大盘"],
            "top": 10,
            "textStyle": {"color": COLOR_TEXT_WEAK, "fontSize": 13},
        },
        "grid": {"left": 80, "right": 30, "top": 60, "bottom": 80},
        "xAxis": {
            "type": "category",
            "data": dates,
            "axisLabel": {"color": COLOR_TEXT_WEAK, "fontSize": 11, "formatter": "{yyyy}-{MM}"},
            "axisLine": {"lineStyle": {"color": "#e5e5ea"}},
        },
        "yAxis": {
            "type": "value",
            "scale": True,
            "axisLabel": {"color": COLOR_TEXT_WEAK, "fontSize": 11, "formatter": "¥{value}"},
            "splitLine": {"lineStyle": {"color": "#f5f5f7"}},
        },
        "dataZoom": [
            {"type": "inside", "start": 0, "end": 100},
            {"type": "slider", "start": 0, "end": 100, "height": 24, "bottom": 10, "borderColor": "#e5e5ea", "fillerColor": "rgba(0,113,227,0.1)"},
        ],
        "series": [
            {
                "name": "组合",
                "type": "line",
                "data": p_vals,
                "smooth": True,
                "symbol": "none",
                "lineStyle": {"width": 2, "color": COLOR_BLUE},
                "areaStyle": {"color": {"type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1, "colorStops": [{"offset": 0, "color": "rgba(0,113,227,0.15)"}, {"offset": 1, "color": "rgba(0,113,227,0)"}]}},
                "itemStyle": {"color": COLOR_BLUE},
            },
            {
                "name": "大盘",
                "type": "line",
                "data": b_vals,
                "smooth": True,
                "symbol": "none",
                "lineStyle": {"width": 1, "color": COLOR_GRAY, "type": "dashed"},
                "itemStyle": {"color": COLOR_GRAY},
            },
        ],
    }
    se.st_echarts(option, height="420px")


def render_radar(radar_data):
    if not radar_data or "indicators" not in radar_data:
        return
    option = {
        "backgroundColor": "#ffffff",
        "animation": True,
        "animationDuration": 500,
        "radar": {
            "indicator": [{"name": n, "max": 100} for n in radar_data["indicators"]],
            "shape": "polygon",
            "splitArea": {"areaStyle": {"color": ["#fff", COLOR_BG]}},
            "axisLine": {"lineStyle": {"color": "#e5e5ea"}},
            "splitLine": {"lineStyle": {"color": "#e5e5ea"}},
        },
        "series": [{
            "type": "radar",
            "data": [
                {
                    "value": radar_data["portfolio"],
                    "name": "组合",
                    "areaStyle": {"color": "rgba(0,113,227,0.2)"},
                    "lineStyle": {"color": COLOR_BLUE, "width": 2},
                    "itemStyle": {"color": COLOR_BLUE},
                },
                {
                    "value": radar_data["benchmark"],
                    "name": "大盘",
                    "areaStyle": {"color": "rgba(134,134,139,0.15)"},
                    "lineStyle": {"color": COLOR_GRAY, "width": 1},
                    "itemStyle": {"color": COLOR_GRAY},
                },
            ],
        }],
        "legend": {"bottom": 0, "textStyle": {"color": COLOR_TEXT_WEAK, "fontSize": 13}},
    }
    se.st_echarts(option, height="360px")


def format_pct(val):
    if val is None:
        return "—"
    if val >= 0:
        return f'<span style="color:{COLOR_UP}">+{val:.2%}</span>'
    return f'<span style="color:{COLOR_DOWN}">{val:.2%}</span>'


col_main, col_sidebar = st.columns([3, 1])

with col_main:
    st.markdown("### 📊 Auto Backtest")
    question = st.text_input(
        "", placeholder="输入你的问题，比如：PE>10的股票组合表现如何？", label_visibility="collapsed"
    )

    if "backtest_result" not in st.session_state:
        st.session_state.backtest_result = None
    if "backtest_error" not in st.session_state:
        st.session_state.backtest_error = None

    if question and question != st.session_state.get("last_question"):
        st.session_state.last_question = question
        with st.spinner("正在回测..."):
            result, error = run_backtest(question)
            st.session_state.backtest_result = result
            st.session_state.backtest_error = error
            st.rerun()

    result = st.session_state.backtest_result
    error = st.session_state.backtest_error

    if error:
        st.error(f"❌ {error}")
    elif result:
        stats = result.get("stats", {})
        render_chart(result.get("portfolio_curve", []), result.get("benchmark_curve", []))

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="stat-card"><div class="stat-value">{format_pct(stats.get("total_return"))}</div><div class="stat-label">总收益</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="stat-card"><div class="stat-value">{format_pct(stats.get("annual_return"))}</div><div class="stat-label">年化收益</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="stat-card"><div class="stat-value">{format_pct(stats.get("max_drawdown"))}</div><div class="stat-label">最大回撤</div></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 组合 vs 大盘")
        render_radar(result.get("radar"))

        holdings = result.get("holdings_by_date", {})
        if holdings:
            st.markdown("---")
            st.markdown("#### 持仓明细")
            sorted_dates = sorted(holdings.keys(), reverse=True)
            selected_date = st.selectbox("选择调仓月份", sorted_dates, format_func=lambda x: f"{x[:4]}年{int(x[4:6])}月")
            if selected_date in holdings:
                h = holdings[selected_date]
                st.json(h)

with col_sidebar:
    st.markdown("🔥 **热门问题**")
    hot_questions = fetch_hot_questions()
    for i, q in enumerate(hot_questions):
        rank = q.get("id", i + 1)
        label = f"{'🥇' if i == 0 else '🥈' if i == 1 else '🥉' if i == 2 else f'{i+1}.'} {q['question']}"
        if st.button(label, key=f"hot_{q['id']}", use_container_width=True):
            st.session_state.last_question = q["question"]
            with st.spinner("正在回测..."):
                result, error = run_backtest(q["question"])
                st.session_state.backtest_result = result
                st.session_state.backtest_error = error
            try:
                requests.post(f"{API_BASE}/api/hot-questions/{q['id']}/click", timeout=2)
            except Exception:
                pass
            st.rerun()
