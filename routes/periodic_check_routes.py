# controllers/periodic_check_router.py (Revised)
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel
# Import the updated check_security and security_state
from controllers.periodic_check_controller import check_security, initiate_hourly_security_check, security_state
from database import user_collection # Import user_collection

periodic_router = APIRouter()

# --- MODIFIED: SecurityCodeRequest to include user_email ---
class SecurityCodeRequest(BaseModel):
    code: str
    user_email: str # Expect email from frontend

class SecurityCheckToggleRequest(BaseModel):
    email: str
    enabled: bool

@periodic_router.post("/security-check")
async def security_check_endpoint(request: SecurityCodeRequest): # Renamed to avoid clash with function
    """Validate the security code entered by the user for a specific email."""
    # Pass both code and user_email to the logic function
    return await check_security(request.code, request.user_email)

@periodic_router.get("/security-check-status")
async def security_check_status():
    """Return the current security check status."""
    return {"pending": security_state["pending"],
            "timestamp": security_state["timestamp"],
            "user_email_pending": security_state["user_email_pending"]}

@periodic_router.post("/trigger-security-check")
async def trigger_security_check_manual():
    """Manually trigger a security check and send a push notification (for testing/immediate check-in)."""
    # This will now respect the isSecurityCheckEnabled setting
    await initiate_hourly_security_check()
    return {"message": "Manual security check initiated. Check your device for notification if feature is enabled."}

@periodic_router.post("/toggle-security-check")
async def toggle_security_check_feature(request: SecurityCheckToggleRequest):
    """
    Allows a user to enable or disable the continuous security check feature.
    """
    try:
        update_result = await user_collection.update_one(
            {"email": request.email},
            {"$set": {"isSecurityCheckEnabled": request.enabled}}
        )
        if update_result.matched_count == 0:
            raise HTTPException(status_code=404, detail=f"User with email {request.email} not found.")
        if update_result.modified_count == 0:
            return {"status": "success", "message": "Security check setting already as requested."}
        
        status_text = "enabled" if request.enabled else "disabled"
        return {"status": "success", "message": f"Security check feature {status_text} for {request.email}."}
    except Exception as e:
        logger.error(f"Error toggling security check for {request.email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update security check setting.")
