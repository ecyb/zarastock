#!/usr/bin/env python3
"""
Telegram Bot for Auto-Registration
Users can send /start to automatically register for stock notifications.
"""

import json
import os
import time
import requests
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class TelegramRegistrationBot:
    """Simple Telegram bot that handles user registration via /start command."""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.bot_token = self.get_bot_token()
        self.last_update_id = 0
        
    def load_config(self) -> Dict:
        """Load configuration from config.json."""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_config(self):
        """Save configuration to config.json."""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get_bot_token(self) -> str:
        """Get bot token from config or environment."""
        # Load .env first
        load_dotenv()
        
        # Check environment variables FIRST (they take priority)
        bot_token = (
            os.getenv('api_key') or
            os.getenv('TELEGRAM_BOT_TOKEN') or
            os.getenv('TELEGRAM_API_KEY') or
            ''
        )
        
        # If not in env, check config.json (but ignore placeholders)
        if not bot_token or bot_token in ['YOUR_BOT_TOKEN', '']:
            telegram_config = self.config.get('telegram', {})
            config_token = telegram_config.get('bot_token', '')
            if config_token and config_token not in ['YOUR_BOT_TOKEN', '']:
                bot_token = config_token
            else:
                bot_token = ''
        
        return bot_token
    
    def get_updates(self, timeout: int = 30) -> List[Dict]:
        """Get updates from Telegram Bot API."""
        if not self.bot_token:
            return []
        
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {
            'offset': self.last_update_id + 1,
            'timeout': timeout,
            'allowed_updates': ['message']
        }
        
        try:
            response = requests.get(url, params=params, timeout=timeout + 5)
            response.raise_for_status()
            data = response.json()
            
            if data.get('ok'):
                updates = data.get('result', [])
                if updates:
                    self.last_update_id = updates[-1]['update_id']
                return updates
        except Exception as e:
            print(f"⚠️  Error getting updates: {e}")
        
        return []
    
    def send_message(self, chat_id: str, text: str, parse_mode: str = 'HTML') -> bool:
        """Send a message to a chat."""
        if not self.bot_token:
            return False
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"⚠️  Error sending message: {e}")
            return False
    
    def register_user(self, chat_id: str) -> bool:
        """Register a user by adding their chat_id to the config."""
        if 'telegram' not in self.config:
            self.config['telegram'] = {}
        
        telegram_config = self.config['telegram']
        
        # Initialize chat_ids list if it doesn't exist
        if 'chat_ids' not in telegram_config:
            telegram_config['chat_ids'] = []
        
        chat_ids = telegram_config['chat_ids']
        chat_id_str = str(chat_id)
        
        # Check if already registered
        if chat_id_str in chat_ids:
            return False  # Already registered
        
        # Add to list
        chat_ids.append(chat_id_str)
        telegram_config['chat_ids'] = chat_ids
        
        # Also set as main chat_id if not set (backward compatibility)
        if not telegram_config.get('chat_id'):
            telegram_config['chat_id'] = chat_id_str
        
        # Enable Telegram if not already enabled
        if not telegram_config.get('enabled'):
            telegram_config['enabled'] = True
        
        # Save config
        self.save_config()
        return True
    
    def handle_message(self, message: Dict):
        """Handle incoming message."""
        if 'text' not in message:
            return
        
        text = message['text'].strip()
        chat_id = str(message['chat']['id'])
        user_name = message.get('from', {}).get('first_name', 'User')
        
        if text == '/start':
            is_new = self.register_user(chat_id)
            
            if is_new:
                welcome_msg = f"""✅ <b>Welcome, {user_name}!</b>

You've been successfully registered for Zara stock notifications! 🎉

I'll notify you whenever the monitored products come in stock or go out of stock.

You can send /status to check your registration status."""
                self.send_message(chat_id, welcome_msg)
                print(f"✅ New user registered: {user_name} (chat_id: {chat_id})")
            else:
                already_msg = f"""👋 <b>Hello again, {user_name}!</b>

You're already registered for stock notifications! 

You can send /status to check your registration status."""
                self.send_message(chat_id, already_msg)
        
        elif text == '/status':
            if 'telegram' in self.config:
                chat_ids = self.config['telegram'].get('chat_ids', [])
                if chat_id in chat_ids:
                    status_msg = f"""✅ <b>You're registered!</b>

Your chat ID: <code>{chat_id}</code>
Total registered users: {len(chat_ids)}

You'll receive notifications for all monitored Zara products."""
                else:
                    status_msg = """❌ <b>You're not registered yet.</b>

Send /start to register for stock notifications!"""
            else:
                status_msg = """❌ <b>You're not registered yet.</b>

Send /start to register for stock notifications!"""
            
            self.send_message(chat_id, status_msg)
        
        elif text == '/help':
            help_msg = """🤖 <b>Zara Stock Checker Bot</b>

<b>Commands:</b>
/start - Register for stock notifications
/status - Check your registration status
/help - Show this help message

Once registered, you'll automatically receive notifications when monitored products change stock status!"""
            self.send_message(chat_id, help_msg)
    
    def run(self):
        """Run the bot in polling mode."""
        if not self.bot_token:
            print("❌ Bot token not found! Please set it in config.json or .env file.")
            print("   Set 'bot_token' in config.json or 'api_key' in .env")
            return
        
        print("🤖 Telegram Registration Bot started!")
        print("   Users can send /start to register automatically")
        print("   Press Ctrl+C to stop\n")
        
        try:
            while True:
                updates = self.get_updates()
                for update in updates:
                    if 'message' in update:
                        self.handle_message(update['message'])
                
                time.sleep(1)  # Small delay between polling
        except KeyboardInterrupt:
            print("\n👋 Bot stopped")


if __name__ == '__main__':
    bot = TelegramRegistrationBot()
    bot.run()

