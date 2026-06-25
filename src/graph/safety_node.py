from src.schemas.state import GraphState
from src.graph.state import get_default_safe_state

def run_safety_node(state: GraphState) -> GraphState:
    """
    Safety Sandbox Locking Node as specified in Section 2 of AGENTS.md.
    
    Responsibilities:
    - Checks if the user is successfully onboarded (state.is_onboarded).
    - If NOT onboarded, activates the DefaultSafeState to sandbox the user.
    - Forces Beginner level, 5kg max load, and strict movement lockouts.
    - Blocks bypass attempts (prompt injections) by ignoring custom requests 
      until a valid onboarding schema has been registered.
    """
    if not state.is_onboarded:
        # User is attempting to bypass onboarding or hasn't completed it.
        # Enforce sandbox lock using DefaultSafeState constraints.
        sandbox_state = get_default_safe_state()
        
        # Preserve any transient session prompt or goals if they exist, but lock physical parameters
        if state.session_context:
            sandbox_state.session_context.session_goals = state.session_context.session_goals
            sandbox_state.session_context.current_energy = state.session_context.current_energy
            
        return sandbox_state
        
    return state
