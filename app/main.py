from typing import List
from fastapi import FastAPI, UploadFile, File, Body, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
import time
import os
import traceback
from pydantic import BaseModel
from dotenv import load_dotenv

# AgentNet Imports
from .agents.vision import VisionAgent
from .agents.allocation import AllocationAgent
from .agents.verification import VerificationAgent
from .agents.exit_billing import BillingAgent
from .agents.sre import SREAgent

from .utils.supabase_client import supabase_manager

load_dotenv()

app = FastAPI(title="AgentNet: Vision-Driven Multi-Agent Parking System")

# --- AGENT SERVICE REGISTRY ---
vision_agent = VisionAgent()
allocation_agent = AllocationAgent()
verification_agent = VerificationAgent()
billing_agent = BillingAgent()
sre_agent = SREAgent()

# --- MODELS ---
class VerifyRequest(BaseModel):
    user_id: str # License Plate
    scanned_qr: str

class ExitRequest(BaseModel):
    license_plate: str

from typing import List

# --- THE AGENTNET PIPELINE (ORCHESTRATION) ---

async def agentnet_entry_pipeline(gate_id: str, frames_bytes: List[bytes]):
    """
    Coordinated Multi-Agent Workflow with Multi-Frame Voting:
    Vision (Consensus) -> Allocation (Execution) -> SRE (Observation)
    """
    pipeline_start = time.time()
    
    # 1. Vision Agent: Perceive (with Consensus Voting)
    v_start = time.time()
    perception = await vision_agent.analyze_stream(gate_id, frames_bytes)
    sre_agent.log_latency("VisionAgent", (time.time() - v_start) * 1000)
    
    # SRE Observation: Log Handover
    sre_agent.log_handover("VisionAgent", "AllocationAgent", perception)
    
    # 2. Allocation Agent: Strategy & Execution
    a_start = time.time()
    execution_result = allocation_agent.allocate_slot(perception)
    sre_agent.log_latency("AllocationAgent", (time.time() - a_start) * 1000)
    
    # SRE Observation: Log Completion
    pipeline_duration = (time.time() - pipeline_start) * 1000
    sre_agent.log_latency("AgentNetPipeline", pipeline_duration)
    
    return {
        "perception": perception,
        "execution": execution_result,
        "network_health": sre_agent.get_system_report(),
        "total_ms": round(pipeline_duration, 2)
    }

# --- NEW ANALYTICS & INFRASTRUCTURE ROUTES ---

@app.get("/api/slots/all")
async def get_all_slots():
    """Returns the full inventory of parking bays."""
    try:
        resp = supabase_manager.client.table("parking_slots").select("*").order("slot_number").execute()
        return {"status": "success", "slots": resp.data}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/stats")
async def get_analytics():
    """Aggregates vehicle flow and confidence trends."""
    try:
        # Mocking complex aggregation for visual performance
        # In production, these would be real 'GROUP BY' queries on the transactions table
        stats = {
            "flow": [12, 19, 3, 5, 2, 3, 10, 15, 25, 22, 18, 12], # Hourly
            "accuracy": [0.85, 0.92, 0.88, 0.95, 0.89, 0.94], # Trend
            "peak_heatmap": [[j % 5 for j in range(24)] for i in range(7)] # 7x24 grid
        }
        return {"status": "success", "data": stats}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/infrastructure")
async def get_infra_health():
    """Real-time health of the AgentNet node topology."""
    return {"status": "success", "data": sre_agent.get_node_health()}

@app.get("/api/logs")
async def get_access_logs():
    """Historical entry/exit audit trail."""
    try:
        resp = supabase_manager.client.table("transactions").select("*").order("timestamp", desc=True).limit(20).execute()
        return {"status": "success", "logs": resp.data}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- EXISTING API ROUTES ---

@app.post("/api/entry")
async def trigger_entry(files: List[UploadFile] = File(...)):
    """
    Supports single or multiple images (1-10 frames) for Multi-Frame Voting.
    """
    try:
        frames_bytes = []
        # Limit to 10 frames for stability
        for file in files[:10]:
            content = await file.read()
            frames_bytes.append(content)
            
        result = await agentnet_entry_pipeline("GATE_MAIN", frames_bytes)
        return {"status": "success", "data": result}
    except Exception as e:
        print(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/verify")
async def verify_parking(req: VerifyRequest):
    try:
        v_start = time.time()
        result = verification_agent.verify_active_location(req.user_id, req.scanned_qr)
        sre_agent.log_latency("VerificationAgent", (time.time() - v_start) * 1000)
        return {"status": "success", "data": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/exit")
async def process_exit(req: ExitRequest):
    try:
        b_start = time.time()
        result = billing_agent.process_exit(req.license_plate)
        sre_agent.log_latency("BillingAgent", (time.time() - b_start) * 1000)
        return {"status": "success", "data": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/health")
async def get_network_health():
    return sre_agent.get_system_report()

# --- STATIC DASHBOARD SERVING ---

# Ensure static directory exists
static_path = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_path):
    os.makedirs(static_path)

app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/")
async def serve_dashboard():
    dashboard_file = os.path.join(static_path, "index.html")
    if os.path.exists(dashboard_file):
        return FileResponse(dashboard_file)
    return {"message": "AgentNet: Dashboard construction in progress. Please check /docs for API."}
