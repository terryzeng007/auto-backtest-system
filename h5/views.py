from flask import Blueprint, render_template_string, jsonify, request
from app.ai.parser import parse_question
from app.backtest.engine import BacktestEngine
from app.report.stats import calc_stats, calc_radar_scores
from app.data.questions import get_hot_questions, click_question

h5_bp = Blueprint("h5", __name__)

H5_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Auto Backtest</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5/dist/echarts.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC", sans-serif; background: #fff; color: #1d1d1f; }
.container { max-width: 100%; padding: 16px; }
.input-box { display: flex; gap: 8px; margin-bottom: 24px; }
.input-box input { flex: 1; border: 1px solid #d2d2d7; border-radius: 16px; padding: 12px 16px; font-size: 15px; outline: none; }
.input-box input:focus { border-color: #0071e3; }
.input-box button { background: #0071e3; color: #fff; border: none; border-radius: 16px; padding: 0 20px; font-size: 15px; cursor: pointer; }
.stats-row { display: flex; gap: 12px; margin-bottom: 24px; }
.stat-card { flex: 1; background: #f5f5f7; border-radius: 16px; padding: 16px; text-align: center; }
.stat-value { font-family: SimHei, "Heiti SC", sans-serif; font-size: 20px; font-weight: 700; }
.stat-label { font-size: 11px; color: #86868b; margin-top: 4px; }
.up { color: #ff3b30; }
.down { color: #34c759; }
.chart-box { width: 100%; height: 300px; margin-bottom: 24px; }
.radar-box { width: 100%; height: 280px; margin-bottom: 24px; }
.section-title { font-size: 16px; font-weight: 600; margin-bottom: 12px; }
.hot-list { list-style: none; }
.hot-list li { padding: 10px 0; border-bottom: 1px solid #e5e5ea; font-size: 14px; cursor: pointer; }
.hot-list li:active { background: #f5f5f7; }
.hot-rank { font-weight: 700; margin-right: 8px; }
.hot-rank.top { color: #ff3b30; }
.loading { text-align: center; padding: 40px; color: #86868b; }
.holdings-table { width: 100%; border-collapse: collapse; font-size: 13px; font-family: SimHei, "Heiti SC", sans-serif; }
.holdings-table th { text-align: left; font-weight: 600; color: #86868b; padding: 8px 4px; border-bottom: 1px solid #e5e5ea; }
.holdings-table td { padding: 8px 4px; border-bottom: 1px solid #e5e5ea; }
.holdings-table tr:hover { background: #f5f5f7; }
.holdings-table .num { text-align: right; font-family: "SF Mono", Menlo, monospace; }
select { border: 1px solid #d2d2d7; border-radius: 8px; padding: 6px 12px; font-size: 14px; margin-bottom: 8px; }
</style>
</head>
<body>
<div class="container">
  <div class="input-box">
    <input id="question" type="text" placeholder="输入你的问题，比如：PE>10的股票组合表现如何？">
    <button onclick="doBacktest()">发送</button>
  </div>
  <div id="result" style="display:none">
    <div id="chart" class="chart-box"></div>
    <div id="stats" class="stats-row"></div>
    <div class="section-title">组合 vs 大盘</div>
    <div id="radar" class="radar-box"></div>
    <div class="section-title">持仓明细</div>
    <select id="month-select" onchange="showHoldings()"></select>
    <table id="holdings" class="holdings-table" style="width:100%"></table>
  </div>
  <div id="loading" class="loading" style="display:none">正在回测...</div>
  <div id="error" style="display:none;color:#ff3b30;padding:16px;"></div>
  <div style="margin-top:32px;">
    <div class="section-title">🔥 热门问题</div>
    <ul id="hot-list" class="hot-list"></ul>
  </div>
</div>
<script>
let lastResult = null;
let chartInstance = null;
let radarInstance = null;

function fmt(v) {
  if (v >= 0) return '<span class="up">+' + (v*100).toFixed(2) + '%</span>';
  return '<span class="down">' + (v*100).toFixed(2) + '%</span>';
}

function doBacktest() {
  const q = document.getElementById('question').value.trim();
  if (!q) return;
  document.getElementById('loading').style.display = 'block';
  document.getElementById('error').style.display = 'none';
  document.getElementById('result').style.display = 'none';
  fetch('/h5/api/backtest', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({question: q})
  })
  .then(r => r.json())
  .then(data => {
    document.getElementById('loading').style.display = 'none';
    if (data.error) {
      document.getElementById('error').textContent = data.error;
      document.getElementById('error').style.display = 'block';
      return;
    }
    lastResult = data;
    renderChart(data);
    renderStats(data.stats);
    renderRadar(data.radar);
    renderHoldingsSelect(data.holdings_by_date);
    document.getElementById('result').style.display = 'block';
  })
  .catch(e => {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('error').textContent = '请求失败: ' + e;
    document.getElementById('error').style.display = 'block';
  });
}

function renderChart(data) {
  if (!chartInstance) chartInstance = echarts.init(document.getElementById('chart'));
  const pCurve = data.portfolio_curve || [];
  const bCurve = data.benchmark_curve || [];
  const dates = pCurve.map(p => p[0]);
  chartInstance.setOption({
    backgroundColor: '#fff',
    animation: true, animationDuration: 800, animationEasing: 'cubicOut',
    tooltip: { trigger: 'axis', backgroundColor: '#fff', borderColor: '#e5e5ea', borderWidth: 1, borderRadius: 12, textStyle: {color: '#1d1d1f', fontSize: 13} },
    legend: { data: ['组合','大盘'], top: 5, textStyle: {color: '#86868b', fontSize: 12} },
    grid: { left: 60, right: 16, top: 40, bottom: 50 },
    xAxis: { type: 'category', data: dates, axisLabel: {color: '#86868b', fontSize: 10}, axisLine: {lineStyle: {color: '#e5e5ea'}} },
    yAxis: { type: 'value', scale: true, axisLabel: {color: '#86868b', fontSize: 10, formatter: '¥{value}'}, splitLine: {lineStyle: {color: '#f5f5f7'}} },
    dataZoom: [{type:'inside'},{type:'slider', height:20, bottom:5}],
    series: [
      { name:'组合', type:'line', data: pCurve.map(p=>p[1]), smooth:true, symbol:'none', lineStyle:{width:2,color:'#0071e3'}, areaStyle:{color:{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{offset:0,color:'rgba(0,113,227,0.15)'},{offset:1,color:'rgba(0,113,227,0)'}]}}, itemStyle:{color:'#0071e3'} },
      { name:'大盘', type:'line', data: bCurve.map(b=>b[1]), smooth:true, symbol:'none', lineStyle:{width:1,color:'#86868b',type:'dashed'}, itemStyle:{color:'#86868b'} }
    ]
  });
}

function renderStats(stats) {
  document.getElementById('stats').innerHTML = `
    <div class="stat-card"><div class="stat-value">${fmt(stats.total_return)}</div><div class="stat-label">总收益</div></div>
    <div class="stat-card"><div class="stat-value">${fmt(stats.annual_return)}</div><div class="stat-label">年化收益</div></div>
    <div class="stat-card"><div class="stat-value">${fmt(stats.max_drawdown)}</div><div class="stat-label">最大回撤</div></div>
  `;
}

function renderRadar(radar) {
  if (!radarInstance) radarInstance = echarts.init(document.getElementById('radar'));
  radarInstance.setOption({
    backgroundColor: '#fff',
    radar: { indicator: radar.indicators.map(n=>({name:n,max:100})), shape:'polygon', splitArea:{areaStyle:{color:['#fff','#f5f5f7']}}, axisLine:{lineStyle:{color:'#e5e5ea'}}, splitLine:{lineStyle:{color:'#e5e5ea'}} },
    series: [{ type:'radar', data:[
      { value: radar.portfolio, name:'组合', areaStyle:{color:'rgba(0,113,227,0.2)'}, lineStyle:{color:'#0071e3',width:2}, itemStyle:{color:'#0071e3'} },
      { value: radar.benchmark, name:'大盘', areaStyle:{color:'rgba(134,134,139,0.15)'}, lineStyle:{color:'#86868b',width:1}, itemStyle:{color:'#86868b'} }
    ]}],
    legend: { bottom:0, textStyle:{color:'#86868b',fontSize:12} }
  });
}

function renderHoldingsSelect(h) {
  const sel = document.getElementById('month-select');
  const dates = Object.keys(h).sort().reverse();
  sel.innerHTML = dates.map(d => `<option value="${d}">${d.slice(0,4)}年${parseInt(d.slice(4,6))}月</option>`).join('');
  showHoldings();
}

function showHoldings() {
  if (!lastResult) return;
  const sel = document.getElementById('month-select').value;
  const h = lastResult.holdings_by_date[sel] || {};
  const codes = Object.keys(h);
  if (!codes.length) { document.getElementById('holdings').innerHTML = '<tr><td colspan="5">无持仓数据</td></tr>'; return; }
  let rows = codes.map(c => `<tr><td>${c}</td><td class="num">${h[c].toFixed(2)}</td></tr>`).join('');
  document.getElementById('holdings').innerHTML = '<tr><th>代码</th><th class="num">权重</th></tr>' + rows;
}

function loadHotQuestions() {
  fetch('/h5/api/hot-questions').then(r=>r.json()).then(qs => {
    const ul = document.getElementById('hot-list');
    ul.innerHTML = qs.map((q,i) => {
      const rankCls = i < 3 ? 'hot-rank top' : 'hot-rank';
      return `<li onclick="clickHot(${q.id},'${q.question.replace(/'/g,"\\\\'")}')"><span class="${rankCls}">${i+1}</span>${q.question}</li>`;
    }).join('');
  }).catch(()=>{});
}

function clickHot(id, q) {
  document.getElementById('question').value = q;
  doBacktest();
  fetch('/h5/api/hot-questions/' + id + '/click', {method:'POST'}).catch(()=>{});
}

loadHotQuestions();
setInterval(loadHotQuestions, 30000);

document.getElementById('question').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') doBacktest();
});
</script>
</body>
</html>
"""


@h5_bp.route("/")
def index():
    return render_template_string(H5_TEMPLATE)


@h5_bp.route("/h5/api/backtest", methods=["POST"])
def h5_backtest():
    body = request.get_json()
    question = body.get("question", "")
    if not question:
        return jsonify({"error": "请输入问题"}), 400

    parsed = parse_question(question)
    if parsed.get("error"):
        return jsonify(parsed), 400

    from datetime import datetime, timedelta
    period = min(parsed.get("period_years", 3), 3)
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=period * 365)).strftime("%Y-%m-%d")

    config = {"initial_capital": 10000}
    engine = BacktestEngine(config)
    result = engine.run(
        parsed.get("filters", []),
        start_date, end_date,
        parsed.get("rebalance", "M"),
        parsed.get("portfolio_method", "market_cap_weight"),
    )

    if "error" in result:
        return jsonify(result), 400

    values = [r["portfolio_value"] for r in result["records"]]
    bm_values = [r.get("benchmark_close") for r in result["records"] if r.get("benchmark_close")]
    bm_start = bm_values[0] if bm_values else None

    stats = calc_stats(values)
    bm_stats = None
    if bm_start and len(bm_values) >= 2:
        bm_norm = [v / bm_start * 10000 for v in bm_values]
        bm_stats = calc_stats(bm_norm)
    radar = calc_radar_scores(stats, bm_stats)

    portfolio_curve = [[r["date"], r["portfolio_value"]] for r in result["records"]]
    benchmark_curve = []
    if bm_start:
        benchmark_curve = [[r["date"], round(r["benchmark_close"] / bm_start * 10000, 2)]
                          for r in result["records"] if r.get("benchmark_close")]

    return jsonify({
        "stats": stats,
        "radar": radar,
        "portfolio_curve": portfolio_curve,
        "benchmark_curve": benchmark_curve,
        "holdings_by_date": result["holdings_by_date"],
    })


@h5_bp.route("/h5/api/hot-questions")
def h5_hot_questions():
    return jsonify(get_hot_questions(5))


@h5_bp.route("/h5/api/hot-questions/<int:qid>/click", methods=["POST"])
def h5_click_question(qid):
    click_question(qid)
    return jsonify({"ok": True})
