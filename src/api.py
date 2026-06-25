import os
from dotenv import load_dotenv

# Load environment variables from .env at the root of the project.
# This makes GEMINI_API_KEY available to os.environ before any node runs.
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from src.database.db import get_all_equipment, init_db
from src.schemas.state import GraphState, SessionContext
from src.graph.state import get_default_safe_state, patch_state
from src.graph.safety_node import run_safety_node
from src.graph.validator_node import run_validator_node
from src.graph.planning_node import run_planning_node
from src.graph.generator import generate_workout_plan

app = FastAPI(title="ATLAS - Adaptive Teammate Leading At Success API", version="2.0")

# Enable CORS for local front-end integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Determine the project root for serving static files
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")

# In-memory graph state store representing the active user session
active_graph_state: GraphState = get_default_safe_state()

class SessionRequestPayload(BaseModel):
    current_energy: Optional[int] = Field(None, ge=1, le=10)
    local_injuries: Optional[List[str]] = Field(default_factory=list)
    time_available: Optional[int] = Field(None, ge=10, le=180)
    session_goals: Optional[str] = None

@app.on_event("startup")
def startup_event():
    # Re-load .env in case the server was started without it already in scope
    load_dotenv()
    # Ensure database is seeded at start
    init_db()
    api_key_status = "SET" if os.environ.get("GEMINI_API_KEY") else "NOT SET"
    print(f"[Startup] GEMINI_API_KEY status: {api_key_status}")

@app.get("/api/equipment")
def get_equipment():
    """Returns the list of seeded home gym equipment types."""
    try:
        return get_all_equipment()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

@app.get("/api/state")
def get_state():
    """Returns the active state of the personal trainer graph."""
    return active_graph_state.model_dump()

@app.post("/api/reset")
def reset_state():
    """Resets the graph back to the unonboarded DefaultSafeState."""
    global active_graph_state
    active_graph_state = get_default_safe_state()
    return {"message": "State reset successfully.", "state": active_graph_state.model_dump()}

@app.post("/api/onboard")
def onboard_user(payload: Dict[str, Any]):
    """
    Onboarding Form Endpoint.
    Passes data through the validator node.
    - If valid: commits UserProfile and unlocks the safety sandbox.
    - If invalid: maintains safe state and returns natural language clarification.
    """
    global active_graph_state
    
    # Run the validator node
    updated_state, response = run_validator_node(active_graph_state, payload)
    
    # Commit state changes to active session
    active_graph_state = updated_state
    return response

@app.post("/api/session")
def create_session(payload: SessionRequestPayload):
    """
    Starts/Generates a daily workout session.
    1. Patches SessionContext transient variables.
    2. Runs Safety Node (checks if sandbox is active).
    3. Runs Planning Node (downscopes and compiles limits).
    4. Generates the structured workout plan.
    """
    global active_graph_state
    
    # 1. Patch session context overrides
    session_patch = {
        "session_context": {
            "current_energy": payload.current_energy,
            "local_injuries": payload.local_injuries or [],
            "time_available": payload.time_available,
            "session_goals": payload.session_goals
        }
    }
    
    try:
        # Run state patch
        patched_state = patch_state(active_graph_state, session_patch)
        
        # 2. Run safety sandbox check
        secured_state = run_safety_node(patched_state)
        
        # 3. Run planning node constraints compilation
        planned_state = run_planning_node(secured_state)
        
        # Save state changes (transient session details are recorded in state)
        active_graph_state = planned_state
        
        # 4. Generate actual workout details
        workout_plan = generate_workout_plan(active_graph_state)
        
        return {
            "success": True,
            "workout_plan": workout_plan,
            "is_sandboxed": not active_graph_state.is_onboarded
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate session: {str(e)}")

# Serve the front-end SPA at root
@app.get("/")
def serve_root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# Mount static assets (CSS, JS) — must be after all API routes
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api:app", host="127.0.0.1", port=8000, reload=True)
