"""
Polymarket API client using official py-clob-client with robust error handling.
"""
import logging
import time
from typing import Dict, List, Optional, Any

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import TradeParams
from py_clob_client.exceptions import PolyApiException

logger = logging.getLogger(__name__)


class PolymarketAPIError(Exception):
    """Custom exception for Polymarket API errors."""
    pass


class PolymarketClient:
    """Client for interacting with Polymarket CLOB API using official client."""

    def __init__(
        self,
        private_key: str,
        chain_id: int = 137,  # Polygon mainnet
        signature_type: int = 1,  # EOA (MetaMask)
        funder: Optional[str] = None,
        max_retries: int = 5,
        initial_retry_delay: int = 2,
        backoff_multiplier: float = 2.0,
    ):
        """
        Initialize Polymarket client using official py-clob-client.

        Args:
            private_key: Private key for wallet authentication
            chain_id: Blockchain chain ID (137 for Polygon mainnet)
            signature_type: 1 for EOA/MetaMask, 2 for Polymarket Proxy
            funder: Funder address (required for proxy wallets)
            max_retries: Maximum number of retry attempts
            initial_retry_delay: Initial delay between retries in seconds
            backoff_multiplier: Multiplier for exponential backoff
        """
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay
        self.backoff_multiplier = backoff_multiplier

        try:
            # Initialize the official CLOB client
            self.client = ClobClient(
                host="https://clob.polymarket.com",
                key=private_key,
                chain_id=chain_id,
                signature_type=signature_type,
                funder=funder
            )

            # Create or derive API credentials
            logger.info("Creating API credentials...")
            api_creds = self.client.create_or_derive_api_creds()
            self.client.set_api_creds(api_creds)

            # Test connection
            logger.info("Testing connection to Polymarket CLOB...")
            server_time = self.client.get_server_time()
            logger.info(f"Connected successfully! Server time: {server_time}")

        except Exception as e:
            logger.error(f"Failed to initialize Polymarket client: {e}")
            raise PolymarketAPIError(f"Initialization failed: {e}")

    def _retry_request(self, func, *args, **kwargs):
        """
        Execute a function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            PolymarketAPIError: If request fails after all retries
        """
        retry_delay = self.initial_retry_delay

        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)

            except PolyApiException as e:
                logger.warning(
                    f"API error on attempt {attempt + 1}/{self.max_retries}: {e}"
                )

            except Exception as e:
                logger.warning(
                    f"Error on attempt {attempt + 1}/{self.max_retries}: {e}"
                )

            # Don't sleep on the last attempt
            if attempt < self.max_retries - 1:
                logger.debug(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= self.backoff_multiplier

        raise PolymarketAPIError(f"Failed after {self.max_retries} attempts")

    def get_trades(
        self,
        market: Optional[str] = None,
        maker_address: Optional[str] = None,
        asset_id: Optional[str] = None,
        before: Optional[int] = None,
        after: Optional[int] = None,
    ) -> List[Dict]:
        """
        Get recent trades from Polymarket.

        Args:
            market: Filter trades by market ID (optional)
            maker_address: Filter trades by maker address (optional)
            asset_id: Filter trades by asset ID (optional)
            before: Get trades before this timestamp (optional)
            after: Get trades after this timestamp (optional)

        Returns:
            List of trade dictionaries
        """
        try:
            # Build TradeParams
            params = TradeParams(
                market=market,
                maker_address=maker_address,
                asset_id=asset_id,
                before=before,
                after=after
            )

            trades = self._retry_request(
                self.client.get_trades,
                params=params
            )

            return trades if trades else []

        except Exception as e:
            logger.error(f"Failed to fetch trades: {e}")
            return []

    def get_markets(self, **kwargs) -> List[Dict]:
        """
        Get list of markets from Polymarket.

        Args:
            **kwargs: Parameters for the API

        Returns:
            List of market dictionaries
        """
        try:
            markets = self._retry_request(
                self.client.get_markets,
                **kwargs
            )
            return markets if markets else []

        except Exception as e:
            logger.error(f"Failed to fetch markets: {e}")
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
            book = self._retry_request(
                self.client.get_order_book,
                token_id
            )
            return book if book else {'bids': [], 'asks': []}

        except Exception as e:
            logger.error(f"Failed to fetch order book for {token_id}: {e}")
            return {'bids': [], 'asks': []}

    def close(self) -> None:
        """Close the client (cleanup if needed)."""
        logger.info("Closing Polymarket client")
