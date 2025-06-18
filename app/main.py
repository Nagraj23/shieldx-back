# main.py (MODIFIED)
from fastapi import FastAPI, Request
import asyncio
from fastapi.middleware.cors import CORSMiddleware
import logging
from dotenv import load_dotenv
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import routers
from routes.periodic_check_routes import periodic_router
from routes.sos_routes import sos_router

from routes.location_routes import location_router
from routes.location_monitor_routes import location_mon_router
from routes.voice_sos_routes import voice_sos_router
from routes.route_monitor_routes import share_router, start_route_tracking, RouteShareRequest
from routes.emergency import router as emergency_router

# FIX: Import the new device token router from its new location
from routes.device_token_routes import device_token_router # <--- NEW IMPORT PATH!

# Import functions from controllers (only logic functions, not routers now)
from controllers.periodic_check_controller import periodic_check_task, initiate_hourly_security_check
from app.config import Config

app = FastAPI(title="ShieldX Safety API", version="1.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routes
app.include_router(voice_sos_router, prefix="/api")
app.include_router(location_mon_router, prefix="/api")
app.include_router(share_router, prefix="/api")
app.include_router(periodic_router, prefix="/api")
app.include_router(sos_router, prefix="/api")

from fastapi import BackgroundTasks
from controllers.location import LocationRequest, share_location

app.include_router(location_router, prefix="/api")

@app.post("/api/location/update_location")
async def update_location_alias(request: LocationRequest, background_tasks: BackgroundTasks):
    """
    Alias route for /api/location/update_location to call the existing /api/share-location endpoint handler.
    """
    # Fix: request is already parsed as LocationRequest, no need to await json()
    location_request = request
    return await share_location(
        user_id=location_request.user_id,
        lat=location_request.lat,
        lng=location_request.lng,
        contacts=location_request.emergency_contacts,
        is_emergency=location_request.is_emergency
    )
app.include_router(sos_router, prefix="/api/emergency", tags=["emergency"])
app.include_router(emergency_router, prefix="/api/emergency", tags=["emergency"])

# FIX: Include the new device_token_router with the /api prefix
app.include_router(device_token_router, prefix="/api") # <--- UPDATED ROUTER TO INCLUDE!

@app.post("/share_route")
async def share_route_alias(request: Request):
    """
    Alias route for /share_route to call the existing /api/share_route endpoint handler.
    """
    body = await request.json()
    print("🔍 Incoming body:", body)
    route_request = RouteShareRequest(**body)
    return await start_route_tracking(route_request, background_tasks=None)

@app.get("/")
async def root():
    return {"message": "Welcome to ShieldX Safety API"}

# Initialize APScheduler
scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_event():
    logging.info("Application startup event triggered.")
    
    scheduler.add_job(
        initiate_hourly_security_check,
        IntervalTrigger(hours=1),
        id='hourly_security_check_job',
        replace_existing=True,
        max_instances=1
    )
    scheduler.start()
    logging.info("APScheduler started for hourly security checks.")

    asyncio.create_task(periodic_check_task())
    logging.info("Background periodic check task started for 1-minute timeout monitoring.")

@app.on_event("shutdown")
async def shutdown_event():
    logging.info("Application shutdown event triggered.")
    scheduler.shutdown()
    logging.info("APScheduler shut down.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=Config.HOST, port=Config.PORT, reload=Config.DEBUG)