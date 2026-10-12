"""
Standalone visual demo of the 4H "sweep + engulf" entry rule, using
dummy XAUUSD (gold) numbers. Generates entry_demo.html.

Rule (per voice note):
  Daily bias bullish -> wait for a 4H candle to sweep BELOW the previous
  4H candle's low, then close back up engulfing the PREVIOUS candle's
  full body (close above prior open, open below prior close).
  Entry = close of that candle. Stop = the swept low (- 1 pip).
  Mirror logic for bearish daily bias (sweep high, engulf down, stop = swept high + 1 pip).
  If a candle sweeps but fails to fully engulf the prior body -> AVOID, wait.
"""

PIP = 0.01  # XAUUSD pip size


def is_bull_engulf_sweep(c1, c2):
    swept = c2["low"] < c1["low"]
    bullish = c2["close"] > c2["open"]
    engulfs = c2["open"] <= c1["close"] and c2["close"] >= c1["open"]
    return swept and bullish and engulfs


def is_bear_engulf_sweep(c1, c2):
    swept = c2["high"] > c1["high"]
    bearish = c2["close"] < c2["open"]
    engulfs = c2["open"] >= c1["close"] and c2["close"] <= c1["open"]
    return swept and bearish and engulfs


def is_bull_sweep_close_beyond(c1, c2):
    """Relaxed rule: sweep the low, close back above C1's open. Doesn't
    require C2's open to also be below C1's close (no full body engulf)."""
    swept = c2["low"] < c1["low"]
    bullish = c2["close"] > c2["open"]
    close_beyond = c2["close"] > c1["open"]
    return swept and bullish and close_beyond


def is_bear_sweep_close_beyond(c1, c2):
    swept = c2["high"] > c1["high"]
    bearish = c2["close"] < c2["open"]
    close_beyond = c2["close"] < c1["open"]
    return swept and bearish and close_beyond


EXAMPLES = [
    {
        "label": "BUY",
        "sub": "full engulf",
        "bias": "Daily bias: BULLISH",
        "color": "#22c55e",
        "c1": {"open": 4190, "high": 4195, "low": 4180, "close": 4183},
        "c2": {"open": 4177, "high": 4200, "low": 4172, "close": 4198},
        "note": "C2 sweeps below C1's low (4180 \u2192 4172), then closes at 4198 \u2014 "
                "fully engulfing C1's body (opens below C1 close 4183, closes above C1 open 4190). "
                "Entry = 4198 (close). Stop = 4171.99 (swept low \u2212 1 pip).",
    },
    {
        "label": "BUY",
        "sub": "partial engulf \u2014 still valid",
        "bias": "Daily bias: BULLISH",
        "color": "#22c55e",
        "c1": {"open": 4190, "high": 4195, "low": 4180, "close": 4188},
        "c2": {"open": 4189, "high": 4196, "low": 4174, "close": 4193},
        "note": "C2 sweeps below C1's low (4180 \u2192 4174), then closes at 4193 \u2014 above "
                "C1's open (4190), so it's a valid entry even though C2's open (4189) is "
                "ABOVE C1's close (4188), meaning the body is NOT fully engulfed. "
                "Close beyond the prior open is enough. Entry = 4193. Stop = 4173.99.",
    },
    {
        "label": "SELL",
        "sub": "partial engulf \u2014 still valid",
        "bias": "Daily bias: BEARISH",
        "color": "#ef4444",
        "c1": {"open": 4205, "high": 4212, "low": 4200, "close": 4207},
        "c2": {"open": 4203, "high": 4219, "low": 4197, "close": 4198},
        "note": "C2 sweeps above C1's high (4212 \u2192 4219), then closes at 4198 \u2014 below "
                "C1's open (4205), so it's a valid entry even though C2's open (4203) is "
                "BELOW C1's close (4207), meaning the body is NOT fully engulfed. "
                "Entry = 4198. Stop = 4219.01.",
    },
    {
        "label": "AVOID",
        "sub": "no reclaim past prior open",
        "bias": "Daily bias: BULLISH",
        "color": "#9ca3af",
        "c1": {"open": 4190, "high": 4196, "low": 4182, "close": 4193},
        "c2": {"open": 4183, "high": 4188, "low": 4178, "close": 4186},
        "note": "C2 sweeps below C1's low (4182 \u2192 4178) but only closes at 4186 \u2014 "
                "it never reclaims back above C1's open (4190) at all. "
                "No entry \u2014 wait for the next 4H candle.",
    },
]


def candle_svg(x, candle, y_of, color_override=None):
    o, h, l, c = candle["open"], candle["high"], candle["low"], candle["close"]
    bullish = c >= o
    color = color_override or ("#22c55e" if bullish else "#ef4444")
    width = 56
    wick_x = x + width / 2
    top = y_of(max(o, c))
    bottom = y_of(min(o, c))
    body_h = max(bottom - top, 3)
    return f'''
    <line x1="{wick_x}" y1="{y_of(h)}" x2="{wick_x}" y2="{y_of(l)}" stroke="{color}" stroke-width="2.5"/>
    <rect x="{x}" y="{top}" width="{width}" height="{body_h}" fill="{color}" fill-opacity="0.85" stroke="{color}" stroke-width="1.5" rx="2"/>
    '''


def dashed_line(y, label, color, svg_width, label_x=8, dash="6,4"):
    return f'''
    <line x1="0" y1="{y}" x2="{svg_width}" y2="{y}" stroke="{color}" stroke-width="1.3" stroke-dasharray="{dash}" opacity="0.8"/>
    <text x="{label_x}" y="{y - 5}" fill="{color}" font-size="11" font-family="monospace">{label}</text>
    '''


def render_example(ex):
    c1, c2 = ex["c1"], ex["c2"]
    prices = [c1["high"], c1["low"], c2["high"], c2["low"]]
    pad = 4
    pmin, pmax = min(prices) - pad, max(prices) + pad
    svg_h, svg_w = 260, 300
    top_margin, bottom_margin = 20, 30
    plot_h = svg_h - top_margin - bottom_margin

    def y_of(price):
        return svg_h - bottom_margin - (price - pmin) / (pmax - pmin) * plot_h

    is_buy = ex["label"] == "BUY"
    is_sell = ex["label"] == "SELL"

    svg = f'<svg viewBox="0 0 {svg_w} {svg_h}" width="100%" height="260">'

    # swept level line (C1 low for buy/avoid, C1 high for sell)
    if is_sell:
        swept_price = c1["high"]
        svg += dashed_line(y_of(swept_price), f"swept high {swept_price}", "#facc15", svg_w)
    else:
        swept_price = c1["low"]
        svg += dashed_line(y_of(swept_price), f"swept low {swept_price}", "#facc15", svg_w)

    # engulf reference line: the C1 open price (threshold C2 must close beyond)
    svg += dashed_line(y_of(c1["open"]), f"C1 open {c1['open']}", "#6b7280", svg_w, dash="2,4")

    # candles
    svg += candle_svg(40, c1, y_of)
    svg += candle_svg(170, c2, y_of)

    svg += f'<text x="62" y="{svg_h - 8}" fill="#9ca3af" font-size="12" text-anchor="middle" font-family="monospace">C1</text>'
    svg += f'<text x="198" y="{svg_h - 8}" fill="#9ca3af" font-size="12" text-anchor="middle" font-family="monospace">C2</text>'

    # entry / stop lines for BUY / SELL only
    if is_buy:
        svg += dashed_line(y_of(c2["close"]), f"entry {c2['close']}", "#22c55e", svg_w)
        stop = round(c2["low"] - PIP, 2)
        svg += dashed_line(y_of(stop), f"stop {stop}", "#ef4444", svg_w)
    elif is_sell:
        svg += dashed_line(y_of(c2["close"]), f"entry {c2['close']}", "#22c55e", svg_w)
        stop = round(c2["high"] + PIP, 2)
        svg += dashed_line(y_of(stop), f"stop {stop}", "#ef4444", svg_w)

    svg += "</svg>"
    return svg


def render_card(ex):
    svg = render_example(ex)
    return f'''
    <div class="card" style="--accent: {ex['color']}">
      <div class="card-head">
        <span class="badge" style="background:{ex['color']}22;color:{ex['color']};border:1px solid {ex['color']}66">{ex['label']}</span>
        <span class="bias-tag">{ex['bias']}</span>
      </div>
      <p class="sub-tag">{ex['sub']}</p>
      <div class="chart">{svg}</div>
      <p class="note">{ex['note']}</p>
    </div>
    '''


def render_html():
    cards = "\n".join(render_card(ex) for ex in EXAMPLES)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>4H Entry Logic Demo \u2014 Sweep &amp; Engulf</title>
<style>
  body {{
    margin: 0; padding: 40px 24px; min-height: 100vh;
    background: radial-gradient(circle at 20% 10%, #15202b, #0b0f14 60%);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    color: #e5e7eb;
  }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  .sub {{ color: #9ca3af; font-size: 14px; margin: 0 0 28px; max-width: 760px; line-height: 1.5; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; max-width: 1000px; }}
  .card {{
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 16px;
    box-shadow: 0 0 0 1px rgba(255,255,255,0.02), 0 8px 24px rgba(0,0,0,0.3);
  }}
  .card-head {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }}
  .badge {{ font-size: 12px; font-weight: 700; letter-spacing: 0.04em; padding: 3px 10px; border-radius: 999px; }}
  .bias-tag {{ font-size: 11px; color: #9ca3af; }}
  .sub-tag {{ font-size: 11px; color: #6b7280; margin: 0 0 6px; font-style: italic; }}
  .chart {{ margin: 8px 0; }}
  .note {{ font-size: 12.5px; color: #cbd5e1; line-height: 1.5; margin: 8px 0 0; }}
</style>
</head>
<body>
  <h1>4H Entry Logic \u2014 Sweep &amp; Engulf (XAUUSD, dummy numbers)</h1>
  <p class="sub">
    Wait for the 4H candle to sweep beyond the <em>previous</em> 4H candle's wick, then close back
    in the direction of daily bias while fully engulfing the previous candle's body.
    That close is the entry; the swept wick (\u00b1 1 pip) is the stop loss. If price sweeps but
    doesn't fully reclaim past the prior candle's open, there's no valid entry yet \u2014 wait.
  </p>
  <div class="grid">
    {cards}
  </div>
</body>
</html>'''


if __name__ == "__main__":
    # sanity check the rule functions against the examples
    for ex in EXAMPLES:
        c1, c2 = ex["c1"], ex["c2"]
        print(ex["label"], ex["sub"],
              "| full_engulf(bull/bear)=", is_bull_engulf_sweep(c1, c2), is_bear_engulf_sweep(c1, c2),
              "| close_beyond(bull/bear)=", is_bull_sweep_close_beyond(c1, c2), is_bear_sweep_close_beyond(c1, c2))

    with open("entry_demo.html", "w") as f:
        f.write(render_html())
    print("wrote entry_demo.html")
