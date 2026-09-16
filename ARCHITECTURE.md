# Market Dost AI - Architecture & Workflow Diagram

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR APPLICATION                         │
│                  (Browser, Mobile, Server)                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────────┐
         │      FastAPI Web Server           │
         │      (Port: 8080)                 │
         │                                   │
         │  ✓ Price Fetching                 │
         │  ✓ P&L Calculation                │
         │  ✓ Webhook Triggers               │
         │  ✓ Telegram Integration           │
         └────┬────────┬────────┬────────────┘
              │        │        │
     ┌────────┘        │        └────────────────┐
     │                 │                         │
     ▼                 ▼                         ▼
┌──────────────┐  ┌──────────────┐      ┌─────────────────┐
│ Twelve Data  │  │   Trading    │      │   Telegram      │
│   API        │  │  Economics   │      │   Bot API       │
│              │  │   API        │      │                 │
│ • XAG/USD    │  │              │      │ • Send Alerts   │
│ • USD/INR    │  │ • Economic   │      │ • Receive Cmds  │
│              │  │   Calendar   │      │                 │
└──────────────┘  └──────────────┘      └─────────────────┘
                         │
                         ▼
            ┌────────────────────────────┐
            │   Your Webhook Servers     │
            │  (External Integrations)   │
            │                            │
            │  Receives notifications:   │
            │  • Price changes           │
            │  • P&L updates             │
            │  • Score changes           │
            └────────────────────────────┘
```

---

## 🔄 Request Flow Diagram

```
CLIENT REQUEST
    │
    ▼
┌─────────────────────────────────┐
│  Validate Request               │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│  Check Configuration            │
│  (API Keys, Settings)           │
└─────────────────────────────────┘
    │
    ├─ YES ──► ┌──────────────────────┐
    │          │ Fetch External API   │
    │          │ (Twelve Data, etc)   │
    │          └──────────────────────┘
    │                    │
    │                    ▼
    │          ┌──────────────────────┐
    │          │ Process Data         │
    │          │ (Calculate P&L, etc) │
    │          └──────────────────────┘
    │                    │
    │                    ▼
    │          ┌──────────────────────┐
    │          │ Trigger Webhooks     │
    │          │ (Non-blocking async) │
    │          └──────────────────────┘
    │                    │
    │                    ▼
    ▼          ┌──────────────────────┐
┌─────────────┤  Return Response     │
│   NO        └──────────────────────┘
│
▼
┌─────────────────────────────────┐
│ Return Error/Missing Config     │
│ ("confirmed": false)            │
└─────────────────────────────────┘
```

---

## 🎯 Data Flow: Get Silver Price

```
GET /silver
    │
    ▼
┌─────────────────────────────────┐
│ Check TD_KEY configured?        │
└─────────────────────────────────┘
    │
    ├─ YES ──► ┌─────────────────────────────┐
    │          │ Call Twelve Data API:       │
    │          │ GET /price?symbol=XAG/USD   │
    │          └─────────────────────────────┘
    │                    │
    │                    ▼
    │          ┌─────────────────────────────┐
    │          │ Get USD/INR Exchange Rate   │
    │          │ GET /price?symbol=USD/INR   │
    │          └─────────────────────────────┘
    │                    │
    │                    ▼
    │          ┌─────────────────────────────┐
    │          │ Calculate Parity:           │
    │          │ XAG_USD × USD_INR × 32.15   │
    │          └─────────────────────────────┘
    │                    │
    │                    ▼
    │          ┌─────────────────────────────┐
    │          │ Trigger Webhooks:           │
    │          │ POST /webhooks (async)      │
    │          └─────────────────────────────┘
    │                    │
    ▼                    ▼
┌────────────────────────────────────┐
│ Return Response:                   │
│ {                                  │
│   "confirmed": true,               │
│   "xag_usd": 28.50,                │
│   "usd_inr": 83.25,                │
│   "indicative_inr_per_kg": 76234.5 │
│ }                                  │
└────────────────────────────────────┘
```

---

## 💰 Data Flow: Get Portfolio P&L

```
GET /mysilver
    │
    ▼
┌──────────────────────────────┐
│ Load Configuration:          │
│ • SILVER_KG = 28             │
│ • AVG_COST = 171000          │
└──────────────────────────────┘
    │
    ▼
┌──────────────────────────────┐
│ Fetch Current Price:         │
│ GET /silver                  │
└──────────────────────────────┘
    │
    ▼
┌──────────────────────────────┐
│ Calculate P&L:               │
│ Cost = 28 × 171000           │
│ Value = 28 × Parity          │
│ PnL = Value - Cost           │
└──────────────────────────────┘
    │
    ▼
┌──────────────────────────────┐
│ Trigger Callbacks:           │
│ event: "pnl_change"          │
│ (async, non-blocking)        │
└──────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────┐
│ Return Response:                     │
│ {                                    │
│   "quantity_kg": 28,                 │
│   "cost_basis_inr": 4788000,         │
│   "indicative_value_inr": 2134575,   │
│   "unrealised_pnl_inr": -2653425,    │
│   "pnl_percentage": -55.44           │
│ }                                    │
└──────────────────────────────────────┘
```

---

## 🔗 Webhook Flow

```
┌────────────────────────────────────┐
│ Price/P&L/Score Updates            │
└────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────┐
│ Check if Webhooks Registered?      │
└────────────────────────────────────┘
    │
    ├─ YES ──┐
    │        │
    │        ▼
    │   ┌─────────────────────────┐
    │   │ For Each Webhook URL:   │
    │   └─────────────────────────┘
    │        │
    │        ▼
    │   ┌──────────────────────────────────┐
    │   │ Create Async Task:               │
    │   │ POST {webhook_url}               │
    │   │ {                                │
    │   │   "event": "price_change",       │
    │   │   "timestamp": "...",            │
    │   │   "data": {...}                  │
    │   │ }                                │
    │   └──────────────────────────────────┘
    │        │
    │        ▼
    │   ┌──────────────────────────────────┐
    │   │ Execute in Background            │
    │   │ (doesn't block response)         │
    │   └──────────────────────────────────┘
    │        │
    │        ▼
    │   ┌──────────────────────────────────┐
    │   │ Log Result in callback_history   │
    │   │ Success/Failure + Timestamp      │
    │   └──────────────────────────────────┘
    │
    └─ NO ──► (Skip, no webhooks registered)
```

---

## 📱 Endpoint Groups

### Group 1: Health & Status
```
Health Probes (for container orchestration)
├── GET /
├── GET /health/live (Kubernetes liveness)
├── GET /health/ready (Kubernetes readiness)
└── GET /providers/status
```

### Group 2: Market Data
```
Market Information
├── GET /silver (Current prices)
├── GET /mysilver (Portfolio P&L)
├── GET /score (Market score)
└── GET /release (Version info)
```

### Group 3: Webhook Management
```
Callback Registration & History
├── POST /callbacks/register (Add webhook)
├── POST /callbacks/unregister (Remove webhook)
├── GET /callbacks/list (View registered webhooks)
└── GET /callbacks/history (View execution history)
```

### Group 4: Telegram
```
Telegram Bot Integration
├── POST /telegram/test (Test connection)
└── POST /telegram/webhook (Receive bot messages)
```

---

## 🔐 Configuration Hierarchy

```
┌──────────────────────────────────┐
│ System Environment Variables     │
│ (docker run -e, .env file, etc)  │
└──────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────┐
│ app.py Reads Configuration:      │
│                                  │
│ TD_KEY = os.getenv(...)          │
│ TG_TOKEN = os.getenv(...)        │
│ SILVER_KG = os.getenv(...)       │
│ AVG_COST = os.getenv(...)        │
└──────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────┐
│ Endpoints Use Configuration      │
│                                  │
│ • /health/ready checks keys      │
│ • /silver uses TD_KEY            │
│ • /mysilver uses SILVER_KG, etc  │
│ • /telegram/* uses TG_TOKEN      │
└──────────────────────────────────┘
```

---

## 🔄 Docker Compose Architecture

```
┌─────────────────────────────────────────┐
│         docker-compose.yml              │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────────┐                   │
│  │  api (FastAPI)   │                   │
│  ├──────────────────┤                   │
│  │ • Port: 8080     │                   │
│  │ • Health checks  │                   │
│  │ • Reads from .env│                   │
│  └────────┬─────────┘                   │
│           │                             │
│           ├─► Twelve Data API           │
│           ├─► Trading Economics API     │
│           ├─► Telegram API              │
│           └─► Your Webhooks             │
│                                         │
│  ┌──────────────────┐                   │
│  │ worker (Python)  │                   │
│  ├──────────────────┤                   │
│  │ • Background job │                   │
│  │ • Polls calendar │                   │
│  │ • Sends alerts   │                   │
│  └────────┬─────────┘                   │
│           │                             │
│           ├─► Trading Economics API     │
│           └─► Telegram API              │
│                                         │
└─────────────────────────────────────────┘
     │
     └─► Shared Environment (.env)
```

---

## 📈 Error Handling Flow

```
Any Request
    │
    ▼
Try:
├─ Fetch Data
├─ Process Data
├─ Trigger Webhooks
└─ Return Response

Except:
├─ Log Error (ERROR level)
├─ Return Safe Response
│  {
│    "confirmed": false,
│    "message": "DATA NOT CONFIRMED",
│    "error": "RequestException"
│  }
└─ Continue (non-blocking)
```

---

## 🎯 Quick Summary

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Client** | Browser, App, Script | Makes HTTP requests |
| **API** | FastAPI (app.py) | Processes requests, fetches data |
| **External APIs** | Twelve Data, Telegram, etc | Provides market data & messaging |
| **Webhooks** | Your Servers | Receives notifications |
| **Storage** | In-memory (callback_history) | Stores callback execution history |
| **Config** | .env file | Stores API keys & settings |

---

## 📞 Support

- **Logs**: Check `docker-compose logs -f api`
- **Docs**: Visit `http://localhost:8080/docs`
- **Issues**: Check GitHub repository
- **Debug**: Use `curl` with `-v` flag for verbose output

```bash
curl -v http://localhost:8080/silver
```

---

**Your Market Dost AI is ready to use! 🚀**
