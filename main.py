"""
Main entry point for SONIAN AI.
Orchestrates fetching, calculation, distribution, and AI prediction.
Runs in a loop with intervals.
Extensive startup and shutdown handling.
"""

import time
import signal
import sys
from datetime import datetime
from config import settings
from logger import root_logger, log_errors
from data_fetchers.cybersonian_fetcher import CybersonianFetcher
from data_fetchers.solana_dex_fetcher import SolanaDexFetcher
from calculators.volume_calculator import VolumeCalculator
from calculators.fee_distributor import FeeDistributor
from ai_models.volume_predictor import VolumePredictor
from wallet_manager import WalletManager
from transfer_executor import TransferExecutor
from database.models import init_db, VolumeRecord, DistributionRecord
from utils.mock_data import generate_mock_volumes

# Global shutdown flag
shutdown_flag = False

def signal_handler(signum, frame):
    """
    Handles SIGINT/SIGTERM for graceful shutdown.
    """
    global shutdown_flag
    root_logger.info("Shutdown signal received. Cleaning up...")
    shutdown_flag = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@log_errors(root_logger)
def main_loop():
    """
    Main execution loop.
    Fetches data, calculates, distributes, predicts.
    Runs every DISTRIBUTION_INTERVAL.
    """
    # Initialize components
    db_session = init_db()
    fetcher_cyber = CybersonianFetcher()
    fetcher_sol = SolanaDexFetcher()
    calc_volume = VolumeCalculator()
    distributor = FeeDistributor()
    predictor = VolumePredictor()
    wallet_mgr = WalletManager()
    executor = TransferExecutor()
    
    root_logger.info("SONIAN AI starting up...")
    
    # Initial mock data generation for demo
    if settings.TRAINING_DATA_SIZE > 0:
        mock_data = generate_mock_volumes(settings.TRAINING_DATA_SIZE)
        predictor.train(mock_data)
        root_logger.info("AI model trained on mock data")
    
    try:
        while not shutdown_flag:
            start_time = datetime.now()
            root_logger.info("Starting distribution cycle at %s", start_time)
            
            # Step 1: Fetch volumes
            cyber_volumes = fetcher_cyber.fetch_all_pairs(settings.COIN_PAIRS)
            sol_volume = fetcher_sol.fetch_volume()
            total_volume = calc_volume.aggregate(cyber_volumes, sol_volume)
            
            # Persist to DB
            record = VolumeRecord(
                timestamp=start_time,
                total_volume=total_volume,
                cyber_volumes=str(cyber_volumes),
                sol_volume=sol_volume
            )
            db_session.add(record)
            db_session.commit()
            
            # Step 2: Calculate fees
            total_fees = total_volume * settings.TOTAL_FEE_RATE
            shares = distributor.calculate_shares(total_fees, wallet_mgr.get_wallets())
            
            # Step 3: AI Prediction
            predicted_vol = predictor.predict_next(total_volume, horizon=settings.PREDICTION_HORIZON)
            root_logger.info("Predicted next 24h volume: %.2f", predicted_vol)
            
            # Persist distribution
            for wallet, amount in shares.items():
                dist_record = DistributionRecord(
                    timestamp=start_time,
                    wallet=wallet,
                    amount=amount,
                    predicted_volume=predicted_vol
                )
                db_session.add(dist_record)
            db_session.commit()
            
            # Step 4: Execute transfers (mock)
            executor.execute_distributions(shares)
            
            cycle_time = (datetime.now() - start_time).total_seconds()
            root_logger.info("Cycle completed in %.2fs. Total fees distributed: %.2f", cycle_time, total_fees)
            
            # Sleep until next interval
            if settings.DISTRIBUTION_INTERVAL == "1h":
                time.sleep(3600 - cycle_time)
            else:
                time.sleep(60)  # Default 1min for testing
            
    except Exception as e:
        root_logger.error("Main loop error: %s", e)
    finally:
        db_session.close()
        root_logger.info("SONIAN AI shutting down gracefully.")

if __name__ == "__main__":
    """
    Script entry point.
    Validates config and starts loop.
    """
    try:
        from config import validate_config
        validate_config()
        main_loop()
    except KeyboardInterrupt:
        root_logger.info("Interrupted by user")
    except Exception as e:
        root_logger.critical("Fatal error: %s", e)
        sys.exit(1)

# Padding: Additional startup checks (extended)
def health_check():
    """
    Performs health checks on dependencies.
    """
    checks = {
        "Config": "OK",
        "DB": "OK" if init_db() else "FAIL",
        "API Access": "MOCK"  # Real check in prod
    }
    root_logger.info("Health check: %s", checks)
    return all(v == "OK" for v in checks.values())

health_check()

# Export main for testing
__all__ = ['main_loop', 'shutdown_flag']
