from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
from app.core.config import FLASK_SECRET_KEY, FLASK_PORT
from app.ai.parser import parse_question
from app.backtest.engine import BacktestEngine
from app.report.stats import calc_stats, calc_radar_scores
from app.data.questions import (
    get_hot_questions, add_question, update_question,
    delete_question, click_question, list_all_questions
)

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
CORS(app)

from h5.views import h5_bp
app.register_blueprint(h5_bp)


@app.route("/api/parse", methods=["POST"])
def api_parse():
    body = request.get_json()
    question = body.get("question", "")
    if not question:
        return jsonify({"error": "question is required"}), 400
    result = parse_question(question)
    return jsonify(result)


@app.route("/api/backtest", methods=["POST"])
def api_backtest():
    body = request.get_json()
    filters = body.get("filters", [])
    start_date = body.get("start_date", "")
    end_date = body.get("end_date", "")
    rebalance_freq = body.get("rebalance", "M")
    portfolio_method = body.get("portfolio_method", "market_cap_weight")
    initial_capital = body.get("initial_capital", 10000)

    if not filters:
        return jsonify({"error": "filters are required"}), 400
    if not start_date or not end_date:
        return jsonify({"error": "start_date and end_date are required"}), 400

    config = {"initial_capital": initial_capital}
    engine = BacktestEngine(config)
    result = engine.run(filters, start_date, end_date, rebalance_freq, portfolio_method)

    if "error" in result:
        return jsonify(result), 400

    values = [r["portfolio_value"] for r in result["records"]]
    bm_values = [r.get("benchmark_close") for r in result["records"] if r.get("benchmark_close")]
    bm_start = bm_values[0] if bm_values else None

    stats = calc_stats(values)
    bm_stats = None
    if bm_start and len(bm_values) >= 2:
        bm_norm = [v / bm_start * initial_capital for v in bm_values]
        bm_stats = calc_stats(bm_norm)
    radar = calc_radar_scores(stats, bm_stats)

    portfolio_curve = []
    benchmark_curve = []
    for r in result["records"]:
        portfolio_curve.append([r["date"], r["portfolio_value"]])
        if r.get("benchmark_close") and bm_start:
            benchmark_curve.append([r["date"], round(r["benchmark_close"] / bm_start * initial_capital, 2)])

    return jsonify({
        "stats": stats,
        "radar": radar,
        "portfolio_curve": portfolio_curve,
        "benchmark_curve": benchmark_curve,
        "holdings_by_date": result["holdings_by_date"],
        "total_trading_days": result["total_trading_days"],
    })


@app.route("/api/holdings/<date_str>", methods=["GET"])
def api_holdings(date_str):
    body = request.get_json(silent=True) or {}
    holdings_by_date = body.get("holdings_by_date", {})
    engine = BacktestEngine()
    details = engine.get_holdings_for_date(holdings_by_date, date_str)
    return jsonify(details)


@app.route("/api/hot-questions", methods=["GET"])
def api_hot_questions():
    top_n = request.args.get("top", 5, type=int)
    questions = get_hot_questions(top_n)
    return jsonify(questions)


@app.route("/api/hot-questions", methods=["POST"])
def api_add_question():
    body = request.get_json()
    question = body.get("question", "")
    if not question:
        return jsonify({"error": "question is required"}), 400
    q = add_question(question)
    return jsonify(q), 201


@app.route("/api/hot-questions/<int:qid>", methods=["PUT"])
def api_update_question(qid):
    body = request.get_json()
    q = update_question(
        qid,
        question=body.get("question"),
        is_active=body.get("is_active"),
        priority=body.get("priority"),
    )
    if q is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(q)


@app.route("/api/hot-questions/<int:qid>", methods=["DELETE"])
def api_delete_question(qid):
    ok = delete_question(qid)
    if not ok:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


@app.route("/api/hot-questions/<int:qid>/click", methods=["POST"])
def api_click_question(qid):
    ok = click_question(qid)
    if not ok:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


@app.route("/api/admin/questions", methods=["GET"])
def api_admin_questions():
    return jsonify(list_all_questions())


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


def create_app():
    return app


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=True)
