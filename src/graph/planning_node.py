from typing import Any, Dict, List, Set

from src.database.db import get_all_exercises
from src.schemas.state import GraphState

CARDIO_OBJECTIVES = {"60 minute ride", "run a 5k", "run a 10k", "lose weight"}
STRENGTH_OBJECTIVES = {"gain muscle"}
SAFE_FALLBACK_EXERCISES = [
    "Chair Sit-to-Stand",
    "Wall Push-up",
    "Supported March",
    "Standing Heel Raise",
    "Push-up",
    "Glute Bridge",
    "Plank",
    "Lunge",
    "Mountain Climber",
]
GENTLE_MODE_EXERCISES = [
    "Chair Sit-to-Stand",
    "Supported March",
    "Standing Heel Raise",
    "Wall Push-up",
    "Glute Bridge",
    "Plank",
]

INJURY_RULES: Dict[str, Dict[str, Any]] = {
    "shoulder": {
        "blocked_movements": [
            "Dumbbell Bench Press",
            "Incline Dumbbell Press",
            "Push-up",
            "Wall Push-up",
        ],
        "blocked_keywords": ["press", "overhead"],
        "max_load_kg": 8.0,
    },
    "lower back": {
        "blocked_movements": [
            "Bodyweight Squat",
            "Dumbbell Romanian Deadlift",
            "Goblet Squat",
            "Bench Step-Up",
            "Burpees",
            "Lunge",
            "Mountain Climber",
        ],
        "blocked_keywords": ["deadlift", "hinge"],
        "max_load_kg": 8.0,
        "max_squat_load_kg": 10.0,
    },
    "knee": {
        "blocked_movements": [
            "Bodyweight Squat",
            "Bench Step-Up",
            "Chair Sit-to-Stand",
            "Goblet Squat",
            "Burpees",
            "Mountain Climber",
        ],
        "blocked_keywords": ["jump", "jog", "lunge", "run", "step-up"],
        "max_squat_load_kg": 5.0,
    },
    "sciatica": {
        "blocked_movements": [
            "Bodyweight Squat",
            "Dumbbell Romanian Deadlift",
            "Goblet Squat",
            "Bench Step-Up",
            "Burpees",
            "Lunge",
            "Mountain Climber",
        ],
        "blocked_keywords": ["deadlift", "hinge"],
        "max_load_kg": 5.0,
        "max_squat_load_kg": 5.0,
    },
}


def apply_downscoping(profile_limits: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applies overrides as a restrictive mask over the persistent profile limits.
    Overrides may only reduce capabilities for the active session.
    """
    final_limits = profile_limits.copy()

    if "max_duration_minutes" in overrides:
        final_limits["max_duration_minutes"] = min(
            profile_limits.get("max_duration_minutes", 60),
            overrides["max_duration_minutes"],
        )

    if "max_load_kg" in overrides:
        final_limits["max_load_kg"] = min(
            profile_limits.get("max_load_kg", 20.0),
            overrides["max_load_kg"],
        )

    profile_blocked = set(profile_limits.get("blocked_movements", []))
    override_blocked = set(overrides.get("blocked_movements", []))
    final_limits["blocked_movements"] = sorted(profile_blocked.union(override_blocked))
    final_limits["blocked_keywords"] = sorted(
        set(profile_limits.get("blocked_keywords", [])).union(overrides.get("blocked_keywords", []))
    )

    return final_limits


def _collect_injury_overrides(local_injuries: List[str]) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {
        "blocked_movements": [],
        "blocked_keywords": [],
    }

    for injury in local_injuries:
        injury_lower = injury.lower()
        for rule_key, rule_data in INJURY_RULES.items():
            if rule_key in injury_lower:
                overrides["blocked_movements"].extend(rule_data.get("blocked_movements", []))
                overrides["blocked_keywords"].extend(rule_data.get("blocked_keywords", []))
                if "max_load_kg" in rule_data:
                    current_load = overrides.get("max_load_kg", rule_data["max_load_kg"])
                    overrides["max_load_kg"] = min(current_load, rule_data["max_load_kg"])
                if "max_squat_load_kg" in rule_data:
                    current_squat = overrides.get("max_squat_load_kg", rule_data["max_squat_load_kg"])
                    overrides["max_squat_load_kg"] = min(current_squat, rule_data["max_squat_load_kg"])

    overrides["blocked_movements"] = sorted(set(overrides["blocked_movements"]))
    overrides["blocked_keywords"] = sorted(set(overrides["blocked_keywords"]))
    return overrides


def _merge_overrides(*override_sets: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {
        "blocked_movements": [],
        "blocked_keywords": [],
    }

    for overrides in override_sets:
        merged["blocked_movements"].extend(overrides.get("blocked_movements", []))
        merged["blocked_keywords"].extend(overrides.get("blocked_keywords", []))

        if "max_load_kg" in overrides:
            current = merged.get("max_load_kg", overrides["max_load_kg"])
            merged["max_load_kg"] = min(current, overrides["max_load_kg"])

        if "max_duration_minutes" in overrides:
            current = merged.get("max_duration_minutes", overrides["max_duration_minutes"])
            merged["max_duration_minutes"] = min(current, overrides["max_duration_minutes"])

        if "max_squat_load_kg" in overrides:
            current = merged.get("max_squat_load_kg", overrides["max_squat_load_kg"])
            merged["max_squat_load_kg"] = min(current, overrides["max_squat_load_kg"])

    merged["blocked_movements"] = sorted(set(merged["blocked_movements"]))
    merged["blocked_keywords"] = sorted(set(merged["blocked_keywords"]))
    return merged


def _cardio_triggered(state: GraphState) -> bool:
    profile = state.user_profile
    if not profile:
        return False
    if profile.training_preference in ("Cardio", "Hybrid"):
        return True
    return any(objective in CARDIO_OBJECTIVES for objective in profile.objectives)


def _strength_requested(state: GraphState, cardio_active: bool) -> bool:
    profile = state.user_profile
    if not profile:
        return True

    goals = (state.session_context.session_goals or "").lower()
    if "cardio only" in goals:
        return False
    if any(objective in STRENGTH_OBJECTIVES for objective in profile.objectives):
        return True
    if profile.training_preference in ("Strength", "Hybrid"):
        return True
    return cardio_active


def _prefers_minimum_strength_block(state: GraphState) -> bool:
    profile = state.user_profile
    if not profile:
        return False

    goals = (state.session_context.session_goals or "").lower()
    strength_keywords = ("strength", "muscle", "legs", "chest", "back", "upper body", "lower body")
    if any(keyword in goals for keyword in strength_keywords):
        return False

    return (
        profile.training_preference == "Cardio"
        or "healthy life" in profile.objectives
        or "lose weight" in profile.objectives
    )


def _requires_joint_protection_minimum(state: GraphState) -> bool:
    profile = state.user_profile
    if not profile:
        return False

    injuries = " ".join(state.session_context.local_injuries).lower()
    protected_area = "knee" in injuries or "lower back" in injuries or "sciatica" in injuries
    if not protected_area:
        return False

    return (
        profile.experience_level == "Beginner"
        or profile.age >= 60
        or profile.weight_kg >= 95.0
    )


def _apply_gentle_mode_filter(
    allowlist: List[str],
    state: GraphState,
    blocked_movements: Set[str],
    blocked_keywords: Set[str],
) -> List[str]:
    if not _is_frail_profile(state.user_profile):
        return allowlist

    gentle_pool = [
        name for name in GENTLE_MODE_EXERCISES
        if name in allowlist and name not in blocked_movements and not any(keyword in name.lower() for keyword in blocked_keywords)
    ]

    if gentle_pool:
        return gentle_pool
    return allowlist


def _resolve_effective_equipment(state: GraphState) -> Set[str]:
    profile_equipment = set(state.user_profile.equipment_list if state.user_profile else [])
    override_equipment = set(state.session_context.equipment_override or [])
    if not override_equipment:
        return profile_equipment
    return profile_equipment.intersection(override_equipment)


def _calculate_bmi(profile: Any) -> float | None:
    if not profile or not profile.height_cm:
        return None
    height_m = profile.height_cm / 100.0
    if height_m <= 0:
        return None
    return profile.weight_kg / (height_m * height_m)


def _is_frail_profile(profile: Any) -> bool:
    if not profile:
        return False
    bmi = _calculate_bmi(profile)
    return (
        profile.experience_level == "Beginner"
        and (
            profile.age >= 70
            or (bmi is not None and bmi >= 35.0)
        )
    )


def _resolve_cardio_config(profile: Any, experience: str, injuries: List[str]) -> Dict[str, Any]:
    objectives = profile.objectives if profile else []
    equipment = set(profile.equipment_list if profile else [])
    injury_text = " ".join(injuries).lower()
    knee_sensitive = "knee" in injury_text
    lower_back_sensitive = "lower back" in injury_text or "sciatica" in injury_text
    frail_profile = _is_frail_profile(profile)

    if "lose weight" in objectives:
        if "stationary_bike" in equipment:
            return {
                "type": "Stationary Bike Fat-Loss Base",
                "instructions": (
                    "Stay at a very sustainable pace on the bike, keep posture tall, and stop before symptoms in the back or legs increase."
                    if frail_profile or lower_back_sensitive
                    else "Stay at a sustainable pace on the bike and prioritize continuous aerobic work over intensity spikes."
                ),
                "target_duration_minutes": 30 if frail_profile else 45 if experience == "Advanced" else 35 if experience == "Intermediate" else 30,
            }
        if "treadmill" in equipment:
            return {
                "type": "Treadmill Incline Walk",
                "instructions": (
                    "Use a flat or very light incline walking pace that feels controlled and symptom-free, holding the rails if needed."
                    if frail_profile or knee_sensitive or lower_back_sensitive
                    else "Use a brisk incline walk that stays joint-friendly while keeping heart rate steadily elevated."
                ),
                "target_duration_minutes": 25 if frail_profile else 40 if experience == "Advanced" else 30 if experience == "Intermediate" else 25,
            }
        return {
            "type": "Low-Impact Fat-Loss Conditioning",
            "instructions": "Choose a sustainable, low-impact cardio pace and focus on keeping the effort continuous, gentle, and repeatable.",
            "target_duration_minutes": 25 if frail_profile else 35 if experience == "Advanced" else 30 if experience == "Intermediate" else 25,
        }

    if "60 minute ride" in objectives:
        return {
            "type": "Stationary Bike / Cyclette",
            "instructions": "Steady-state stationary bike ride. Focus on consistent pedaling and breathing.",
            "target_duration_minutes": 60 if experience == "Advanced" else 45 if experience == "Intermediate" else 35,
        }
    if "run a 10k" in objectives:
        return {
            "type": "Low-Impact Aerobic Base" if knee_sensitive else "10k Prep Steady Run",
            "instructions": (
                "Low-impact aerobic base work to protect the knees while preserving endurance development."
                if knee_sensitive
                else "Steady-state jog or run at conversational pace to build endurance for 10k."
            ),
            "target_duration_minutes": 40 if experience == "Advanced" else 30 if experience == "Intermediate" else 25,
        }
    if "run a 5k" in objectives:
        return {
            "type": "Low-Impact Aerobic Base" if knee_sensitive else "5k Prep Light Run",
            "instructions": (
                "Low-impact aerobic base work to protect the knees while preserving conditioning."
                if knee_sensitive
                else "Continuous light run or jog to build steady-state conditioning for 5k."
            ),
            "target_duration_minutes": 30 if experience == "Advanced" else 25 if experience == "Intermediate" else 20,
        }

    if "gain muscle" in objectives:
        return {
            "type": "Short Aerobic Recovery Block",
            "instructions": "Keep the cardio easy and recovery-focused so it supports the strength emphasis instead of competing with it.",
            "target_duration_minutes": 20 if experience == "Advanced" else 15,
        }

    if knee_sensitive:
        return {
            "type": "Low-Impact Conditioning Walk",
            "instructions": "Use a pain-free walking pace or light cycling effort that keeps the knees comfortable.",
            "target_duration_minutes": 25 if experience == "Advanced" else 20,
        }

    if lower_back_sensitive:
        return {
            "type": "Supported Aerobic Base Conditioning",
            "instructions": "Choose a smooth, posture-friendly cardio option and keep the effort comfortably aerobic.",
            "target_duration_minutes": 25 if experience == "Advanced" else 20,
        }

    return {
        "type": "Aerobic Base Conditioning",
        "instructions": "Maintain steady aerobic base work and adjust pace to stay on target heart rate.",
        "target_duration_minutes": 30 if experience == "Advanced" else 25 if experience == "Intermediate" else 20,
    }


def _resolve_cardio_trigger_reason(state: GraphState, cardio_active: bool) -> str:
    if not state.is_onboarded:
        return "Cardio finisher inactive while the safety sandbox is active. Complete onboarding to unlock profile-driven cardio planning."

    if not cardio_active:
        return "Cardio finisher inactive because the profile does not require a cardio block."
    profile = state.user_profile

    if profile.training_preference in ("Cardio", "Hybrid"):
        return f"Cardio finisher activated by training preference: {profile.training_preference}."

    matched_objectives = [objective for objective in profile.objectives if objective in CARDIO_OBJECTIVES]
    if matched_objectives:
        return f"Cardio finisher activated by cardio objective: {matched_objectives[0]}."

    return "Cardio finisher activated by planning policy."


def _resolve_cardio_target(profile: Any, experience: str, injuries: List[str]) -> tuple[int, int]:
    if not profile:
        return (130, 5)

    bmi = _calculate_bmi(profile)
    injury_text = " ".join(injuries).lower()
    fragile_or_sensitive = (
        _is_frail_profile(profile)
        or "knee" in injury_text
        or "lower back" in injury_text
        or "sciatica" in injury_text
    )

    if fragile_or_sensitive:
        return (110, 10)
    if experience == "Beginner":
        if profile.age >= 60 or (bmi is not None and bmi >= 30.0):
            return (115, 8)
        return (120, 8)
    if experience == "Intermediate":
        return (125, 6)
    return (130, 5)


def _resolve_strength_time(session_time: int, cardio_duration: int, strength_requested: bool) -> int:
    if not strength_requested:
        return 0
    remaining = max(0, session_time - cardio_duration)
    if remaining <= 0:
        return min(20, session_time)
    return remaining


def _build_downscoping_reasons(
    state: GraphState,
    combined_overrides: Dict[str, Any],
    effective_equipment: Set[str],
    cardio_duration: int | None = None,
    target_cardio_duration: int | None = None,
) -> List[str]:
    reasons: List[str] = []
    if state.session_context.local_injuries:
        reasons.append(
            "Local injuries triggered protective downscoping: "
            + ", ".join(state.session_context.local_injuries)
            + "."
        )
    if state.session_context.equipment_override:
        reasons.append(
            "Session equipment override reduced the available inventory to: "
            + ", ".join(sorted(effective_equipment))
            + "."
        )
    if "max_load_kg" in combined_overrides:
        reasons.append(f"Session downscoping reduced max load to {combined_overrides['max_load_kg']} kg.")
    if "max_squat_load_kg" in combined_overrides:
        reasons.append(
            f"Session downscoping reduced max squat load to {combined_overrides['max_squat_load_kg']} kg."
        )
    if cardio_duration is not None and target_cardio_duration is not None and cardio_duration < target_cardio_duration:
        reasons.append(
            f"Cardio duration was reduced from the ideal {target_cardio_duration} minutes to {cardio_duration} minutes to stay within the requested session time."
        )
    if not reasons:
        reasons.append("No transient downscoping was required beyond the baseline profile and hard equipment locks.")
    return reasons


def _filter_allowlist(allowlist: List[str], blocked_movements: Set[str], blocked_keywords: Set[str]) -> List[str]:
    filtered: List[str] = []
    for name in allowlist:
        lowered = name.lower()
        if name in blocked_movements:
            continue
        if any(keyword in lowered for keyword in blocked_keywords):
            continue
        filtered.append(name)
    return filtered


def _extend_with_safe_fallbacks(
    allowlist: List[str],
    blocked_movements: Set[str],
    blocked_keywords: Set[str],
) -> List[str]:
    extended = list(allowlist)
    for candidate in SAFE_FALLBACK_EXERCISES:
        lowered = candidate.lower()
        if candidate in extended or candidate in blocked_movements:
            continue
        if any(keyword in lowered for keyword in blocked_keywords):
            continue
        extended.append(candidate)
    return extended


def _count_selectable_strength_exercises(allowlist: List[str]) -> int:
    return len([name for name in allowlist if name not in ("Shadow Boxing", "Burpees")])


def compile_planning_rules(state: GraphState) -> Dict[str, Any]:
    """
    Compiles planning rules combining UserProfile and SessionContext downscoping.
    Adheres strictly to the physical equipment locks specified in AGENTS.md.
    """
    profile = state.user_profile
    experience = profile.experience_level if profile else "Beginner"

    if not state.is_onboarded:
        baseline_load = 5.0
        baseline_duration = 30
        baseline_blocked = sorted(set(state.session_context.override.get("blocked_movements", [])))
        baseline_keywords = sorted(set(state.session_context.override.get("blocked_keywords", [])))
    elif experience == "Advanced":
        baseline_load = 15.0
        baseline_duration = 90
        baseline_blocked = []
        baseline_keywords = []
    elif experience == "Intermediate":
        baseline_load = 10.0
        baseline_duration = 75
        baseline_blocked = []
        baseline_keywords = []
    else:
        baseline_load = 5.0
        baseline_duration = 45
        baseline_blocked = []
        baseline_keywords = []

    profile_limits = {
        "max_load_kg": baseline_load,
        "max_duration_minutes": baseline_duration,
        "blocked_movements": baseline_blocked,
        "blocked_keywords": baseline_keywords,
    }

    session_overrides = state.session_context.override
    injury_overrides = _collect_injury_overrides(state.session_context.local_injuries)
    combined_overrides = _merge_overrides(session_overrides, injury_overrides)
    active_limits = apply_downscoping(profile_limits, combined_overrides)

    active_limits["available_dumbbell_pairs_kg"] = [5.0, 8.0, 10.0, 15.0]
    active_limits["bench_angles_range_degrees"] = {
        "min": 90.0,
        "max": 180.0,
        "decline_allowed": False,
    }
    active_limits["max_squat_load_kg"] = min(
        active_limits.get("max_load_kg", 20.0),
        combined_overrides.get("max_squat_load_kg", 20.0),
        20.0,
    )

    session_time = state.session_context.time_available
    if session_time is None:
        session_time = baseline_duration
    session_time = min(session_time, 180)

    cardio_active = _cardio_triggered(state) if state.is_onboarded else False
    strength_requested = _strength_requested(state, cardio_active)
    cardio_cfg = _resolve_cardio_config(profile, experience, state.session_context.local_injuries)
    target_cardio_duration = cardio_cfg.get("target_duration_minutes", 20)

    min_strength_duration = 20 if strength_requested else 0
    minimum_strength_block_only = (
        _prefers_minimum_strength_block(state)
        or _requires_joint_protection_minimum(state)
    )

    if cardio_active:
        cardio_budget_ceiling = max(0, session_time - min_strength_duration)
        cardio_duration = min(target_cardio_duration, cardio_budget_ceiling) if strength_requested else min(
            target_cardio_duration,
            session_time,
        )
    else:
        cardio_duration = 0

    strength_duration = _resolve_strength_time(session_time, cardio_duration, strength_requested)

    if strength_requested:
        if minimum_strength_block_only:
            strength_duration = min(20, session_time)
            if cardio_active:
                cardio_duration = max(0, session_time - strength_duration)
        max_strength_exercises = max(2, strength_duration // 10) if strength_duration >= 20 else 2
        strength_duration = max_strength_exercises * 10
        if cardio_active and strength_duration + cardio_duration > session_time:
            strength_duration = max(20, session_time - cardio_duration)
            max_strength_exercises = max(2, strength_duration // 10)
            strength_duration = max_strength_exercises * 10
        if cardio_active and strength_duration + cardio_duration > session_time:
            cardio_duration = max(0, session_time - strength_duration)
        if cardio_active and strength_duration + cardio_duration < session_time:
            cardio_duration += session_time - (strength_duration + cardio_duration)
    else:
        max_strength_exercises = 0

    total_budgeted_minutes = strength_duration + cardio_duration

    cardio_target_bpm, cardio_tolerance_bpm = _resolve_cardio_target(
        profile,
        experience,
        state.session_context.local_injuries,
    )
    cardio_trigger_reason = _resolve_cardio_trigger_reason(state, cardio_active)
    active_limits["post_strength_cardio"] = {
        "active": cardio_active,
        "type": cardio_cfg["type"],
        "duration_minutes": cardio_duration,
        "target_heart_rate_bpm": cardio_target_bpm,
        "tolerance_bpm": cardio_tolerance_bpm,
        "instructions": cardio_cfg["instructions"],
        "trigger_reason": cardio_trigger_reason,
    }

    active_limits["max_strength_exercises"] = max_strength_exercises
    active_limits["max_duration_minutes"] = session_time
    active_limits["strength_duration_minutes"] = strength_duration
    active_limits["budgeted_session_minutes"] = total_budgeted_minutes
    effective_equipment = _resolve_effective_equipment(state)
    active_limits["effective_equipment"] = sorted(effective_equipment)
    active_limits["applied_injuries"] = list(state.session_context.local_injuries)
    active_limits["strength_requested"] = strength_requested
    active_limits["strength_request_reason"] = (
        "Strength block kept to the minimum maintenance dose because this session prioritizes joint protection or cardio emphasis."
        if strength_requested and minimum_strength_block_only
        else "Strength block preserved because the profile or session goals requested strength work."
        if strength_requested
        else "Strength block omitted because the session goals explicitly requested cardio only."
    )
    active_limits["downscoping_reasons"] = _build_downscoping_reasons(
        state,
        combined_overrides,
        effective_equipment,
        cardio_duration=cardio_duration,
        target_cardio_duration=target_cardio_duration if cardio_active else None,
    )
    active_limits["agent_trace"] = [
        {
            "step": "intake",
            "status": "completed",
            "detail": "Session context collected from onboarding and workout inputs.",
        },
        {
            "step": "safety",
            "status": "completed",
            "detail": "Safety sandbox and profile state evaluated before planning.",
        },
        {
            "step": "planning",
            "status": "completed",
            "detail": "Constraints compiled from profile, session overrides, injuries, and equipment locks.",
        },
        {
            "step": "composition",
            "status": "pending",
            "detail": "Workout plan composition will use the compiled planning rules.",
        },
        {
            "step": "critic",
            "status": "pending",
            "detail": "Plan review will verify that the composed workout respects all hard constraints.",
        },
    ]

    blocked_movements = set(active_limits.get("blocked_movements", []))
    blocked_keywords = set(active_limits.get("blocked_keywords", []))

    if not state.is_onboarded:
        safe_allowlist = state.session_context.override.get("movement_allowlist", [])
        filtered_allowlist = _filter_allowlist(
            safe_allowlist,
            blocked_movements,
            blocked_keywords,
        )
        active_limits["movement_allowlist"] = _apply_gentle_mode_filter(
            filtered_allowlist,
            state,
            blocked_movements,
            blocked_keywords,
        )
    else:
        user_equipment = set(active_limits["effective_equipment"])
        allowed_experience_levels = {"Beginner"}
        if experience in ("Intermediate", "Advanced"):
            allowed_experience_levels.add("Intermediate")
        if experience == "Advanced":
            allowed_experience_levels.add("Advanced")

        try:
            all_exercises = get_all_exercises()
            movement_allowlist = []
            for exercise in all_exercises:
                required = set(exercise["required_equipment"])
                if required.issubset(user_equipment) and exercise["min_experience"] in allowed_experience_levels:
                    movement_allowlist.append(exercise["name"])

            filtered_allowlist = _filter_allowlist(
                movement_allowlist,
                blocked_movements,
                blocked_keywords,
            )
            extended_allowlist = _extend_with_safe_fallbacks(
                filtered_allowlist,
                blocked_movements,
                blocked_keywords,
            )
            active_limits["movement_allowlist"] = _apply_gentle_mode_filter(
                extended_allowlist,
                state,
                blocked_movements,
                blocked_keywords,
            )
        except Exception:
            filtered_allowlist = _filter_allowlist(
                ["Bodyweight Squat", "Shadow Boxing"],
                blocked_movements,
                blocked_keywords,
            )
            extended_allowlist = _extend_with_safe_fallbacks(
                filtered_allowlist,
                blocked_movements,
                blocked_keywords,
            )
            active_limits["movement_allowlist"] = _apply_gentle_mode_filter(
                extended_allowlist,
                state,
                blocked_movements,
                blocked_keywords,
            )

    available_strength_exercises = _count_selectable_strength_exercises(active_limits["movement_allowlist"])
    if max_strength_exercises > available_strength_exercises:
        max_strength_exercises = available_strength_exercises
        strength_duration = max_strength_exercises * 10
        if cardio_active:
            cardio_duration = min(cardio_duration, max(0, session_time - strength_duration))
        total_budgeted_minutes = strength_duration + cardio_duration

    active_limits["max_strength_exercises"] = max_strength_exercises
    active_limits["strength_duration_minutes"] = strength_duration
    active_limits["budgeted_session_minutes"] = total_budgeted_minutes

    return active_limits


def run_planning_node(state: GraphState) -> GraphState:
    """
    Workflow Planning Node responsible for generating the safe workout plan boundaries.
    """
    active_constraints = compile_planning_rules(state)

    updated_state = state.model_copy(deep=True)
    updated_state.session_context.override.update({
        "compiled_planning_rules": active_constraints
    })

    return updated_state
