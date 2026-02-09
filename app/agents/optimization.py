from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from ..db.models import ParkingSlot

class OptimizationAgent:
    """
    Implements Bin-Packing logic to find the best slot.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_optimal_slot(self, vehicle_size: str) -> ParkingSlot | None:
        """
        Finds the Smallest Available Slot that fits the vehicle (Best Fit).
        """
        # Logic: 
        # 1. Get all free slots.
        # 2. Filter by size compatibility (Small fits Small, Medium fits S/M, Large fits S/M/L)
        #    ...Actually usually it's: Vehicle fits in Slot if Slot >= Vehicle.
        #    Small Car -> Small/Medium/Large Slot.
        #    Medium Car -> Medium/Large Slot.
        #    Large Car -> Large Slot.
        #
        # Optimization: We want to use the SMALLEST functional slot to save big slots for big cars.
        
        statement = select(ParkingSlot).where(ParkingSlot.is_occupied == False)
        result = await self.session.exec(statement)
        free_slots = result.all()
        
        # Priority: Small Slot (if car fits) > Medium > Large
        # Mapping sizes to integer for comparison? 
        # For prototype, let's just look for EXACT match first, then upgrade using python logic.
        
        # Robust "Best Fit" Logic:
        target_size = vehicle_size.lower()
        
        # Define hierarchy: Size -> Int
        size_map = {"small": 1, "medium": 2, "large": 3, "unknown": 2} # Unknown assumes Medium
        vehicle_size_int = size_map.get(target_size, 2)
        
        best_slot = None
        
        # Sort slots by size (Small < Medium < Large) to ensure Best Fit
        # Assuming DB has "small", "medium", "large" strings
        
        for slot in free_slots:
            slot_size_int = size_map.get(slot.size, 0)
            
            # Condition: Slot must be >= Vehicle
            if slot_size_int >= vehicle_size_int:
                # We want the smallest possible slot that fits (Minimize waste)
                if best_slot is None:
                    best_slot = slot
                else:
                    # Compare current best with new candidate
                    best_size_int = size_map.get(best_slot.size, 3)
                    if slot_size_int < best_size_int:
                        best_slot = slot
                        
        return best_slot
