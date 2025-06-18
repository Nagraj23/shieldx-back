# controllers/device_token_controller.py (MODIFIED)
from fastapi import HTTPException # Still needed for potential exceptions
import logging

# Import database operations
from database import save_device_token, get_device_token 

logger = logging.getLogger(__name__)

# REMOVED: router = APIRouter() and @router.post("/register-token")

async def register_token(email: str, token: str, token_type: str = "expo"):
    """
    Core logic to register or update a device token for a user.
    This function performs the actual database operation.
    """
    try:
        await save_device_token(email, token, token_type)
        logger.info(f"Controller logic: Registered/Updated token for {email}: {token}")
        # No return value here, let the route handler construct the response
    except Exception as e:
        logger.error(f"Controller logic: Failed to save token for {email}: {e}")
        # Raise an exception that the route handler can catch and translate to HTTP 500
        raise ValueError(f"Database operation failed for token registration: {e}") 

# This function remains as it's a utility for other controllers/modules
async def get_user_device_token(email: str) -> str | None:
    """Retrieves a user's device token from their user document using their email."""
    return await get_device_token(email)