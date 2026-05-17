import json
import requests
from app.core.config import VOLCENGINE_API_KEY, VOLCENGINE_MODEL, VOLCENGINE_BASE_URL

SUPPORTED_FIELDS = {
    "pe": "PE(市盈率)",
    "pb": "PB(市净率)",
    "roe": "ROE(净资产收益率)",
    "roa": "ROA(总资产收益率)",
    "revenue_growth": "营收增长率",
    "profit_growth": "净利润增长率",
    "cashflow": "经营现金流",
    "dividend_yield": "股息率",
    "market_cap": "市值",
    "debt_ratio": "负债率",
}

REBALANCE_MAP = {"月度调仓": "M", "月调仓": "M", "季度调仓": "Q", "季调仓": "Q", "年度调仓": "Y", "年调仓": "Y", "每月": "M", "每季": "Q", "每年": "Y"}


def parse_question(question: str) -> dict:
    result = _try_llm_parse(question)
    if result is None:
        result = _rule_parse(question)
    if result is None:
        return {"error": True, "message": f"无法理解您的问题，请尝试类似格式：'PE>10、现金流为正的股票组合过去5年表现'"}
    result["original_question"] = question
    return result


def _try_llm_parse(question: str) -> dict | None:
    if not VOLCENGINE_API_KEY:
        return None
    try:
        prompt = f"""你是一个股票回测系统的解析器。把用户的自然语言问题解析为结构化JSON。

支持的字段: {json.dumps(SUPPORTED_FIELDS, ensure_ascii=False)}
操作符: >, >=, <, <=, ==, !=
调仓频率: 月度(M), 季度(Q), 年度(Y)
组合方式: equal_weight(等权), market_cap_weight(市值加权)

用户问题: {question}

只返回JSON，不要其他文字:
{{
  "filters": [{{"field": "字段名", "op": "操作符", "value": 数值}}],
  "rebalance": "M/Q/Y",
  "portfolio_method": "market_cap_weight/equal_weight",
  "period_years": 数字,
  "unrecognized": ["未识别的条件"]
}}"""

        resp = requests.post(
            f"{VOLCENGINE_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {VOLCENGINE_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": VOLCENGINE_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 500,
            },
            timeout=3,
        )
        if resp.status_code != 200:
            return None
        content = resp.json()["choices"][0]["message"]["content"]
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception:
        return None


def _rule_parse(question: str) -> dict | None:
    import re
    filters = []
    unrecognized = []

    for field, label in SUPPORTED_FIELDS.items():
        patterns = [field, label.split("(")[0]]
        for p in patterns:
            matches = re.findall(rf'{p}\s*(>|>=|<|<=|=|==|!=)\s*(\d+\.?\d*)', question, re.IGNORECASE)
            for op, val in matches:
                op = "==" if op == "=" else op
                filters.append({"field": field, "op": op, "value": float(val)})
            if matches:
                break

    for kw, field in [("现金流为正", "cashflow"), ("现金流>0", "cashflow"), ("现金流大于0", "cashflow")]:
        if kw in question and not any(f["field"] == field for f in filters):
            filters.append({"field": field, "op": ">", "value": 0})

    rebalance = "Q"
    for kw, freq in REBALANCE_MAP.items():
        if kw in question:
            rebalance = freq
            break

    period_years = 3
    year_match = re.search(r'(\d+)\s*年', question)
    if year_match:
        period_years = int(year_match.group(1))
    month_match = re.search(r'(\d+)\s*个?月', question)
    if month_match and not year_match:
        period_years = max(1, int(month_match.group(1)) // 12 + 1)

    portfolio_method = "market_cap_weight"
    if "等权" in question:
        portfolio_method = "equal_weight"

    if not filters:
        return None

    return {
        "filters": filters,
        "rebalance": rebalance,
        "portfolio_method": portfolio_method,
        "period_years": period_years,
        "unrecognized": unrecognized,
    }
