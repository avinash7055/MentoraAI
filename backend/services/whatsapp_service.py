"""
WhatsApp service for sending and processing WhatsApp messages.
Handles communication with the WhatsApp Business API.
"""
import os
import logging
import json
import httpx
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, HttpUrl

from ..config import settings

logger = logging.getLogger(__name__)

class WhatsAppMessage(BaseModel):
    """Model for WhatsApp message data."""
    to: str
    type: str
    text: Optional[Dict[str, str]] = None
    template: Optional[Dict[str, Any]] = None
    interactive: Optional[Dict[str, Any]] = None

class WhatsAppService:
    """Service for interacting with the WhatsApp Business API."""
    
    def __init__(self):
        self.base_url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}"
        self.phone_number_id = settings.WHATSAPP_PHONE_ID
        self.access_token = settings.WHATSAPP_APP_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def send_message(self, to: str, message: str) -> Dict[str, Any]:
        """
        Send a text message to a WhatsApp user.
        
        Args:
            to: The recipient's phone number in international format (e.g., "1234567890@c.us")
            message: The text message to send
            
        Returns:
            Dict containing the API response
        """
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message}
        }
        
        return await self._make_request("POST", url, payload)
    
    async def send_template_message(
        self, 
        to: str, 
        template_name: str, 
        language_code: str = "en",
        components: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Send a template message to a WhatsApp user.
        
        Args:
            to: The recipient's phone number in international format
            template_name: The name of the template to send
            language_code: The language code for the template (default: "en")
            components: Optional components for the template
            
        Returns:
            Dict containing the API response
        """
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code}
            }
        }
        
        if components:
            payload["template"]["components"] = components
            
        return await self._make_request("POST", url, payload)
    
    async def mark_message_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Mark a message as read.
        
        Args:
            message_id: The ID of the message to mark as read
            
        Returns:
            Dict containing the API response
        """
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        return await self._make_request("POST", url, payload)
    
    async def get_media_url(self, media_id: str) -> Optional[str]:
        """
        Get the URL for a media file.
        
        Args:
            media_id: The ID of the media file
            
        Returns:
            The URL of the media file, or None if not found
        """
        try:
            url = f"{self.base_url}/{media_id}"
            response = await self._make_request("GET", url)
            return response.get("url")
        except Exception as e:
            logger.error(f"Error getting media URL: {str(e)}")
            return None
    
    async def download_media(self, media_url: str, output_path: str) -> bool:
        """
        Download a media file from WhatsApp.
        
        Args:
            media_url: The URL of the media file
            output_path: The path to save the downloaded file
            
        Returns:
            True if the download was successful, False otherwise
        """
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            async with httpx.AsyncClient() as client:
                response = await client.get(media_url, headers=headers, follow_redirects=True)
                response.raise_for_status()
                
                with open(output_path, "wb") as f:
                    f.write(response.content)
                    
                return True
                
        except Exception as e:
            logger.error(f"Error downloading media: {str(e)}")
            return False
    
    async def _make_request(self, method: str, url: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make an HTTP request to the WhatsApp API.
        
        Args:
            method: The HTTP method (GET, POST, etc.)
            url: The URL to make the request to
            data: The request payload
            
        Returns:
            The JSON response from the API
            
        Raises:
            HTTPError: If the request fails
        """
        try:
            async with httpx.AsyncClient() as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=self.headers)
                else:
                    response = await client.post(
                        url, 
                        headers=self.headers,
                        json=data
                    )
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
            
        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

# Create a singleton instance
whatsapp_service = WhatsAppService()
