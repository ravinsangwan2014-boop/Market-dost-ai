# Market Dost AI - Quick Reference Card

## 🚀 START HERE (Copy & Paste)

### **Docker (Easiest)**
```bash
git clone https://github.com/ravinsangwan2014-boop/Market-dost-ai.git
cd Market-dost-ai
cp .env.example .env
# Edit .env with your API keys
docker-compose up -d
curl http://localhost:8080/
```

### **Python (Local)**
```bash
cd Market-dost-ai
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows
pip install -r requirements.txt
export TWELVE_DATA_API_KEY=your_key
uvicorn app:app --port 8080
```

---

## 📡 API Endpoints (Ready to Use)

| Method | Endpoint | Purpose | Response |
|--------|----------|---------|----------|
| `GET` | `/` | API Status | `{"status": "running"}` |
| `GET` | `/health/live` | Liveness Probe | `{"ok": true}` |
| `GET` | `/health/ready` | Config Check | `{"ready": true, "missing": []}` |
| `GET` | `/silver` | Silver Price + Parity | `{"xag_usd": 28.5, "usd_inr": 83.25, ...}` |
| `GET` | `/mysilver` | Portfolio P&L | `{"quantity_kg": 28, "unrealised_pnl_inr": ...}` |
| `GET` | `/score` | Market Score | `{"score": 50, "bias": "Neutral"}` |
| `GET` | `/providers/status` | API Keys Status | `{"market_feed": true, ...}` |
| `POST` | `/callbacks/register` | Add Webhook | `{"message": "Callback registered"}` |
| `GET` | `/callbacks/list` | List Webhooks | `{"callbacks": [...], "total": 1}` |
| `GET` | `/callbacks/history` | Webhook History | `{"history": [...]}` |
| `POST` | `/callbacks/unregister` | Remove Webhook | `{"message": "Callback unregistered"}` |
| `POST` | `/telegram/test` | Test Telegram | `{"sent": true}` |

---

## 🧪 Test Commands (Copy & Paste)

```bash
# 1. Check if API is running
curl http://localhost:8080/

# 2. Check configuration
curl http://localhost:8080/health/ready

# 3. Get silver price (requires TWELVE_DATA_API_KEY)
curl http://localhost:8080/silver

# 4. Get your portfolio P&L
curl http://localhost:8080/mysilver

# 5. Get market score
curl http://localhost:8080/score

# 6. Register a webhook
curl -X POST http://localhost:8080/callbacks/register \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-webhook.com/notify"}'

# 7. List all webhooks
curl http://localhost:8080/callbacks/list

# 8. View webhook history
curl http://localhost:8080/callbacks/history?limit=10

# 9. Test Telegram
curl -X POST http://localhost:8080/telegram/test
```

---

## ⚙️ Environment Variables

```env
# REQUIRED
TWELVE_DATA_API_KEY=your_api_key_from_twelvedata.com

# OPTIONAL
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
TRADING_ECONOMICS_API_KEY=your_key

# PORTFOLIO CONFIG
SILVER_KG=28                              # Your silver quantity
SILVER_AVG_COST_INR_PER_KG=171000        # Average cost per kg

# OPTIONAL CONFIG
TIMEZONE=Asia/Kolkata
WATCHER_INTERVAL_MINUTES=5
ECONOMIC_CALENDAR_MIN_IMPORTANCE=2
```

---

## 📊 Response Examples

### Silver Price Response
```json
{
  "confirmed": true,
  "xag_usd": 28.50,
  "usd_inr": 83.25,
  "indicative_inr_per_kg": 76234.50,
  "note": "Indicative international parity; not MCX/retail physical price."
}
```

### Portfolio P&L Response
```json
{
  "confirmed": true,
  "quantity_kg": 28,
  "avg_cost_inr_per_kg": 171000,
  "cost_basis_inr": 4788000.0,
  "indicative_value_inr": 2134575.0,
  "unrealised_pnl_inr": -2653425.0,
  "pnl_percentage": -55.44
}
```

### Webhook Payload (Received at your endpoint)
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

---

## 🔍 Status Codes

| Code | Meaning |
|------|----------|
| 200 | ✅ Success |
| 400 | ❌ Bad Request |
| 404 | ❌ Not Found |
| 500 | ❌ Server Error |

---

## 🛠️ Common Tasks

### Get Silver Price
```bash
curl http://localhost:8080/silver | python -m json.tool
```

### Monitor P&L (Every 5 seconds)
```bash
watch -n 5 'curl -s http://localhost:8080/mysilver | python -m json.tool'
```

### Register Multiple Webhooks
```bash
for url in "https://webhook1.com" "https://webhook2.com"; do
  curl -X POST http://localhost:8080/callbacks/register \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"$url\"}"
done
```

### Get Config Status
```bash
curl http://localhost:8080/health/ready | python -m json.tool
```

### Check All Providers
```bash
curl http://localhost:8080/providers/status | python -m json.tool
```

---

## 📱 Docker Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f api

# Check status
docker-compose ps

# Restart
docker-compose restart api

# Rebuild
docker-compose up -d --build
```

---

## 🐍 Python Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run with auto-reload (development)
uvicorn app:app --reload --port 8080

# Run normally (production)
uvicorn app:app --host 0.0.0.0 --port 8080

# View in browser
# API Docs: http://localhost:8080/docs
# ReDoc: http://localhost:8080/redoc
```

---

## 🚨 Troubleshooting

| Problem | Solution |
|---------|----------|
| Port 8080 in use | Change port: `--port 8081` or kill process |
| API key error | Check `.env` file is in root directory |
| Docker won't start | Run: `docker-compose up -d --build` |
| Can't connect | Ensure Docker/Python is running: `docker ps` or check Python process |
| Module not found | Reinstall: `pip install -r requirements.txt` |
| Webhook not working | Check URL is publicly accessible |

---

## 📚 Documentation Files

- **README.md** - Full documentation
- **STARTUP_GUIDE.md** - Detailed setup instructions
- **CHANGELOG.md** - Version history
- **This file** - Quick reference

---

## 🎯 Next Steps

1. ✅ Clone repo
2. ✅ Configure .env
3. ✅ Start service
4. ✅ Test endpoints
5. ✅ Register webhooks
6. ✅ Deploy to production

---

## 💡 Tips

- Use `curl` or **Postman** for testing
- Access interactive docs at `/docs`
- Watch logs in real-time: `docker-compose logs -f`
- Save responses: `curl ... > response.json`
- Pretty print JSON: `| python -m json.tool`

---

**Made with ❤️ for silver investors** 📈
