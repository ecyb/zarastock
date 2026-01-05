#!/usr/bin/env python3
"""
Delete all previous messages from the bot for configured users
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load .env file
try:
    load_dotenv()
except:
    pass

# Load config
config_file = "config.json"
if os.path.exists(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
else:
    config = {}

# Get bot token
bot_token = (
    os.getenv('TELEGRAM_BOT_TOKEN') or 
    os.getenv('api_key') or 
    config.get('telegram', {}).get('bot_token', '')
)

if not bot_token or bot_token == 'YOUR_BOT_TOKEN':
    print("❌ Bot token not found!")
    print("Set TELEGRAM_BOT_TOKEN or api_key in .env, or bot_token in config.json")
    exit(1)

# Get chat IDs
telegram_config = config.get('telegram', {})
chat_ids = []

# Add single chat_id if specified
chat_id = telegram_config.get('chat_id', '')
if chat_id:
    chat_ids.append(str(chat_id))

# Add all chat_ids from list
chat_ids_list = telegram_config.get('chat_ids', [])
if chat_ids_list:
    chat_ids.extend([str(cid) for cid in chat_ids_list])

# Remove duplicates
chat_ids = list(set(chat_ids))

if not chat_ids:
    print("❌ No chat IDs configured!")
    print("Add chat_id or chat_ids in config.json")
    exit(1)

print("=" * 60)
print("🗑️  Delete Bot Messages")
print("=" * 60)
print(f"Bot Token: {bot_token[:10]}...")
print(f"Chat IDs: {chat_ids}")
print()

def get_updates(offset=None):
    """Get updates from Telegram."""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    params = {'timeout': 1}
    if offset:
        params['offset'] = offset
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error getting updates: {e}")
        return None

def delete_message(chat_id, message_id):
    """Delete a message."""
    url = f"https://api.telegram.org/bot{bot_token}/deleteMessage"
    params = {
        'chat_id': chat_id,
        'message_id': message_id
    }
    
    try:
        response = requests.post(url, json=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"   ❌ Error deleting message {message_id}: {e}")
        return None

# Get all messages from bot
print("📥 Fetching messages from bot...")
all_messages = []

# Get updates to find message IDs
print("   Getting recent updates...")
updates = get_updates()
if updates and updates.get('ok'):
    for update in updates.get('result', []):
        if 'message' in update:
            message = update['message']
            chat_id = str(message.get('from', {}).get('id', ''))
            message_id = message.get('message_id')
            from_bot = message.get('from', {}).get('is_bot', False)
            
            # Only track messages from our bot
            if from_bot and chat_id in chat_ids:
                all_messages.append({
                    'chat_id': chat_id,
                    'message_id': message_id,
                    'text': message.get('text', '')[:50]
                })

print(f"   Found {len(all_messages)} messages from bot")
print()

# Check for command line arguments (delete specific message IDs)
import sys
if len(sys.argv) > 1:
    message_ids = []
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == '--range' and i < len(sys.argv) - 2:
            # Range mode: --range start end
            try:
                start_id = int(sys.argv[i + 1])
                end_id = int(sys.argv[i + 2])
                message_ids.extend(range(start_id, end_id + 1))
                break
            except:
                pass
        elif arg.isdigit():
            message_ids.append(int(arg))
    
    if message_ids:
        print(f"🗑️  Deleting {len(message_ids)} specific messages...")
        deleted_count = 0
        failed_count = 0
        
        for chat_id in chat_ids:
            for msg_id in message_ids:
                result = delete_message(chat_id, msg_id)
                if result and result.get('ok'):
                    print(f"   ✅ Deleted message {msg_id} from chat {chat_id}")
                    deleted_count += 1
                else:
                    failed_count += 1
        
        print()
        print("=" * 60)
        print(f"✅ Deleted: {deleted_count}")
        print(f"❌ Failed: {failed_count}")
        print("=" * 60)
        exit(0)

if not all_messages:
    print("⚠️  No messages found from bot in recent updates")
    print("   Note: Telegram only returns recent updates (last 24 hours)")
    print("   Older messages cannot be retrieved via API")
    print()
    print("💡 To delete specific messages:")
    print("   python3 delete_bot_messages.py <message_id1> <message_id2> ...")
    print("   Example: python3 delete_bot_messages.py 55 56 57")
    print("   Or range: python3 delete_bot_messages.py --range 55 60")
    exit(0)

# Delete messages
print("🗑️  Deleting messages...")
deleted_count = 0
failed_count = 0

for msg in all_messages:
    chat_id = msg['chat_id']
    message_id = msg['message_id']
    text_preview = msg['text']
    
    print(f"   Deleting message {message_id} from chat {chat_id}...")
    result = delete_message(chat_id, message_id)
    
    if result and result.get('ok'):
        print(f"   ✅ Deleted: {text_preview}...")
        deleted_count += 1
    else:
        print(f"   ❌ Failed to delete message {message_id}")
        failed_count += 1

print()
print("=" * 60)
print(f"✅ Deleted: {deleted_count}")
print(f"❌ Failed: {failed_count}")
print("=" * 60)
print()
print("💡 Note: Telegram API only returns recent updates (last 24 hours)")
print("   Older messages cannot be deleted via API")
print("   Users can manually delete messages in their Telegram app")

