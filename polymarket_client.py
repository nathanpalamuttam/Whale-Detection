"""
Polymarket API client with robust error handling and retry logic.
"""
import requests
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class PolymarketAPIError(Exception):
    """Custom exception for Polymarket API errors."""
    pass


class PolymarketClient:
    """Client for interacting with Polymarket API."""

    def __init__(
        self,
        base_url: str = "https://clob.polymarket.com",
        max_retries: int = 5,
        initial_retry_delay: int = 2,
        backoff_multiplier: float = 2.0,
        timeout: int = 30
    ):
        """
        Initialize Polymarket client.

        Args:
            base_url: Base URL for Polymarket API
            max_retries: Maximum number of retry attempts
            initial_retry_delay: Initial delay between retries in seconds
            backoff_multiplier: Multiplier for exponential backoff
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.backoff_multiplier = backoff_multiplier
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PolymarketWhaleTracker/1.0',
            'Accept': 'application/json'
        })

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            **kwargs: Additional arguments for requests

        Returns:
            JSON response as dictionary

        Raises:
            PolymarketAPIError: If request fails after all retries
        """
        url = f"{self.base_url}{endpoint}"
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
                    # Server error, retry
                    logger.warning(
                        f"Server error {response.status_code} on attempt {attempt + 1}/{self.max_retries}"
                    )
                elif response.status_code == 429:
                    # Rate limit, retry with longer delay
                    logger.warning(f"Rate limited on attempt {attempt + 1}/{self.max_retries}")
                    retry_delay *= 2
                else:
                    # Client error, don't retry
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

            # Don't sleep on the last attempt
            if attempt < self.max_retries - 1:
                logger.debug(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= self.backoff_multiplier

        raise PolymarketAPIError(f"Failed after {self.max_retries} attempts")

    def get_markets(self, limit: int = 100, offset: int = 0, closed: bool = False) -> List[Dict]:
        """
        Get list of markets from Polymarket.

        Args:
            limit: Maximum number of markets to return
            offset: Offset for pagination
            closed: Include closed markets

        Returns:
            List of market dictionaries
        """
        try:
            params = {
                'limit': limit,
                'offset': offset,
                'closed': str(closed).lower()
            }

            response = self._make_request('GET', '/markets', params=params)

            # Handle both list response and paginated response
            if isinstance(response, list):
                return response
            elif isinstance(response, dict) and 'data' in response:
                return response['data']
            else:
                logger.warning(f"Unexpected response format: {type(response)}")
                return []

        except Exception as e:
            logger.error(f"Failed to fetch markets: {e}")
            return []

    def get_trades(
        self,
        market_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get recent trades from Polymarket.

        Args:
            market_id: Filter trades by market ID (optional)
            limit: Maximum number of trades to return
            offset: Offset for pagination

        Returns:
            List of trade dictionaries
        """
        try:
            params = {
                'limit': limit,
                'offset': offset
            }

            if market_id:
                params['market'] = market_id

            response = self._make_request('GET', '/trades', params=params)

            # Handle both list response and paginated response
            if isinstance(response, list):
                return response
            elif isinstance(response, dict) and 'data' in response:
                return response['data']
            else:
                logger.warning(f"Unexpected response format: {type(response)}")
                return []

        except Exception as e:
            logger.error(f"Failed to fetch trades: {e}")
            return []

    def get_order_book(self, token_id: str) -> Dict[str, Any]:
        """
        Get order book for a specific token.

        Args:
            token_id: Token ID

        Returns:
            Order book dictionary with bids and asks
        """
        try:
            response = self._make_request('GET', f'/book?token_id={token_id}')
            return response
        except Exception as e:
            logger.error(f"Failed to fetch order book for {token_id}: {e}")
            return {'bids': [], 'asks': []}

    def get_events(self, limit: int = 100) -> List[Dict]:
        """
        Get recent events from Polymarket.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of event dictionaries
        """
        try:
            params = {'limit': limit}
            response = self._make_request('GET', '/events', params=params)

            if isinstance(response, list):
                return response
            elif isinstance(response, dict) and 'data' in response:
                return response['data']
            else:
                return []

        except Exception as e:
            logger.error(f"Failed to fetch events: {e}")
            return []

    def close(self) -> None:
        """Close the session."""
        self.session.close()
