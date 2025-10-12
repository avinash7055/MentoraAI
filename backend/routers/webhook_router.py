from fastapi import APIRouter, Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, List
import hmac
import hashlib
import json
import logging
import asyncio
from pydantic import BaseModel, HttpUrl

from ..services.whatsapp_service import whatsapp_service
from ..services.message_processor import message_processor, IntentType
from ..services.agent_manager import agent_manager
from ..config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/webhook", tags=["whatsapp"])

class WebhookVerification(BaseModel):
    """Model for webhook verification request."""
    hub_mode: str
    hub_verify_token: str
    hub_challenge: str

class WhatsAppMessage(BaseModel):
    """Model for incoming WhatsApp message."""
    object: str
    entry: List[Dict[str, Any]]

@router.get("", status_code=status.HTTP_200_OK)
async def verify_webhook(request: Request):
    """
    Endpoint for WhatsApp webhook verification.
    WhatsApp will send a GET request to this endpoint to verify the webhook URL.
    """
    try:
        # Get query parameters
        query_params = dict(request.query_params)
        logger.info(f"Received webhook verification request: {query_params}")
        
        # Parse and validate request
        verification = WebhookVerification(**query_params)
        
        # Check if the verification token matches
        if verification.hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
            logger.info("Webhook verified successfully")
            return int(verification.hub_challenge)
        else:
            logger.warning(f"Invalid verification token: {verification.hub_verify_token}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid verification token"
            )
    except Exception as e:
        logger.error(f"Error verifying webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request"
        )

@router.post("", status_code=status.HTTP_200_OK)
async def handle_webhook(request: Request):
    """
    Endpoint to handle incoming WhatsApp messages.
    WhatsApp will send a POST request to this endpoint for each message.
    """
    try:
        # Read the raw request body for signature verification
        body_bytes = await request.body()
        
        # Verify the request signature
        if not await verify_whatsapp_signature(request, body_bytes):
            logger.warning("Invalid WhatsApp signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )
        
        # Parse the request body
        try:
            body = await request.json()
            logger.debug(f"Received webhook payload: {json.dumps(body, indent=2)}")
        except json.JSONDecodeError:
            logger.error("Failed to parse request body as JSON")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )
        
        # Process the webhook asynchronously
        asyncio.create_task(process_whatsapp_message(body))
        
        # Return 200 OK to acknowledge receipt
        return {"status": "ok"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

async def verify_whatsapp_signature(request: Request, body_bytes: bytes) -> bool:
    """
    Verify that the request came from WhatsApp using the X-Hub-Signature-256 header.
    """
    try:
        # Get the signature from the request headers
        signature_header = request.headers.get("X-Hub-Signature-256", "")
        if not signature_header:
            logger.warning("Missing X-Hub-Signature-256 header")
            return False
        
        # The signature is in the format "sha256=<signature>"
        signature_hash = signature_header.split("=")[1] if "=" in signature_header else ""
        
        # Create a new HMAC SHA256 hash using the app secret
        expected_signature = hmac.new(
            key=settings.WHATSAPP_APP_SECRET.encode('utf-8'),
            msg=body_bytes,
            digestmod=hashlib.sha256
        ).hexdigest()
        
        # Compare the signatures
        return hmac.compare_digest(signature_hash, expected_signature)
        
    except Exception as e:
        logger.error(f"Error verifying signature: {str(e)}", exc_info=True)
        return False

async def process_whatsapp_message(body: Dict[str, Any]):
    """
    Process incoming WhatsApp message and route to appropriate handler.
    """
    try:
        # Check if this is a WhatsApp message
        if body.get("object") != "whatsapp_business_account":
            logger.warning(f"Unexpected message object: {body.get('object')}")
            return
        
        # Process each entry in the webhook payload
        for entry in body.get("entry", []):
            phone_number_id = entry.get("changes", [{}])[0].get("value", {}).get("metadata", {}).get("phone_number_id")
            messages = entry.get("changes", [{}])[0].get("value", {}).get("messages", [])
            statuses = entry.get("changes", [{}])[0].get("value", {}).get("statuses", [])
            
            if messages:
                await process_messages(messages, phone_number_id)
            elif statuses:
                await process_status_updates(statuses)
                
    except Exception as e:
        logger.error(f"Error in process_whatsapp_message: {str(e)}", exc_info=True)

async def process_messages(messages: List[Dict[str, Any]], phone_number_id: str):
    """Process incoming WhatsApp messages."""
    for message in messages:
        try:
            # Get the sender's phone number
            from_number = message.get("from")
            if not from_number:
                logger.warning("Message missing 'from' field")
                continue
            
            # Get the message ID for tracking
            message_id = message.get("id")
            
            # Handle different message types
            if "text" in message:
                text = message["text"]["body"]
                await handle_text_message(from_number, text, message_id, phone_number_id)
                
            elif "image" in message:
                # Handle image messages
                image = message["image"]
                caption = image.get("caption", "")
                await handle_media_message(from_number, "image", image["id"], caption, message_id, phone_number_id)
                
            elif "document" in message:
                # Handle document messages
                document = message["document"]
                caption = document.get("caption", "")
                await handle_media_message(from_number, "document", document["id"], caption, message_id, phone_number_id)
                
            elif "button" in message:
                # Handle button responses
                button = message["button"]
                text = button.get("text", "")
                await handle_text_message(from_number, text, message_id, phone_number_id)
                
            else:
                logger.warning(f"Unhandled message type: {message.keys()}")
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)

async def process_status_updates(statuses: List[Dict[str, Any]]):
    """Process message status updates (delivered, read, etc.)."""
    for status_update in statuses:
        try:
            message_id = status_update.get("id")
            status_val = status_update.get("status", "")
            timestamp = status_update.get("timestamp", "")
            
            logger.info(f"Message {message_id} status updated to {status_val} at {timestamp}")
            
            # Update message status in the database if needed
            # ...
            
        except Exception as e:
            logger.error(f"Error processing status update: {str(e)}", exc_info=True)

async def handle_text_message(phone_number: str, text: str, message_id: str, phone_number_id: str):
    """Handle incoming text messages."""
    try:
        logger.info(f"Received message from {phone_number}: {text}")
        
        # Mark message as read
        await whatsapp_service.mark_message_as_read(message_id)
        
        # Detect intent using the message processor
        intent_result = message_processor.detect_intent(text)
        intent = intent_result.intent.value  # Convert enum to string
        entities = intent_result.entities
        
        logger.info(f"Detected intent: {intent} with entities: {entities}")
        
        # Get response from the appropriate agent
        response = await agent_manager.process_message(
            phone_number=phone_number,
            message=text,
            intent=intent,
            context={"entities": entities, "message_id": message_id}
        )
        
        # Send the response back to the user
        await whatsapp_service.send_text_message(
            to=phone_number,
            text=response,
            preview_url=False
        )
        
    except Exception as e:
        logger.error(f"Error handling text message: {str(e)}", exc_info=True)
        
        # Send error message to user
        error_message = "I'm sorry, I encountered an error processing your request. Please try again later."
        await whatsapp_service.send_text_message(
            to=phone_number,
            text=error_message,
            preview_url=False
        )

async def handle_media_message(phone_number: str, media_type: str, media_id: str, caption: str, message_id: str, phone_number_id: str):
    """Handle incoming media messages (images, documents, etc.)."""
    try:
        logger.info(f"Received {media_type} message from {phone_number} with caption: {caption}")
        
        # Mark message as read
        await whatsapp_service.mark_message_as_read(message_id)
        
        # For now, we'll just acknowledge media messages with a simple response
        response = f"Thanks for sending a {media_type}! "
        
        if caption:
            response += f"You wrote: '{caption}'. "
            
        response += "I'm still learning to process media messages. Could you describe what you need help with?"
        
        await whatsapp_service.send_text_message(
            to=phone_number,
            text=response,
            preview_url=False
        )
        
    except Exception as e:
        logger.error(f"Error handling {media_type} message: {str(e)}", exc_info=True)
        
        # Send error message to user
        error_message = "I'm sorry, I had trouble processing your media. Please try sending a text message instead."
        await whatsapp_service.send_text_message(
            to=phone_number,
            text=error_message,
            preview_url=False
        )
