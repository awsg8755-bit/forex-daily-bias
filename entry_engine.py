"""
4H Entry Engine

Scans the current trading day's 4H candles for a valid entry in the
direction of the daily bias.

Rule (sweep + close beyond prior open):
  - Daily bias BULLISH -> wait for a 4H candle (C2) to sweep BELOW the
    previous 4H candle's (C1) low, then close bullish AND beyond C1's
    open. C2 does NOT need to fully engulf C1's body (C2's open can be
    above C1's close) - only the close has to reclaim past C1's open.
  - Daily bias BEARISH -> mirror: C2 sweeps above C1's high, closes
    bearish and beyond C1's open.
  - If price sweeps but the close doesn't reclaim past C1's open -> no
    entry yet, wait for the next 4H candle.

- 4H candle boundaries (Brisbane, AEST UTC+10): 7am, 11am, 3pm, 7pm, 11pm, 3am
- Entries only considered within the 7am-7pm window (candle pairs:
  7am->11am, 11am->3pm, 3pm->7pm). Anything from 7pm/11pm/3am onward is
  outside the tradeable window.
- Stop loss: 1 pip beyond the swept level of the entry candle
  (below the swept low for BUY, above the swept high for SELL).
"""

from bias_engine import BUY, SELL

# 4H candle times (Brisbane). Only candles up to and including 19:00 (7pm)
# are inside the tradeable entry window.
ENTRY_WINDOW_TIMES = ["07:00", "11:00", "15:00", "19:00"]

PIP_SIZE = {
    "EURUSD": 0.0001,
    "GBPUSD": 0.0001,
    "EURGBP": 0.0001,
    "USDJPY": 0.01,
    "GBPJPY": 0.01,
    "AUDJPY": 0.01,
    "XAUUSD": 0.01,
}


def is_bull_sweep(c1: dict, c2: dict) -> bool:
    swept = c2["low"] < c1["low"]
    bullish = c2["close"] > c2["open"]
    close_beyond = c2["close"] > c1["open"]
    return swept and bullish and close_beyond


def is_bear_sweep(c1: dict, c2: dict) -> bool:
    swept = c2["high"] > c1["high"]
    bearish = c2["close"] < c2["open"]
    close_beyond = c2["close"] < c1["open"]
    return swept and bearish and close_beyond


def entry_signal(c1: dict, c2: dict):
    if is_bull_sweep(c1, c2):
        return BUY
    if is_bear_sweep(c1, c2):
        return SELL
    return None


def entry_reason(c1: dict, c2: dict, direction: str) -> str:
    if direction == BUY:
        return (f"Swept below prior low ({c1['low']} \u2192 {c2['low']}), "
                f"closed at {c2['close']} \u2014 beyond prior open ({c1['open']})")
    elif direction == SELL:
        return (f"Swept above prior high ({c1['high']} \u2192 {c2['high']}), "
                f"closed at {c2['close']} \u2014 beyond prior open ({c1['open']})")
    raise ValueError(f"No reason for direction: {direction}")


def stop_loss(pair: str, direction: str, entry_candle: dict) -> float:
    """
    1 pip beyond the swept level of the entry candle.
    direction: "BUY" or "SELL"
    entry_candle: {"high": float, "low": float}
    """
    pip = PIP_SIZE[pair]
    if direction == BUY:
        return round(entry_candle["low"] - pip, 5)
    elif direction == SELL:
        return round(entry_candle["high"] + pip, 5)
    raise ValueError(f"No stop loss for direction: {direction}")


def find_entries(daily_bias: str, candles_4h: list, pair: str) -> list:
    """
    daily_bias: "BUY", "SELL", or "AVOID" (from bias_engine.calculate_bias)
    candles_4h: list of {"time": "07:00", "open": float, "high": float,
                "low": float, "close": float} in chronological order,
                covering today's 7am-7pm window (and optionally
                earlier/later candles - only in-window consecutive
                pairs are checked)
    pair: e.g. "EURUSD" (needed for pip size on the stop loss)

    Returns a list of valid entries (daily bias AVOID -> always empty):
      {"time": entry candle's time, "entry_price": close, "stop_loss": float,
       "direction": "BUY"/"SELL", "reason": str}
    """
    if daily_bias not in (BUY, SELL):
        return []

    entries = []
    for i in range(1, len(candles_4h)):
        c1, c2 = candles_4h[i - 1], candles_4h[i]

        # Both candles of the pair must fall within the tradeable window.
        if c1["time"] not in ENTRY_WINDOW_TIMES or c2["time"] not in ENTRY_WINDOW_TIMES:
            continue

        signal = entry_signal(c1, c2)
        if signal != daily_bias:
            continue

        entries.append({
            "time": c2["time"],
            "entry_price": c2["close"],
            "stop_loss": stop_loss(pair, signal, c2),
            "direction": signal,
            "reason": entry_reason(c1, c2, signal),
        })

    return entries


if __name__ == "__main__":
    # Daily bias BUY, 4H candles with a sweep-low + close-beyond-prior-open
    # (partial engulf) on the 11am->3pm pair - should produce one valid entry.
    daily_bias = BUY
    candles_4h = [
        {"time": "07:00", "open": 4200, "high": 4205, "low": 4195, "close": 4198},
        {"time": "11:00", "open": 4190, "high": 4195, "low": 4180, "close": 4188},  # C1
        {"time": "15:00", "open": 4189, "high": 4196, "low": 4174, "close": 4193},  # C2: sweeps 4180 low, closes above C1 open 4190
        {"time": "19:00", "open": 4193, "high": 4200, "low": 4190, "close": 4197},
    ]
    entries = find_entries(daily_bias, candles_4h, "XAUUSD")
    for e in entries:
        print(e)
