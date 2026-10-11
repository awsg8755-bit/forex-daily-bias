"""
Daily Bias Engine

Implements the locked daily-bias ruleset:
- Daily candle = 7:00am -> 7:00am Brisbane time (AEST, UTC+10)
- Candle 1 = older of the 2 most recently closed daily candles
- Candle 2 = newer (most recently closed) daily candle
- "Sweep" = wick pierces through the level (even by a small margin)

Rules:
1. Sweep low  + close back ABOVE the low            -> BUY  (reversal)
2. Sweep high + close ABOVE the high too             -> BUY  (continuation)
3. Sweep high + close back BELOW the high            -> SELL (reversal)
4. Sweep low  + close BELOW the low too              -> SELL (continuation)
5. No sweep of either level (inside bar)             -> AVOID
6. Sweep both high and low, closes in the middle     -> AVOID
"""

BUY = "BUY"
SELL = "SELL"
AVOID = "AVOID"


def calculate_bias(candle1: dict, candle2: dict) -> str:
    """
    candle1: {"high": float, "low": float}                    (older candle)
    candle2: {"high": float, "low": float, "close": float}    (newer/most recent candle)

    Returns "BUY", "SELL", or "AVOID".
    """
    c1_high, c1_low = candle1["high"], candle1["low"]
    c2_high, c2_low, c2_close = candle2["high"], candle2["low"], candle2["close"]

    swept_high = c2_high > c1_high
    swept_low = c2_low < c1_low

    if swept_high and swept_low:
        # Outside bar - direction decided by where it closed
        if c2_close > c1_high:
            return BUY
        elif c2_close < c1_low:
            return SELL
        else:
            return AVOID  # Rule 6: closed in the middle
    elif swept_high:
        return BUY if c2_close > c1_high else SELL  # Rule 2 / Rule 3
    elif swept_low:
        return SELL if c2_close < c1_low else BUY  # Rule 4 / Rule 1
    else:
        return AVOID  # Rule 5: inside bar, no sweep


def bias_reason(candle1: dict, candle2: dict) -> str:
    """Short human-readable explanation of why a bias was reached."""
    c1_high, c1_low = candle1["high"], candle1["low"]
    c2_high, c2_low, c2_close = candle2["high"], candle2["low"], candle2["close"]

    swept_high = c2_high > c1_high
    swept_low = c2_low < c1_low

    if swept_high and swept_low:
        if c2_close > c1_high:
            return "Swept both sides, closed above prior high (outside bar breakout up)"
        elif c2_close < c1_low:
            return "Swept both sides, closed below prior low (outside bar breakout down)"
        else:
            return "Swept both sides, closed inside prior range (no clear direction)"
    elif swept_high:
        if c2_close > c1_high:
            return "Swept prior high and closed above it (confirmed breakout)"
        else:
            return "Swept prior high but closed back below it (failed breakout / reversal)"
    elif swept_low:
        if c2_close < c1_low:
            return "Swept prior low and closed below it (confirmed breakdown)"
        else:
            return "Swept prior low but closed back above it (failed breakdown / reversal)"
    else:
        return "No sweep of prior high or low (inside bar)"
