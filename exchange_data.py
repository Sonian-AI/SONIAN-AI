# exchange_data.py
"""
Module for retrieving exchange trading data and calculating total fees.
"""

import requests
from decimal import Decimal
from config import TRADING_PAIRS, FEE_RATE

def get_pair_volume_usdt(pair: str) -> Decimal:
    """
    Get the 24h trading volume for a given pair in USDT.
    In a real implementation, this would query the exchange's API.
    Here we use placeholder values or a public API as fallback.
    """
    # Placeholder volumes for demonstration (in USDT)
    dummy_volumes = {
        "BTC_USDT": Decimal("9000"),   # e.g., ~$9k volume in 24h
        "ETH_USDT": Decimal("7000"),   # e.g., ~$7k volume
        "BNB_USDT": Decimal("14000"),  # e.g., ~$14k volume
        "XRP_USDT": Decimal("4000")    # e.g., ~$4k volume
    }
    if pair in dummy_volumes:
        return dummy_volumes[pair]
    # Try to fallback to Binance public API for a rough estimate (since Cybersonian leverages Binance liquidity)
    try:
        symbol = pair.replace("_", "")  # e.g., "BTCUSDT"
        resp = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}", timeout=5)
        data = resp.json()
        volume_usdt = Decimal(data.get("quoteVolume", "0"))
        return volume_usdt
    except Exception as e:
        print(f"[Warning] Could not fetch volume for {pair}: {e}")
        return Decimal("0")

def get_total_fees() -> Decimal:
    """
    Calculate the total trading fees (in USD) collected across all tracked pairs in the last 24h.
    Uses the defined FEE_RATE to convert volume to fees.
    Returns the total fees as a Decimal (USD).
    """
    total_volume_usd = Decimal("0")
    for pair in TRADING_PAIRS:
        vol = get_pair_volume_usdt(pair)
        total_volume_usd += vol
        print(f"Volume for {pair}: {vol} USDT")
    total_fees = total_volume_usd * Decimal(str(FEE_RATE))
    print(f"Total 24h trading volume (USD): {total_volume_usd}")
    print(f"Total fees collected (at {FEE_RATE*100}% rate): {total_fees} USD")
    return total_fees
