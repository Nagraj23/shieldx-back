from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
import logging
from typing import Dict, List, Optional
import os

from utils.network import is_online
from utils.notifier import send_notification
from services.sms_service import SMSService

router = APIRouter()
logger = logging.getLogger(__name__)

# Load environment variables
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
GSM_PORT = os.getenv("GSM_PORT", "COM3" if os.name == 'nt' else "/dev/ttyUSB0")

class EmergencyAlert(BaseModel):
    phone_number: str
    message: str

class EmergencyRequest(BaseModel):
    user_id: str
    lat: float
    lng: float
    emergency_contacts: List[str]
    is_emergency: bool = True

def get_sms_service() -> SMSService:
    """Dependency to get SMS service instance"""
    # For development, if no Twilio credentials, create a mock implementation
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        class MockSMSService:
            def send_via_twilio(self, phone_number, message):
                logger.info(f"[MOCK] Sending SMS to {phone_number}: {message}")
                return True
                
            def send_via_gsm(self, phone_number, message):
                logger.info(f"[MOCK] Sending GSM SMS to {phone_number}: {message}")
                return True
        
        return MockSMSService()
    
    # Return real implementation if credentials exist
    return SMSService(
        twilio_account_sid=TWILIO_ACCOUNT_SID,
        twilio_auth_token=TWILIO_AUTH_TOKEN,
        twilio_phone_number=TWILIO_PHONE_NUMBER,
        gsm_port=GSM_PORT
    )

@router.post("/emergency-alert/")
async def send_emergency_alert(alert: EmergencyAlert) -> Dict[str, str]:
    """
    Send emergency alert using appropriate method based on network status
    
    Args:
        alert (EmergencyAlert): Alert details containing phone number and message
        
    Returns:
        Dict[str, str]: Status message indicating success and mode used
    """
    try:
        network_status = is_online()
        success = await send_notification(
            phone_number=alert.phone_number,
            message=alert.message,
            is_online=network_status
        )
        
        if success:
            mode = "Online Mode" if network_status else "Offline Mode"
            return {"status": f"Message sent successfully ({mode})"}
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to send emergency alert"
            )
    except Exception as e:
        logger.error(f"Failed to send emergency alert: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send emergency alert: {str(e)}"
        )

@router.post("/sos")
async def send_sos(
    request: EmergencyRequest, 
    background_tasks: BackgroundTasks,
    sms_service: SMSService = Depends(get_sms_service)
):
    """
    Send SOS alerts to emergency contacts with location information
    
    Args:
        request (EmergencyRequest): Emergency request with user info and contacts
        background_tasks (BackgroundTasks): FastAPI background tasks
        sms_service (SMSService): SMS service dependency
        
    Returns:
        Dict: Status and notification details
    """
    try:
        # Process emergency SOS request
        notified_contacts = []
        network_status = is_online()
        
        for contact in request.emergency_contacts:
            # Check if it's a phone number (simple check)
            if contact.startswith("+"):
                message = f"EMERGENCY SOS from ShieldX! User needs help at location: {request.lat}, {request.lng}"
                
                try:
                    if network_status:
                        # Try Twilio if online
                        sms_service.send_via_twilio(contact, message)
                    else:
                        # Use GSM if offline
                        sms_service.send_via_gsm(contact, message)
                    
                    notified_contacts.append(contact)
                except Exception as e:
                    logger.error(f"Failed to send SOS to {contact}: {str(e)}")
                    # Try alternative method if first one fails
                    try:
                        if network_status:
                            sms_service.send_via_gsm(contact, message)
                        else:
                            sms_service.send_via_twilio(contact, message)
                        notified_contacts.append(contact)
                    except Exception as backup_error:
                        logger.error(f"Backup method also failed for {contact}: {str(backup_error)}")
        
        # Return response
        mode = "Online Mode" if network_status else "Offline Mode"
        return {
            "status": "success",
            "message": f"SOS alert sent successfully! ({mode})",
            "contacts_notified": notified_contacts
        }
    except Exception as e:
        logger.error(f"Failed to send SOS: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send SOS: {str(e)}")