# Market Dost AI 📈

A FastAPI-based service for real-time silver price monitoring, P&L tracking, and market alerts with webhook callback support.

## Features

✅ Real-time silver prices (XAG/USD) via Twelve Data API  
✅ Automatic INR parity calculation (XAG/USD → INR/kg)  
✅ Personal silver portfolio P&L tracking  
✅ Market score & bias analysis  
✅ Telegram bot integration  
✅ **Webhook callbacks** for price/P&L/score changes  
✅ Economic calendar monitoring (worker service)  
✅ Production-ready with logging & error handling  

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/ravinsangwan2014-boop/Market-dost-ai.git
cd Market-dost-ai

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys

# Start services
docker-compose up -d

# Check health
curl http://localhost:8080/health/live
```

### Option 2: Local Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export TWELVE_DATA_API_KEY=your_key_here
export TELEGRAM_BOT_TOKEN=your_token_here
export TELEGRAM_CHAT_ID=your_chat_id_here

# Run API server
uvicorn app:app --host 0.0.0.0 --port 8080
```

## API Endpoints

### Health & Status
- `GET /` - API status
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness check
- `GET /providers/status` - External provider status

### Market Data
- `GET /silver` - Current silver price & INR parity
- `GET /mysilver` - Personal portfolio P&L
- `GET /score` - Market score & bias
- `GET /release` - Release info

### Callbacks
- `POST /callbacks/register` - Register webhook
- `POST /callbacks/unregister` - Remove webhook
- `GET /callbacks/list` - List all webhooks
- `GET /callbacks/history` - View execution history

### Telegram
- `POST /telegram/test` - Test bot connectivity
- `POST /telegram/webhook` - Telegram bot webhook receiver

## Configuration

All configuration via environment variables:

```env
# Silver Portfolio
SILVER_KG=28
SILVER_AVG_COST_INR_PER_KG=171000

# API Keys (Required)
TWELVE_DATA_API_KEY=your_key
TRADING_ECONOMICS_API_KEY=your_key
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# Optional
TIMEZONE=Asia/Kolkata
WATCHER_INTERVAL_MINUTES=5
ECONOMIC_CALENDAR_MIN_IMPORTANCE=2
CALENDAR_MODE=trading_economics

# Google Calendar (required when CALENDAR_MODE=google)
GOOGLE_CALENDAR_ID=primary
GOOGLE_CALENDAR_ALERT_LEAD_MINUTES=30
GOOGLE_CALENDAR_LOOKBACK_MINUTES=15
GOOGLE_CALENDAR_LOOKAHEAD_MINUTES=180

# Choose one auth method for Google Calendar:
# A) Public calendar
GOOGLE_API_KEY=
# B) Private calendar (OAuth refresh token)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REFRESH_TOKEN=
```

## Usage Examples

### Get Silver Price
```bash
curl http://localhost:8080/silver
```

### Get Portfolio P&L
```bash
curl http://localhost:8080/mysilver
```

### Register a Webhook
```bash
curl -X POST http://localhost:8080/callbacks/register \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-service.com/webhook",
    "events": ["price_change", "pnl_change"]
  }'
```

### View Callback History
```bash
curl http://localhost:8080/callbacks/history?limit=10
```

## Webhook Payload Format

When a callback is triggered, your endpoint receives:

```json
{
  "event": "price_change",
  "timestamp": "2026-09-16T10:30:00.123456",
  "data": {
    "xag_usd": 28.50,
    "usd_inr": 83.25,
    "indicative_inr_per_kg": 76234.50
  }
}
```

## Architecture

```
┌─────────────────────┐
│   Market Dost AI    │
├─────────────────────┤
│ FastAPI Application │
├─────────────────────┤
│ ✓ Price Fetching    │
│ ✓ P&L Calculation   │
│ ✓ Webhook Triggers  │
│ ✓ Telegram Bot      │
└─────────────────────┘
         ↓ ↓ ↓
    [External APIs]
    - Twelve Data
    - Trading Economics
    - Telegram
    - Your Webhooks
```

## Services

### API Service
- Port: 8080
- Health Check: `/health/live`
- Readiness Check: `/health/ready`

### Worker Service (Optional)
- Background economic calendar monitoring
- Supports `CALENDAR_MODE=trading_economics` and `CALENDAR_MODE=google`
- Automatic Telegram alerts
- Configurable polling interval

## Error Handling

- Missing API keys are handled gracefully
- Failed API calls return `confirmed: False`
- Callback failures are logged but don't block responses
- All errors include meaningful error types

## Logging

Application logs are printed to stdout:
- INFO: Major operations (registration, callback triggers)
- WARNING: Missing configs, API issues
- ERROR: Exceptions and failed operations

## Development

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run locally
python -m uvicorn app:app --reload --port 8080

# Test endpoints
curl http://localhost:8080/
curl http://localhost:8080/health/ready
```

## Production Deployment

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: market-dost-api
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: api
        image: market-dost-ai:latest
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8080
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8080
```

### Cloud Run
```bash
gcloud run deploy market-dost-api \
  --source . \
  --platform managed \
  --set-env-vars "TWELVE_DATA_API_KEY=xxx,..."
```

## Testing

```bash
# Basic connectivity
curl http://localhost:8080/health/live

# Check config status
curl http://localhost:8080/health/ready

# Get silver price
curl http://localhost:8080/silver

# Get portfolio status
curl http://localhost:8080/mysilver
```

## License

MIT

## Support

For issues, questions, or suggestions: [Create an Issue](https://github.com/ravinsangwan2014-boop/Market-dost-ai/issues)

---

**Made with ❤️ for silver investors**
