from typing import Dict, Any
from app.utils.supabase_client import supabase_manager

class VerificationAgent:
    """
    The Inspector of AgentNet.
    Verifies that a vehicle is correctly parked in its allocated slot via QR check.
    """
    
    def __init__(self):
        self.supabase = supabase_manager.client

    def verify_active_location(self, license_plate: str, scanned_qr: str) -> Dict[str, Any]:
        """
        1. Find active session for plate.
        2. Cross-reference QR (slot_number) with session's slot_id.
        3. Confirm if vehicle is in the correct zone.
        """
        if not self.supabase:
            return {"status": "error", "message": "DB Disconnected"}

        print(f"[VerificationAgent] Verifying location for {license_plate} at {scanned_qr}...")

        try:
            # 1. Query active session
            session_resp = self.supabase.table("active_sessions")\
                .select("*")\
                .eq("license_plate", license_plate)\
                .eq("is_active", True)\
                .execute()
            
            if not session_resp.data:
                return {
                    "status": "error", 
                    "message": f"Verification Failed: Vehicle {license_plate} not found in the lot."
                }
            
            active_session = session_resp.data[0]
            slot_id = active_session["slot_id"]
            
            # 2. Cross-reference slot ID with Slot Number (QR)
            slot_resp = self.supabase.table("parking_slots")\
                .select("slot_number")\
                .eq("id", slot_id)\
                .execute()
            
            if not slot_resp.data:
                return {"status": "error", "message": "Infrastructure Error: Allocated slot not found."}
            
            allocated_slot_num = slot_resp.data[0]["slot_number"]
            
            # 3. Final Validation
            if str(scanned_qr).strip().upper() == str(allocated_slot_num).strip().upper():
                print(f"[VerificationAgent] SUCCESS: {license_plate} verified at {scanned_qr}.")
                return {
                    "status": "success",
                    "license_plate": license_plate,
                    "slot_number": allocated_slot_num,
                    "message": "Identity Verified. Location Correct."
                }
            else:
                print(f"[VerificationAgent] ALERT: {license_plate} is in WRONG SLOT (Allocated: {allocated_slot_num}, Scanned: {scanned_qr}).")
                return {
                    "status": "error",
                    "message": f"Verification Failed: You are parked in {scanned_qr}, but your allocated slot is {allocated_slot_num}."
                }

        except Exception as e:
            print(f"[VerificationAgent] Operational Error: {e}")
            return {"status": "error", "message": f"Net Communication Error: {str(e)}"}
