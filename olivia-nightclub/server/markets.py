"""Shared EUR quotes. Kraken data is real; luxury prices are a game simulation.

No account, API key or real order is involved. Fetching never holds the game lock.
Snapshots (including history and the luxury seed) persist in SQLite settings.
"""
import copy
import hashlib
import json
import math
import secrets
import time
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CATALOG = {
    "BTC": ("Bitcoin", "XBTEUR", "XXBTZEUR"),
    "ETH": ("Ethereum", "ETHEUR", "XETHZEUR"),
    "SOL": ("Solana", "SOLEUR", "SOLEUR"),
    "XRP": ("XRP", "XRPEUR", "XXRPZEUR"),
    "ADA": ("Cardano", "ADAEUR", "ADAEUR"),
    "DOGE": ("Dogecoin", "DOGEEUR", "XDGEUR"),
    "DOT": ("Polkadot", "DOTEUR", "DOTEUR"),
    "LINK": ("Chainlink", "LINKEUR", "LINKEUR"),
    "AVAX": ("Avalanche", "AVAXEUR", "AVAXEUR"),
    "LTC": ("Litecoin", "LTCEUR", "XLTCZEUR"),
    "BCH": ("Bitcoin Cash", "BCHEUR", "BCHEUR"),
    "UNI": ("Uniswap", "UNIEUR", "UNIEUR"),
}
POLL_SECONDS = 15
STALE_SECONDS = 90
FEE = Decimal("0.005")
QUANTUM = Decimal("0.00000001")
BTC_VOLATILITY = 5


def amplify_bitcoin(previous, quote):
    """Amplify log returns against a persisted anchor; polling frequency has no effect.

    On activation, preserve the existing game valuation. Old real-price history
    must not be presented as if it had already been amplified.
    """
    real = positive(quote["price"])
    old = previous if previous.get("leverage") == BTC_VOLATILITY else {}
    anchor_real = old.get("anchor_market", real)
    anchor_game = old.get("anchor_game", previous.get("price", real))
    price = max(.000001, min(1e12, anchor_game * (real / anchor_real) ** BTC_VOLATILITY))
    return dict(quote, price=price, market_price=real, leverage=BTC_VOLATILITY,
                anchor_market=anchor_real, anchor_game=anchor_game), bool(old)


def positive(value):
    n = float(value)
    if not math.isfinite(n) or n <= 0 or n > 1e12:
        raise ValueError("Invalid market price")
    return n


def quantity(value):
    if isinstance(value, bool):
        raise ValueError("Invalid quantity")
    try:
        q = Decimal(str(value))
        if not q.is_finite() or q <= 0 or q > 1_000_000:
            raise ValueError("Invalid quantity")
        if q != q.quantize(QUANTUM):
            raise ValueError("Maximum 8 decimals")
        return q
    except (InvalidOperation, TypeError):
        raise ValueError("Invalid quantity") from None


def balance(club, symbol):
    return Decimal(str(club.get("bitcoin", 0) if symbol == "BTC"
                       else club.get("crypto", {}).get(symbol, 0)))


def set_balance(club, symbol, value):
    # BTC remains in its historical field, preserving saves and player trades.
    if symbol == "BTC":
        club["bitcoin"] = float(value)
    else:
        club.setdefault("crypto", {})[symbol] = str(value)


def trade(club, symbol, op, amount, quote, now=None):
    now = time.time() if now is None else now
    if symbol not in CATALOG or op not in ("buy", "sell"):
        return False, "INVALID", {}
    try:
        q = quantity(amount)
    except ValueError:
        return False, "INVALID", {}
    if not quote or not quote.get("updated_at") or not 0 <= now - quote["updated_at"] <= STALE_SECONDS:
        return False, "MARKET_STALE", {}
    try:
        price = Decimal(str(positive(quote["price"])))
    except (ValueError, KeyError, TypeError):
        return False, "MARKET_STALE", {}
    held = balance(club, symbol)
    gross = q * price
    total = int((gross * (1 + FEE if op == "buy" else 1 - FEE)).to_integral_value(
        rounding=ROUND_CEILING if op == "buy" else ROUND_FLOOR))
    payload = {"symbol": symbol, "quantity": str(q), "unit": float(price),
               "quote_time": quote["updated_at"], "fee_rate": float(FEE),
               "cost" if op == "buy" else "gain": total}
    if op == "buy" and club.get("cash", 0) < total:
        return False, "NO_MONEY", payload
    if op == "sell" and held < q:
        return False, "NOT_OWNED", {}
    if total < 1:
        return False, "MINIMUM", {}
    club["cash"] = int(club.get("cash", 0)) + (-total if op == "buy" else total)
    set_balance(club, symbol, held + (q if op == "buy" else -q))
    return True, "OK", payload


def request_public(endpoint, **params):
    url = "https://api.kraken.com/0/public/" + endpoint + "?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "OliviaNightclub/1.0", "Accept": "application/json"})
    with urlopen(req, timeout=8) as response:
        data = json.load(response)
    if data.get("error") or not isinstance(data.get("result"), dict):
        raise ValueError("Market provider unavailable")
    return data["result"]


def fetch_tickers():
    result = request_public("Ticker", pair=",".join(row[1] for row in CATALOG.values()))
    stamp = time.time()
    quotes = {}
    for symbol, (name, pair, key) in CATALOG.items():
        row = result.get(key) or result.get(pair)
        if not row:
            continue
        try:
            price, opening = positive(row["c"][0]), positive(row["o"])
            quotes[symbol] = {"name": name, "price": price, "updated_at": stamp,
                              "change_pct": (price / opening - 1) * 100}
        except (ValueError, KeyError, TypeError, IndexError):
            continue
    if not quotes:
        raise ValueError("No valid quote")
    return quotes


def fetch_history(symbol):
    stamp = time.time()
    result = request_public("OHLC", pair=CATALOG[symbol][1], interval=5, since=int(stamp - 86400))
    rows = next((v for k, v in result.items() if k != "last" and isinstance(v, list)), [])
    # Candle close is observed at the end of the interval, or now for the live candle.
    return [[min(float(row[0]) + 300, stamp), positive(row[4])] for row in rows
            if stamp - 86400 <= float(row[0]) <= stamp][-289:]


def history_point(points, ts, price):
    points = [p for p in points if ts - 86400 <= p[0] <= ts]
    # Keep the first observed price as a baseline, even during the first bucket.
    if points and (points[-1][0] == ts or
                   (len(points) > 1 and int(points[-1][0] // 300) == int(ts // 300))):
        points[-1] = [ts, price]
    else:
        points.append([ts, price])
    return points[-289:]


def advance_luxury(state, shop, now):
    """Seeded, bounded, mean-reverting minute steps, shared by every player."""
    seed = state.setdefault("seed", secrets.token_hex(16))
    minute = int(now // 60)
    for category in ("cars", "watches"):
        group = state.setdefault(category, {})
        for item_id, item in shop[category].items():
            base = int(item["price"])
            row = group.setdefault(item_id, {"price": base, "minute": minute, "history": [[now, base]]})
            previous = row["price"]
            # Long absences are capped at one day; no historical curve is invented for the skipped gap.
            start = max(int(row["minute"]) + 1, minute - 1439)
            for step in range(start, minute + 1):
                digest = hashlib.sha256(f"{seed}:{category}:{item_id}:{step}".encode()).digest()
                noise = int.from_bytes(digest[:8], "big") / (2**64 - 1) * 2 - 1
                reversion = (base / row["price"] - 1) * 0.0008
                row["price"] = max(round(base * .45), min(round(base * 2.5),
                    max(1, round(row["price"] * (1 + noise * .0025 + reversion)))))
                row["history"] = history_point(row["history"], step * 60, row["price"])
            if minute > row["minute"]:
                row["previous"] = previous
            row["minute"] = minute
    return state


def public_snapshot(state, shop, now=None):
    now = time.time() if now is None else now
    coins = {}
    for symbol, (name, *_rest) in CATALOG.items():
        row = copy.deepcopy(state.get("crypto", {}).get(symbol, {}))
        age = now - row.get("updated_at", 0)
        row.update(symbol=symbol, name=name, stale=not 0 <= age <= STALE_SECONDS,
                   history=[p for p in row.get("history", []) if p[0] >= now - 86400])
        coins[symbol] = row
    luxury = {}
    for category in ("cars", "watches"):
        luxury[category] = {}
        for item_id, item in shop[category].items():
            row = state.get(category, {}).get(item_id, {})
            price = row.get("price", item["price"])
            points = [p for p in row.get("history", []) if p[0] >= now - 86400]
            reference = points[0][1] if points else price
            luxury[category][item_id] = {"price": price, "history": points,
                "change_pct": (price / reference - 1) * 100,
                "updated_at": row.get("minute", int(now // 60)) * 60}
    return {"crypto": coins, **luxury, "server_time": now, "source": "Kraken",
            "poll_seconds": POLL_SECONDS, "stale_seconds": STALE_SECONDS,
            "fee_rate": float(FEE), "luxury_source": "Simulation Olivia"}


def priced_config(base, state):
    """Light copy: never modify cached administrative configuration."""
    shop = dict(base["shop"])
    for category in ("cars", "watches"):
        shop[category] = {key: dict(item, price=state.get(category, {}).get(key, {}).get("price", item["price"]))
                          for key, item in shop[category].items()}
    shop["crypto_quotes"] = {key: {k: v for k, v in row.items() if k != "history"}
                             for key, row in state.get("crypto", {}).items()}
    # Zero means unpriced, never substitute a fictitious live cryptocurrency price.
    shop["bitcoin_price"] = shop["crypto_quotes"].get("BTC", {}).get("price", 0)
    return dict(base, shop=shop)
