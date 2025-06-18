# routes/device_token_routes.py (Final Fixes)
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel
import logging

# Import the actual logic function from the controller
from controllers.device_token_controller import register_token as register_token_logic # Alias to avoid naming conflict

device_token_router = APIRouter()
logger = logging.getLogger(__name__)

class DeviceTokenRequest(BaseModel):
    email: str
    token: str
    type: str = "expo"

@device_token_router.post("/register-token")
async def register_token_route(request: DeviceTokenRequest): # Endpoint function
    """
    API endpoint to register or update a device token for a user.
    Calls the core logic from the controller.
    """
    try:
        # Correctly access attributes from the Pydantic request object
        await register_token_logic(request.email, request.token, request.type)
        logger.info(f"API route: Token registration successful for email: {request.email}") # FIX 2: Correct access
        return {"status": "success", "message": "Token registered successfully"}
    except HTTPException as e: # Catch FastAPI's HTTPExceptions
        raise e
    except Exception as e:
        logger.error(f"API route: Unexpected error during token registration for email: {request.email}: {e}") # FIX 2: Correct access
        raise HTTPException(status_code=500, detail="An unexpected error occurred during token registration.")