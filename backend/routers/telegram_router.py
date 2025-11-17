"""
Telegram webhook router for handling incoming Telegram bot updates.
"""
from fastapi import APIRouter, Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import logging
import hmac
import hashlib
import json
import asyncio
from pydantic import BaseModel

from ..services.telegram_service import telegram_service
from ..services.message_processor import message_processor, IntentType
from ..services.agent_manager import agent_manager
from ..config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/telegram", tags=["telegram"])

class TelegramUpdate(BaseModel):
    """Model for incoming Telegram update."""
    update_id: int
    message: Optional[Dict[str, Any]] = None
    edited_message: Optional[Dict[str, Any]] = None
    channel_post: Optional[Dict[str, Any]] = None
    edited_channel_post: Optional[Dict[str, Any]] = None

@router.post("/webhook", status_code=status.HTTP_200_OK)
async def handle_telegram_webhook(update: Dict[str, Any]):
    """
    Endpoint to handle incoming Telegram updates.
    Telegram will send a POST request to this endpoint for each update.
    """
    try:
        # Process the update asynchronously
        asyncio.create_task(process_telegram_update(update))
        
        # Return 200 OK to acknowledge receipt
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing Telegram update: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing update"
        )

async def process_telegram_update(update: Dict[str, Any]):
    """
    Process incoming Telegram update and route to appropriate handler.
    """
    try:
        logger.debug(f"Processing Telegram update: {json.dumps(update, indent=2)}")
        
        # Handle different types of updates
        if "message" in update:
            await process_message(update["message"])
        elif "edited_message" in update:
            logger.info("Received edited message, ignoring")
        elif "channel_post" in update:
            logger.info("Received channel post, ignoring")
        elif "edited_channel_post" in update:
            logger.info("Received edited channel post, ignoring")
        else:
            logger.warning(f"Unhandled update type: {update.keys()}")
            
    except Exception as e:
        logger.error(f"Error in process_telegram_update: {str(e)}", exc_info=True)

async def process_message(message: Dict[str, Any]):
    """Process incoming Telegram message."""
    try:
        chat_id = message["chat"]["id"]
        
        # Check if the message is a command
        if "text" in message and message["text"].startswith('/'):
            await handle_command(message)
            return
            
        # Handle different types of messages
        if "text" in message:
            await handle_text_message(chat_id, message)
        elif "document" in message:
            await handle_document_message(chat_id, message)
        elif "photo" in message:
            await handle_photo_message(chat_id, message)
        else:
            logger.info(f"Unhandled message type: {message.keys()}")
            
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        await send_error_message(chat_id, "Sorry, I encountered an error processing your message.")

async def handle_text_message(chat_id: int, message: Dict[str, Any]):
    """Handle incoming text messages."""
    try:
        text = message["text"]
        message_id = message["message_id"]
        
        # Process the message using the message processor
        response = await message_processor.process_message(
            user_id=str(chat_id),
            message=text,
            platform="telegram",
            message_id=str(message_id)
        )
        
        # Send the response back to the user
        await telegram_service.send_message(
            chat_id=chat_id,
            text=response["message"]
        )
        
    except Exception as e:
        logger.error(f"Error in handle_text_message: {str(e)}", exc_info=True)
        await send_error_message(chat_id, "Sorry, I couldn't process your message.")

async def handle_document_message(chat_id: int, message: Dict[str, Any]):
    """Handle incoming document messages."""
    try:
        document = message["document"]
        file_id = document["file_id"]
        file_name = document.get("file_name", "document")
        
        # Get file info to get the download link
        file_info = await telegram_service._make_request(
            "GET",
            f"{telegram_service.base_url}/getFile?file_id={file_id}",
            {}
        )
        
        if not file_info.get("ok"):
            raise Exception("Failed to get file info from Telegram")
            
        file_path = file_info["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{settings.TELEGRAM_BOT_TOKEN}/{file_path}"
        
        # Process the document
        response = await message_processor.process_document(
            user_id=str(chat_id),
            file_url=file_url,
            file_name=file_name,
            platform="telegram"
        )
        
        # Send the response back to the user
        await telegram_service.send_message(
            chat_id=chat_id,
            text=response["message"]
        )
        
    except Exception as e:
        logger.error(f"Error in handle_document_message: {str(e)}", exc_info=True)
        await send_error_message(chat_id, "Sorry, I couldn't process your document.")

async def handle_photo_message(chat_id: int, message: Dict[str, Any]):
    """Handle incoming photo messages."""
    try:
        # Get the highest resolution photo
        photo_sizes = message["photo"]
        photo = photo_sizes[-1]  # Last element has the highest resolution
        file_id = photo["file_id"]
        
        # Get file info to get the download link
        file_info = await telegram_service._make_request(
            "GET",
            f"{telegram_service.base_url}/getFile?file_id={file_id}",
            {}
        )
        
        if not file_info.get("ok"):
            raise Exception("Failed to get file info from Telegram")
            
        file_path = file_info["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{settings.TELEGRAM_BOT_TOKEN}/{file_path}"
        
        # Process the photo
        caption = message.get("caption", "")
        response = await message_processor.process_image(
            user_id=str(chat_id),
            image_url=file_url,
            caption=caption,
            platform="telegram"
        )
        
        # Send the response back to the user
        await telegram_service.send_message(
            chat_id=chat_id,
            text=response["message"]
        )
        
    except Exception as e:
        logger.error(f"Error in handle_photo_message: {str(e)}", exc_info=True)
        await send_error_message(chat_id, "Sorry, I couldn't process your photo.")

async def handle_command(message: Dict[str, Any]):
    """Handle bot commands."""
    try:
        chat_id = message["chat"]["id"]
        command = message["text"].split()[0].lower()
        
        if command == "/start":
            await handle_start_command(chat_id)
        elif command == "/help":
            await handle_help_command(chat_id)
        else:
            await telegram_service.send_message(
                chat_id=chat_id,
                text="❌ Unknown command. Type /help to see available commands."
            )
            
    except Exception as e:
        logger.error(f"Error in handle_command: {str(e)}", exc_info=True)
        await send_error_message(chat_id, "Sorry, I couldn't process your command.")

async def handle_start_command(chat_id: int):
    """Handle the /start command."""
    welcome_message = """
👋 *Welcome to UPSC Mentor Bot!* \U0001F4DA

I'm here to help you with your UPSC preparation. Here's what I can do:

• Answer your UPSC-related questions
• Provide study materials and resources
• Help you with current affairs
• Give you practice questions
• And much more!

Type /help to see all available commands.

*Let's ace UPSC together!* \U0001F4AA
    """.strip()
    
    await telegram_service.send_message(
        chat_id=chat_id,
        text=welcome_message,
        parse_mode="Markdown"
    )

async def handle_help_command(chat_id: int):
    """Handle the /help command."""
    help_message = """
*Available Commands:* \U0001F4DD

/start - Start the bot and see welcome message
/help - Show this help message

*Features:*
• Ask me any UPSC-related questions
• Send me study materials to save
• Get daily current affairs updates
• Practice with previous year questions

Just type your question or upload a document to get started!
    """.strip()
    
    await telegram_service.send_message(
        chat_id=chat_id,
        text=help_message,
        parse_mode="Markdown"
    )

async def send_error_message(chat_id: int, message: str):
    """Send an error message to the user."""
    try:
        await telegram_service.send_message(
            chat_id=chat_id,
            text=f"❌ {message}"
        )
    except Exception as e:
        logger.error(f"Failed to send error message: {str(e)}", exc_info=True)
