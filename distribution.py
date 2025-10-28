# distribution.py
"""
Module for calculating reward allocations and distributing the fees to eligible holders.
"""
from decimal import Decimal, getcontext
from solana.publickey import PublicKey
from solana.keypair import Keypair
from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import transfer_checked, TransferCheckedParams, create_associated_token_account
import config

# Set high precision for reward calculations
getcontext().prec = 50

def calculate_rewards(eligible_holders, total_fee_pool_usd: Decimal):
    """
    Calculate each eligible holder's reward from the total fee pool (USD).
    Returns a list of (holder PublicKey, reward_amount_atomic) for the distribution token.
    """
    # Convert the total fee pool (USD) to distribution token atomic units (e.g., USDT minor units).
    dist_decimals = config.DIST_TOKEN_DECIMALS
    total_fee_pool_atomic = int(total_fee_pool_usd * (10 ** dist_decimals))
    if total_fee_pool_atomic <= 0 or not eligible_holders:
        return []  # nothing to distribute or no eligible holders

    # Sum total SONIAN tokens (in atomic units) among eligible holders
    total_sonian_atomic = sum(balance for (_, balance) in eligible_holders)
    # Compute reward for each holder
    rewards = []
    distributed_total = 0
    for holder_pubkey, holder_balance_atomic in eligible_holders:
        # Proportional share = (holder_balance / total_balance) * total_fee_pool_atomic
        # Use integer math for exact distribution (floor division for each holder)
        share_atomic = (holder_balance_atomic * total_fee_pool_atomic) // total_sonian_atomic
        if share_atomic > 0:
            rewards.append((holder_pubkey, share_atomic))
            distributed_total += share_atomic
    # If there is any remainder due to flooring, it will remain undistributed.
    remainder = total_fee_pool_atomic - distributed_total
    if remainder > 0:
        print(f"[Info] Undistributed remainder due to rounding: {remainder} (atomic units of distribution token)")
    return rewards

def distribute_rewards(rewards_list):
    """
    Execute the distribution of rewards to each eligible holder.
    Signs and sends a transaction for each holder's reward transfer.
    """
    if not rewards_list:
        print("No rewards to distribute.")
        return

    # Initialize Solana client and distribution wallet keypair
    client = Client(config.RPC_ENDPOINT)
    dist_secret = config.DISTRIBUTION_SECRET_KEY
    if not dist_secret:
        raise RuntimeError("Distribution secret key is not set in config.")
    # Load the distribution wallet keypair from the secret (list of ints or base58 string)
    if isinstance(dist_secret, str):
        # If base58 string is provided
        try:
            from base58 import b58decode
            secret_bytes = b58decode(dist_secret)
            dist_keypair = Keypair.from_secret_key(secret_bytes)
        except Exception as e:
            raise RuntimeError(f"Failed to decode base58 secret key: {e}")
    elif isinstance(dist_secret, (bytes, bytearray)):
        dist_keypair = Keypair.from_secret_key(dist_secret)
    elif isinstance(dist_secret, list):
        dist_keypair = Keypair.from_secret_key(bytes(dist_secret))
    else:
        raise RuntimeError("DISTRIBUTION_SECRET_KEY must be a base58 string, bytes, or list of int bytes.")
    dist_pubkey = dist_keypair.public_key

    # Determine the source (distribution wallet's USDT token account)
    dist_token_mint = PublicKey(config.DIST_TOKEN_MINT)
    owner_accounts = client.get_token_accounts_by_owner(dist_pubkey, 
                                                        {"mint": str(dist_token_mint)}, 
                                                        commitment=Confirmed)
    owner_accounts_list = owner_accounts.get("result", [])
    if not owner_accounts_list:
        raise RuntimeError("Distribution wallet's token account for the distribution token not found.")
    dist_token_account_pubkey = PublicKey(owner_accounts_list[0]["pubkey"])
    print(f"Using distribution wallet {dist_pubkey} USDT account {dist_token_account_pubkey} as source.")

    # Prepare program IDs as PublicKey objects
    token_program_pub = PublicKey(config.TOKEN_PROGRAM_ID)
    assoc_token_program_pub = PublicKey(config.ASSOCIATED_TOKEN_PROGRAM_ID)

    # Iterate through each reward and send transaction
    for recipient_pubkey, amount_atomic in rewards_list:
        # Derive the recipient's associated token account for USDT
        seeds = [
            bytes(recipient_pubkey),
            bytes(token_program_pub),
            bytes(dist_token_mint)
        ]
        # find_program_address returns (PublicKey, bump), we take address
        ata_address, _ = PublicKey.find_program_address(seeds, assoc_token_program_pub)
        recipient_ata = ata_address

        # Build transaction: create ATA if not exists, then transfer tokens
        transaction = Transaction()
        # Instruction: create associated token account (idempotent, will not fail if exists)
        create_ata_instr = create_associated_token_account(
            payer=dist_pubkey,
            owner=recipient_pubkey,
            mint=dist_token_mint
        )
        transaction.add(create_ata_instr)
        # Instruction: transfer tokens to recipient ATA
        transfer_instr = transfer_checked(
            TransferCheckedParams(
                program_id=TOKEN_PROGRAM_ID,        # SPL Token program
                source=dist_token_account_pubkey,   # distribution wallet's USDT account
                mint=dist_token_mint, 
                dest=recipient_ata,                # recipient's USDT token account
                owner=dist_pubkey,                 # authority of source account (distribution wallet)
                amount=amount_atomic,
                decimals=config.DIST_TOKEN_DECIMALS,
                signers=[]                         # no additional signers besides owner
            )
        )
        transaction.add(transfer_instr)

        try:
            # Send transaction
            response = client.send_transaction(transaction, dist_keypair, opts=TxOpts(skip_confirmation=False, preflight_commitment=Confirmed))
            tx_sig = response.get("result")
            if tx_sig:
                print(f"✅ Sent {amount_atomic} (atomic units) to {recipient_pubkey}. Transaction signature: {tx_sig}")
            else:
                error_msg = response.get("error")
                print(f"❌ Failed to send to {recipient_pubkey}: {error_msg}")
        except Exception as tx_err:
            print(f"❌ Exception during transfer to {recipient_pubkey}: {tx_err}")
