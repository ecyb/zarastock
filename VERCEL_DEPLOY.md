# Vercel Deployment Guide

## Quick Start

1. **Connect to Vercel:**
   - Go to [vercel.com](https://vercel.com)
   - Sign in with GitHub
   - Click "New Project"
   - Import your `zarastock` repository

2. **Set Environment Variables:**
   In Vercel dashboard → Project Settings → Environment Variables, add:
   - `ZARA_PRODUCTS` - Your product API URLs (comma-separated)
   - `TELEGRAM_BOT_TOKEN` - Your Telegram bot token
   - `TELEGRAM_CHAT_ID` - Your Telegram chat ID (or use `chat_ids` in config.json)
   - `SKIP_NOSTOCK_NOTIFICATION` - Set to `true` to skip out-of-stock notifications (optional)

3. **Deploy:**
   - Vercel will automatically detect `vercel.json` and deploy
   - Your API will be available at:
     - `https://your-project.vercel.app/api/check`
     - `https://your-project.vercel.app/api/health`
     - `https://your-project.vercel.app/check` (alias)
     - `https://your-project.vercel.app/health` (alias)

## Testing

After deployment, test with:
```bash
curl https://your-project.vercel.app/api/check
curl https://your-project.vercel.app/api/health
```

## Cron Jobs

To set up automatic checks, use Vercel Cron Jobs or external cron services:
- [cron-job.org](https://cron-job.org)
- [EasyCron](https://www.easycron.com)

Point the cron job to: `https://your-project.vercel.app/api/check`

## Notes

- Vercel serverless functions have a 10-second timeout on Hobby plan
- For longer-running checks, consider upgrading or using Vercel Pro
- The proxy fallback logic will work from Vercel's edge locations

