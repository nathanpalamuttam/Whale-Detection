#!/usr/bin/env python3
"""
Polymarket Whale Tracker - Main Application

Monitors Polymarket for large bets (whales) with robust error handling,
automatic retry logic, and network connectivity monitoring.
"""
import json
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Optional

from logger_config import setup_logging
from network_monitor import NetworkMonitor
from polymarket_client import PolymarketClient, PolymarketAPIError
from whale_detector import WhaleDetector

logger = logging.getLogger(__name__)


class WhaleTracker:
    """Main application for tracking Polymarket whales."""

    def __init__(self, config_path: str = "config.json"):
        """
        Initialize whale tracker.

        Args:
            config_path: Path to configuration file
        """
        self.running = False
        self.config = self._load_config(config_path)

        # Setup logging
        setup_logging(self.config.get('log_level', 'INFO'))

        # Initialize components
        self.network_monitor = NetworkMonitor()
        self.polymarket_client = PolymarketClient(
            base_url=self.config.get('polymarket_api_base_url', 'https://clob.polymarket.com'),
            max_retries=self.config.get('max_retries', 5),
            initial_retry_delay=self.config.get('initial_retry_delay_seconds', 2),
            backoff_multiplier=self.config.get('retry_backoff_multiplier', 2.0)
        )
        self.whale_detector = WhaleDetector(
            threshold=self.config.get('whale_threshold', 50000),
            cooldown_minutes=self.config.get('notification_cooldown_minutes', 60)
        )

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("=" * 80)
        logger.info("Polymarket Whale Tracker initialized")
        logger.info("=" * 80)
        logger.info(f"Whale threshold: ${self.config.get('whale_threshold', 50000):,}")
        logger.info(f"Polling interval: {self.config.get('polling_interval_seconds', 60)}s")
        logger.info(f"Network check interval: {self.config.get('network_check_interval_seconds', 10)}s")
        logger.info("=" * 80)

    def _load_config(self, config_path: str) -> dict:
        """
        Load configuration from JSON file.

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dictionary
        """
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            return {}

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"\nReceived signal {signum}, shutting down gracefully...")
        self.running = False

    def _poll_trades(self) -> None:
        """Poll for new trades and detect whales."""
        try:
            # Check network connectivity first
            if not self.network_monitor.check_connectivity():
                self.network_monitor.wait_for_connection(
                    self.config.get('network_check_interval_seconds', 10)
                )

            # Fetch recent trades
            logger.debug("Fetching recent trades...")
            trades = self.polymarket_client.get_trades(limit=200)

            if not trades:
                logger.debug("No trades returned from API")
                return

            logger.debug(f"Fetched {len(trades)} trades")

            # Detect whales
            whale_trades = self.whale_detector.process_trades(trades)

            # Alert on new whales
            for whale_trade in whale_trades:
                alert_message = self.whale_detector.format_whale_alert(whale_trade)
                logger.warning(f"\n{alert_message}")

                # Here you could add additional notification methods:
                # - Send to Discord webhook
                # - Send to Telegram
                # - Send email
                # - Write to database
                # - etc.

            if whale_trades:
                stats = self.whale_detector.get_statistics()
                logger.info(
                    f"Stats: {stats['total_trades_seen']} total trades seen, "
                    f"{stats['unique_whale_traders']} unique whale traders"
                )

        except PolymarketAPIError as e:
            logger.error(f"Polymarket API error: {e}")
            # Continue running despite API errors

        except Exception as e:
            logger.error(f"Unexpected error during polling: {e}", exc_info=True)
            # Continue running despite errors

    def run(self) -> None:
        """Run the whale tracker main loop."""
        self.running = True
        polling_interval = self.config.get('polling_interval_seconds', 60)
        error_count = 0
        max_consecutive_errors = 10

        logger.info("🚀 Starting whale tracker...")

        while self.running:
            try:
                # Check network connectivity
                if not self.network_monitor.check_connectivity():
                    self.network_monitor.wait_for_connection(
                        self.config.get('network_check_interval_seconds', 10)
                    )

                # Poll for trades
                self._poll_trades()

                # Reset error count on successful poll
                error_count = 0

                # Wait before next poll
                logger.debug(f"Waiting {polling_interval}s until next poll...")
                time.sleep(polling_interval)

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received, shutting down...")
                break

            except Exception as e:
                error_count += 1
                logger.error(
                    f"Critical error in main loop (#{error_count}): {e}",
                    exc_info=True
                )

                if error_count >= max_consecutive_errors:
                    logger.critical(
                        f"Too many consecutive errors ({error_count}), shutting down"
                    )
                    break

                # Wait before retrying
                backoff = min(polling_interval, 30 * error_count)
                logger.info(f"Retrying in {backoff}s...")
                time.sleep(backoff)

        self._shutdown()

    def _shutdown(self) -> None:
        """Perform cleanup on shutdown."""
        logger.info("Shutting down whale tracker...")

        try:
            self.polymarket_client.close()
            logger.info("Polymarket client closed")
        except Exception as e:
            logger.error(f"Error closing Polymarket client: {e}")

        stats = self.whale_detector.get_statistics()
        logger.info("=" * 80)
        logger.info("Final Statistics:")
        logger.info(f"  Total trades seen: {stats['total_trades_seen']}")
        logger.info(f"  Unique whale traders: {stats['unique_whale_traders']}")
        logger.info(f"  Whale threshold: ${stats['threshold_usd']:,}")
        logger.info("=" * 80)
        logger.info("Goodbye! 👋")


def main():
    """Entry point for the application."""
    try:
        tracker = WhaleTracker()
        tracker.run()
    except Exception as e:
        logger.critical(f"Failed to start whale tracker: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
