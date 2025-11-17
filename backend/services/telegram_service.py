"""
Telegram service for sending and processing Telegram messages.
Handles communication with the Telegram Bot API.
"""
import os
import logging
import json
import httpx
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, HttpUrl

from ..config import settings

logger = logging.getLogger(__name__)

class TelegramMessage(BaseModel):
    """Model for Telegram message data."""
    chat_id: Union[int, str]
    text: str
    parse_mode: Optional[str] = "HTML"
    reply_markup: Optional[Dict[str, Any]] = None

class TelegramService:
    """Service for interacting with the Telegram Bot API."""
    
    def __init__(self):
        self.base_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"
        self.headers = {
            "Content-Type": "application/json"
        }
    
    async def send_message(
        self, 
        chat_id: Union[int, str], 
        text: str,
        parse_mode: Optional[str] = "HTML",
        reply_markup: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a text message to a Telegram chat.
        
        Args:
            chat_id: Unique identifier for the target chat or username of the target channel
            text: Text of the message to be sent
            parse_mode: Send Markdown or HTML, if you want Telegram apps to show bold, italic,
                      fixed-width text or inline URLs in your bot's message.
            reply_markup: Additional interface options
            
        Returns:
            Dict containing the API response
        """
        url = f"{self.base_url}/sendMessage"
        
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        if reply_markup:
            payload["reply_markup"] = reply_markup
        
        return await self._make_request("POST", url, payload)
    
    async def send_document(
        self,
        chat_id: Union[int, str],
        document: str,
        caption: Optional[str] = None,
        parse_mode: Optional[str] = "HTML"
    ) -> Dict[str, Any]:
        """
        Send a document to a Telegram chat.
        
        Args:
            chat_id: Unique identifier for the target chat or username of the target channel
            document: File to send. Pass a file_id as String to send a file that exists on the Telegram servers,
                    or an HTTP URL as a String for Telegram to get a file from the Internet
            caption: Document caption, 0-1024 characters after entities parsing
            parse_mode: Send Markdown or HTML, if you want Telegram apps to show bold, italic,
                      fixed-width text or inline URLs in the media caption.
            
        Returns:
            Dict containing the API response
        """
        url = f"{self.base_url}/sendDocument"
        
        payload = {
            "chat_id": chat_id,
            "document": document
        }
        
        if caption:
            payload["caption"] = caption
            payload["parse_mode"] = parse_mode
        
        return await self._make_request("POST", url, payload)
    
    async def _make_request(self, method: str, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make an HTTP request to the Telegram API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: The URL to send the request to
            payload: The request payload
            
        Returns:
            Dict containing the API response
            
        Raises:
            HTTPException: If the request fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method,
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error from Telegram API: {str(e)}"
            logger.error(f"{error_msg}. Response: {e.response.text}")
            raise
            
        except Exception as e:
            error_msg = f"Error making request to Telegram API: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise

# Create a singleton instance
telegram_service = TelegramService()
