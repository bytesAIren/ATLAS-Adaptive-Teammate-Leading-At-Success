from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from src.schemas.onboarding import OnboardingPayload

class UserProfile(BaseModel):
    """
    Persistent state layer containing the user's historical profile
    derived from the onboarding form.
    """
    nickname: str
    age: int
    height_cm: float
    weight_kg: float
    experience_level: str
    training_preference: str
    frequency: str
    equipment_list: List[str]
    objectives: List[str]



class SessionContext(BaseModel):
    """
    Transient state layer representing single-session context.
    Discarded upon session termination and does not write back to UserProfile.
    """
    current_energy: Optional[int] = Field(None, ge=1, le=10, description="User energy level from 1 to 10")
    local_injuries: List[str] = Field(default_factory=list, description="Active session injuries or painful areas")
    time_available: Optional[int] = Field(None, ge=10, le=180, description="Available duration for the session in minutes")
    equipment_override: List[str] = Field(default_factory=list, description="Available equipment overrides for the session")
    session_goals: Optional[str] = Field(None, description="Specific goals or focus for the session")
    
    # Restrictive overrides dynamically parsed from session prompt
    override: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dynamic overrides (e.g. max squat load, movement exclusions) that downscope baseline limits"
    )

class GraphState(BaseModel):
    """
    The full ADK 2.0 Graph State combining persistent and transient layers.
    """
    user_profile: Optional[UserProfile] = Field(None, description="Active user profile; None if not onboarded")
    session_context: SessionContext = Field(default_factory=SessionContext, description="Current transient session variables")
    is_onboarded: bool = Field(False, description="Flag indicating if the onboarding payload has been successfully validated")
