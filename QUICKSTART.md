# 🚀 Quick Start Guide

Get up and running with Polymarket Whale Tracker in 2 minutes!

## Step 1: Install

```bash
# Clone the repository
git clone https://github.com/nathanpalamuttam/Whale-Detection.git
cd Whale-Detection

# Run setup (installs dependencies)
bash setup.sh
```

## Step 2: Run

```bash
# Option 1: Use the run script
./run.sh

# Option 2: Run directly
source venv/bin/activate
python main.py
```

## Step 3: Watch for Whales! 🐋

The tracker will automatically:
- Monitor Polymarket for large bets ($50K+)
- Alert you when whales are detected
- Pause if you lose internet and resume when reconnected
- Keep running indefinitely with robust error handling

## Test First (Optional)

Want to verify everything works before running?

```bash
source venv/bin/activate
python test_connection.py
```

This will test:
- Network connectivity
- Polymarket API connection
- Whale detection logic

## Customization

Want to change the whale threshold or polling frequency?

Edit `config.json`:
```json
{
  "whale_threshold": 50000,          // Change this to your desired threshold
  "polling_interval_seconds": 60     // How often to check (in seconds)
}
```

## Stopping the Tracker

Press `Ctrl+C` to stop gracefully. The tracker will:
- Save current state
- Show statistics
- Clean up resources
- Exit cleanly

## What You'll See

Normal operation:
```
2024-01-15 14:23:45 - INFO - Polymarket Whale Tracker initialized
2024-01-15 14:23:45 - INFO - Whale threshold: $50,000
2024-01-15 14:23:45 - INFO - 🚀 Starting whale tracker...
2024-01-15 14:24:45 - DEBUG - Fetching recent trades...
2024-01-15 14:24:46 - DEBUG - Fetched 150 trades
```

When a whale is detected:
```
================================================================================
🐋 WHALE ALERT 🐋
================================================================================
Value: $75,432.50
Trader: 0x1234567890abcdef...
Market: Will Trump win 2024 election?
Side: BUY
Price: 0.58
Timestamp: 2024-01-15T14:23:45Z
================================================================================
```

When offline:
```
2024-01-15 14:25:00 - WARNING - ✗ Network connectivity lost
2024-01-15 14:25:00 - WARNING - ⏸ Waiting for network connectivity...
2024-01-15 14:25:30 - INFO - ✓ Network connectivity restored
2024-01-15 14:25:30 - INFO - ▶ Network connectivity restored, resuming operations
```

## Need Help?

- Check the full [README.md](README.md) for detailed documentation
- View logs in the `logs/` directory
- Run tests with `python test_connection.py`

## Next Steps

- **Run as a service**: See [README.md](README.md#running-as-a-service) to run 24/7
- **Add notifications**: Extend with Discord/Telegram alerts (see code comments)
- **Analyze data**: Check `state/seen_whales.json` for historical data

Happy whale hunting! 🐋
