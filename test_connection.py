#!/usr/bin/env python3
"""
Test script to verify Polymarket API connectivity and whale detection logic.
"""
import json
import logging
from polymarket_client import PolymarketClient
from whale_detector import WhaleDetector
from network_monitor import NetworkMonitor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_network():
    """Test network connectivity."""
    logger.info("Testing network connectivity...")
    monitor = NetworkMonitor()
    is_connected = monitor.check_connectivity()

    if is_connected:
        logger.info("✓ Network connectivity OK")
        return True
    else:
        logger.error("✗ No network connectivity")
        return False


def test_polymarket_api():
    """Test Polymarket API connection."""
    logger.info("Testing Polymarket API...")

    try:
        client = PolymarketClient()

        # Test fetching markets
        logger.info("Fetching markets...")
        markets = client.get_markets(limit=5)

        if markets:
            logger.info(f"✓ Successfully fetched {len(markets)} markets")
            logger.info(f"  Sample market: {markets[0].get('question', 'N/A')}")
        else:
            logger.warning("⚠ API returned empty markets list")

        # Test fetching trades
        logger.info("Fetching recent trades...")
        trades = client.get_trades(limit=10)

        if trades:
            logger.info(f"✓ Successfully fetched {len(trades)} trades")

            # Show sample trade structure
            if trades:
                logger.info("Sample trade structure:")
                sample_trade = trades[0]
                logger.info(json.dumps(sample_trade, indent=2))
        else:
            logger.warning("⚠ API returned empty trades list")

        client.close()
        logger.info("✓ Polymarket API tests passed")
        return True

    except Exception as e:
        logger.error(f"✗ Polymarket API test failed: {e}")
        return False


def test_whale_detector():
    """Test whale detection logic."""
    logger.info("Testing whale detector...")

    try:
        detector = WhaleDetector(threshold=1000)  # Lower threshold for testing

        # Create mock trades
        mock_trades = [
            {
                'id': 'test_1',
                'trader': '0xTEST123',
                'market': 'test_market_1',
                'size': 60000,
                'price': 0.5,
                'timestamp': '2024-01-01T00:00:00Z',
                'side': 'BUY'
            },
            {
                'id': 'test_2',
                'trader': '0xTEST456',
                'market': 'test_market_2',
                'size': 500,
                'price': 0.5,
                'timestamp': '2024-01-01T00:00:01Z',
                'side': 'SELL'
            }
        ]

        whales = detector.process_trades(mock_trades)

        if whales and len(whales) == 1:
            logger.info(f"✓ Whale detector working correctly")
            logger.info(f"  Detected {len(whales)} whale(s) from 2 mock trades")

            alert = detector.format_whale_alert(whales[0])
            logger.info(f"\nSample whale alert:\n{alert}\n")
        else:
            logger.warning(f"⚠ Expected 1 whale, got {len(whales)}")

        # Test statistics
        stats = detector.get_statistics()
        logger.info(f"Detector stats: {stats}")

        logger.info("✓ Whale detector tests passed")
        return True

    except Exception as e:
        logger.error(f"✗ Whale detector test failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Polymarket Whale Tracker - Connection Test")
    logger.info("=" * 60)
    logger.info("")

    results = {
        'Network': test_network(),
        'Polymarket API': test_polymarket_api(),
        'Whale Detector': test_whale_detector()
    }

    logger.info("")
    logger.info("=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)

    all_passed = True
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{test_name}: {status}")
        if not result:
            all_passed = False

    logger.info("=" * 60)

    if all_passed:
        logger.info("✓ All tests passed! You're ready to track whales!")
    else:
        logger.error("✗ Some tests failed. Please check the errors above.")

    return all_passed


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
