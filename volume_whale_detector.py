"""
Volume-based whale detector that monitors market volume changes.
Since we can't access individual trades without auth, we detect whales
by monitoring large volume spikes in markets.
"""
import logging
import json
from pathlib import Path
from typing import Dict, List, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class VolumeWhaleDetector:
    """Detects whale activity by monitoring volume changes."""

    def __init__(
        self,
        volume_spike_threshold: float = 50000,  # $50K volume increase
        state_dir: str = "state"
    ):
        """
        Initialize volume whale detector.

        Args:
            volume_spike_threshold: Minimum volume increase to trigger alert (USD)
            state_dir: Directory to store state
        """
        self.volume_spike_threshold = volume_spike_threshold
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)

        # Track previous volume for each market
        self.previous_volumes: Dict[str, float] = {}
        self.alerted_markets: Set[str] = set()

        # Statistics
        self.total_markets_seen = 0
        self.total_spikes_detected = 0

        self._load_state()

        logger.info("=" * 80)
        logger.info("Volume Whale Detector initialized")
        logger.info(f"Volume spike threshold: ${self.volume_spike_threshold:,}")
        logger.info("=" * 80)

    def _load_state(self) -> None:
        """Load previous state from disk."""
        state_file = self.state_dir / "volume_state.json"
        try:
            if state_file.exists():
                with open(state_file, 'r') as f:
                    data = json.load(f)
                    self.previous_volumes = data.get('previous_volumes', {})
                    self.alerted_markets = set(data.get('alerted_markets', []))
                    logger.info(f"Loaded state: {len(self.previous_volumes)} markets tracked")
        except Exception as e:
            logger.warning(f"Could not load state: {e}")

    def _save_state(self) -> None:
        """Save current state to disk."""
        state_file = self.state_dir / "volume_state.json"
        try:
            data = {
                'previous_volumes': self.previous_volumes,
                'alerted_markets': list(self.alerted_markets),
                'last_updated': datetime.now().isoformat()
            }
            with open(state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save state: {e}")

    def process_markets(self, markets: List[Dict]) -> List[Dict]:
        """
        Process markets and detect volume spikes.

        Args:
            markets: List of market dictionaries with volume data

        Returns:
            List of markets with whale activity (large volume spikes)
        """
        whale_markets = []

        for market in markets:
            market_id = market.get('id')
            if not market_id:
                continue

            self.total_markets_seen += 1

            # Get current volume (use event_volume_24hr for 24h changes)
            current_volume_24h = float(market.get('event_volume_24hr', 0))
            current_total_volume = float(market.get('event_volume', 0))

            # Skip if already alerted for this market recently
            if market_id in self.alerted_markets:
                # Update volume tracking
                self.previous_volumes[market_id] = current_total_volume
                continue

            # Get previous volume
            previous_volume = self.previous_volumes.get(market_id, 0)

            # Calculate volume increase
            volume_increase = current_total_volume - previous_volume

            # Detect spike
            if volume_increase >= self.volume_spike_threshold:
                logger.info(
                    f"Volume spike detected: {market.get('event_title', 'Unknown')} "
                    f"(+${volume_increase:,.2f})"
                )

                whale_markets.append({
                    'market_id': market_id,
                    'event_title': market.get('event_title', 'Unknown'),
                    'question': market.get('question', 'Unknown'),
                    'category': market.get('category', 'Unknown'),
                    'volume_increase': volume_increase,
                    'total_volume': current_total_volume,
                    'volume_24hr': current_volume_24h,
                    'timestamp': datetime.now().isoformat()
                })

                self.alerted_markets.add(market_id)
                self.total_spikes_detected += 1

            # Update tracking
            self.previous_volumes[market_id] = current_total_volume

        # Save state after processing
        if whale_markets:
            self._save_state()

        return whale_markets

    def format_whale_alert(self, whale_market: Dict) -> str:
        """
        Format whale alert message.

        Args:
            whale_market: Market dictionary with spike data

        Returns:
            Formatted alert string
        """
        separator = "=" * 80
        alert = f"""
{separator}
🐋 WHALE ACTIVITY DETECTED 🐋
{separator}
Market: {whale_market['event_title']}
Question: {whale_market['question']}
Category: {whale_market['category']}
Volume Increase: ${whale_market['volume_increase']:,.2f}
Total Volume: ${whale_market['total_volume']:,.2f}
24h Volume: ${whale_market['volume_24hr']:,.2f}
Timestamp: {whale_market['timestamp']}
{separator}
"""
        return alert

    def get_statistics(self) -> Dict:
        """
        Get detector statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            'total_markets_seen': self.total_markets_seen,
            'markets_tracked': len(self.previous_volumes),
            'total_spikes_detected': self.total_spikes_detected,
            'threshold_usd': self.volume_spike_threshold
        }

    def reset_alerts(self) -> None:
        """Reset the alerted markets set."""
        self.alerted_markets.clear()
        self._save_state()
        logger.info("Reset alerted markets")

    def reset_state(self) -> None:
        """Reset all tracking state."""
        self.previous_volumes.clear()
        self.alerted_markets.clear()
        self._save_state()
        logger.info("Reset all state")
