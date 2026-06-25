from src.schemas.state import GraphState
from typing import Dict, Any, List
from src.database.db import get_all_exercises

def apply_downscoping(profile_limits: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applies overrides as a restrictive downscoping mask over profile limits.
    Overrides can only DECREASE intensity/volume or restrict exercises; they can
    never scale limits beyond physical limits established in the UserProfile.
    """
    final_limits = profile_limits.copy()
    
    # Example Downscoping: Time constraint
    if "max_duration_minutes" in overrides:
        final_limits["max_duration_minutes"] = min(
            profile_limits.get("max_duration_minutes", 60),
            overrides["max_duration_minutes"]
        )
        
    # Example Downscoping: Load constraint
    if "max_load_kg" in overrides:
        final_limits["max_load_kg"] = min(
            profile_limits.get("max_load_kg", 20.0),
            overrides["max_load_kg"]
        )
        
    # Example Downscoping: Movement exclusion union
    profile_blocked = set(profile_limits.get("blocked_movements", []))
    override_blocked = set(overrides.get("blocked_movements", []))
    final_limits["blocked_movements"] = list(profile_blocked.union(override_blocked))
    
    return final_limits

def compile_planning_rules(state: GraphState) -> Dict[str, Any]:
    """
    Compiles planning rules combining UserProfile and SessionContext downscoping.
    Adheres strictly to the physical equipment locks specified in Section 3 of AGENTS.md.
    """
    # 1. Fetch baseline constraints based on experience level
    profile = state.user_profile
    experience = profile.experience_level if profile else "Beginner"
    
    # Establish baseline physical limits
    if experience == "Advanced":
        baseline_load = 15.0 # Max individual dumbbell weight
        baseline_duration = 90
    elif experience == "Intermediate":
        baseline_load = 10.0
        baseline_duration = 75
    else:
        baseline_load = 5.0
        baseline_duration = 45
        
    profile_limits = {
        "max_load_kg": baseline_load,
        "max_duration_minutes": baseline_duration,
        "blocked_movements": []
    }
    
    # 2. Apply active session context overrides (Restrictive downscoping only)
    overrides = state.session_context.override
    active_limits = apply_downscoping(profile_limits, overrides)
    
    # 3. Apply Hard-Locked Domain Constraints (Section 3 of AGENTS.md)
    # Dumbbell Inventory Pairs: 15kg, 10kg, 8kg, 5kg
    active_limits["available_dumbbell_pairs_kg"] = [5.0, 8.0, 10.0, 15.0]
    
    # Adjustable Bench Lock: 180 (flat) down to 90 (upright incline). Decline locked out (< 180).
    active_limits["bench_angles_range_degrees"] = {
        "min": 90.0,
        "max": 180.0,
        "decline_allowed": False
    }
    
    # Squat Capacity Lock: max squat load strictly capped at 20kg (10kg+10kg with bands)
    active_limits["max_squat_load_kg"] = min(active_limits.get("max_load_kg", 20.0), 20.0)
    
    # Determine if a strength portion is requested
    strength_requested = profile.training_preference in ("Strength", "Hybrid") if profile else True

    # Retrieve available session time — user's request is the authority.
    # The experience-based baseline_duration is ONLY used as a fallback default
    # when the user has not specified a time. It never caps a user-supplied value.
    session_time = state.session_context.time_available
    if session_time is None:
        session_time = baseline_duration  # use experience-based default
    # Clamp to 3-hour maximum for home gym context
    session_time = min(session_time, 180)

    # 1. Determine baseline target cardio finisher details based on level & objectives
    cardio_type = "Power Walk"
    target_cardio_dur = 20
    cardio_target_hr = 120
    cardio_instructions = "Maintain a steady pace to keep your heart rate in the aerobic zone."

    user_objectives = profile.objectives if profile else []
    
    if "60 minute ride" in user_objectives:
        cardio_type = "Stationary Bike / Cyclette"
        target_cardio_dur = 60
        cardio_target_hr = 130
        cardio_instructions = "Steady-state stationary bike ride. Focus on consistent pedaling and breathing."
    elif "run a 10k" in user_objectives:
        cardio_type = "10k Prep Steady Run"
        cardio_target_hr = 135
        cardio_instructions = "Steady-state jog or run at conversational pace to build endurance for 10k."
        if experience == "Advanced":
            target_cardio_dur = 40
        elif experience == "Intermediate":
            target_cardio_dur = 45
        else:
            target_cardio_dur = 50
    elif "run a 5k" in user_objectives:
        cardio_type = "5k Prep Light Run"
        cardio_target_hr = 135
        cardio_instructions = "Continuous light run or jog to build steady-state conditioning for 5k."
        if experience == "Advanced":
            target_cardio_dur = 25
        elif experience == "Intermediate":
            target_cardio_dur = 30
        else:
            target_cardio_dur = 35
    elif "10k steps a day" in user_objectives:
        cardio_type = "Post-Workout Walk"
        cardio_instructions = "Relaxed or brisk post-workout walk to cool down and hit your steps goal."
        if experience == "Advanced":
            target_cardio_dur = 35
            cardio_target_hr = 120
        elif experience == "Intermediate":
            target_cardio_dur = 30
            cardio_target_hr = 115
        else:
            target_cardio_dur = 25
            cardio_target_hr = 110
    else:
        # Default based on experience level
        cardio_instructions = "Steady aerobic base conditioning matching your current experience level."
        if experience == "Advanced":
            cardio_type = "Steady Run"
            target_cardio_dur = 30
            cardio_target_hr = 130
        elif experience == "Intermediate":
            cardio_type = "Light Jog / Cyclette"
            target_cardio_dur = 25
            cardio_target_hr = 125
        else:
            cardio_type = "Power Walk"
            target_cardio_dur = 20
            cardio_target_hr = 115

    # 2. Dynamic duration budgeting
    warmup_time = 5
    min_strength_time = 20 if strength_requested else 0

    # If the session_time is too short to even fit warmup + min strength
    if session_time <= warmup_time + min_strength_time:
        cardio_active = False
        cardio_duration = 0
        strength_time = max(0, session_time - warmup_time)
    else:
        cardio_active = True
        # Reserve at least the target cardio duration, but scale down if time is tight
        remaining_after_warmup = session_time - warmup_time
        if remaining_after_warmup - target_cardio_dur >= min_strength_time:
            reserved_cardio = target_cardio_dur
        else:
            # Scale down cardio to guarantee a minimum strength block
            reserved_cardio = max(10, remaining_after_warmup - min_strength_time)

        strength_time = remaining_after_warmup - reserved_cardio
        if strength_time < 0:
            strength_time = 0

    # 3. Dynamic Strength Exercises Count calculation
    # ~10 min per exercise. Cap at 10 exercises max for home gym context, minimum 2.
    if strength_requested:
        max_strength_exercises = min(10, max(2, strength_time // 10))
    else:
        max_strength_exercises = 0

    final_strength_time = max_strength_exercises * 10

    # Any time not consumed by strength exercises is added back into the cardio finisher,
    # so the full requested session_time is always honoured.
    if cardio_active:
        leftover = strength_time - final_strength_time
        cardio_duration = reserved_cardio + max(0, leftover)
    else:
        cardio_duration = 0

    # Cardio finisher constraints
    active_limits["post_strength_cardio"] = {
        "active": cardio_active,
        "type": cardio_type,
        "duration_minutes": cardio_duration,
        "target_heart_rate_bpm": cardio_target_hr,
        "tolerance_bpm": 5,
        "instructions": cardio_instructions
    }

    active_limits["max_strength_exercises"] = max_strength_exercises
    active_limits["max_duration_minutes"] = session_time
    active_limits["strength_duration_minutes"] = final_strength_time

    
    # 4. Resolve Dynamic Movement Allowlist via DB Cross-Referencing
    user_equipment = set(profile.equipment_list if profile else [])
    
    # Map experience thresholds
    allowed_experience_levels = {"Beginner"}
    if experience in ("Intermediate", "Advanced"):
        allowed_experience_levels.add("Intermediate")
    if experience == "Advanced":
        allowed_experience_levels.add("Advanced")
        
    try:
        all_exercises = get_all_exercises()
        movement_allowlist = []
        for ex in all_exercises:
            required = set(ex["required_equipment"])
            # Check equipment availability (all required equipment must be owned by user)
            if required.issubset(user_equipment):
                # Check experience requirement
                if ex["min_experience"] in allowed_experience_levels:
                    movement_allowlist.append(ex["name"])
        
        # Apply downscoping: filter out any blocked movements from the allowlist
        blocked = set(active_limits.get("blocked_movements", []))
        active_limits["movement_allowlist"] = [
            name for name in movement_allowlist if name not in blocked
        ]
    except Exception as e:
        # Fallback if DB query fails
        active_limits["movement_allowlist"] = ["Bodyweight Squat", "Shadow Boxing"]
    
    return active_limits


def run_planning_node(state: GraphState) -> GraphState:
    """
    Workflow Planning Node responsible for generating the safe workout plan boundaries.
    
    Implementation details under AGENTS.md:
    - Reads UserProfile and SessionContext.
    - Applies downscoping rules where overrides restrict baseline capabilities.
    - Enforces equipment locks (Bench angles, Dumbbell pairs, 20kg Squat limit).
    - Incorporates post-strength cardio protocols.
    """
    # Compile the active limits constraint dict
    active_constraints = compile_planning_rules(state)
    
    # In a fully implemented graph, these constraints would be fed into the prompt generator or local planner.
    # For now, we attach the compiled rules to the session context overrides for validation downstream.
    updated_state = state.model_copy(deep=True)
    updated_state.session_context.override.update({
        "compiled_planning_rules": active_constraints
    })
    
    return updated_state
