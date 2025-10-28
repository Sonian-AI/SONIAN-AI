# config.py
"""
Configuration for the Sonian AI Fee Distribution Program.
Define network endpoints, token addresses, fee parameters, and keys.
"""

# RPC endpoint for Solana mainnet
RPC_ENDPOINT = "https://api.mainnet-beta.solana.com"

# Addresses of relevant Solana programs (constant, usually should not change)
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"          # SPL Token Program
ASSOCIATED_TOKEN_PROGRAM_ID = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"  # Associated Token Program (for token accounts)

# Token mint addresses (Solana SPL tokens)
SONIAN_MINT = "7aWo4u6iP4dXKvJCvahZL51a3ijL4PFM4RXZDnPdpump"  # SONIAN token mint (Solana address)
DIST_TOKEN_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"  # Distribution token mint (USDT on Solana)

# Known decimals for the distribution token (USDT). SONIAN decimals will be fetched from chain.
DIST_TOKEN_DECIMALS = 6  # USDT typically has 6 decimal places on Solana

# Trading pairs on the exchange to consider for fee calculation (using USDT as quote currency)
TRADING_PAIRS = ["BTC_USDT", "ETH_USDT", "BNB_USDT", "XRP_USDT"]

# Fee rate (e.g., 0.001 = 0.1% per trade). Adjust if the exchange uses a different fee structure.
FEE_RATE = 0.001

# Eligibility threshold for holders (in USD). Holders must have at least this much value in SONIAN to get rewards.
THRESHOLD_USD = 100

# Secret key for the distribution wallet (which holds collected fees and will distribute rewards).
# **IMPORTANT**: Replace the placeholder with the actual secret key.
# You can provide this as a list of 64 integers (the private key bytes) or a base58-encoded string.
DISTRIBUTION_SECRET_KEY = None  # ← Fill this with the exchange's distribution wallet secret.
