# Environment Variables for Vercel

## Required Variables

### Telegram Bot Token
**Use:** `TELEGRAM_BOT_TOKEN`
- This is your Telegram bot token from @BotFather
- Alternative names also supported: `api_key` or `TELEGRAM_API_KEY`

### Telegram Chat ID(s)
**Use:** `TELEGRAM_CHAT_ID` (for single chat)
- OR use `chat_id` (also supported)
- For multiple chats, use `chat_ids` array in `config.json` instead

## Optional Variables

### Products
**Use:** `ZARA_PRODUCTS`
- Comma-separated list of product API URLs
- Example: `https://www.zara.com/itxrest/1/catalog/store/10706/product/id/483276547/availability`

### Skip Out-of-Stock Notifications
**Use:** `SKIP_NOSTOCK_NOTIFICATION`
- Set to `true` to skip notifications when items are out of stock
- Set to `false` or leave unset to send all notifications

## Summary

**In Vercel Dashboard → Environment Variables, set:**
1. `TELEGRAM_BOT_TOKEN` = your bot token
2. `TELEGRAM_CHAT_ID` = your chat ID (or use `chat_ids` in config.json for multiple)
3. `ZARA_PRODUCTS` = your product URLs (comma-separated)
4. `SKIP_NOSTOCK_NOTIFICATION` = `true` or `false` (optional)

## Multiple Chat IDs

If you need to send to multiple Telegram chats:
- Option 1: Set `TELEGRAM_CHAT_ID` and add more in `config.json` under `telegram.chat_ids`
- Option 2: Use only `config.json` with `telegram.chat_ids` array

Example `config.json`:
```json
{
  "telegram": {
    "enabled": true,
    "bot_token": "your_token_here",
    "chat_ids": ["1042960831", "742044567"]
  }
}
```

