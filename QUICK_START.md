# Quick Start - Run App & Send Telegram

## Current Status

✅ App is ready to run
✅ Telegram chat IDs configured: `['1042960831', '742044567']`
❌ Bot token needs to be set

## To Run & Send Telegram Notifications

### Option 1: Set Bot Token in config.json

1. Get your bot token from [@BotFather](https://t.me/BotFather) on Telegram
2. Edit `config.json`:
   ```json
   {
     "telegram": {
       "enabled": true,
       "bot_token": "YOUR_ACTUAL_BOT_TOKEN_HERE",
       "chat_ids": ["1042960831", "742044567"]
     }
   }
   ```

3. Run:
   ```bash
   python3 run_and_notify.py
   ```

### Option 2: Set Bot Token via Environment Variable

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
python3 run_and_notify.py
```

### Option 3: Run Flask API Server

```bash
# Set bot token
export TELEGRAM_BOT_TOKEN="your_bot_token_here"

# Start server
python3 app.py

# In another terminal, trigger check:
curl "http://localhost:5000/check?url=https://www.zara.com/itxrest/1/catalog/store/10706/product/id/483276547/availability"
```

## What Will Happen

1. ✅ Stock check via API (no browser needed)
2. ✅ Parse stock availability
3. ✅ Send Telegram notification to both chat IDs
4. ✅ Show beautiful formatted message

## Test Message Preview

**In Stock:**
```
✅ Zara Item In Stock! 🚀

📦 Product Name
💰 Price: £199.00
📏 Available Sizes: XS, S, M, L

🔗 View Product

⏰ Check it out now before it sells out!
```

**Out of Stock:**
```
❌ Zara Item Out of Stock 🚀

📦 Product Name
💰 Price: £199.00
📏 Status: OUT OF STOCK

🔗 View Product

⏰ Will notify you when it's back in stock!
```

## On Railway

Just set the environment variable:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

The app will automatically use it!

