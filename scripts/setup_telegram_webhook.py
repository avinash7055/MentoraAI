#!/usr/bin/env python3
"""
Script to set up or remove a Telegram webhook.

Usage:
    python setup_telegram_webhook.py --set <webhook_url> [--remove]
    
Example:
    python setup_telegram_webhook.py --set https://yourdomain.com/telegram/webhook
    python setup_telegram_webhook.py --remove
"""
import os
import sys
import argparse
import httpx
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_webhook(bot_token: str, webhook_url: str, secret_token: Optional[str] = None) -> bool:
    """
    Set up a Telegram webhook.
    
    Args:
        bot_token: Telegram bot token
        webhook_url: Webhook URL to receive updates
        secret_token: Secret token to validate requests (optional)
        
    Returns:
        bool: True if successful, False otherwise
    """
    url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    
    payload = {
        "url": webhook_url,
        "drop_pending_updates": True,
    }
    
    if secret_token:
        payload["secret_token"] = secret_token
    
    try:
        response = httpx.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        
        if result.get("ok"):
            logger.info(f"Webhook set successfully: {result.get('description')}")
            logger.info(f"Webhook info: {result.get('result')}")
            return True
        else:
            logger.error(f"Failed to set webhook: {result.get('description')}")
            return False
            
    except Exception as e:
        logger.error(f"Error setting webhook: {str(e)}")
        return False

def remove_webhook(bot_token: str) -> bool:
    """
    Remove the currently set webhook.
    
    Args:
        bot_token: Telegram bot token
        
    Returns:
        bool: True if successful, False otherwise
    """
    url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
    
    try:
        response = httpx.post(url, params={"drop_pending_updates": True})
        response.raise_for_status()
        result = response.json()
        
        if result.get("ok"):
            logger.info("Webhook removed successfully")
            return True
        else:
            logger.error(f"Failed to remove webhook: {result.get('description')}")
            return False
            
    except Exception as e:
        logger.error(f"Error removing webhook: {str(e)}")
        return False

def get_webhook_info(bot_token: str) -> None:
    """
    Get information about the currently set webhook.
    
    Args:
        bot_token: Telegram bot token
    """
    url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    
    try:
        response = httpx.get(url)
        response.raise_for_status()
        result = response.json()
        
        if result.get("ok"):
            webhook_info = result.get("result", {})
            logger.info("Current webhook info:")
            for key, value in webhook_info.items():
                logger.info(f"  {key}: {value}")
        else:
            logger.error(f"Failed to get webhook info: {result.get('description')}")
            
    except Exception as e:
        logger.error(f"Error getting webhook info: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Manage Telegram webhook settings")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--set", help="Set webhook URL")
    group.add_argument("--remove", action="store_true", help="Remove webhook")
    group.add_argument("--info", action="store_true", help="Get webhook info")
    parser.add_argument("--token", help="Telegram bot token (or set TELEGRAM_BOT_TOKEN env var)")
    parser.add_argument("--secret", help="Secret token for webhook verification (optional)")
    
    args = parser.parse_args()
    
    # Get bot token from args or environment variable
    bot_token = args.token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("Please provide a bot token using --token or set TELEGRAM_BOT_TOKEN environment variable")
        sys.exit(1)
    
    if args.set:
        # Set webhook
        success = setup_webhook(
            bot_token=bot_token,
            webhook_url=args.set,
            secret_token=args.secret
        )
        if success:
            logger.info("Webhook set successfully")
        else:
            logger.error("Failed to set webhook")
            sys.exit(1)
            
    elif args.remove:
        # Remove webhook
        success = remove_webhook(bot_token=bot_token)
        if success:
            logger.info("Webhook removed successfully")
        else:
            logger.error("Failed to remove webhook")
            sys.exit(1)
            
    elif args.info:
        # Get webhook info
        get_webhook_info(bot_token=bot_token)

if __name__ == "__main__":
    main()
