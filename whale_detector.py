"""
Whale detection and tracking logic.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class WhaleDetector:
    """Detects and tracks large bets (whales) on Polymarket."""

    def __init__(
        self,
        threshold: float = 50000.0,
        cooldown_minutes: int = 60,
        state_file: str = "state/seen_whales.json"
    ):
        """
        Initialize whale detector.

        Args:
            threshold: Minimum bet size to be considered a whale (in USD)
            cooldown_minutes: Minutes before alerting about same trader again
            state_file: Path to file for tracking seen whales
        """
        self.threshold = threshold
        self.cooldown = timedelta(minutes=cooldown_minutes)
        self.state_file = Path(state_file)
        self.seen_trades: Set[str] = set()
        self.trader_alerts: Dict[str, datetime] = {}
        self._load_state()

    def _load_state(self) -> None:
        """Load previously seen whales from state file."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.seen_trades = set(state.get('seen_trades', []))

                    # Load trader alerts with datetime parsing
                    trader_alerts_raw = state.get('trader_alerts', {})
                    self.trader_alerts = {
                        trader: datetime.fromisoformat(timestamp)
                        for trader, timestamp in trader_alerts_raw.items()
                    }

                logger.info(f"Loaded state: {len(self.seen_trades)} seen trades")
            else:
                logger.info("No previous state found, starting fresh")
                self.state_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            self.seen_trades = set()
            self.trader_alerts = {}

    def _save_state(self) -> None:
        """Save current state to file."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            state = {
                'seen_trades': list(self.seen_trades),
                'trader_alerts': {
                    trader: timestamp.isoformat()
                    for trader, timestamp in self.trader_alerts.items()
                },
                'last_updated': datetime.now().isoformat()
            }

            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _calculate_trade_value(self, trade: Dict) -> Optional[float]:
        """
        Calculate the USD value of a trade.

        Args:
            trade: Trade dictionary from Polymarket API

        Returns:
            Trade value in USD, or None if cannot be calculated
        """
        try:
            # Polymarket trades typically have 'size' (shares) and 'price' fields
            # Price is typically between 0-1 representing probability
            # Size is the number of shares

            # Different API endpoints may return different field names
            size = None
            price = None

            # Try different field name variations
            if 'size' in trade:
                size = float(trade['size'])
            elif 'amount' in trade:
                size = float(trade['amount'])
            elif 'shares' in trade:
                size = float(trade['shares'])

            if 'price' in trade:
                price = float(trade['price'])
            elif 'executionPrice' in trade:
                price = float(trade['executionPrice'])

            if size is not None and price is not None:
                # For binary markets, the value is roughly size * price
                # But the actual USD value is just the size in many cases
                # since each share costs a portion of $1
                return size * price

            # Some APIs might directly provide USD value
            if 'value' in trade:
                return float(trade['value'])
            if 'usdValue' in trade:
                return float(trade['usdValue'])
            if 'notional' in trade:
                return float(trade['notional'])

            # If we have size but no price, assume price is 0.5 (50/50 odds)
            if size is not None:
                return size * 0.5

            return None

        except (ValueError, TypeError, KeyError) as e:
            logger.debug(f"Could not calculate trade value: {e}")
            return None

    def _get_trade_id(self, trade: Dict) -> str:
        """
        Generate a unique ID for a trade.

        Args:
            trade: Trade dictionary

        Returns:
            Unique trade ID
        """
        # Try to use the trade ID if available
        if 'id' in trade:
            return str(trade['id'])

        # Otherwise create a composite key
        trader = trade.get('trader', trade.get('maker', trade.get('taker', 'unknown')))
        timestamp = trade.get('timestamp', trade.get('time', ''))
        market = trade.get('market', trade.get('market_id', ''))

        return f"{trader}_{market}_{timestamp}"

    def should_alert_trader(self, trader: str) -> bool:
        """
        Check if we should alert about this trader (cooldown check).

        Args:
            trader: Trader address/ID

        Returns:
            True if should alert, False if in cooldown period
        """
        if trader not in self.trader_alerts:
            return True

        time_since_last_alert = datetime.now() - self.trader_alerts[trader]
        return time_since_last_alert >= self.cooldown

    def process_trades(self, trades: List[Dict]) -> List[Dict]:
        """
        Process trades and identify whale bets.

        Args:
            trades: List of trade dictionaries from API

        Returns:
            List of whale trades (new ones only)
        """
        whale_trades = []

        for trade in trades:
            try:
                trade_id = self._get_trade_id(trade)

                # Skip if we've already seen this trade
                if trade_id in self.seen_trades:
                    continue

                # Calculate trade value
                value = self._calculate_trade_value(trade)

                if value is None:
                    logger.debug(f"Could not determine value for trade {trade_id}")
                    continue

                # Check if it's a whale trade
                if value >= self.threshold:
                    trader = trade.get('trader', trade.get('maker', trade.get('taker', 'unknown')))

                    # Check cooldown for this trader
                    if self.should_alert_trader(trader):
                        # Add computed value to trade data
                        trade['computed_value_usd'] = value
                        whale_trades.append(trade)

                        # Update tracker
                        self.trader_alerts[trader] = datetime.now()
                        logger.info(
                            f"🐋 WHALE DETECTED: ${value:,.2f} by {trader[:10]}... "
                            f"on market {trade.get('market', 'unknown')}"
                        )
                    else:
                        logger.debug(
                            f"Skipping alert for trader {trader[:10]}... (cooldown)"
                        )

                # Mark trade as seen
                self.seen_trades.add(trade_id)

            except Exception as e:
                logger.error(f"Error processing trade: {e}", exc_info=True)
                continue

        # Save state after processing
        if whale_trades:
            self._save_state()

        return whale_trades

    def format_whale_alert(self, trade: Dict) -> str:
        """
        Format a whale trade into a human-readable alert message.

        Args:
            trade: Trade dictionary with whale information

        Returns:
            Formatted alert string
        """
        value = trade.get('computed_value_usd', 0)
        trader = trade.get('trader', trade.get('maker', trade.get('taker', 'unknown')))
        market = trade.get('market', trade.get('market_id', 'unknown'))
        timestamp = trade.get('timestamp', trade.get('time', 'unknown'))
        side = trade.get('side', trade.get('type', 'unknown'))
        price = trade.get('price', trade.get('executionPrice', 'unknown'))

        alert = [
            "=" * 80,
            "🐋 WHALE ALERT 🐋",
            "=" * 80,
            f"Value: ${value:,.2f}",
            f"Trader: {trader}",
            f"Market: {market}",
            f"Side: {side}",
            f"Price: {price}",
            f"Timestamp: {timestamp}",
            "=" * 80
        ]

        return "\n".join(alert)

    def get_statistics(self) -> Dict:
        """
        Get statistics about detected whales.

        Returns:
            Dictionary with statistics
        """
        return {
            'total_trades_seen': len(self.seen_trades),
            'unique_whale_traders': len(self.trader_alerts),
            'threshold_usd': self.threshold,
            'cooldown_minutes': self.cooldown.total_seconds() / 60
        }

    def reset_state(self) -> None:
        """Reset all state (for testing or manual reset)."""
        self.seen_trades.clear()
        self.trader_alerts.clear()
        self._save_state()
        logger.info("State reset complete")
