from typing import Dict, Any
import datetime
from app.utils.supabase_client import supabase_manager

class BillingAgent:
    """
    The Auditor of AgentNet.
    Handles vehicle exits, fee calculation, and real-time slot release.
    """
    
    def __init__(self):
        self.supabase = supabase_manager.client

    def process_exit(self, license_plate: str) -> Dict[str, Any]:
        """
        Handle Vehicle Exit:
        1. Find Active Session
        2. Calculate Fee (Rs 20/hr)
        3. Close Session & Free Slot
        4. Log Transaction
        """
        if not self.supabase:
            return {"status": "error", "message": "DB Disconnected"}
            
        print(f"[BillingAgent] Processing Exit for {license_plate}...")
        
        try:
            # 1. Find Session
            session = self.supabase.table("active_sessions")\
                .select("*")\
                .eq("license_plate", license_plate)\
                .eq("is_active", True)\
                .execute()
                
            if not session.data:
                print(f"[BillingAgent] Alert: No active session found for {license_plate}.")
                return {"status": "error", "message": "Vehicle not found in active registry."}
                
            record = session.data[0]
            slot_id = record.get('slot_id')
            entry_time_str = record.get('entry_time')
            
            # 2. Calculate Duration & Fee
            try:
                 # Entry time is stored as ISO format in Supabase
                 entry_dt = datetime.datetime.fromisoformat(entry_time_str.replace("Z", "+00:00"))
            except Exception as e:
                 print(f"[BillingAgent] Time parse error: {e}")
                 entry_dt = datetime.datetime.now(datetime.timezone.utc)
                 
            exit_dt = datetime.datetime.now(datetime.timezone.utc)
            duration_total_sec = (exit_dt - entry_dt).total_seconds()
            duration_hours = max(0.1, duration_total_sec / 3600.0) # Min 0.1h for billing
            
            base_rate = 20.0 # Rs per hour
            fee = round(duration_hours * base_rate, 2)
            if fee < 10: fee = 10 # Minimum charge
            
            # 3. Atomic Updates
            # A. Close Session
            self.supabase.table("active_sessions").update({
                "is_active": False,
                "updated_at": exit_dt.isoformat()
            }).eq("id", record['id']).execute()
            
            # B. Free Slot
            if slot_id:
                self.supabase.table("parking_slots").update({
                    "status": "FREE", 
                    "current_vehicle": None
                }).eq("id", slot_id).execute()
            
            # C. Log Historical Transaction
            self.supabase.table("transactions").insert({
                "license_plate": license_plate,
                "slot_id": slot_id,
                "action_type": "EXIT",
                "metadata": {"fee": fee, "duration_hours": round(duration_hours, 2)}
            }).execute()
            
            print(f"[BillingAgent] Exit complete for {license_plate}. Fee: Rs {fee}.")
            
            return {
                "status": "success",
                "license_plate": license_plate,
                "duration_hours": round(duration_hours, 2),
                "fee": fee,
                "message": f"Exit Approved. Slot released."
            }
        except Exception as e:
            print(f"[BillingAgent] Operational Error: {e}")
            return {"status": "error", "message": f"Net Communication Error: {str(e)}"}
