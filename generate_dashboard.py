"""
Generates dashboard.html showing the daily bias for each tracked pair,
based on data/candles.json and the rules in bias_engine.py.

Includes a mini SVG candle chart per pair (Candle 1 vs Candle 2, with the
swept level highlighted) and a summary/filter bar.
"""

import json
from datetime import datetime
from pathlib import Path

from bias_engine import calculate_bias, bias_reason

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data" / "candles.json"
OUTPUT_FILE = ROOT / "dashboard.html"

BADGE_CLASS = {"BUY": "buy", "SELL": "sell", "AVOID": "avoid"}

CHART_W = 220
CHART_H = 130
PAD = 14


def load_data():
    with open(DATA_FILE) as f:
        return json.load(f)


def build_rows(data):
    rows = []
    for pair, candles in data["pairs"].items():
        c1, c2 = candles["candle1"], candles["candle2"]
        bias = calculate_bias(c1, c2)
        reason = bias_reason(c1, c2)
        rows.append({"pair": pair, "bias": bias, "reason": reason, "c1": c1, "c2": c2})
    return rows


def price_to_y(price, min_low, max_high):
    rng = max_high - min_low or 1
    usable = CHART_H - 2 * PAD
    return PAD + (max_high - price) / rng * usable


def render_mini_chart(c1, c2, bias):
    pad_range = (max(c1["high"], c2["high"]) - min(c1["low"], c2["low"])) * 0.1 or 0.0001
    min_low = min(c1["low"], c2["low"]) - pad_range
    max_high = max(c1["high"], c2["high"]) + pad_range

    def y(p):
        return round(price_to_y(p, min_low, max_high), 1)

    c1_x, c2_x = CHART_W * 0.30, CHART_W * 0.72
    body_w = 26

    def candle_svg(x, o, h, l, c, dim=False):
        color = "#3fb950" if c >= o else "#f85149"
        opacity = "0.55" if dim else "1"
        top = min(o, c)
        bottom = max(o, c)
        body_y = y(bottom)
        body_h = max(y(top) - y(bottom), 2)
        return f"""
          <line x1="{x}" y1="{y(h)}" x2="{x}" y2="{y(l)}" stroke="{color}" stroke-width="2" opacity="{opacity}"/>
          <rect x="{x - body_w/2}" y="{body_y}" width="{body_w}" height="{body_h}" fill="{color}" opacity="{opacity}"/>
        """

    # C1 high/low reference lines spanning the chart width, dashed
    c1_high_y, c1_low_y = y(c1["high"]), y(c1["low"])
    ref_lines = f"""
      <line x1="4" y1="{c1_high_y}" x2="{CHART_W-4}" y2="{c1_high_y}" stroke="#8b949e" stroke-width="1" stroke-dasharray="3,3"/>
      <line x1="4" y1="{c1_low_y}" x2="{CHART_W-4}" y2="{c1_low_y}" stroke="#8b949e" stroke-width="1" stroke-dasharray="3,3"/>
    """

    sweep_color = {"BUY": "#3fb950", "SELL": "#f85149", "AVOID": "#8b949e"}[bias]

    svg = f"""
    <svg width="{CHART_W}" height="{CHART_H}" viewBox="0 0 {CHART_W} {CHART_H}" class="mini-chart">
      {ref_lines}
      {candle_svg(c1_x, c1["open"] if "open" in c1 else (c1["high"]+c1["low"])/2, c1["high"], c1["low"], c1.get("close", (c1["high"]+c1["low"])/2), dim=True)}
      {candle_svg(c2_x, c2["open"], c2["high"], c2["low"], c2["close"])}
      <circle cx="{c2_x}" cy="{y(c2['close'])}" r="3" fill="{sweep_color}"/>
      <text x="{c1_x}" y="{CHART_H - 2}" font-size="9" fill="#8b949e" text-anchor="middle">C1</text>
      <text x="{c2_x}" y="{CHART_H - 2}" font-size="9" fill="#e6edf3" text-anchor="middle">C2</text>
    </svg>
    """
    return svg


def render_html(data, rows):
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    counts = {"BUY": 0, "SELL": 0, "AVOID": 0}
    for r in rows:
        counts[r["bias"]] += 1

    cards = ""
    for r in rows:
        cls = BADGE_CLASS[r["bias"]]
        c1, c2 = r["c1"], r["c2"]
        chart = render_mini_chart(c1, c2, r["bias"])
        cards += f"""
        <div class="card {cls}" data-bias="{r['bias']}">
          <div class="card-header">
            <span class="pair">{r['pair']}</span>
            <span class="badge {cls}">{r['bias']}</span>
          </div>
          <div class="reason">{r['reason']}</div>
          {chart}
          <div class="candles">
            <div class="candle">
              <span class="label">{data['candle1_label']} (C1)</span>
              <span>H {c1['high']}</span>
              <span>L {c1['low']}</span>
            </div>
            <div class="candle">
              <span class="label">{data['candle2_label']} (C2)</span>
              <span>H {c2['high']}</span>
              <span>L {c2['low']}</span>
              <span>C {c2['close']}</span>
            </div>
          </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Daily Bias Dashboard</title>
<style>
  :root {{
    --bg: #0d1117;
    --card-bg: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --muted: #8b949e;
    --buy: #3fb950;
    --sell: #f85149;
    --avoid: #8b949e;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 40px;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }}
  h1 {{ font-size: 22px; margin-bottom: 4px; }}
  .subtitle {{ color: var(--muted); font-size: 13px; margin-bottom: 20px; }}

  .summary-bar {{
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 24px;
    padding: 14px 16px;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
  }}
  .summary-counts {{
    display: flex;
    gap: 16px;
    font-size: 13px;
    margin-right: auto;
  }}
  .summary-counts span.count-buy {{ color: var(--buy); font-weight: 700; }}
  .summary-counts span.count-sell {{ color: var(--sell); font-weight: 700; }}
  .summary-counts span.count-avoid {{ color: var(--avoid); font-weight: 700; }}
  .filter-btn {{
    background: #21262d;
    border: 1px solid var(--border);
    color: var(--text);
    padding: 6px 14px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
  }}
  .filter-btn:hover {{ background: #30363d; }}
  .filter-btn.active {{ background: #1f6feb; border-color: #1f6feb; }}

  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 16px;
  }}
  .card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-left: 4px solid var(--border);
    border-radius: 8px;
    padding: 16px;
  }}
  .card.buy {{ border-left-color: var(--buy); }}
  .card.sell {{ border-left-color: var(--sell); }}
  .card.avoid {{ border-left-color: var(--avoid); }}
  .card.hidden {{ display: none; }}
  .card-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }}
  .pair {{ font-size: 17px; font-weight: 600; letter-spacing: 0.5px; }}
  .badge {{
    font-size: 12px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 999px;
    letter-spacing: 0.5px;
  }}
  .badge.buy {{ background: rgba(63,185,80,0.15); color: var(--buy); }}
  .badge.sell {{ background: rgba(248,81,73,0.15); color: var(--sell); }}
  .badge.avoid {{ background: rgba(139,148,158,0.15); color: var(--avoid); }}
  .reason {{ color: var(--muted); font-size: 13px; margin-bottom: 10px; min-height: 34px; }}
  .mini-chart {{
    width: 100%;
    height: auto;
    background: #0d1117;
    border: 1px solid var(--border);
    border-radius: 6px;
    margin-bottom: 12px;
  }}
  .candles {{
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 12px;
    color: var(--muted);
    border-top: 1px solid var(--border);
    padding-top: 10px;
  }}
  .candle {{ display: flex; gap: 10px; }}
  .candle .label {{ min-width: 90px; color: var(--text); font-weight: 500; }}
  footer {{ margin-top: 32px; color: var(--muted); font-size: 12px; }}
</style>
</head>
<body>
  <h1>Daily Bias Dashboard</h1>
  <div class="subtitle">Generated {generated_at} &middot; Source: {data['source']}</div>

  <div class="summary-bar">
    <div class="summary-counts">
      <span><span class="count-buy">{counts['BUY']}</span> BUY</span>
      <span><span class="count-sell">{counts['SELL']}</span> SELL</span>
      <span><span class="count-avoid">{counts['AVOID']}</span> AVOID</span>
    </div>
    <button class="filter-btn active" data-filter="ALL">All</button>
    <button class="filter-btn" data-filter="BUY">BUY</button>
    <button class="filter-btn" data-filter="SELL">SELL</button>
    <button class="filter-btn" data-filter="AVOID">AVOID</button>
  </div>

  <div class="grid" id="grid">
    {cards}
  </div>

  <footer>
    Rules: Sweep + reclaim = reversal bias &middot; Sweep + close-through = continuation bias &middot; No sweep or sweep-both-closed-middle = AVOID
  </footer>

  <script>
    const buttons = document.querySelectorAll('.filter-btn');
    const cards = document.querySelectorAll('.card');
    buttons.forEach(btn => {{
      btn.addEventListener('click', () => {{
        buttons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const filter = btn.dataset.filter;
        cards.forEach(card => {{
          if (filter === 'ALL' || card.dataset.bias === filter) {{
            card.classList.remove('hidden');
          }} else {{
            card.classList.add('hidden');
          }}
        }});
      }});
    }});
  </script>
</body>
</html>
"""


def main():
    data = load_data()
    rows = build_rows(data)
    html = render_html(data, rows)
    OUTPUT_FILE.write_text(html)
    print(f"Dashboard written to {OUTPUT_FILE}")
    for r in rows:
        print(f"  {r['pair']:7s} -> {r['bias']}")


if __name__ == "__main__":
    main()
