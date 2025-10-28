# holders.py
"""
Module to retrieve SONIAN token holders from Solana and filter eligible holders.
"""
from decimal import Decimal, getcontext
from solana.rpc.api import Client
from solana.publickey import PublicKey
import requests
import config

# Increase decimal precision to handle small price and large token amounts
getcontext().prec = 50

def _get_sonian_price_usd() -> Decimal:
    """
    Fetch the current SONIAN token price in USD using DexScreener API.
    Returns the price as a Decimal.
    """
    # Pair ID for SONIAN/SOL on PumpSwap (from DexScreener or GeckoTerminal data)
    pair_id = "KpmMXpSzmtTxsdGyZZqZQXWvYSSEzbxzLyB3qcnRSoE"
    url = f"https://api.dexscreener.com/latest/dex/pairs/solana/{pair_id}"
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        price_str = data["pairs"][0]["priceUsd"]
        price = Decimal(price_str)
        return price
    except Exception as e:
        print(f"[Error] Unable to fetch SONIAN price from DexScreener: {e}")
        # If API call fails, default to a saved price or 0 to prevent miscalculation
        return Decimal("0")

def get_eligible_holders_with_balance():
    """
    Retrieve all SONIAN token holders and filter those who meet the threshold (config.THRESHOLD_USD).
    Returns a list of (PublicKey holder_address, int balance_atomic) for eligible holders.
    """
    client = Client(config.RPC_ENDPOINT)
    sonian_mint = PublicKey(config.SONIAN_MINT)
    # Use getProgramAccounts to fetch all token accounts for the SONIAN mint, with parsed data
    response = client.get_program_accounts(
        PublicKey(config.TOKEN_PROGRAM_ID),
        encoding="jsonParsed",
        filters=[
            {"dataSize": 165},  # SPL Token Account size
            {"memcmp": {"offset": 0, "bytes": str(sonian_mint)}}  # filter for accounts with this mint
        ]
    )
    accounts = response.get("result", [])
    if not accounts:
        print("[Info] No token accounts found for SONIAN mint. Check mint address or network.")
        return []
    # Fetch current price of SONIAN in USD
    price_usd = _get_sonian_price_usd()
    if price_usd <= 0:
        print("[Warning] SONIAN price is 0 or unavailable. All holders will be considered ineligible.")
    print(f"Current SONIAN price: ${price_usd} USD")

    eligible_holders = []
    total_holders = 0
    # We will retrieve decimals from the first account (all SONIAN token accounts share the same decimals)
    token_decimals = None

    for acct in accounts:
        total_holders += 1
        info = acct["account"]["data"]["parsed"]["info"]
        owner_addr = info["owner"]
        token_amount_info = info["tokenAmount"]
        amount_str = token_amount_info["amount"]   # balance in atomic units (string)
        decimals = token_amount_info["decimals"]
        if token_decimals is None:
            token_decimals = int(decimals)
        # Convert to integer
        balance_atomic = int(amount_str)
        if price_usd > 0:
            # Check if value >= threshold (using atomic units to avoid float issues):
            # condition: balance_atomic * price_usd >= THRESHOLD_USD * 10^decimals
            threshold_scaled = Decimal(str(config.THRESHOLD_USD)) * (10 ** token_decimals)
            if Decimal(balance_atomic) * price_usd < threshold_scaled:
                # This holder's value is below threshold, skip
                continue
        else:
            # If price is not available, treat all holders as ineligible (or break out)
            continue
        # This holder meets the threshold
        eligible_holders.append((PublicKey(owner_addr), balance_atomic))
    print(f"Total holders found: {total_holders}, Eligible holders (>= ${config.THRESHOLD_USD} in SONIAN): {len(eligible_holders)}")
    return eligible_holders
