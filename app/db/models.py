from typing import Optional
from sqlmodel import Field, SQLModel

class ParkingSlot(SQLModel, table=True):
    """
    Represents a physical parking spot in the lot.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    size: str = Field(index=True)  # small, medium, large
    is_occupied: bool = Field(default=False, index=True)
    coordinates: str  # JSON string "x,y,z" or similar
    
    # Metadata for the current vehicle (if occupied)
    current_vehicle_id: Optional[str] = None 
