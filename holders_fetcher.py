import requests
import json
import logging
from solana.publickey import PublicKey
from solana.rpc.api import Client
from solana.transaction import Transaction
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address, create_associated_token_account, transfer, TransferParams
from config import SOLANA_RPC_URL, SONIAN_MINT_ADDRESS, USDT_MINT_ADDRESS, ELIGIBILITY_THRESHOLD_USD, EXCLUDED_ADDRESSES

class HolderFetcher:
    """
    Fetches SONIAN token holders from Solana and filters eligible addresses.
    """
    def __init__(self, rpc_url: str = SOLANA_RPC_URL):
        self.client = Client(rpc_url)
        self.sonian_mint = PublicKey(SONIAN_MINT_ADDRESS)
        self.usdt_mint = PublicKey(USDT_MINT_ADDRESS)
        logging.info(f"Initialized HolderFetcher for SONIAN mint: {SONIAN_MINT_ADDRESS}")
    
    def get_sonian_price_usd(self) -> float:
        """
        Get the current SONIAN token price in USD using the DexScreener API.
        """
        # DexScreener pair ID for SONIAN (SONIAN/SOL on PumpSwap, Solana):contentReference[oaicite:16]{index=16}
        pair_id = "KpmMXpSzmtTxsdGyZZqZQXWvYSSEzbxzLyB3qcnRSoE"
        url = f"https://api.dexscreener.com/latest/dex/pairs/solana/{pair_id}"
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            price = float(data["pairs"][0]["priceUsd"])
            logging.info(f"Fetched SONIAN price: ${price:.8f} USD")
            return price
        except Exception as e:
            logging.error(f"Error fetching SONIAN price from DexScreener: {e}")
            return 0.0
    
    def fetch_holders(self):
        """
        Retrieve all token accounts for the SONIAN mint and determine eligible holders.
        Returns a list of (holder_wallet_address, balance_base_units) for eligible holders.
        """
        logging.info("Fetching all SONIAN token accounts from Solana...")
        params = [
            str(self.sonian_mint),
            {"commitment": "confirmed", "encoding": "jsonParsed"}
        ]
        try:
            response = requests.post(SOLANA_RPC_URL, json={
                "jsonrpc": "2.0", "id": 1,
                "method": "getTokenAccountsByMint",
                "params": params
            }, timeout=10)
            response.raise_for_status()
            result = response.json().get("result", {})
        except Exception as e:
            logging.error(f"RPC request failed: {e}")
            return []
        
        token_accounts = result.get("value", [])
        holders = []
        total_tokens = 0
        decimals = None
        # Parse token account data
        for entry in token_accounts:
            try:
                acct_info = entry["account"]["data"]["parsed"]["info"]
                owner = acct_info["owner"]
                # Exclude known ineligible accounts (e.g. liquidity pool or contract addresses)
                if owner in EXCLUDED_ADDRESSES or entry["pubkey"] in EXCLUDED_ADDRESSES:
                    logging.info(f"Excluding address {owner} (or account {entry['pubkey']}) from rewards")
                    continue
                token_amount = acct_info["tokenAmount"]
                # Determine decimals (same for all accounts of this mint)
                if decimals is None:
                    decimals = int(token_amount.get("decimals", 0))
                    logging.info(f"Detected SONIAN token decimals: {decimals}")
                balance_base = int(token_amount["amount"])  # raw balance in smallest units
                if balance_base == 0:
                    continue  # skip empty accounts
                total_tokens += balance_base
                holders.append((owner, balance_base))
            except KeyError as ke:
                logging.warning(f"Unexpected account format: {ke}")
                continue
        logging.info(f"Total token-holding accounts (pre-eligibility): {len(holders)}")
        logging.info(f"Aggregated SONIAN token supply in tracked accounts: {total_tokens} base units")
        
        # Determine price and filter eligible holders by value
        price_usd = self.get_sonian_price_usd()
        if price_usd <= 0:
            logging.warning("SONIAN price unavailable; cannot determine eligibility.")
            return []  # No price means we cannot apply the threshold criteria
        eligible_holders = []
        for owner, balance_base in holders:
            # Compute holder's token value in USD: (balance / 10^decimals) * price_usd
            if decimals is None:
                decimals = 0  # default if not set (should not happen if token accounts exist)
            balance_tokens = balance_base / (10 ** (decimals or 0))
            value_usd = balance_tokens * price_usd
            if value_usd >= ELIGIBILITY_THRESHOLD_USD:
                eligible_holders.append((owner, balance_base))
            else:
                logging.debug(f"Address {owner}: holding value ${value_usd:.2f} < ${ELIGIBILITY_THRESHOLD_USD}, not eligible")
        logging.info(f"Eligible holders (≥ ${ELIGIBILITY_THRESHOLD_USD} in SONIAN): {len(eligible_holders)}")
        return eligible_holders, total_tokens, decimals

class FeeDistributor:
    """
    Calculates each holder's reward and dispatches the USDT payments.
    """
    def __init__(self, distributor_keypair):
        self.distributor = distributor_keypair
        self.distributor_pubkey = distributor_keypair.public_key
        self.client = Client(SOLANA_RPC_URL)
        # Determine the distributor's USDT token account (associated token account for USDT)
        self.usdt_mint = PublicKey(USDT_MINT_ADDRESS)
        self.source_token_account = get_associated_token_address(owner=self.distributor_pubkey, mint=self.usdt_mint)
        logging.info(f"Distributor wallet: {self.distributor_pubkey}")
        logging.info(f"Distributor USDT source account: {self.source_token_account}")
    
    def distribute(self, eligible_holders, total_fee_usd):
        """
        Distribute 50% of the total fees (in USDT) among eligible holders proportionally to their SONIAN stake.
        """
        if total_fee_usd <= 0 or not eligible_holders:
            logging.warning("No fees to distribute or no eligible holders.")
            return False
        # Calculate distribution amount (50% of total fees):contentReference[oaicite:17]{index=17}
        distribution_usd = total_fee_usd * 0.5
        usdt_decimals = 6  # USDT has 6 decimal places on Solana
        distribution_base_total = int(distribution_usd * (10 ** usdt_decimals))
        logging.info(f"Total fees: ${total_fee_usd:.2f} -> Distributing 50% = ${distribution_usd:.2f} ({distribution_base_total} microUSDT)")
        # Ensure the distributor has enough USDT balance
        balance_resp = self.client.get_token_account_balance(self.source_token_account)
        try:
            available = int(balance_resp["result"]["value"]["amount"])
        except Exception as e:
            logging.error(f"Could not fetch distributor USDT balance: {e}")
            return False
        if available < distribution_base_total:
            logging.error(f"Insufficient USDT in distributor account (have {available}, need {distribution_base_total})")
            return False
        
        # Calculate total SONIAN held by eligible holders (in base units)
        total_base_eligible = sum(balance for (_owner, balance) in eligible_holders)
        # Determine each holder's allocation in USDT base units
        allocations = []
        allocated_sum = 0
        remainders = []
        for owner, balance_base in eligible_holders:
            # Proportional allocation = (holder_balance / total_base_eligible) * distribution_base_total
            share_num = balance_base * distribution_base_total
            alloc_base = share_num // total_base_eligible  # floor division for base units
            allocations.append((owner, alloc_base))
            allocated_sum += alloc_base
            # Calculate remainder part for fair rounding
            remainder_part = share_num % total_base_eligible
            remainders.append((remainder_part, owner))
        # Handle any leftover due to rounding down
        remainder_total = distribution_base_total - allocated_sum
        if remainder_total > 0:
            # Give an extra micro-unit to the holders with the largest remainders
            remainders.sort(reverse=True, key=lambda x: x[0])
            for i in range(min(remainder_total, len(remainders))):
                _, owner = remainders[i]
                # Find and increment the allocation for this owner by 1
                for j, (ow, alloc) in enumerate(allocations):
                    if ow == owner:
                        allocations[j] = (ow, alloc + 1)
                        break
            allocated_sum += remainder_total
        logging.info(f"Total distributed (post-rounding): {allocated_sum} of {distribution_base_total} microUSDT")
        
        # Create and send transactions for each holder
        success = True
        for owner, alloc_base in allocations:
            if alloc_base <= 0:
                continue  # skip zero allocations
            dest_wallet = PublicKey(owner)
            dest_ata = get_associated_token_address(owner=dest_wallet, mint=self.usdt_mint)
            # Build the transaction: create associated account if needed, then transfer
            tx = Transaction()
            ata_info = self.client.get_account_info(dest_ata)
            if ata_info["result"]["value"] is None:
                # No associated token account exists for this wallet – add creation instruction
                tx.add(create_associated_token_account(payer=self.distributor_pubkey, owner=dest_wallet, mint=self.usdt_mint))
            # Add token transfer instruction for the reward
            tx.add(transfer(TransferParams(
                program_id=TOKEN_PROGRAM_ID,
                source=self.source_token_account,
                dest=dest_ata,
                owner=self.distributor_pubkey,
                amount=alloc_base
            )))
            # Sign and send the transaction
            try:
                response = self.client.send_transaction(tx, self.distributor)
                logging.info(f"Sent {alloc_base} microUSDT to {owner} (transaction signature: {response})")
            except Exception as txe:
                logging.error(f"Failed to send reward to {owner}: {txe}")
                success = False
        return success
}
