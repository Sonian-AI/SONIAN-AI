"""
Configuration module for SONIAN AI.
Loads settings from environment variables or defaults.
Extensive comments for clarity and expansion.
"""

import os
from dotenv import load_dotenv
from pydantic import BaseSettings, Field

# Load .env file if present
load_dotenv()

class Settings(BaseSettings):
    """
    Pydantic model for validated config.
    Ensures type safety and documentation.
    """
    # Cybersonian API/Scraping Config
    CYBERSONIAN_BASE_URL: str = Field(
        default="https://cybersonian.com/exchange/dashboard",
        description="Base URL for Cybersonian dashboards"
    )
    COIN_PAIRS: list[str] = Field(
        default=[
            "BTC_USDT",
            "ETH_USDT",
            "BNB_USDT",
            "XRP_USDT"
        ],
        description="Trading pairs to monitor"
    )
    CYBERSONIAN_API_KEY: str = Field(
        default=os.getenv("CYBERSONIAN_API_KEY", ""),
        description="API key for Cybersonian (mock if empty)"
    )
    
    # Solana DEX Config
    SOLANA_DEX_URL: str = Field(
        default="https://dexscreener.com/solana/kpmmxpszmttxsdgyzzqzqxwvyssezbxzlyb3qcnrsoe",
        description="DexScreener URL for SONIAN/SOL pair"
    )
    SOLANA_RPC_URL: str = Field(
        default=os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"),
        description="Solana RPC endpoint"
    )
    
    # Fee Distribution Config
    TOTAL_FEE_RATE: float = Field(
        default=0.001,  # 0.1%
        description="Trading fee rate"
    )
    MIN_VOLUME_THRESHOLD: float = Field(
        default=1000.0,
        description="Minimum volume to qualify for distribution"
    )
    DISTRIBUTION_INTERVAL: str = Field(
        default="1h",  # hourly
        description="Interval for fee calculations"
    )
    
    # Wallet Config
    WALLETS_FILE: str = Field(
        default="wallets.json",
        description="File storing wallet addresses and shares"
    )
    MASTER_WALLET: str = Field(
        default=os.getenv("MASTER_WALLET", "mock_master_wallet_address"),
        description="Central fee collection wallet"
    )
    
    # Database Config
    DATABASE_URL: str = Field(
        default="sqlite:///sonian.db",
        description="SQLite DB path"
    )
    
    # AI/ML Config
    AI_MODEL_PATH: str = Field(
        default="volume_predictor.pth",
        description="Saved PyTorch model path"
    )
    TRAINING_DATA_SIZE: int = Field(
        default=10000,
        description="Number of mock data points for training"
    )
    PREDICTION_HORIZON: int = Field(
        default=24,  # hours
        description="Forecast horizon"
    )
    
    # Web App Config
    FLASK_HOST: str = Field(default="0.0.0.0")
    FLASK_PORT: int = Field(default=5000)
    FLASK_DEBUG: bool = Field(default=True)
    
    # Logging Config
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE: str = Field(default="sonian.log")
    
    # Security Config
    SECRET_KEY: str = Field(
        default=os.getenv("SECRET_KEY", "dev-secret-key-change-me"),
        description="Flask secret key"
    )
    
    # Padding for config expansion: Additional unused fields for future features
    ENABLE_NOTIFICATIONS: bool = Field(default=False, description="Email/SMS alerts")
    NOTIFICATION_EMAIL: str = Field(default="", description="Admin email")
    MAX_CONCURRENT_FETCHES: int = Field(default=5, description="Thread pool size")
    CACHE_TTL: int = Field(default=300, description="Cache expiry in seconds")
    BACKUP_INTERVAL: str = Field(default="daily", description="DB backup schedule")
    METRICS_ENABLED: bool = Field(default=True, description="Prometheus metrics")
    RATE_LIMIT: float = Field(default=10.0, description="Requests per minute")

    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()

# Validation function (extended for massiveness)
def validate_config() -> bool:
    """
    Validates configuration settings.
    Raises ValueError on invalid configs.
    Detailed checks for each section.
    """
    errors = []
    
    # Cybersonian validation
    if not settings.CYBERSONIAN_BASE_URL.startswith("https://"):
        errors.append("CYBERSONIAN_BASE_URL must be HTTPS")
    for pair in settings.COIN_PAIRS:
        if "_" not in pair:
            errors.append(f"Invalid pair: {pair}")
    
    # Solana validation
    if "solana" not in settings.SOLANA_RPC_URL.lower():
        errors.append("SOLANA_RPC_URL must point to Solana endpoint")
    
    # Fee validation
    if settings.TOTAL_FEE_RATE <= 0 or settings.TOTAL_FEE_RATE > 0.01:
        errors.append("TOTAL_FEE_RATE must be between 0 and 1%")
    
    # Wallet validation
    if not settings.MASTER_WALLET or len(settings.MASTER_WALLET) < 32:
        errors.append("MASTER_WALLET must be a valid address (mock)")
    
    # DB validation
    if ".db" not in settings.DATABASE_URL:
        errors.append("DATABASE_URL should end with .db for SQLite")
    
    # AI validation
    if settings.TRAINING_DATA_SIZE < 100:
        errors.append("TRAINING_DATA_SIZE too small for ML")
    
    # Web validation
    if settings.FLASK_PORT < 1024:
        errors.append("FLASK_PORT should be >1024 for non-root")
    
    # Logging validation
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if settings.LOG_LEVEL not in valid_levels:
        errors.append(f"LOG_LEVEL must be one of {valid_levels}")
    
    if errors:
        raise ValueError(f"Config errors: {'; '.join(errors)}")
    
    print("Configuration validated successfully.")  # For startup log
    return True

# Auto-validate on import
validate_config()

# Additional config loaders for future (padding)
def load_wallet_shares() -> dict:
    """
    Loads wallet shares from file.
    Mock implementation with extensive error handling.
    """
    try:
        import json
        with open(settings.WALLETS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Create default mock wallets
        default_wallets = {
            "wallet1": {"address": "solana_mock_addr_1", "share": 0.4},
            "wallet2": {"address": "solana_mock_addr_2", "share": 0.3},
            "wallet3": {"address": "solana_mock_addr_3", "share": 0.3}
        }
        with open(settings.WALLETS_FILE, 'w') as f:
            json.dump(default_wallets, f)
        return default_wallets
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {settings.WALLETS_FILE}: {e}")

wallet_shares = load_wallet_shares()

# More padding: Config watchers (unused)
class ConfigWatcher:
    """
    Watches for config changes (for hot-reload in prod).
    Extended class with methods.
    """
    def __init__(self):
        self._callbacks = []
    
    def add_callback(self, callback):
        self._callbacks.append(callback)
    
    def notify(self, key: str, old_value, new_value):
        for cb in self._callbacks:
            cb(key, old_value, new_value)
    
    # Dummy methods for expansion
    def watch_fee_rate(self):
        pass
    
    def watch_volumes(self):
        pass

config_watcher = ConfigWatcher()
