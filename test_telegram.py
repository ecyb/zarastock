#!/usr/bin/env python3
"""
Test Telegram notification
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load .env file
load_dotenv()

bot_token = os.getenv('api_key') or os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('chat_id') or os.getenv('TELEGRAM_CHAT_ID')

if not bot_token:
    print("❌ Error: api_key or TELEGRAM_BOT_TOKEN not found in .env file")
    sys.exit(1)

if not chat_id:
    print("❌ Error: chat_id or TELEGRAM_CHAT_ID not found in .env file")
    sys.exit(1)

print(f"✅ Bot token found: {bot_token[:10]}...")
print(f"✅ Chat ID found: {chat_id}")

# Test message
test_message = """✅ <b>Test Notification</b>

🧪 This is a test message from Zara Stock Checker!

If you received this, Telegram notifications are working correctly! 🎉"""

url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
payload = {
    'chat_id': chat_id,
    'text': test_message,
    'parse_mode': 'HTML'
}

print("\n📤 Sending test message to Telegram...")
try:
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    result = response.json()
    
    if result.get('ok'):
        print("✅ SUCCESS! Test message sent to Telegram!")
        print("   Check your Telegram app - you should see the test message.")
    else:
        print(f"❌ Error: {result.get('description', 'Unknown error')}")
except requests.exceptions.RequestException as e:
    print(f"❌ Error sending message: {e}")
    if hasattr(e, 'response') and e.response is not None:
        try:
            error_data = e.response.json()
            error_desc = error_data.get('description', 'Unknown')
            print(f"   Telegram API error: {error_desc}")
            
            if 'chat not found' in error_desc.lower():
                print("\n💡 Fix: You need to start a conversation with your bot first!")
                print("   1. Open Telegram")
                print("   2. Search for your bot (the one you created with @BotFather)")
                print("   3. Click 'Start' or send /start command")
                print("   4. Then run this test again")
        except:
            print(f"   Response: {e.response.text}")

