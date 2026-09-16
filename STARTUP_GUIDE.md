---
title: "Market Dost AI - Complete Startup Guide"
description: "Step-by-step instructions to get your app running in 5 minutes"
---

# 🚀 Market Dost AI - Complete Startup Guide

## 📋 Prerequisites

Before you start, make sure you have:

- **Git** installed
- **Docker & Docker Compose** (for easiest setup) OR **Python 3.8+**
- **API Keys**:
  - Twelve Data API key (for silver prices)
  - Telegram Bot Token (optional but recommended)
  - Trading Economics API key (optional)

---

## 🎯 FASTEST START (Docker - 3 Steps)

### **Step 1: Clone Repository**
```bash
git clone https://github.com/ravinsangwan2014-boop/Market-dost-ai.git
cd Market-dost-ai
```

### **Step 2: Setup Environment**
```bash
# Copy template
cp .env.example .env

# Edit with your API keys
nano .env
# Or use your favorite editor (VS Code, Sublime, etc.)
```

**What to add in `.env`:**
```env
TWELVE_DATA_API_KEY=your_key_from_twelvedata.com
TELEGRAM_BOT_TOKEN=your_telegram_bot_token (optional)
TELEGRAM_CHAT_ID=your_chat_id (optional)
TRADING_ECONOMICS_API_KEY=your_key (optional)
SILVER_KG=28
SILVER_AVG_COST_INR_PER_KG=171000
TIMEZONE=Asia/Kolkata
```

### **Step 3: Start Services**
```bash
# Start API and Worker
docker-compose up -d

# Check if running
docker-compose ps

# View logs
docker-compose logs -f api
```

✅ **API is live at:** `http://localhost:8080`

---

## 💻 LOCAL PYTHON START (2 Steps)

### **Step 1: Install Dependencies**
```bash
# Navigate to project
cd Market-dost-ai

# Create virtual environment (recommended)
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### **Step 2: Set Environment & Run**
```bash
# Set API keys (replace with your actual keys)
export TWELVE_DATA_API_KEY=your_key_here
export TELEGRAM_BOT_TOKEN=your_token (optional)
export TELEGRAM_CHAT_ID=your_chat_id (optional)

# Run the API server
uvicorn app:app --host 0.0.0.0 --port 8080 --reload
```

**Output should look like:**
```
INFO:     Uvicorn running on http://0.0.0.0:8080
INFO:     Application startup complete
```

✅ **API is live at:** `http://localhost:8080`

---

## ✅ Test Your Setup

### **1. Check if API is Running**
```bash
curl http://localhost:8080/
```

**Expected response:**
```json
{
  "name": "Market Dost AI",
  "version": "2.0.0",
  "status": "running"
}
```

### **2. Check Configuration Status**
```bash
curl http://localhost:8080/health/ready
```

**Response shows which API keys are missing/configured:**
```json
{
  "ready": true,
  "missing": []
}
```

### **3. Get Silver Price (if TWELVE_DATA_API_KEY is set)**
```bash
curl http://localhost:8080/silver
```

**Response:**
```json
{
  "confirmed": true,
  "xag_usd": 28.50,
  "usd_inr": 83.25,
  "indicative_inr_per_kg": 76234.50,
  "note": "Indicative international parity; not MCX/retail physical price."
}
```

### **4. Get Your Portfolio P&L**
```bash
curl http://localhost:8080/mysilver
```

**Response:**
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

---

## 🔗 Quick Command Reference

### **Get All Status**
```bash
# API health
curl http://localhost:8080/health/live

# Readiness check
curl http://localhost:8080/health/ready

# Provider status
curl http://localhost:8080/providers/status

# Release info
curl http://localhost:8080/release
```

### **Market Data**
```bash
# Silver price
curl http://localhost:8080/silver

# Your portfolio
curl http://localhost:8080/mysilver

# Market score
curl http://localhost:8080/score
```

### **Webhook Management**
```bash
# Register webhook
curl -X POST http://localhost:8080/callbacks/register \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-webhook-url.com/notify"}'

# List webhooks
curl http://localhost:8080/callbacks/list

# View callback history
curl http://localhost:8080/callbacks/history

# Unregister webhook
curl -X POST "http://localhost:8080/callbacks/unregister?url=https://your-webhook-url.com/notify"
```

### **Telegram Test**
```bash
# Test Telegram connectivity
curl -X POST http://localhost:8080/telegram/test
```

---

## 🐛 Troubleshooting

### **Problem: "Port 8080 already in use"**
```bash
# Use different port
uvicorn app:app --port 8081

# Or kill process using 8080
# On macOS/Linux:
lsof -ti:8080 | xargs kill -9
# On Windows:
netstat -ano | findstr :8080
taskkill /PID <PID> /F
```

### **Problem: "API key not configured"**
**Solution:** Make sure your `.env` file has the correct keys set
```bash
# Check environment variables are loaded
echo $TWELVE_DATA_API_KEY
# Should print your key, not empty
```

### **Problem: "ModuleNotFoundError: No module named 'fastapi'"**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### **Problem: Docker container won't start**
```bash
# Check logs
docker-compose logs api

# Rebuild container
docker-compose up -d --build

# Stop and restart
docker-compose down
docker-compose up -d
```

### **Problem: "Cannot connect to API"**
```bash
# Make sure Docker is running
docker ps

# Check if container is running
docker-compose ps

# View container logs
docker-compose logs -f api
```

---

## 📊 Monitor Your App

### **View Live Logs (Docker)**
```bash
docker-compose logs -f api
```

### **View API Response Times**
```bash
# Measure request time
time curl http://localhost:8080/silver
```

### **Check System Resources**
```bash
# View Docker resource usage
docker stats market-dost-api
```

### **Access OpenAPI Docs**
```
Open browser: http://localhost:8080/docs
```
(Interactive API documentation!)

---

## 🌐 Access API from Other Machines

If running on a server and want to access from another machine:

```bash
# Get server IP
hostname -I  # Linux
ifconfig    # macOS

# Access from another machine
curl http://<server-ip>:8080/silver
```

---

## 📱 Use with Telegram Bot

1. **Get Telegram Bot Token:**
   - Message `@BotFather` on Telegram
   - Create new bot
   - Copy the token

2. **Get Chat ID:**
   ```bash
   # Send any message to your bot, then:
   curl "https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates"
   # Find "chat":{"id": YOUR_CHAT_ID}
   ```

3. **Add to .env:**
   ```env
   TELEGRAM_BOT_TOKEN=your_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

4. **Test:**
   ```bash
   curl -X POST http://localhost:8080/telegram/test
   # Should send message to your Telegram
   ```

---

## 🚀 Next Steps

1. **Set up webhooks** to receive price alerts:
   ```bash
   curl -X POST http://localhost:8080/callbacks/register \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://your-service.com/webhook",
       "events": ["price_change", "pnl_change"]
     }'
   ```

2. **Deploy to production** (see PRODUCTION.md)

3. **Create automated alerts** based on price movements

4. **Integrate with your trading system**

---

## 📞 Need Help?

- **Check README.md** for detailed documentation
- **Check CHANGELOG.md** for what's new
- **Create an issue** on GitHub
- **Check logs** for error messages

---

## ✨ Success! 

Your Market Dost AI is now running! 🎉

**Next:** Try the test commands above and start using the API!

