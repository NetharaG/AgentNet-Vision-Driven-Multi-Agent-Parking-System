from typing import Dict, Any, Optional
from datetime import datetime
from app.utils.supabase_client import supabase_manager
from .optimization import OptimizationAgent

class AllocationAgent:
    """
    The Executioner of AgentNet.
    Coordinates with the OptimizationAgent to secure space and log active sessions.
    """
    
    def __init__(self):
        self.supabase = supabase_manager.client
        self.strategist = OptimizationAgent()
        
    def allocate_slot(self, perception_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agentic Allocation:
        1. Perceive Vehicle Size.
        2. Consult Optimization Strategist for Best-Fit.
        3. Execute DB writes to secure the spot.
        """
        if not self.supabase:
            return {"allocated": False, "error": "Database not connected", "slot_id": "N/A"}

        plate = perception_data.get("license_plate", "UNKNOWN")
        if plate == "UNKNOWN":
            return {"allocated": False, "error": "Vision Failure: Plate not identified", "slot_id": "N/A"}

        # We assume 'Medium' if not specified by vision
        size_class = perception_data.get("dimensions", {}).get("size_class", "Medium")
        
        print(f"[AllocationAgent] Coordinating entry for {plate} ({size_class})...")

        try:
            # 1. Prevent double entry
            existing = self.supabase.table("active_sessions").select("*").eq("license_plate", plate).eq("is_active", True).execute()
            if existing.data:
                slot_info = existing.data[0]
                print(f"[AllocationAgent] Alert: Duplicate entry attempt for {plate}.")
                return {
                    "allocated": False, 
                    "message": f"Vehicle {plate} already inside.", 
                    "slot_id": f"SLOT_{slot_info.get('slot_id')}"
                }

            # 2. Strategic Consultation (Handover to OptimizationAgent)
            allocated_slot = self.strategist.find_optimal_slot(size_class)
            
            if allocated_slot:
                slot_db_id = allocated_slot.get('id')
                slot_num = allocated_slot.get('slot_number', f"SLOT_{slot_db_id}")
                
                if not slot_db_id:
                     raise KeyError("Strategic Error: Slot ID is missing from strategist response.")
                
                print(f"[AllocationAgent] Strategist locked {slot_num}. Completing handover.")
                
                # 3. Execution Phase (Atomic Updates)
                # Mark slot as occupied
                self.supabase.table("parking_slots").update({
                    "status": "OCCUPIED", 
                    "current_vehicle": plate
                }).eq("id", slot_db_id).execute()
                
                # Create active session
                self.supabase.table("active_sessions").insert({
                    "license_plate": plate,
                    "slot_id": slot_db_id,
                    "vehicle_type": size_class,
                    "is_active": True
                }).execute()
                
                # Log to transactions for historical audit
                self.supabase.table("transactions").insert({
                    "license_plate": plate,
                    "slot_id": slot_db_id,
                    "action_type": "ENTRY",
                    "metadata": perception_data
                }).execute()
                
                return {
                    "allocated": True,
                    "slot_id": slot_num,
                    "transaction_id": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "message": f"Secured {slot_num} for {plate}."
                }
            else:
                return {
                    "allocated": False,
                    "slot_id": "FULL",
                    "message": "Strategic Failure: Capacity limit reached."
                }
                
        except Exception as e:
            print(f"[AllocationAgent] Operational Error: {e}")
            return {"allocated": False, "message": f"Net Communication Error: {str(e)}"}
