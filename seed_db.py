import asyncio
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.database import engine, init_db
from app.db.models import ParkingSlot

async def seed_data():
    """
    Populates the database with initial parking slots.
    """
    print("Initializing Database...")
    await init_db()
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Check if data exists
        from sqlmodel import select
        result = await session.exec(select(ParkingSlot))
        if result.first():
            print("Database already seeded.")
            return

        print("Seeding Parking Slots...")
        slots = []
        
        # 10 Small Slots
        for i in range(1, 11):
            slots.append(ParkingSlot(id=i, size="small", coordinates=f"1,{i},0"))
            
        # 10 Medium Slots
        for i in range(11, 21):
            slots.append(ParkingSlot(id=i, size="medium", coordinates=f"2,{i-10},0"))
            
        # 5 Large Slots
        for i in range(21, 26):
            slots.append(ParkingSlot(id=i, size="large", coordinates=f"3,{i-20},0"))
            
        session.add_all(slots)
        await session.commit()
        print(f"✅ Successfully added {len(slots)} parking slots.")

if __name__ == "__main__":
    asyncio.run(seed_data())
