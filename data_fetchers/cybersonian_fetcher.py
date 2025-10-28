"""
Cybersonian volume fetcher.
Scrapes dashboard URLs or uses API.
Mocked for demo; replace with real API calls.
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from logger import fetcher_logger
from config import settings
from utils.validators import validate_volume

class CybersonianFetcher:
    """
    Fetches volumes for Cybersonian pairs.
    Supports scraping if no API.
    Extensive error handling and retries.
    """
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'SONIAN-AI/1.0'
        })
        if settings.CYBERSONIAN_API_KEY:
            self.session.headers['Authorization'] = f'Bearer {settings.CYBERSONIAN_API_KEY}'
    
    def fetch_pair_volume(self, pair: str) -> float:
        """
        Fetches volume for a single pair.
        Tries API first, falls back to scraping.
        """
        url = f"{settings.CYBERSONIAN_BASE_URL}?coin_pair={pair}"
        fetcher_logger.info("Fetching %s from %s", pair, url)
        
        try:
            # API attempt
            if settings.CYBERSONIAN_API_KEY:
                api_response = self.session.get(f"{settings.CYBERSONIAN_BASE_URL}/api/volume/{pair}")
                if api_response.status_code == 200:
                    data = api_response.json()
                    volume = data.get('volume_24h', 0.0)
                    fetcher_logger.debug("API success for %s: %.2f", pair, volume)
                    return validate_volume(volume)
            
            # Scraping fallback
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            # Mock selector – replace with real (e.g., '.volume-stat')
            volume_elem = soup.find('div', class_='volume-24h') or soup.find(text=lambda t: 'Volume' in t)
            volume = float(volume_elem.text.replace('$', '').replace(',', '')) if volume_elem else 0.0
            fetcher_logger.warning("Scraped %s volume: %.2f (API failed)", pair, volume)
            return validate_volume(volume)
            
        except requests.RequestException as e:
            fetcher_logger.error("Request error for %s: %s", pair, e)
            return 0.0
        except ValueError as e:
            fetcher_logger.error("Parse error for %s: %s", pair, e)
            return 0.0
    
    def fetch_all_pairs(self, pairs: List[str]) -> Dict[str, float]:
        """
        Fetches all pairs in parallel (mocked with loop for simplicity).
        Returns dict of pair: volume.
        """
        volumes = {}
        for pair in pairs:
            volumes[pair] = self.fetch_pair_volume(pair)
            time.sleep(0.1)  # Rate limit mock
        total = sum(volumes.values())
        fetcher_logger.info("Fetched volumes: %s, total=%.2f", volumes, total)
        if total < settings.MIN_VOLUME_THRESHOLD:
            fetcher_logger.warning("Total volume below threshold: %.2f", total)
        return volumes

# Padding: Retry decorator
def retry(max_attempts=3):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    fetcher_logger.warning("Retry %d/%d for %s: %s", attempt+1, max_attempts, func.__name__, e)
                    time.sleep(2 ** attempt)
        return wrapper
    return decorator

fetch_pair_volume = retry()(CybersonianFetcher.fetch_pair_volume)

# Instance for convenience
fetcher = CybersonianFetcher()

# More padding: Historical fetch method
def fetch_historical(self, pair: str, days: int = 7) -> List[float]:
    """
    Fetches historical volumes.
    Mocked data.
    """
    return [10000 + i*1000 for i in range(days)]  # Dummy

CybersonianFetcher.fetch_historical = fetch_historical
