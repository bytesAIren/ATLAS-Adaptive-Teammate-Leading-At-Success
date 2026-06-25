from typing import Dict, Any, List
from copy import deepcopy
from src.schemas.state import GraphState, UserProfile, SessionContext

class StateConflictError(ValueError):
    """Exception raised when a state patch operation encounters conflicting updates."""
    pass

def get_default_safe_profile() -> UserProfile:
    """
    Returns the UserProfile representation under DefaultSafeState sandbox constraints.
    Note: These are baseline safety constraints applied if onboarding is bypassed.
    """
    return UserProfile(
        nickname="SandboxUser",
        age=16,
        height_cm=130.0,
        weight_kg=40.0,
        experience_level="Beginner",
        training_preference="Hybrid",
        frequency="1-2 times/week",
        equipment_list=[],
        objectives=[]
    )



def get_default_safe_session_context() -> SessionContext:
    """
    Returns the SessionContext under DefaultSafeState sandbox constraints.
    """
    return SessionContext(
        current_energy=5,
        local_injuries=[],
        time_available=30,
        equipment_override=["Light Resistance Bands"],
        session_goals="Introduction and Safety Orientation",
        override={
            "max_load_capacity": "5 kg",
            "movement_allowlist": [
                "bodyweight squat", 
                "wall push-up", 
                "light band pull", 
                "glute bridge", 
                "plank"
            ],
            "blocked_movements": [
                "overhead press", 
                "barbell back squat", 
                "deadlift", 
                "kettlebell swing", 
                "clean and jerk", 
                "snatch"
            ]
        }
    )

def get_default_safe_state() -> GraphState:
    """
    Constructs the default sandbox safe state.
    Triggers automatically when onboarding has not been completed.
    """
    return GraphState(
        user_profile=get_default_safe_profile(),
        session_context=get_default_safe_session_context(),
        is_onboarded=False
    )

def patch_state(current_state: GraphState, patch_data: Dict[str, Any]) -> GraphState:
    """
    Applies partial patching (PATCH semantics) to the GraphState.
    Upserts / complete state replacements are strictly prohibited.
    
    If conflicting keys or invalid operations are detected, it raises a
    StateConflictError, allowing the graph to rollback to the last healthy state.
    """
    # Create a backup for rollback
    last_known_healthy = current_state.model_copy(deep=True)
    
    try:
        # Prevent full state replacement attempts (UPSERT block)
        if not isinstance(patch_data, dict):
            raise StateConflictError("Patch payload must be a dictionary, full replacements are prohibited.")
            
        # Detect conflict: trying to overwrite the entire state structure instead of patching fields
        # If the patch payload tries to completely replace 'user_profile' or 'session_context' as a whole object,
        # rather than updating their fields, we enforce dictionary-based merging.
        merged_profile_dict = {}
        if "user_profile" in patch_data:
            if patch_data["user_profile"] is None:
                merged_profile_dict = None
            elif isinstance(patch_data["user_profile"], dict):
                current_profile_dict = (
                    current_state.user_profile.model_dump() 
                    if current_state.user_profile 
                    else {}
                )
                # Check for direct conflicts (e.g. if the patch is trying to upsert and delete all existing keys)
                merged_profile_dict = {**current_profile_dict, **patch_data["user_profile"]}
            else:
                raise StateConflictError("UserProfile must be patched as a dictionary, not replaced entirely.")
        else:
            merged_profile_dict = current_state.user_profile.model_dump() if current_state.user_profile else None

        merged_session_dict = {}
        if "session_context" in patch_data:
            if isinstance(patch_data["session_context"], dict):
                current_session_dict = current_state.session_context.model_dump()
                # Deep merge session overrides specifically
                current_override = current_session_dict.get("override", {})
                patch_override = patch_data["session_context"].get("override", {})
                
                if isinstance(patch_override, dict):
                    merged_override = {**current_override, **patch_override}
                else:
                    raise StateConflictError("SessionContext override must be a dictionary.")
                
                # Merge main session context fields
                merged_session_dict = {**current_session_dict, **patch_data["session_context"]}
                merged_session_dict["override"] = merged_override
            else:
                raise StateConflictError("SessionContext must be patched as a dictionary, not replaced entirely.")
        else:
            merged_session_dict = current_state.session_context.model_dump()

        # Compile patched state
        patched_profile = UserProfile(**merged_profile_dict) if merged_profile_dict else None
        patched_session = SessionContext(**merged_session_dict)
        
        is_onboarded_val = patch_data.get("is_onboarded", current_state.is_onboarded)
        
        # Build new state object
        new_state = GraphState(
            user_profile=patched_profile,
            session_context=patched_session,
            is_onboarded=is_onboarded_val
        )
        return new_state
        
    except Exception as e:
        if isinstance(e, StateConflictError):
            raise e
        # Raise StateConflictError on any validation/parsing crash to force rollback
        raise StateConflictError(f"State mutation failed due to a schema conflict: {str(e)}") from e
