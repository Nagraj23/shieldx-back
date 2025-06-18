# Update the existing location_routes.py

from fastapi import APIRouter, BackgroundTasks, HTTPException
from controllers.location import LocationRequest, share_location
from utils.network import is_online

location_router = APIRouter()

@location_router.post("/share-location")
async def share_location_endpoint(request: LocationRequest, background_tasks: BackgroundTasks):
    try:
        if not request.user_id:
            raise HTTPException(status_code=400, detail="User ID is required")
            
        # Check network status for response info
        network_status = await is_online()
        
        # Process location sharing and notifications
        result = await share_location(
            user_id=request.user_id,
            lat=request.lat,
            lng=request.lng,
            contacts=request.emergency_contacts,
            is_emergency=request.is_emergency
        )

        # Return response
        mode = "Online Mode" if network_status else "Offline Mode"
        return {
            "status": "success",
            "message": f"Location shared successfully! ({mode})",
            "contacts_notified": request.emergency_contacts,
            "is_emergency": request.is_emergency,
            "notification_mode": mode
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))