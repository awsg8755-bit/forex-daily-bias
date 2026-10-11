"""
Generates dashboard.html showing the daily bias for each tracked pair,
based on data/candles.json and the rules in bias_engine.py.

Includes a mini SVG candle chart per pair (Candle 1 vs Candle 2, with the
swept level highlighted), a summary/filter bar, and a small animated SVG
"trader at a desk" scene per card whose monitor glows BUY/SELL/AVOID.
"""

import html
import json
from datetime import datetime
from pathlib import Path

from bias_engine import calculate_bias, bias_reason
from economic_calendar import load_events_by_pair

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data" / "candles.json"
OUTPUT_FILE = ROOT / "dashboard.html"

BADGE_CLASS = {"BUY": "buy", "SELL": "sell", "AVOID": "avoid"}

FLAGS = {
    "XAUUSD": "🥇",
    "GBPJPY": "🇬🇧🇯🇵",
    "GBPUSD": "🇬🇧🇺🇸",
    "EURGBP": "🇪🇺🇬🇧",
    "EURUSD": "🇪🇺🇺🇸",
    "AUDJPY": "🇦🇺🇯🇵",
    "USDJPY": "🇺🇸🇯🇵",
}

CHART_W = 220
CHART_H = 130
PAD = 14


def load_data():
    with open(DATA_FILE) as f:
        return json.load(f)


def build_rows(data):
    rows = []
    events_by_pair = load_events_by_pair(data["pairs"].keys())
    for pair, candles in data["pairs"].items():
        c1, c2 = candles["candle1"], candles["candle2"]
        bias = calculate_bias(c1, c2)
        reason = bias_reason(c1, c2)
        rows.append({
            "pair": pair,
            "bias": bias,
            "reason": reason,
            "c1": c1,
            "c2": c2,
            "events": events_by_pair.get(pair, []),
        })
    return rows


def price_to_y(price, min_low, max_high):
    rng = max_high - min_low or 1
    usable = CHART_H - 2 * PAD
    return PAD + (max_high - price) / rng * usable


def render_mini_chart(c1, c2, bias, idx):
    pad_range = (max(c1["high"], c2["high"]) - min(c1["low"], c2["low"])) * 0.1 or 0.0001
    min_low = min(c1["low"], c2["low"]) - pad_range
    max_high = max(c1["high"], c2["high"]) + pad_range

    def y(p):
        return round(price_to_y(p, min_low, max_high), 1)

    c1_x, c2_x = CHART_W * 0.30, CHART_W * 0.72
    body_w = 26

    def candle_svg(x, o, h, l, c, delay, dim=False):
        color = "#3fe074" if c >= o else "#ff5c5c"
        glow = "candle-glow-buy" if c >= o else "candle-glow-sell"
        opacity = "0.5" if dim else "1"
        top = min(o, c)
        bottom = max(o, c)
        body_y = y(bottom)
        body_h = max(y(top) - y(bottom), 2)
        return f"""
          <g class="draw-in {glow}" style="animation-delay:{delay}ms">
            <line x1="{x}" y1="{y(h)}" x2="{x}" y2="{y(l)}" stroke="{color}" stroke-width="2" opacity="{opacity}"/>
            <rect x="{x - body_w/2}" y="{body_y}" width="{body_w}" height="{body_h}" rx="2" fill="{color}" opacity="{opacity}"/>
          </g>
        """

    c1_high_y, c1_low_y = y(c1["high"]), y(c1["low"])
    ref_lines = f"""
      <line x1="4" y1="{c1_high_y}" x2="{CHART_W-4}" y2="{c1_high_y}" stroke="#4a5568" stroke-width="1" stroke-dasharray="3,3"/>
      <line x1="4" y1="{c1_low_y}" x2="{CHART_W-4}" y2="{c1_low_y}" stroke="#4a5568" stroke-width="1" stroke-dasharray="3,3"/>
    """

    sweep_color = {"BUY": "#3fe074", "SELL": "#ff5c5c", "AVOID": "#8b949e"}[bias]
    base_delay = idx * 90

    svg = f"""
    <svg width="{CHART_W}" height="{CHART_H}" viewBox="0 0 {CHART_W} {CHART_H}" class="mini-chart">
      {ref_lines}
      {candle_svg(c1_x, c1["open"] if "open" in c1 else (c1["high"]+c1["low"])/2, c1["high"], c1["low"], c1.get("close", (c1["high"]+c1["low"])/2), base_delay, dim=True)}
      {candle_svg(c2_x, c2["open"], c2["high"], c2["low"], c2["close"], base_delay + 150)}
      <circle cx="{c2_x}" cy="{y(c2['close'])}" r="4" fill="{sweep_color}" class="pulse-dot" style="animation-delay:{base_delay+300}ms"/>
      <text x="{c1_x}" y="{CHART_H - 2}" font-size="9" fill="#8b949e" text-anchor="middle">C1</text>
      <text x="{c2_x}" y="{CHART_H - 2}" font-size="9" fill="#e6edf3" text-anchor="middle">C2</text>
    </svg>
    """
    return svg


def render_trader_scene(bias, idx):
    """Bigger bird's-eye-view SVG: a person seen from above, sitting at a desk,
    monitor screen glowing BUY/SELL/AVOID."""
    color = {"BUY": "#3fe074", "SELL": "#ff5c5c", "AVOID": "#8b949e"}[bias]
    delay = idx * 90

    if bias == "BUY":
        icon = '<polygon points="110,34 85,60 135,60" fill="{c}"/>'.format(c=color)
    elif bias == "SELL":
        icon = '<polygon points="110,60 85,34 135,34" fill="{c}"/>'.format(c=color)
    else:
        icon = '<rect x="85" y="44" width="50" height="6" rx="3" fill="{c}"/>'.format(c=color)

    return f"""
    <svg width="100%" height="auto" viewBox="0 0 220 170" class="trader-scene" style="animation-delay:{delay}ms">
      <!-- desk, viewed from directly above -->
      <rect x="8" y="8" width="204" height="154" rx="12" fill="#1b2130" stroke="#2a3142" stroke-width="2"/>

      <!-- coffee mug -->
      <circle cx="30" cy="30" r="11" fill="#2a3142"/>
      <circle cx="30" cy="30" r="7" fill="#171c28"/>
      <rect x="39" y="27" width="7" height="6" rx="3" fill="#2a3142"/>

      <!-- small plant -->
      <circle cx="192" cy="28" r="12" fill="#232a3a"/>
      <circle cx="187" cy="22" r="6" fill="#3fa15f"/>
      <circle cx="196" cy="20" r="6" fill="#2f8a4e"/>
      <circle cx="197" cy="30" r="6" fill="#3fa15f"/>

      <!-- monitor -->
      <rect x="70" y="18" width="80" height="56" rx="7" fill="#11151f" stroke="#2a3142" stroke-width="3"/>
      <rect x="78" y="27" width="64" height="40" rx="3" fill="#0a0d14" stroke="{color}" stroke-width="2"
            class="screen" style="--glow:{color}"/>
      {icon}
      <rect x="102" y="76" width="16" height="7" rx="2" fill="#2a3142"/>

      <!-- keyboard -->
      <rect x="76" y="92" width="68" height="22" rx="4" fill="#232a3a" stroke="#2a3142" stroke-width="1.5"/>
      <rect x="82" y="97" width="56" height="3" rx="1.5" fill="#333c50"/>
      <rect x="82" y="103" width="56" height="3" rx="1.5" fill="#333c50"/>

      <!-- mouse pad + mouse -->
      <rect x="150" y="88" width="30" height="40" rx="7" fill="#1b2130" stroke="#2a3142" stroke-width="1.5"/>
      <ellipse cx="165" cy="104" rx="8" ry="13" fill="#2a3142" stroke="#333c50" stroke-width="1.5"/>

      <!-- chair back, seen from above as a ring behind the person -->
      <ellipse cx="110" cy="138" rx="42" ry="36" fill="#171c28"/>

      <g class="person">
        <!-- shoulders / torso -->
        <ellipse cx="110" cy="132" rx="32" ry="26" fill="#8b96a8"/>

        <!-- arms reaching forward to the keyboard -->
        <path d="M86,120 Q74,104 84,96" stroke="#8b96a8" stroke-width="12" fill="none"
              stroke-linecap="round" class="hand"/>
        <path d="M134,120 Q146,104 136,96" stroke="#8b96a8" stroke-width="12" fill="none"
              stroke-linecap="round" class="hand" style="animation-delay:0.25s"/>
        <circle cx="84" cy="96" r="7" fill="#cdd5e0" class="hand"/>
        <circle cx="136" cy="96" r="7" fill="#cdd5e0" class="hand" style="animation-delay:0.25s"/>

        <!-- head + headphones -->
        <path d="M91,113 a19,12 0 0,1 38,0" fill="none" stroke="#2a3142" stroke-width="4"/>
        <circle cx="91" cy="115" r="6" fill="#2a3142"/>
        <circle cx="129" cy="115" r="6" fill="#2a3142"/>
        <circle cx="110" cy="112" r="19" fill="#cdd5e0"/>
        <path d="M94,102 a16,13 0 0,1 32,0" fill="none" stroke="#b7c0cf" stroke-width="3"/>
      </g>
    </svg>
    """


def render_html(data, rows):
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    counts = {"BUY": 0, "SELL": 0, "AVOID": 0}
    for r in rows:
        counts[r["bias"]] += 1

    cards = ""
    for i, r in enumerate(rows):
        cls = BADGE_CLASS[r["bias"]]
        c1, c2 = r["c1"], r["c2"]
        chart = render_mini_chart(c1, c2, r["bias"], i)
        trader = render_trader_scene(r["bias"], i)
        flag = FLAGS.get(r["pair"], "")
        delay = i * 90

        events = r.get("events", [])
        event_badge = ""
        if events:
            highest_high = any(e["impact"] == "High" for e in events)
            badge_cls = "high" if highest_high else "medium"
            tooltip_rows = "".join(
                f'<div class="event-row {e["impact"].lower()}">'
                f'<span class="event-time">{html.escape(e["time"])}</span>'
                f'<span class="event-ccy">{html.escape(e["country"])}</span>'
                f'<span class="event-name">{html.escape(e["title"])}</span>'
                f'</div>'
                for e in events
            )
            event_badge = (
                f'<span class="event-badge-wrap">'
                f'<span class="event-badge {badge_cls}">📅 {len(events)}</span>'
                f'<div class="event-tooltip">{tooltip_rows}</div>'
                f'</span>'
            )

        cards += f"""
        <div class="card {cls}" data-bias="{r['bias']}" style="animation-delay:{delay}ms">
          <div class="scan-sweep"></div>
          <div class="card-header">
            <span class="pair">{flag} {r['pair']}</span>
            <div class="header-right">
              {event_badge}
              <span class="badge {cls}"><span class="badge-dot"></span>{r['bias']}</span>
            </div>
          </div>
          <div class="reason">{r['reason']}</div>
          <div class="trader-wrap">{trader}</div>
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
<title>Daily Bias Agent</title>
<style>
  :root {{
    --bg: #05070d;
    --card-bg: rgba(22, 27, 38, 0.65);
    --border: #262c3b;
    --text: #e6edf3;
    --muted: #8b949e;
    --buy: #3fe074;
    --sell: #ff5c5c;
    --avoid: #8b949e;
    --accent: #5b8cff;
  }}
  * {{ box-sizing: border-box; }}

  body {{
    margin: 0;
    padding: 40px;
    min-height: 100vh;
    background:
      radial-gradient(circle at 15% 10%, rgba(91,140,255,0.12), transparent 40%),
      radial-gradient(circle at 85% 0%, rgba(63,224,116,0.08), transparent 35%),
      linear-gradient(180deg, #05070d 0%, #0a0e18 100%);
    background-attachment: fixed;
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    position: relative;
    overflow-x: hidden;
  }}

  /* animated grid background */
  body::before {{
    content: "";
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(91,140,255,0.05) 1px, transparent 1px),
      linear-gradient(90deg, rgba(91,140,255,0.05) 1px, transparent 1px);
    background-size: 42px 42px;
    mask-image: radial-gradient(ellipse 80% 60% at 50% 0%, black 40%, transparent 90%);
    animation: drift 30s linear infinite;
    pointer-events: none;
    z-index: 0;
  }}
  @keyframes drift {{
    from {{ background-position: 0 0, 0 0; }}
    to {{ background-position: 42px 42px, 42px 42px; }}
  }}

  .content {{ position: relative; z-index: 1; max-width: 1280px; margin: 0 auto; }}

  header {{ display: flex; align-items: center; gap: 14px; margin-bottom: 4px; }}
  .agent-avatar {{
    width: 40px; height: 40px; border-radius: 10px;
    background: linear-gradient(135deg, var(--accent), #8b5bff);
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
    box-shadow: 0 0 22px rgba(91,140,255,0.5);
    animation: avatar-pulse 2.4s ease-in-out infinite;
  }}
  @keyframes avatar-pulse {{
    0%, 100% {{ box-shadow: 0 0 14px rgba(91,140,255,0.4); }}
    50% {{ box-shadow: 0 0 28px rgba(91,140,255,0.75); }}
  }}
  h1 {{ font-size: 24px; margin: 0; letter-spacing: 0.3px; }}
  .live-badge {{
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 11px; font-weight: 700; letter-spacing: 1px;
    color: var(--buy); background: rgba(63,224,116,0.1);
    border: 1px solid rgba(63,224,116,0.3);
    padding: 3px 10px; border-radius: 999px; margin-left: 10px;
  }}
  .live-dot {{
    width: 6px; height: 6px; border-radius: 50%; background: var(--buy);
    animation: blink 1.4s ease-in-out infinite;
  }}
  @keyframes blink {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.25; }} }}

  .subtitle {{ color: var(--muted); font-size: 13px; margin: 6px 0 24px 54px; }}

  .summary-bar {{
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 24px;
    padding: 14px 18px;
    background: var(--card-bg);
    backdrop-filter: blur(12px);
    border: 1px solid var(--border);
    border-radius: 10px;
  }}
  .summary-counts {{ display: flex; gap: 18px; font-size: 13px; margin-right: auto; }}
  .summary-counts span.count-buy {{ color: var(--buy); font-weight: 700; }}
  .summary-counts span.count-sell {{ color: var(--sell); font-weight: 700; }}
  .summary-counts span.count-avoid {{ color: var(--avoid); font-weight: 700; }}
  .filter-btn {{
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 6px 14px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }}
  .filter-btn:hover {{ background: rgba(255,255,255,0.08); transform: translateY(-1px); }}
  .filter-btn.active {{ background: var(--accent); border-color: var(--accent); box-shadow: 0 0 14px rgba(91,140,255,0.4); }}

  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 16px;
    margin-bottom: 28px;
  }}
  .card {{
    position: relative;
    overflow: hidden;
    background: var(--card-bg);
    backdrop-filter: blur(12px);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
    opacity: 0;
    transform: translateY(14px);
    animation: card-in 0.5s ease forwards;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }}
  .card:hover {{ transform: translateY(-3px); }}
  @keyframes card-in {{ to {{ opacity: 1; transform: translateY(0); }} }}
  .card.buy {{ box-shadow: inset 3px 0 0 var(--buy), 0 0 0 1px rgba(63,224,116,0.08); }}
  .card.sell {{ box-shadow: inset 3px 0 0 var(--sell), 0 0 0 1px rgba(255,92,92,0.08); }}
  .card.avoid {{ box-shadow: inset 3px 0 0 var(--avoid); }}
  .card.buy:hover {{ box-shadow: inset 3px 0 0 var(--buy), 0 0 24px rgba(63,224,116,0.18); }}
  .card.sell:hover {{ box-shadow: inset 3px 0 0 var(--sell), 0 0 24px rgba(255,92,92,0.18); }}
  .card.hidden {{ display: none; }}

  .scan-sweep {{
    position: absolute; top: 0; left: -40%;
    width: 40%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent);
    animation: sweep 5s ease-in-out infinite;
    pointer-events: none;
  }}
  @keyframes sweep {{ 0% {{ left: -40%; }} 60%, 100% {{ left: 120%; }} }}

  .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
  .header-right {{ display: flex; align-items: center; gap: 8px; }}
  .pair {{ font-size: 16px; font-weight: 600; letter-spacing: 0.3px; }}
  .event-badge-wrap {{ position: relative; display: inline-flex; }}
  .event-badge {{
    font-size: 11px; font-weight: 700; cursor: default;
    padding: 3px 8px; border-radius: 999px;
    display: inline-flex; align-items: center; gap: 3px;
    border: 1px solid currentColor;
  }}
  .event-badge.high {{ color: var(--sell); background: rgba(255,92,92,0.1); animation: badge-pulse 1.6s ease-in-out infinite; }}
  .event-badge.medium {{ color: #f5a623; background: rgba(245,166,35,0.1); }}
  @keyframes badge-pulse {{ 0%,100% {{ box-shadow: 0 0 0 rgba(255,92,92,0); }} 50% {{ box-shadow: 0 0 8px rgba(255,92,92,0.5); }} }}
  .event-tooltip {{
    position: absolute; top: calc(100% + 8px); right: -8px; z-index: 30;
    background: rgba(12,12,20,0.98); border: 1px solid rgba(255,255,255,0.15);
    border-radius: 10px; padding: 8px 10px; min-width: 220px;
    opacity: 0; visibility: hidden; transform: translateY(-4px);
    transition: opacity .15s ease, transform .15s ease, visibility .15s;
    box-shadow: 0 12px 32px rgba(0,0,0,0.5);
  }}
  .event-badge-wrap:hover .event-tooltip {{ opacity: 1; visibility: visible; transform: translateY(0); }}
  .event-row {{
    display: flex; gap: 8px; align-items: baseline;
    font-size: 11px; padding: 3px 0; white-space: nowrap;
    border-bottom: 1px solid rgba(255,255,255,0.06);
  }}
  .event-row:last-child {{ border-bottom: none; }}
  .event-time {{ color: var(--muted); width: 54px; flex-shrink: 0; }}
  .event-ccy {{ font-weight: 700; width: 34px; flex-shrink: 0; }}
  .event-row.high .event-ccy {{ color: var(--sell); }}
  .event-row.medium .event-ccy {{ color: #f5a623; }}
  .event-name {{ color: #e8e8f0; overflow: hidden; text-overflow: ellipsis; }}
  .badge {{
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 999px;
    letter-spacing: 0.5px;
  }}
  .badge-dot {{ width: 5px; height: 5px; border-radius: 50%; background: currentColor; }}
  .badge.buy {{ background: rgba(63,224,116,0.12); color: var(--buy); }}
  .badge.sell {{ background: rgba(255,92,92,0.12); color: var(--sell); }}
  .badge.avoid {{ background: rgba(139,148,158,0.12); color: var(--avoid); }}
  .reason {{ color: var(--muted); font-size: 12.5px; margin-bottom: 10px; min-height: 34px; line-height: 1.4; }}

  .mini-chart {{
    width: 100%; height: auto;
    background: rgba(5,7,13,0.6);
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 12px;
  }}
  .draw-in {{ opacity: 0; animation: fade-in 0.4s ease forwards; }}
  @keyframes fade-in {{ to {{ opacity: 1; }} }}
  .pulse-dot {{ opacity: 0; animation: dot-in 0.3s ease forwards, dot-pulse 2s ease-in-out infinite 0.6s; }}
  @keyframes dot-in {{ to {{ opacity: 1; }} }}
  @keyframes dot-pulse {{ 0%,100% {{ r: 4; opacity: 1; }} 50% {{ r: 6; opacity: 0.5; }} }}

  .candles {{
    display: flex; flex-direction: column; gap: 6px;
    font-size: 11.5px; color: var(--muted);
    border-top: 1px solid var(--border);
    padding-top: 10px;
  }}
  .candle {{ display: flex; gap: 10px; }}
  .candle .label {{ min-width: 90px; color: var(--text); font-weight: 500; }}

  /* trader-at-desk scene */
  .trader-wrap {{
    background: rgba(5,7,13,0.5);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 8px 6px 4px;
    margin-bottom: 12px;
  }}
  .trader-scene {{
    display: block;
    width: 60%;
    margin: 0 auto;
    opacity: 0;
    animation: card-in 0.5s ease forwards;
  }}
  .person {{ animation: idle-bob 2.6s ease-in-out infinite; transform-origin: center; }}
  @keyframes idle-bob {{ 0%, 100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-1.5px); }} }}
  .hand {{ animation: type-hand 0.5s ease-in-out infinite; transform-origin: left center; }}
  @keyframes type-hand {{ 0%, 100% {{ transform: translateY(0); }} 50% {{ transform: translateY(1.5px); }} }}
  .screen {{
    filter: drop-shadow(0 0 5px var(--glow)) drop-shadow(0 0 10px var(--glow));
    animation: screen-flicker 2.8s ease-in-out infinite;
  }}
  @keyframes screen-flicker {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.82; }} }}

  footer {{ margin-top: 24px; color: var(--muted); font-size: 11.5px; text-align: center; }}
</style>
</head>
<body>
<div class="content">

  <header>
    <div class="agent-avatar">🤖</div>
    <h1>Daily Bias Agent</h1>
    <span class="live-badge"><span class="live-dot"></span>LIVE</span>
  </header>
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

</div>

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
