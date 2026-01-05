#!/usr/bin/env python3
"""
Set up Telegram webhook to receive bot updates
This allows the bot to automatically register users when they press /start
"""

import os
import sys
import requests

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # e.g., https://your-app.vercel.app/api/webhook


def set_webhook(webhook_url: str):
    """Set Telegram webhook URL."""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set in environment")
        print("   Set it in .env file or export it:")
        print("   export TELEGRAM_BOT_TOKEN=your_bot_token")
        return False
    
    if not webhook_url:
        print("❌ WEBHOOK_URL not set")
        print("   Set it in .env file or export it:")
        print("   export WEBHOOK_URL=https://your-app.vercel.app/api/webhook")
        print()
        print("   Or pass it as an argument:")
        print("   python3 setup_webhook.py https://your-app.vercel.app/api/webhook")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    payload = {
        'url': webhook_url
    }
    
    print("=" * 60)
    print("🔧 Setting up Telegram webhook...")
    print("=" * 60)
    print(f"   Bot Token: {TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"   Webhook URL: {webhook_url}")
    print()
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('ok'):
            print("✅ Webhook set successfully!")
            print(f"   Description: {data.get('description', 'N/A')}")
            
            # Get webhook info
            info_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
            info_response = requests.get(info_url, timeout=10)
            if info_response.status_code == 200:
                info_data = info_response.json()
                if info_data.get('ok'):
                    webhook_info = info_data.get('result', {})
                    print()
                    print("📋 Webhook Info:")
                    print(f"   URL: {webhook_info.get('url', 'N/A')}")
                    print(f"   Pending Updates: {webhook_info.get('pending_update_count', 0)}")
                    if webhook_info.get('last_error_date'):
                        print(f"   ⚠️  Last Error: {webhook_info.get('last_error_message', 'N/A')}")
                        print(f"   Last Error Date: {webhook_info.get('last_error_date', 'N/A')}")
            
            print()
            print("=" * 60)
            print("✅ Done! Users can now press /start to register automatically")
            print("=" * 60)
            return True
        else:
            print(f"❌ Failed to set webhook: {data.get('description', 'Unknown error')}")
            return False
    
    except Exception as e:
        print(f"❌ Error setting webhook: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_webhook_info():
    """Get current webhook info."""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('ok'):
            webhook_info = data.get('result', {})
            print("=" * 60)
            print("📋 Current Webhook Info:")
            print("=" * 60)
            print(f"   URL: {webhook_info.get('url', 'Not set')}")
            print(f"   Pending Updates: {webhook_info.get('pending_update_count', 0)}")
            if webhook_info.get('last_error_date'):
                print(f"   ⚠️  Last Error: {webhook_info.get('last_error_message', 'N/A')}")
                print(f"   Last Error Date: {webhook_info.get('last_error_date', 'N/A')}")
            print("=" * 60)
        else:
            print(f"❌ Error: {data.get('description', 'Unknown error')}")
    
    except Exception as e:
        print(f"❌ Error getting webhook info: {e}")


def delete_webhook():
    """Delete webhook (stop receiving updates)."""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook"
    
    print("=" * 60)
    print("🗑️  Deleting webhook...")
    print("=" * 60)
    
    try:
        response = requests.post(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('ok'):
            print("✅ Webhook deleted successfully!")
            return True
        else:
            print(f"❌ Failed to delete webhook: {data.get('description', 'Unknown error')}")
            return False
    
    except Exception as e:
        print(f"❌ Error deleting webhook: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'info':
            get_webhook_info()
        elif command == 'delete':
            delete_webhook()
        elif command.startswith('http'):
            # URL provided as argument
            set_webhook(command)
        else:
            print("Usage:")
            print("  python3 setup_webhook.py <webhook_url>  # Set webhook")
            print("  python3 setup_webhook.py info           # Get webhook info")
            print("  python3 setup_webhook.py delete         # Delete webhook")
    else:
        # Try to use WEBHOOK_URL from environment
        webhook_url = WEBHOOK_URL
        if not webhook_url:
            print("=" * 60)
            print("❌ WEBHOOK_URL not provided")
            print("=" * 60)
            print()
            print("Usage:")
            print("  1. Set WEBHOOK_URL environment variable:")
            print("     export WEBHOOK_URL=https://your-app.vercel.app/api/webhook")
            print("     python3 setup_webhook.py")
            print()
            print("  2. Or pass webhook URL as argument:")
            print("     python3 setup_webhook.py https://your-app.vercel.app/api/webhook")
            print()
            print("  3. Or check current webhook info:")
            print("     python3 setup_webhook.py info")
            print()
            print("  4. Or delete webhook:")
            print("     python3 setup_webhook.py delete")
            sys.exit(1)
        
        set_webhook(webhook_url)

