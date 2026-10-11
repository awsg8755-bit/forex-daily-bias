"""
Lot Size Calculator

Account: $500
Risk per trade: $10 total, split evenly across 3 positions (~$3.33 risk each)
Target per trade: $20 total, split evenly across 3 positions (~$6.67 target each)
All 3 positions opened at the same entry price and same stop price
(stop = the sweep wick, no buffer), so all 3 positions use the SAME lot size.

Pepperstone contract specs (standard, confirm against your actual platform specs):
- Forex pairs: 1.0 standard lot = 100,000 units of base currency
- XAUUSD: 1.0 standard lot = 100 troy ounces
- Minimum lot step: 0.01

Pip value depends on the quote (2nd) currency of the pair:
- Quote currency = USD (EURUSD, GBPUSD)   -> no conversion needed
- Quote currency = JPY (USDJPY, GBPJPY, AUDJPY) -> convert via USDJPY rate
- Quote currency = GBP (EURGBP)           -> convert via GBPUSD rate
- XAUUSD is quoted directly in USD        -> no conversion needed
"""

PAIR_SPECS = {
    "EURUSD": {"contract_size": 100_000, "quote_ccy": "USD"},
    "GBPUSD": {"contract_size": 100_000, "quote_ccy": "USD"},
    "USDJPY": {"contract_size": 100_000, "quote_ccy": "JPY"},
    "GBPJPY": {"contract_size": 100_000, "quote_ccy": "JPY"},
    "AUDJPY": {"contract_size": 100_000, "quote_ccy": "JPY"},
    "EURGBP": {"contract_size": 100_000, "quote_ccy": "GBP"},
    "XAUUSD": {"contract_size": 100, "quote_ccy": "USD"},
}

MIN_LOT = 0.01
LOT_STEP = 0.01
LEVERAGE = 30  # Pepperstone account leverage 1:30
ACCOUNT_BALANCE = 500.0

TOTAL_RISK_USD = 10.0
TOTAL_TARGET_USD = 20.0
NUM_POSITIONS = 3

RISK_PER_POSITION = TOTAL_RISK_USD / NUM_POSITIONS      # ~$3.33
TARGET_PER_POSITION = TOTAL_TARGET_USD / NUM_POSITIONS  # ~$6.67


def value_per_lot_usd(pair: str, price_distance: float, conversion_rate: float = None) -> float:
    """
    USD profit/loss for a 1.0 lot position if price moves `price_distance`
    (e.g. abs(entry - stop)).

    conversion_rate required for non-USD-quoted pairs:
    - JPY-quoted pairs: pass the current USDJPY rate
    - EURGBP: pass the current GBPUSD rate
    """
    spec = PAIR_SPECS[pair]
    raw_value = price_distance * spec["contract_size"]

    if spec["quote_ccy"] == "USD":
        return raw_value
    elif spec["quote_ccy"] == "JPY":
        if conversion_rate is None:
            raise ValueError(f"{pair}: need current USDJPY rate to convert JPY value to USD")
        return raw_value / conversion_rate
    elif spec["quote_ccy"] == "GBP":
        if conversion_rate is None:
            raise ValueError(f"{pair}: need current GBPUSD rate to convert GBP value to USD")
        return raw_value * conversion_rate
    else:
        raise ValueError(f"Unknown quote currency for {pair}")


def notional_value_usd(pair: str, price: float, lot_size: float, conversion_rate: float = None) -> float:
    """USD notional (position) value for a given lot size at the current price."""
    spec = PAIR_SPECS[pair]
    units = lot_size * spec["contract_size"]
    raw_value = units * price  # value in quote currency

    if spec["quote_ccy"] == "USD":
        return raw_value
    elif spec["quote_ccy"] == "JPY":
        if conversion_rate is None:
            raise ValueError(f"{pair}: need current USDJPY rate to convert notional to USD")
        return raw_value / conversion_rate
    elif spec["quote_ccy"] == "GBP":
        if conversion_rate is None:
            raise ValueError(f"{pair}: need current GBPUSD rate to convert notional to USD")
        return raw_value * conversion_rate
    else:
        raise ValueError(f"Unknown quote currency for {pair}")


def margin_required_usd(pair: str, price: float, lot_size: float, conversion_rate: float = None, leverage: float = LEVERAGE) -> float:
    """USD margin required to open a position of this lot size, at 1:leverage."""
    return notional_value_usd(pair, price, lot_size, conversion_rate) / leverage


def max_positions_at_lot_size(pair: str, price: float, lot_size: float, conversion_rate: float = None,
                               leverage: float = LEVERAGE, account_balance: float = ACCOUNT_BALANCE) -> dict:
    """
    How many positions of `lot_size` could be opened simultaneously on margin alone
    (ignores risk rules - pure margin-capacity question).
    """
    margin_per_position = margin_required_usd(pair, price, lot_size, conversion_rate, leverage)
    max_positions = int(account_balance // margin_per_position) if margin_per_position > 0 else 0
    return {
        "pair": pair,
        "lot_size": lot_size,
        "price": price,
        "leverage": f"1:{int(leverage)}",
        "margin_per_position_usd": round(margin_per_position, 2),
        "account_balance": account_balance,
        "max_positions_by_margin": max_positions,
        "margin_used_for_your_3_positions": round(margin_per_position * 3, 2),
        "free_margin_after_3_positions": round(account_balance - margin_per_position * 3, 2),
    }


def calculate_lot_size(pair: str, entry_price: float, stop_price: float, conversion_rate: float = None) -> dict:
    """
    Returns the lot size to use for EACH of the 3 positions, given the
    locked $10 total risk / 3 rule, plus how many pips/points of favorable
    move are needed to hit the $20 total target / 3 per position.
    """
    price_distance = abs(entry_price - stop_price)
    if price_distance == 0:
        raise ValueError("Entry and stop price can't be the same")

    per_lot_value = value_per_lot_usd(pair, price_distance, conversion_rate)

    raw_lot = RISK_PER_POSITION / per_lot_value
    lot_size = max(MIN_LOT, round(raw_lot / LOT_STEP) * LOT_STEP)
    lot_size = round(lot_size, 2)

    actual_risk_per_position = lot_size * per_lot_value
    actual_total_risk = actual_risk_per_position * NUM_POSITIONS

    # Price distance needed (per position) to hit the $20 total target / 3
    target_value_per_lot = value_per_lot_usd(pair, 1.0, conversion_rate)  # value per 1.0 lot per 1 unit of price move
    distance_for_target = TARGET_PER_POSITION / (lot_size * target_value_per_lot) if lot_size > 0 else None

    warning = None
    if raw_lot < MIN_LOT:
        warning = (
            f"Calculated lot size ({raw_lot:.4f}) is below the {MIN_LOT} minimum. "
            f"Using {MIN_LOT} means actual risk per position is ${actual_risk_per_position:.2f}, "
            f"higher than the intended ${RISK_PER_POSITION:.2f}."
        )

    return {
        "pair": pair,
        "entry_price": entry_price,
        "stop_price": stop_price,
        "stop_distance": round(price_distance, 5),
        "lot_size_per_position": lot_size,
        "num_positions": NUM_POSITIONS,
        "total_lot_size": round(lot_size * NUM_POSITIONS, 2),
        "intended_risk_per_position": round(RISK_PER_POSITION, 2),
        "actual_risk_per_position": round(actual_risk_per_position, 2),
        "actual_total_risk": round(actual_total_risk, 2),
        "price_distance_for_20_target": round(distance_for_target, 5) if distance_for_target else None,
        "warning": warning,
    }


if __name__ == "__main__":
    # Example: GBPJPY sell signal, entry 209.528, stop above the swept high at 209.747
    # USDJPY conversion rate needed since GBPJPY is JPY-quoted
    result = calculate_lot_size(
        pair="GBPJPY",
        entry_price=209.528,
        stop_price=209.747,
        conversion_rate=158.30,  # current USDJPY rate
    )
    for k, v in result.items():
        print(f"{k}: {v}")

    print()
    margin_info = max_positions_at_lot_size(
        pair="GBPJPY",
        price=209.528,
        lot_size=0.02,
        conversion_rate=158.30,
    )
    for k, v in margin_info.items():
        print(f"{k}: {v}")
