"""
Simple Polymarket API client using gamma API (no authentication required).
This monitors market volume changes to detect whale activity.
"""
import requests
import logging
from typing import Dict, List, Optional
import time

logger = logging.getLogger(__name__)


class PolymarketAPIError(Exception):
    """Custom exception for Polymarket API errors."""
    pass


class PolymarketClient:
    """Client for Polymarket gamma API - no authentication required."""

    BASE_URL = "https://gamma-api.polymarket.com"

    def __init__(
        self,
        max_retries: int = 5,
        initial_retry_delay: int = 2,
        backoff_multiplier: float = 2.0,
        timeout: int = 30
    ):
        """
        Initialize Polymarket client.

        Args:
            max_retries: Maximum number of retry attempts
            initial_retry_delay: Initial delay between retries in seconds
            backoff_multiplier: Multiplier for exponential backoff
            timeout: Request timeout in seconds
        """
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.backoff_multiplier = backoff_multiplier
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PolymarketWhaleTracker/1.0',
            'Accept': 'application/json'
        })
        logger.info("Initialized Polymarket gamma API client (no auth required)")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        **kwargs
    ) -> Dict:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            **kwargs: Additional arguments for requests

        Returns:
            JSON response

        Raises:
            PolymarketAPIError: If request fails after all retries
        """
        url = f"{self.BASE_URL}{endpoint}"
        retry_delay = self.initial_retry_delay

        for attempt in range(self.max_retries):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=self.timeout,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError as e:
                if response.status_code >= 500:
                    logger.warning(
                        f"Server error {response.status_code} on attempt {attempt + 1}/{self.max_retries}"
                    )
                elif response.status_code == 429:
                    logger.warning(f"Rate limited on attempt {attempt + 1}/{self.max_retries}")
                    retry_delay *= 2
                else:
                    raise PolymarketAPIError(f"HTTP {response.status_code}: {e}")

            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout on attempt {attempt + 1}/{self.max_retries}")

            except requests.exceptions.ConnectionError as e:
                logger.warning(
                    f"Connection error on attempt {attempt + 1}/{self.max_retries}: {e}"
                )

            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                raise PolymarketAPIError(f"Request failed: {e}")

            if attempt < self.max_retries - 1:
                logger.debug(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= self.backoff_multiplier

        raise PolymarketAPIError(f"Failed after {self.max_retries} attempts")

    def get_markets(
        self,
        limit: int = 100,
        offset: int = 0,
        active: bool = True,
        closed: bool = False
    ) -> List[Dict]:
        """
        Get markets from Polymarket events endpoint.

        Args:
            limit: Maximum number of events to return
            offset: Offset for pagination
            active: Include active markets
            closed: Include closed markets

        Returns:
            List of market dictionaries with volume data
        """
        try:
            params = {
                'limit': limit,
                'offset': offset,
                'active': str(active).lower(),
                'closed': str(closed).lower()
            }

            events = self._make_request('GET', '/events', params=params)

            # Flatten markets from events
            markets = []
            for event in events:
                event_markets = event.get('markets', [])
                for market in event_markets:
                    # Add event-level volume data
                    market['event_volume'] = event.get('volume', 0)
                    market['event_volume_24hr'] = event.get('volume24hr', 0)
                    market['event_title'] = event.get('title', '')
                    market['category'] = event.get('category', '')
                    markets.append(market)

            return markets

        except Exception as e:
            logger.error(f"Failed to fetch markets: {e}")
            return []

    def get_events(
        self,
        limit: int = 100,
        offset: int = 0,
        active: bool = True,
        closed: bool = False
    ) -> List[Dict]:
        """
        Get events with volume data from Polymarket.

        Args:
            limit: Maximum number of events to return
            offset: Offset for pagination
            active: Include active events
            closed: Include closed events

        Returns:
            List of event dictionaries with volume data
        """
        try:
            params = {
                'limit': limit,
                'offset': offset,
                'active': str(active).lower(),
                'closed': str(closed).lower()
            }

            events = self._make_request('GET', '/events', params=params)
            return events if events else []

        except Exception as e:
            logger.error(f"Failed to fetch events: {e}")
            return []

    def close(self) -> None:
        """Close the session."""
        self.session.close()
        logger.info("Closed Polymarket client")
