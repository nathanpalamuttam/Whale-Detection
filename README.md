# 🐋 Polymarket Whale Tracker

A robust, production-ready application for tracking large bets (whales) on Polymarket. This tracker automatically monitors all Polymarket trades and alerts you when someone places a bet of $50,000 or more.

## ✨ Features

- **Automatic Polling**: Continuously monitors Polymarket for new trades
- **Whale Detection**: Identifies bets of $50K+ (configurable threshold)
- **Network Resilience**: Automatically pauses when offline and resumes when connectivity is restored
- **Robust Error Handling**: Retry logic with exponential backoff for all API calls
- **Smart Deduplication**: Tracks seen trades to avoid duplicate alerts
- **Cooldown System**: Prevents alert spam from the same trader
- **Persistent State**: Maintains state across restarts
- **Comprehensive Logging**: Color-coded console output and detailed file logs
- **Zero Dependencies on External Services**: Works completely standalone

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Internet connection (program will pause if connection is lost)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/nathanpalamuttam/Whale-Detection.git
cd Whale-Detection
```

2. Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. (Optional) Configure settings by editing `config.json`

### Running the Tracker

Simply run:
```bash
python main.py
```

Or make it executable and run directly:
```bash
chmod +x main.py
./main.py
```

The tracker will:
1. Initialize all components
2. Check network connectivity
3. Start monitoring Polymarket trades
4. Alert you whenever a whale bet is detected
5. Automatically pause if you lose internet and resume when reconnected

## 📋 Configuration

Edit `config.json` to customize behavior:

```json
{
  "whale_threshold": 50000,              // Minimum bet size in USD
  "polling_interval_seconds": 60,        // How often to check for new trades
  "network_check_interval_seconds": 10,  // How often to check connectivity when offline
  "max_retries": 5,                      // Max retry attempts for API calls
  "retry_backoff_multiplier": 2,         // Exponential backoff multiplier
  "initial_retry_delay_seconds": 2,      // Initial delay between retries
  "log_level": "INFO",                   // Logging level (DEBUG, INFO, WARNING, ERROR)
  "notification_cooldown_minutes": 60    // Minutes before re-alerting same trader
}
```

## 📊 Output

When a whale is detected, you'll see:

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

## 📁 Project Structure

```
Whale-Detection/
├── main.py                  # Main application entry point
├── polymarket_client.py     # Polymarket API client with retry logic
├── whale_detector.py        # Whale detection and tracking logic
├── network_monitor.py       # Network connectivity monitoring
├── logger_config.py         # Logging configuration
├── config.json              # Configuration file
├── requirements.txt         # Python dependencies
├── .env.example            # Example environment file
├── .gitignore              # Git ignore rules
├── logs/                   # Log files (auto-created)
└── state/                  # State persistence (auto-created)
    └── seen_whales.json    # Tracks processed trades
```

## 🛡️ Robustness Features

### Network Resilience
- Automatically detects when you're offline
- Pauses operations and waits for connectivity
- Resumes immediately when connection is restored
- Tests multiple endpoints (Google DNS, Cloudflare, Polymarket)

### Error Handling
- Exponential backoff retry for all API calls
- Handles rate limiting gracefully
- Continues running despite individual errors
- Logs all errors for debugging
- Graceful shutdown on critical failures

### State Management
- Persists seen trades to disk
- Survives application restarts
- Prevents duplicate alerts
- Tracks trader alert cooldowns

### Signal Handling
- Graceful shutdown on SIGINT (Ctrl+C)
- Graceful shutdown on SIGTERM
- Cleanup and statistics on exit

## 🔧 Advanced Usage

### Running as a Service

#### Linux (systemd)

Create `/etc/systemd/system/polymarket-whale.service`:

```ini
[Unit]
Description=Polymarket Whale Tracker
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/Whale-Detection
ExecStart=/path/to/Whale-Detection/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable polymarket-whale
sudo systemctl start polymarket-whale
sudo systemctl status polymarket-whale
```

#### macOS (launchd)

Create `~/Library/LaunchAgents/com.polymarket.whale.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.polymarket.whale</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/venv/bin/python</string>
        <string>/path/to/Whale-Detection/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/Whale-Detection</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Load and start:
```bash
launchctl load ~/Library/LaunchAgents/com.polymarket.whale.plist
```

### Viewing Logs

Logs are stored in the `logs/` directory with timestamps:

```bash
# View latest log
tail -f logs/whale_tracker_*.log

# View all whale alerts
grep "WHALE DETECTED" logs/*.log
```

### Resetting State

To start fresh (clear all seen trades):

```python
from whale_detector import WhaleDetector

detector = WhaleDetector()
detector.reset_state()
```

Or simply delete the state file:
```bash
rm state/seen_whales.json
```

## 🔮 Future Enhancements

Potential additions (not yet implemented):

- Discord webhook notifications
- Telegram bot integration
- Email alerts
- Web dashboard
- Database storage
- Historical analysis
- Market-specific filtering
- Price movement correlation

## 🐛 Troubleshooting

### "Connection refused" or "Network unreachable"
- Check your internet connection
- The tracker will automatically pause and resume

### No whales detected
- Whale bets ($50K+) are relatively rare
- Lower the threshold in `config.json` for testing
- Check logs to ensure trades are being fetched

### High CPU usage
- Increase `polling_interval_seconds` in config
- Default is 60 seconds between polls

### Missing dependencies
```bash
pip install -r requirements.txt --upgrade
```

## 📜 License

MIT License - feel free to use and modify as needed.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## ⚠️ Disclaimer

This tool is for informational purposes only. Always verify information independently. Not financial advice.
