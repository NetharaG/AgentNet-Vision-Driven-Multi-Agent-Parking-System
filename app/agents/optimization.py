from typing import Dict, Any, List, Optional
from app.utils.supabase_client import supabase_manager

class OptimizationAgent:
    """
    The Brain of AgentNet.
    Specializes in Space Optimization and Best-Fit Bin-Packing.
    """
    
    def __init__(self):
        self.supabase = supabase_manager.client

    def find_optimal_slot(self, vehicle_size_class: str) -> Optional[Dict[str, Any]]:
        """
        Consultancy: Finds the most efficient available slot.
        Prioritizes exact size matches to preserve larger slots for larger vehicles.
        """
        if not self.supabase:
            print("[OptimizationAgent] Critical: No DB connection.")
            return None

        try:
            # 1. Fetch live inventory of FREE slots
            response = self.supabase.table("parking_slots").select("*").eq("status", "FREE").execute()
            free_slots = response.data
            
            if not free_slots:
                print("[OptimizationAgent] Logic: All slots occupied. Optimization impossible.")
                return None

            # 2. Strategic Sizing Priority
            # We want the SMALLEST functional slot.
            size_hierarchy = {
                "Small": ["Small", "Medium", "Large"],
                "Medium": ["Medium", "Large"],
                "Large": ["Large"]
            }
            
            prio_list = size_hierarchy.get(vehicle_size_class, ["Medium", "Large"])
            
            for size in prio_list:
                # Filter slots of this size from the free_slots list
                candidate_slots = [s for s in free_slots if s.get('size_type') == size]
                if candidate_slots:
                    # In a real 'Net', we'd select by distance to gate here. 
                    # For now, we take the first optimal match.
                    best_slot = candidate_slots[0]
                    print(f"[OptimizationAgent] Strategy: Assigned {size} slot to {vehicle_size_class} vehicle (Best Fit).")
                    return best_slot
            
            print(f"[OptimizationAgent] Strategy: No functional slot found for size {vehicle_size_class}.")
            return None

        except Exception as e:
            print(f"[OptimizationAgent] Analysis Error: {e}")
            return None
