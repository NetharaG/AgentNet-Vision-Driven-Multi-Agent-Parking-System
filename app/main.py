from contextlib import asynccontextmanager
from sqlmodel import select
from .db.models import ParkingSlot
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, UploadFile, File
from sqlmodel.ext.asyncio.session import AsyncSession
import time
import numpy as np # For mock embeddings

from .db.database import get_session, init_db
from .db.vector import ChromaVectorStore
from .agents.vision import VisionAgent
from .agents.optimization import OptimizationAgent
from .agents.sre import SREAgent

# --- LIFESPAN (Startup/Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB 
    await init_db()
    # Pre-load Vision Model
    # vision_agent._get_model() 
    yield

app = FastAPI(title="OptiSlot AO", lifespan=lifespan)

# --- SINGLETON AGENTS ---
vision_agent = VisionAgent()
sre_agent = SREAgent()
# Initialize Vector Store (Synchronous/Fast)
vector_store = ChromaVectorStore()

# --- BACKGROUND WORKFLOW ---
async def process_entry_workflow(gate_id: str, session: AsyncSession, image_bytes: bytes = None):
    """
    The "Heavy Lifting" happens here. Returns the result for the API.
    """
    start_time = time.time()
    
    # 1. Vision Analysis (Real Inference)
    vehicle_data = await vision_agent.analyze_stream(gate_id, image_bytes)
    print(f"[Workflow] Vision Result: {vehicle_data}")
    
    # 1.1 Check for Duplicate Entry
    detected_plate = vehicle_data.get('license_plate')
    if detected_plate and "AI-" not in detected_plate: # Only check real plates
        stmt = select(ParkingSlot).where(ParkingSlot.current_vehicle_id == detected_plate)
        result = await session.exec(stmt)
        existing_slot = result.first()
        
        if existing_slot:
            duration = (time.time() - start_time) * 1000
            print(f"[Workflow] 🚫 DUPLICATE ENTRY: {detected_plate} is already in Slot {existing_slot.id}")
            return {
                "license_plate": detected_plate,
                "vehicle_type": vehicle_data.get('vehicle_type'),
                "confidence": vehicle_data.get('confidence'),
                "allocated_slot_id": "ALREADY_PARKED",
                "processing_time_ms": round(duration, 2),
                "message": f"Vehicle {detected_plate} is already parked in Slot {existing_slot.id}"
            }

    # 1.5 Vector Memory (Re-Identification)
    embedding = np.random.rand(128).tolist() 
    
    returning_id = vector_store.search_vehicle(embedding)
    
    if returning_id:
        print(f"[Workflow] 🧠 MEMORY TRIGGERED: Welcome back, {returning_id}!")
    else:
        print("[Workflow] New Visitor Detected. Memorizing appearance...")
        vector_store.upsert_vector(vehicle_data['license_plate'], embedding)

    # 2. Optimization (Bin Packing)
    opti_agent = OptimizationAgent(session)
    slot = await opti_agent.find_optimal_slot(vehicle_data['vehicle_type'])
    
    allocated_slot_id = None
    if slot:
        print(f"[Workflow] Allocated Slot: {slot.id} (Size: {slot.size})")
        slot.is_occupied = True
        slot.current_vehicle_id = vehicle_data['license_plate']
        session.add(slot)
        await session.commit()
        allocated_slot_id = slot.id
    else:
        print("[Workflow] No suitable slot found!")

    # 3. SRE Metric
    duration = (time.time() - start_time) * 1000
    sre_agent.log_latency("process_entry_workflow", duration)
    
    # Return data for the API response
    return {
        "license_plate": vehicle_data.get('license_plate'),
        "vehicle_type": vehicle_data.get('vehicle_type'),
        "confidence": vehicle_data.get('confidence'),
        "allocated_slot_id": allocated_slot_id,
        "processing_time_ms": round(duration, 2)
    }


# --- API ROUTES ---

@app.post("/gate/{gate_id}/entry")
async def trigger_entry(
    gate_id: str, 
    # background_tasks: BackgroundTasks, # Removed for synchronous demo
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
):
    """
    Synchronous Entry Trigger (Wait for Result)
    """
    import traceback
    from fastapi.responses import JSONResponse

    try:
        # Read bytes immediately
        image_bytes = await file.read()
        
        # Run workflow synchronously (await it) so we can return the result
        result = await process_entry_workflow(gate_id, session, image_bytes)
        
        # Return the full result
        return {
            "status": "success", 
            "data": result
        }
    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e), "traceback": traceback.format_exc()}
        )

@app.get("/api/slots")
async def get_slots(session: AsyncSession = Depends(get_session)):
    """
    Get current state of all parking slots.
    """
    result = await session.exec(select(ParkingSlot))
    slots = result.all()
    return slots

@app.delete("/api/reset")
async def reset_database(session: AsyncSession = Depends(get_session)):
    """
    Clears all data and Re-seeds the Parking Slots.
    """
    from sqlmodel import delete
    try:
        # 1. Delete all slots (which clears vehicles/occupancy)
        statement = delete(ParkingSlot)
        await session.exec(statement)
        await session.commit()
        
        # 2. Re-seed the Infrastructure (25 Slots)
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
        
        return {"status": "success", "message": "System Reset: Data Cleared & Slots Restored."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

