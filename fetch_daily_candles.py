"""
Pulls the last few CLOSED daily candles for the 7 tracked pairs from the
cTrader Open API (read-only market data - no orders are ever placed here),
then applies the same 6-rule daily-bias sweep logic as bias_engine.py /
tradingview_strategy.pine.

Requires CTRADER_CLIENT_ID, CTRADER_CLIENT_SECRET, CTRADER_ACCESS_TOKEN in
.env (see ctrader_auth.py + ctrader_token.py to generate these).
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from twisted.internet import reactor

from ctrader_open_api import Client, Protobuf, TcpProtocol, EndPoints
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAApplicationAuthReq,
    ProtoOAGetAccountListByAccessTokenReq,
    ProtoOAAccountAuthReq,
    ProtoOASymbolsListReq,
    ProtoOAGetTrendbarsReq,
)
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOATrendbarPeriod
from ctrader_open_api.messages.OpenApiMessages_pb2 import ProtoOAErrorRes

load_dotenv()

CLIENT_ID = os.environ["CTRADER_CLIENT_ID"]
CLIENT_SECRET = os.environ["CTRADER_CLIENT_SECRET"]
ACCESS_TOKEN = os.environ["CTRADER_ACCESS_TOKEN"]

PAIRS = ["XAUUSD", "EURGBP", "AUDJPY"]
PRICE_SCALE = 100000.0
DATA_FILE = Path(__file__).parent / "data" / "candles.json"

client = Client(EndPoints.PROTOBUF_LIVE_HOST, EndPoints.PROTOBUF_PORT, TcpProtocol)

state = {"accountId": None, "symbolIds": {}, "results": {}, "pairQueue": []}


def onError(failure):
    print("Error:", failure.getErrorMessage() if hasattr(failure, "getErrorMessage") else failure)
    if reactor.running:
        reactor.stop()


def extract(res):
    """Decode the raw ProtoMessage into its concrete payload type, and
    surface API error responses with a clear message instead of a vague
    AttributeError."""
    msg = Protobuf.extract(res)
    if isinstance(msg, ProtoOAErrorRes):
        raise RuntimeError(f"cTrader API error [{msg.errorCode}]: {msg.description}")
    return msg


def computeBias(h1, l1, c1, h2, l2):
    """Same 6-rule sweep logic as bias_engine.py / the Pine script."""
    sweptHigh = h1 > h2
    sweptLow = l1 < l2
    if sweptHigh and sweptLow:
        if c1 > h2:
            return "BUY"
        elif c1 < l2:
            return "SELL"
        return "AVOID"
    elif sweptHigh:
        return "BUY" if c1 > h2 else "SELL"
    elif sweptLow:
        return "SELL" if c1 < l2 else "BUY"
    return "AVOID"


def requestTrendbars(symbolName, symbolId):
    now = int(time.time() * 1000)
    req = ProtoOAGetTrendbarsReq()
    req.ctidTraderAccountId = state["accountId"]
    req.period = ProtoOATrendbarPeriod.D1
    req.toTimestamp = now
    req.fromTimestamp = now - 10 * 24 * 60 * 60 * 1000  # last 10 days
    req.symbolId = symbolId
    d = client.send(req)
    d.addCallbacks(lambda res: onTrendbars(symbolName, res), onError)
    return d


def onTrendbars(symbolName, res):
    res = extract(res)
    bars = sorted(res.trendbar, key=lambda b: b.utcTimestampInMinutes)
    # The API only returns CLOSED bars (no in-progress/forming bar included),
    # so the last 2 bars ARE the 2 most recently closed daily candles.
    closed = bars[-2:]
    parsed = []
    for b in closed:
        low = b.low / PRICE_SCALE
        high = low + b.deltaHigh / PRICE_SCALE
        open_ = low + b.deltaOpen / PRICE_SCALE
        close = low + b.deltaClose / PRICE_SCALE
        day = datetime.fromtimestamp(b.utcTimestampInMinutes * 60, tz=timezone.utc)
        parsed.append({"open": open_, "high": high, "low": low, "close": close, "day": day})

    d2, d1 = parsed[-2], parsed[-1]  # d2 = older, d1 = newer (most recent closed)
    bias = computeBias(d1["high"], d1["low"], d1["close"], d2["high"], d2["low"])
    state["results"][symbolName] = {"candle1": d2, "candle2": d1}
    print(f"{symbolName:8s} -> {bias:6s}  "
          f"(prior H/L {d2['high']:.5f}/{d2['low']:.5f} | "
          f"last H/L/C {d1['high']:.5f}/{d1['low']:.5f}/{d1['close']:.5f})")

    if len(state["results"]) == len(PAIRS):
        writeCandlesFile()
        reactor.stop()


def writeCandlesFile():
    existing = {}
    if DATA_FILE.exists():
        existing = json.loads(DATA_FILE.read_text())

    # candle2 ("last closed day") is the same calendar day for every pair,
    # since all 7 D1 bars share the same broker day-boundary (7am Brisbane).
    any_result = next(iter(state["results"].values()))
    c1_day, c2_day = any_result["candle1"]["day"], any_result["candle2"]["day"]

    # Bars are timestamped at their UTC start (21:00 UTC = 7am Brisbane the
    # NEXT day), so the trading day they represent is start-date + 1 day.
    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "cTrader Open API (Pepperstone, Daily TF, 7am Brisbane candle)",
        "candle1_label": (c1_day + timedelta(days=1)).strftime("%A"),
        "candle2_label": (c2_day + timedelta(days=1)).strftime("%A"),
        "pairs": {},
        "candles_4h": existing.get("candles_4h", {p: [] for p in PAIRS}),
    }
    for pair, r in state["results"].items():
        out["pairs"][pair] = {
            "candle1": {k: v for k, v in r["candle1"].items() if k != "day"},
            "candle2": {k: v for k, v in r["candle2"].items() if k != "day"},
        }

    DATA_FILE.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nWrote {DATA_FILE}")


def onSymbols(res):
    res = extract(res)
    byName = {s.symbolName: s.symbolId for s in res.symbol}
    missing = [p for p in PAIRS if p not in byName]
    if missing:
        print("Symbols not found on this account:", missing)
        print("Available symbol names (sample):", list(byName.keys())[:20])
        reactor.stop()
        return
    state["pairQueue"] = [(p, byName[p]) for p in PAIRS]
    requestNextTrendbar()


def requestNextTrendbar():
    if not state["pairQueue"]:
        return
    pair, symbolId = state["pairQueue"].pop(0)
    d = requestTrendbars(pair, symbolId)
    d.addBoth(lambda _: reactor.callLater(0.5, requestNextTrendbar))


def onAccountAuth(res):
    extract(res)
    req = ProtoOASymbolsListReq()
    req.ctidTraderAccountId = state["accountId"]
    d = client.send(req)
    d.addCallbacks(onSymbols, onError)


def onAccountList(res):
    res = extract(res)
    accounts = res.ctidTraderAccount
    if not accounts:
        print("No trading accounts found for this access token.")
        reactor.stop()
        return
    account = accounts[0]
    state["accountId"] = account.ctidTraderAccountId
    print(f"Using account login {account.traderLogin} "
          f"({'live' if account.isLive else 'demo'})")

    req = ProtoOAAccountAuthReq()
    req.ctidTraderAccountId = account.ctidTraderAccountId
    req.accessToken = ACCESS_TOKEN
    d = client.send(req)
    d.addCallbacks(onAccountAuth, onError)


def onAppAuth(res):
    extract(res)
    req = ProtoOAGetAccountListByAccessTokenReq()
    req.accessToken = ACCESS_TOKEN
    d = client.send(req)
    d.addCallbacks(onAccountList, onError)


def connected(client):
    req = ProtoOAApplicationAuthReq()
    req.clientId = CLIENT_ID
    req.clientSecret = CLIENT_SECRET
    d = client.send(req)
    d.addCallbacks(onAppAuth, onError)


def disconnected(client, reason):
    print("Disconnected:", reason)


client.setConnectedCallback(connected)
client.setDisconnectedCallback(disconnected)
client.startService()
reactor.run()

print("\nDone.")
