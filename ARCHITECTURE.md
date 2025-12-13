# 🏗️ Architecture Documentation

## Overview

The Polymarket Whale Tracker is designed with robustness, maintainability, and fault tolerance as primary goals. The architecture follows a modular design with clear separation of concerns.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Main Loop                            │
│                        (main.py)                            │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  1. Check Network Connectivity                        │ │
│  │  2. Poll Polymarket API                               │ │
│  │  3. Detect Whales                                     │ │
│  │  4. Alert on New Whales                               │ │
│  │  5. Wait (Polling Interval)                           │ │
│  │  6. Handle Errors & Retry                             │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
           │                 │                 │
           ▼                 ▼                 ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │   Network   │   │  Polymarket │   │    Whale    │
    │   Monitor   │   │    Client   │   │  Detector   │
    └─────────────┘   └─────────────┘   └─────────────┘
```

## Component Breakdown

### 1. Main Application (`main.py`)

**Responsibilities:**
- Application lifecycle management
- Signal handling (SIGINT, SIGTERM)
- Orchestrating components
- Error recovery and backoff logic
- Graceful shutdown

**Key Features:**
- Infinite polling loop with configurable interval
- Network connectivity checks before each poll
- Consecutive error tracking with automatic shutdown
- Statistics reporting on exit

### 2. Network Monitor (`network_monitor.py`)

**Responsibilities:**
- Internet connectivity detection
- Blocking wait for connection restoration
- Multi-host connectivity verification

**Implementation Details:**
- Tests multiple endpoints (Google DNS, Cloudflare, Polymarket)
- Uses socket connections to verify actual connectivity
- Configurable timeout and check interval
- State tracking (online/offline)

**Robustness Features:**
- Tries multiple hosts before declaring offline
- Handles DNS resolution failures
- Socket timeout protection
- Automatic retry with configurable intervals

### 3. Polymarket Client (`polymarket_client.py`)

**Responsibilities:**
- HTTP communication with Polymarket API
- Request retry logic with exponential backoff
- Rate limit handling
- Response parsing and error handling

**API Endpoints Used:**
- `/markets` - Get list of prediction markets
- `/trades` - Get recent trades across all markets
- `/book` - Get order book for specific tokens
- `/events` - Get recent events

**Robustness Features:**
- Automatic retry on network errors (5 attempts default)
- Exponential backoff (2s → 4s → 8s → 16s → 32s)
- Special handling for rate limits (429 status)
- Server error retry (5xx status codes)
- Request timeout protection (30s default)
- Session reuse for connection pooling

**Error Classification:**
```
Client Errors (4xx)     → No retry (except 429)
Server Errors (5xx)     → Retry with backoff
Network Errors          → Retry with backoff
Timeouts               → Retry with backoff
Rate Limits (429)      → Retry with 2x backoff
```

### 4. Whale Detector (`whale_detector.py`)

**Responsibilities:**
- Trade value calculation
- Whale threshold comparison
- Deduplication of seen trades
- Trader cooldown management
- State persistence

**Detection Algorithm:**

```python
for each trade:
    1. Calculate USD value from size and price
    2. Check if trade ID already seen → skip if yes
    3. Check if value >= threshold
    4. Check trader cooldown → skip if too recent
    5. Mark as whale and alert
    6. Update seen trades and cooldowns
    7. Persist state to disk
```

**Value Calculation Strategy:**
```python
# Try multiple field combinations in order:
1. size * price
2. amount * executionPrice
3. shares * price
4. Direct 'value' or 'usdValue' fields
5. Fallback: size * 0.5 (assume 50/50 odds)
```

**Robustness Features:**
- Multiple field name variations support
- Graceful handling of missing data
- State persistence survives crashes
- Cooldown prevents alert spam
- Statistics tracking

### 5. Logger Configuration (`logger_config.py`)

**Responsibilities:**
- Centralized logging setup
- File and console output
- Color-coded console messages (optional)
- Log rotation and organization

**Features:**
- Dual output: console (INFO+) and file (DEBUG+)
- Timestamped log files
- Color-coded severity levels (when colorlog available)
- Automatic log directory creation

## Data Flow

### Normal Operation Flow

```
1. Check Network
   │
   ├─ Online → Continue
   └─ Offline → Wait until online

2. Fetch Trades (API)
   │
   ├─ Success → Process trades
   ├─ Timeout → Retry (up to 5x)
   ├─ Rate Limit → Backoff and retry
   └─ Error → Log and retry

3. Process Trades
   │
   ├─ Calculate value
   ├─ Check if seen before
   ├─ Compare to threshold
   └─ Check cooldown

4. Alert on Whales
   │
   ├─ Log to console
   ├─ Log to file
   └─ Update state

5. Wait
   │
   └─ Sleep for polling_interval

6. Repeat from step 1
```

### Error Handling Flow

```
Error Occurs
│
├─ Network Error
│  ├─ Check connectivity
│  ├─ Wait if offline
│  └─ Retry when online
│
├─ API Error
│  ├─ Server Error (5xx) → Retry
│  ├─ Rate Limit (429) → Backoff
│  ├─ Client Error (4xx) → Log and skip
│  └─ Timeout → Retry
│
├─ Processing Error
│  ├─ Log error
│  ├─ Skip problematic trade
│  └─ Continue with next
│
└─ Critical Error
   ├─ Track consecutive errors
   ├─ Shutdown if > 10 consecutive
   └─ Otherwise backoff and retry
```

## State Management

### Persisted State (`state/seen_whales.json`)

```json
{
  "seen_trades": [
    "trade_id_1",
    "trade_id_2",
    "..."
  ],
  "trader_alerts": {
    "0xADDRESS1": "2024-01-15T14:23:45",
    "0xADDRESS2": "2024-01-15T15:00:00"
  },
  "last_updated": "2024-01-15T16:00:00"
}
```

### In-Memory State

- Network connectivity status
- HTTP session (connection pooling)
- Error counters
- Current configuration

## Configuration System

All configuration is centralized in `config.json`:

```json
{
  "whale_threshold": 50000,              // Business logic
  "polling_interval_seconds": 60,        // Performance tuning
  "network_check_interval_seconds": 10,  // Network monitoring
  "max_retries": 5,                      // Error handling
  "retry_backoff_multiplier": 2,         // Error handling
  "initial_retry_delay_seconds": 2,      // Error handling
  "log_level": "INFO",                   // Debugging
  "notification_cooldown_minutes": 60    // Business logic
}
```

## Robustness Guarantees

### 1. Network Resilience
- ✅ Survives complete network loss
- ✅ Automatic reconnection
- ✅ No data loss during disconnection
- ✅ Immediate resume on reconnection

### 2. API Resilience
- ✅ Handles rate limiting
- ✅ Retries on server errors
- ✅ Exponential backoff prevents hammering
- ✅ Timeout protection
- ✅ Connection pooling for efficiency

### 3. Data Integrity
- ✅ State persisted to disk
- ✅ Atomic file writes
- ✅ No duplicate alerts
- ✅ Survives process crashes

### 4. Error Recovery
- ✅ Individual trade errors don't stop processing
- ✅ API errors don't crash application
- ✅ Automatic retry with backoff
- ✅ Graceful degradation
- ✅ Comprehensive error logging

### 5. Resource Management
- ✅ Proper session cleanup
- ✅ Signal handling for graceful shutdown
- ✅ No resource leaks
- ✅ Configurable timeouts

## Performance Considerations

### Memory Usage
- **Minimal**: Only stores trade IDs and timestamps
- **Bounded**: Seen trades set grows linearly with unique trades
- **Optimized**: Uses sets for O(1) lookups

### CPU Usage
- **Idle most of the time**: Sleeps between polls
- **Burst processing**: Quick trade processing
- **Configurable**: Adjust polling interval to reduce load

### Network Usage
- **Efficient**: Reuses HTTP connections
- **Configurable**: Adjust polling frequency
- **Typical**: ~100 trades per poll ≈ 10-50KB

### Disk Usage
- **Logs**: Grows over time (one file per run)
- **State**: Small JSON file (< 1MB for 10K trades)
- **Negligible**: Total < 10MB typically

## Extension Points

### Adding Notification Methods

In `main.py`, after whale detection:

```python
for whale_trade in whale_trades:
    alert_message = self.whale_detector.format_whale_alert(whale_trade)
    logger.warning(f"\n{alert_message}")

    # Add your notification here:
    # self.send_discord_notification(alert_message)
    # self.send_telegram_notification(alert_message)
    # self.send_email(alert_message)
```

### Adding Custom Filters

In `whale_detector.py`, modify `process_trades()`:

```python
# Add custom filtering logic:
if value >= self.threshold:
    # Filter by market
    if 'trump' not in trade.get('market', '').lower():
        continue

    # Filter by time
    if not self.is_during_trading_hours():
        continue

    # Your custom logic here
```

### Database Integration

Replace state file persistence with database:

```python
class DatabaseWhaleDetector(WhaleDetector):
    def _load_state(self):
        # Load from database

    def _save_state(self):
        # Save to database
```

## Security Considerations

- ✅ No API keys required (public API)
- ✅ No sensitive data stored
- ✅ Read-only operations
- ✅ No code execution from external sources
- ✅ Input validation on all external data

## Testing Strategy

### Unit Tests (Recommended)
- Test each component in isolation
- Mock API responses
- Test error conditions
- Verify state persistence

### Integration Tests
- Test end-to-end flow
- Use test configuration
- Verify network handling
- Check error recovery

### Manual Testing
- Run `test_connection.py`
- Monitor logs for errors
- Test with different configurations
- Simulate network failures

## Monitoring and Observability

### Logs
- **Location**: `logs/whale_tracker_*.log`
- **Format**: Timestamped, leveled, detailed
- **Retention**: Manual cleanup required

### Metrics to Monitor
- Trades processed per hour
- Whales detected per day
- API error rate
- Network disconnection frequency
- Average processing time per poll

### Health Checks
- Check if process is running
- Check last log timestamp
- Check state file modification time
- Monitor error rate in logs

## Deployment Recommendations

### Development
```bash
python main.py
```

### Production
- Use systemd/launchd service (see README)
- Monitor logs with log aggregation
- Set up alerts for crashes
- Regular log rotation
- Backup state file periodically

### Scalability
- Current design: Single instance per user
- For multiple users: Add database layer
- For high frequency: Add message queue
- For analytics: Add time-series database
