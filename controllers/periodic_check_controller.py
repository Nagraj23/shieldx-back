import os
import time
import asyncio
import bcrypt
from typing import List
from fastapi import HTTPException

from database import user_collection
from utils.sos import trigger_sos
from utils.notifier import send_push_notification

# 🧠 In-memory security state (for 1 global session)
security_state = {
    "pending": False,
    "timestamp": None,
    "user_email_pending": None
}

# ✅ 1. INITIATE SECURITY CHECK (Triggered hourly or on demand)
async def initiate_hourly_security_check():
    if security_state["pending"]:
        print("🟡 Security check already pending. Skipping...")
        return

    print("🟢 Starting hourly security check...")

    users_to_notify = await user_collection.find({
        "deviceToken.token": {"$exists": True, "$ne": None},
        "isSecurityCheckEnabled": True
    }).to_list(length=None)

    if not users_to_notify:
        print("😴 No eligible users found.")
        return

    for user_doc in users_to_notify:
        user_email = user_doc.get("email")
        device_token = user_doc.get("deviceToken", {}).get("token")

        if not user_email or not device_token:
            continue

        check_id = str(time.time())
        print(f"📲 Sending push notification to {user_email}")

        # 🧠 Track current user (global state — basic)
        security_state.update({
            "pending": True,
            "timestamp": time.time(),
            "user_email_pending": user_email
        })

        await send_push_notification(
            device_token,
            title="🔐 ShieldX Security Check Required",
            body="Enter your code to confirm you're safe. Tap to respond.",
            data={
                "type": "security_check",
                "check_id": check_id,
                "user_email": user_email
            }
        )

# 🔁 2. BACKGROUND TASK FOR TIMEOUT (Check every 10s)
async def periodic_check_task():
    while True:
        await asyncio.sleep(10)
        await periodic_safety_check()

# ⏰ 3. HANDLE 1-MINUTE TIMEOUT
async def periodic_safety_check():
    if not security_state["pending"]:
        return

    if time.time() - security_state["timestamp"] <= 60:
        return  # still within 1 min

    user_email = security_state["user_email_pending"]
    print(f"🚨 Timeout! No response from {user_email}. Triggering SOS...")

    user_doc = await user_collection.find_one({"email": user_email})
    lat = user_doc.get("lastLocation", {}).get("latitude", 0.0)
    lng = user_doc.get("lastLocation", {}).get("longitude", 0.0)

    emergency_contacts = user_doc.get("emergencyContacts") or [os.getenv("EMERGENCY_CONTACT", "+917620101655")]

    await trigger_sos(user_email, lat, lng, emergency_contacts)

    # 🔁 Reset
    security_state.update({
        "pending": False,
        "timestamp": None,
        "user_email_pending": None
    })

# 🔐 4. VALIDATE CODE (called from UI)
# 🔐 4. VALIDATE CODE (called from UI)
async def check_security(code: str, user_email: str, emergency_contacts: List[str] = None):
    if not security_state["pending"] or security_state["user_email_pending"] != user_email:
        raise HTTPException(status_code=400, detail="No active check for this user.")

    user_doc = await user_collection.find_one({"email": user_email})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found.")

    hashed_code = user_doc.get("hashed_security_code")
    if not hashed_code:
        raise HTTPException(status_code=400, detail="Security code not set for this user.")

    try:
        is_valid = bcrypt.checkpw(code.encode(), hashed_code.encode())
    except Exception as e:
        print(f"❌ Error comparing code: {e}")
        raise HTTPException(status_code=500, detail="Internal error.")

    # ✅ If the code is correct
    if is_valid:
        print(f"✅ Correct code for {user_email}")
        security_state.update({
            "pending": False,
            "timestamp": None,
            "user_email_pending": None
        })
        return {"status": "success", "message": "✅ Access Granted"}

    # ❌ If the code is wrong
    print(f"🚨 Wrong code for {user_email} — Triggering SOS")

    lat = user_doc.get("lastLocation", {}).get("latitude", 0.0)
    lng = user_doc.get("lastLocation", {}).get("longitude", 0.0)

    # 🚀 Accept UI-passed contacts first
    if not emergency_contacts or not isinstance(emergency_contacts, list) or not all(isinstance(c, str) for c in emergency_contacts):
        emergency_contacts = user_doc.get("emergencyContacts") or [os.getenv("EMERGENCY_CONTACT", "+917620101655")]

    print(f"📡 Using emergency contacts: {emergency_contacts}")

    await trigger_sos(user_email, lat, lng, emergency_contacts)

    # Reset state
    security_state.update({
        "pending": False,
        "timestamp": None,
        "user_email_pending": None
    })

    return {"status": "error", "message": "🚨 Wrong Code! SOS Triggered"}

