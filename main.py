#!/usr/bin/env python3
"""
Polymarket Whale Tracker - Main Application

Monitors Polymarket for large bets (whales) with robust error handling,
automatic retry logic, and network connectivity monitoring.
"""
import json
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from logger_config import setup_logging
from network_monitor import NetworkMonitor
from polymarket_client_simple import PolymarketClient, PolymarketAPIError
from volume_whale_detector import VolumeWhaleDetector

# Load environment variables from .env file
load_dotenv()

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

        # No authentication required for gamma API
        self.polymarket_client = PolymarketClient(
            max_retries=self.config.get('max_retries', 5),
            initial_retry_delay=self.config.get('initial_retry_delay_seconds', 2),
            backoff_multiplier=self.config.get('retry_backoff_multiplier', 2.0)
        )

        # Use volume-based whale detection (monitors volume spikes)
        self.whale_detector = VolumeWhaleDetector(
            volume_spike_threshold=self.config.get('whale_threshold', 50000)
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

    def _poll_markets(self) -> None:
        """Poll for markets and detect whale volume spikes."""
        try:
            # Check network connectivity first
            if not self.network_monitor.check_connectivity():
                self.network_monitor.wait_for_connection(
                    self.config.get('network_check_interval_seconds', 10)
                )

            # Fetch active markets
            logger.debug("Fetching active markets...")
            markets = self.polymarket_client.get_markets(limit=500, active=True)

            if not markets:
                logger.debug("No markets returned from API")
                return

            logger.debug(f"Fetched {len(markets)} markets")

            # Detect whale volume spikes
            whale_markets = self.whale_detector.process_markets(markets)

            # Alert on new whale activity
            for whale_market in whale_markets:
                alert_message = self.whale_detector.format_whale_alert(whale_market)
                logger.warning(f"\n{alert_message}")

                # Here you could add additional notification methods:
                # - Send to Discord webhook
                # - Send to Telegram
                # - Send email
                # - Write to database
                # - etc.

            if whale_markets:
                stats = self.whale_detector.get_statistics()
                logger.info(
                    f"Stats: {stats['markets_tracked']} markets tracked, "
                    f"{stats['total_spikes_detected']} whale spikes detected"
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

                # Poll for markets
                self._poll_markets()

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
        logger.info(f"  Total markets seen: {stats['total_markets_seen']}")
        logger.info(f"  Markets tracked: {stats['markets_tracked']}")
        logger.info(f"  Whale spikes detected: {stats['total_spikes_detected']}")
        logger.info(f"  Volume spike threshold: ${stats['threshold_usd']:,}")
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
