# Telegram Notification Setup Guide

## ✅ What's Already Configured

The Telegram notification system is fully integrated with the API-based stock checker:

- ✅ Works with API-based stock checks (no browser needed)
- ✅ Shows method indicator (🚀 for API, 🌐 for HTML)
- ✅ Supports multiple chat IDs
- ✅ Handles both in-stock and out-of-stock notifications
- ✅ Beautiful HTML-formatted messages

## 📱 Setup Instructions

### 1. Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the prompts to name your bot
4. Copy the **bot token** (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get Your Chat ID

1. Start a chat with your bot (search for your bot's username)
2. Send any message to your bot
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Look for `"chat":{"id":123456789}` - that's your chat ID

### 3. Configure in config.json

```json
{
  "telegram": {
    "enabled": true,
    "bot_token": "YOUR_BOT_TOKEN_HERE",
    "chat_id": "YOUR_CHAT_ID",
    "chat_ids": [
      "1042960831",
      "742044567"
    ]
  }
}
```

### 4. Or Use Environment Variables (for Railway)

Set these in Railway dashboard → Variables:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

Or for multiple users:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=1042960831,742044567
```

## 📨 Message Format

### In Stock Message:
```
✅ Zara Item In Stock! 🚀

📦 Wool Double Breasted Coat
💰 Price: £199.00
📏 Available Sizes: XS, S, M, L

🔗 View Product

⏰ Check it out now before it sells out!
```

### Out of Stock Message:
```
❌ Zara Item Out of Stock 🚀

📦 Wool Double Breasted Coat
💰 Price: £199.00
📏 Status: OUT OF STOCK

🔗 View Product

⏰ Will notify you when it's back in stock!
```

## 🔧 Configuration Options

### Skip Out-of-Stock Notifications

In `config.json`:
```json
{
  "skip_nostock_notification": true
}
```

Or via environment variable:
```
SKIP_NOSTOCK_NOTIFICATION=true
```

### Multiple Chat IDs

Add multiple users to receive notifications:
```json
{
  "telegram": {
    "chat_ids": [
      "1042960831",
      "742044567",
      "123456789"
    ]
  }
}
```

## 🧪 Testing

Run the test script:
```bash
python3 test_telegram_api.py
```

This will show you:
- Current Telegram configuration status
- Message previews
- Test sending notifications (if configured)

## 🚀 On Railway

1. Add environment variables in Railway dashboard
2. The app will automatically use them
3. Notifications will be sent when stock changes are detected

## 📝 Notes

- The 🚀 emoji indicates API-based checks (faster, no limits)
- The 🌐 emoji indicates HTML-based checks (fallback)
- Notifications are sent to all configured chat IDs
- Messages use HTML formatting for better readability

