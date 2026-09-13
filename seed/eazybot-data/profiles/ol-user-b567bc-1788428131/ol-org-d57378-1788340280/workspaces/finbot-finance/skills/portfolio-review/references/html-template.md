<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>自选股复盘 | {{DATE}}</title>
<style>
  :root {
    --up: #e74c3c; --down: #27ae60; --flat: #888;
    --bg: #f5f6fa; --card: #fff; --text: #2c3e50;
    --muted: #95a5a6; --border: #ecf0f1; --accent: #3498db;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system,'PingFang SC','Noto Sans SC',sans-serif; background: var(--bg); color: var(--text); padding: 20px; }
  .container { max-width: 800px; margin: 0 auto; }
  .header { text-align: center; padding: 30px 0 20px; }
  .header h1 { font-size: 24px; font-weight: 700; }
  .header .data-source { color: var(--muted); font-size: 13px; margin-top: 4px; }
  .card { background: var(--card); border-radius: 12px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
  .card h2 { font-size: 16px; font-weight: 600; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 2px solid var(--border); }
  .card h3 { font-size: 14px; font-weight: 600; margin: 14px 0 8px; color: var(--accent); }
  .card h4 { font-size: 13px; font-weight: 600; margin: 10px 0 6px; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--border); }
  th { font-weight: 600; color: var(--muted); font-size: 12px; }
  .up { color: var(--up); font-weight: 600; }
  .down { color: var(--down); font-weight: 600; }
  .summary-row { display: flex; gap: 8px; margin-bottom: 14px; }
  .summary-item { flex: 1; text-align: center; padding: 10px 6px; border-radius: 8px; background: var(--bg); }
  .summary-item .num { font-size: 22px; font-weight: 700; }
  .summary-item .label { font-size: 11px; color: var(--muted); margin-top: 2px; }
  .comment { font-size: 13px; line-height: 1.7; margin-top: 8px; }
  .comment p { margin-bottom: 6px; }
  .section-label { font-size: 14px; font-weight: 600; margin: 12px 0 6px; padding: 4px 0; color: var(--text); }
  .mood-grid { display: flex; gap: 8px; margin-bottom: 12px; }
  .mood-item { flex: 1; text-align: center; padding: 10px 8px; background: var(--bg); border-radius: 6px; }
  .mood-item .val { font-weight: 700; font-size: 16px; }
  .mood-item .lbl { font-size: 11px; color: var(--muted); margin-top: 2px; }
  .event-item { padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 14px; display: flex; gap: 12px; }
  .event-item:last-child { border-bottom: none; }
  .event-date { font-weight: 600; color: var(--accent); font-size: 12px; white-space: nowrap; min-width: 100px; }
  .event-type { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; background: var(--bg); white-space: nowrap; font-weight: 500; }
  .view-item { padding: 10px 0; border-bottom: 1px solid var(--border); font-size: 13px; line-height: 1.6; }
  .view-item:last-child { border-bottom: none; }
  .view-stock { font-weight: 600; font-size: 14px; }
  .footer { text-align: center; padding: 20px; color: var(--muted); font-size: 12px; }
</style>
</head>
<body>
<div class="container">
  <div class="header"><h1>自选股复盘日报</h1><div class="data-source">{{DATE}}（{{WEEKDAY}}）｜ 数据来源：Gangtise</div></div>

  <!-- 一、盘面速览 -->
  <div class="card">
    <h2>一、盘面速览</h2>
    <div class="summary-row">
      <div class="summary-item"><div class="num">{{STOCK_COUNT}}</div><div class="label">自选股池</div></div>
      <div class="summary-item"><div class="num up">{{UP_COUNT}}</div><div class="label">上涨</div></div>
      <div class="summary-item"><div class="num down">{{DOWN_COUNT}}</div><div class="label">下跌</div></div>
      <div class="summary-item"><div class="num">{{AVG_PCT}}</div><div class="label">平均涨跌幅</div></div>
      <div class="summary-item"><div class="num">{{MEDIAN_PCT}}</div><div class="label">涨幅中位数</div></div>
    </div>

    <h3>大盘指数</h3>
    <table>
      <thead><tr><th>指数</th><th>收盘</th><th>涨跌幅</th></tr></thead>
      <tbody>
        <tr><td><strong>上证指数</strong></td><td>{{SH_VAL}}</td><td class="{{SH_CLASS}}">{{SH_PCT}}</td></tr>
        <tr><td><strong>深证成指</strong></td><td>{{SZ_VAL}}</td><td class="{{SZ_CLASS}}">{{SZ_PCT}}</td></tr>
        <tr><td><strong>创业板指</strong></td><td>{{CY_VAL}}</td><td class="{{CY_CLASS}}">{{CY_PCT}}</td></tr>
        <tr><td><strong>科创50</strong></td><td>{{KC_VAL}}</td><td class="{{KC_CLASS}}">{{KC_PCT}}</td></tr>
        <tr><td><strong>恒生指数</strong></td><td>{{HSI_VAL}}</td><td class="{{HSI_CLASS}}">{{HSI_PCT}}</td></tr>
        <tr><td><strong>恒生科技</strong></td><td>{{HSTECH_VAL}}</td><td class="{{HSTECH_CLASS}}">{{HSTECH_PCT}}</td></tr>
      </tbody>
    </table>

    <h3>市场情绪</h3>
    <div class="mood-grid">
      <div class="mood-item"><div class="val">{{TURNOVER}}</div><div class="lbl">成交额</div></div>
      <div class="mood-item"><div class="val">{{TURNOVER_CHG}}</div><div class="lbl">较上日变化</div></div>
      <div class="mood-item"><div class="val">{{LEAD_SECTOR}}</div><div class="lbl">领涨行业</div></div>
      <div class="mood-item"><div class="val">{{DOWN_STOCKS}}</div><div class="lbl">下跌个股</div></div>
      <div class="mood-item"><div class="val">{{LIMIT_UP}}</div><div class="lbl">涨停</div></div>
      <div class="mood-item"><div class="val">{{SEAL_RATE}}</div><div class="lbl">封板率</div></div>
    </div>

    <div class="section-label">【市场综述】</div>
    <div class="comment"><p>{{MARKET_OVERVIEW}}</p></div>

    <div class="section-label">【自选股综述】</div>
    <div class="comment"><p>{{PORTFOLIO_OVERVIEW}}</p></div>
  </div>

  <!-- 二～七 按 SKILL.md 模板填充 -->
</div>
<div class="footer"><strong>免责声明：</strong> 本报告仅为数据客观归因，不构成任何投资建议。数据来源：Gangtise。</div>
</body>
</html>
