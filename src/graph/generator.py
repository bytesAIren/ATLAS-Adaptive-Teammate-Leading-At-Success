import json
import os
from typing import Any, Dict, List

from src.database.db import get_all_exercises
from src.schemas.state import GraphState


FALLBACK_EXERCISE_METADATA: Dict[str, Dict[str, str]] = {
    "Chair Sit-to-Stand": {"muscle_group": "Legs", "exercise_type": "Strength"},
    "Wall Push-up": {"muscle_group": "Chest", "exercise_type": "Strength"},
    "Supported March": {"muscle_group": "Core", "exercise_type": "Strength"},
    "Standing Heel Raise": {"muscle_group": "Legs", "exercise_type": "Strength"},
    "Push-up": {"muscle_group": "Chest", "exercise_type": "Strength"},
    "Glute Bridge": {"muscle_group": "Legs", "exercise_type": "Strength"},
    "Plank": {"muscle_group": "Core", "exercise_type": "Strength"},
    "Lunge": {"muscle_group": "Legs", "exercise_type": "Strength"},
    "Mountain Climber": {"muscle_group": "Core", "exercise_type": "Strength"},
}

FOCUS_MUSCLE_MAP: Dict[str, List[str]] = {
    "quad": ["Legs"],
    "quads": ["Legs"],
    "leg": ["Legs"],
    "legs": ["Legs"],
    "lower body": ["Legs"],
    "glute": ["Legs"],
    "glutes": ["Legs"],
    "hamstring": ["Legs"],
    "hamstrings": ["Legs"],
    "chest": ["Chest"],
    "pec": ["Chest"],
    "pecs": ["Chest"],
    "back": ["Back"],
    "lats": ["Back"],
    "shoulder": ["Back"],
    "shoulders": ["Back"],
    "core": ["Core"],
    "abs": ["Core"],
    "ab": ["Core"],
    "upper body": ["Chest", "Back"],
    "push": ["Chest"],
    "pull": ["Back"],
}


def _build_warmup_section(allowlist: List[str]) -> Dict[str, Any]:
    warmup_movements: List[str] = []
    if "Supported March" in allowlist:
        warmup_movements.append("2 mins Supported March")
    if "Chair Sit-to-Stand" in allowlist:
        warmup_movements.append("2 mins Chair Sit-to-Stand practice")
    if "Shadow Boxing" in allowlist:
        warmup_movements.append("3 mins Shadow Boxing")
    if "Bodyweight Squat" in allowlist:
        warmup_movements.append("2 mins Bodyweight Squats")
    if not warmup_movements:
        warmup_movements.append("5 mins dynamic joint mobility (shoulder rolls, knee pulls)")

    return {
        "title": "Warm-Up",
        "duration_minutes": 5,
        "instructions": warmup_movements,
    }


def _get_exercise_metadata_map() -> Dict[str, Dict[str, str]]:
    metadata_map = {
        exercise["name"]: {
            "muscle_group": exercise.get("muscle_group", ""),
            "exercise_type": exercise.get("exercise_type", ""),
        }
        for exercise in get_all_exercises()
    }
    metadata_map.update(FALLBACK_EXERCISE_METADATA)
    return metadata_map


def _resolve_focus_targets(session_goals: str | None) -> List[str]:
    goals = (session_goals or "").lower()
    targets: List[str] = []
    for keyword, muscle_groups in FOCUS_MUSCLE_MAP.items():
        if keyword in goals:
            for muscle_group in muscle_groups:
                if muscle_group not in targets:
                    targets.append(muscle_group)
    return targets


def _rank_strength_candidates(
    candidates: List[str],
    focus_targets: List[str],
    metadata_map: Dict[str, Dict[str, str]],
) -> List[str]:
    if not focus_targets:
        return candidates

    target_set = set(focus_targets)

    def rank_key(name: str) -> tuple[int, int, str]:
        metadata = metadata_map.get(name, {})
        muscle_group = metadata.get("muscle_group", "")
        primary_score = 0 if muscle_group in target_set else 1
        secondary_score = 0 if metadata.get("exercise_type") == "Strength" else 1
        return (primary_score, secondary_score, name)

    return sorted(candidates, key=rank_key)


def _matches_focus(name: str, focus_targets: List[str], metadata_map: Dict[str, Dict[str, str]]) -> bool:
    if not focus_targets:
        return False
    return metadata_map.get(name, {}).get("muscle_group", "") in set(focus_targets)


def _select_strength_exercises(rules: Dict[str, Any], state: GraphState) -> List[str]:
    allowlist = rules.get("movement_allowlist", [])
    max_exercises = rules.get("max_strength_exercises", 0)
    focus_targets = _resolve_focus_targets(state.session_context.session_goals)
    metadata_map = _get_exercise_metadata_map()

    strength_pool = [
        name for name in allowlist
        if metadata_map.get(name, {}).get("exercise_type") == "Strength"
    ]
    ranked_strength_pool = _rank_strength_candidates(strength_pool, focus_targets, metadata_map)
    blocked_movements = set(rules.get("blocked_movements", []))
    blocked_keywords = set(rules.get("blocked_keywords", []))

    fallback_pool = [
        name for name in [
            "Chair Sit-to-Stand",
            "Supported March",
            "Standing Heel Raise",
            "Wall Push-up",
            "Bodyweight Squat",
            "Push-up",
            "Glute Bridge",
            "Plank",
            "Lunge",
            "Mountain Climber",
        ]
        if name in allowlist
    ]
    ranked_fallback_pool = _rank_strength_candidates(fallback_pool, focus_targets, metadata_map)

    selected: List[str] = []

    def try_append(candidate: str) -> None:
        if len(selected) >= max_exercises:
            return
        lowered = candidate.lower()
        if candidate in selected or candidate in blocked_movements:
            return
        if any(keyword in lowered for keyword in blocked_keywords):
            return
        selected.append(candidate)

    if focus_targets:
        for candidate in ranked_strength_pool:
            if _matches_focus(candidate, focus_targets, metadata_map):
                try_append(candidate)
        for candidate in ranked_fallback_pool:
            if _matches_focus(candidate, focus_targets, metadata_map):
                try_append(candidate)

    for candidate in ranked_strength_pool:
        try_append(candidate)
    for candidate in ranked_fallback_pool:
        try_append(candidate)

    return selected[:max_exercises]


def _exercise_details(name: str, experience: str, rules: Dict[str, Any]) -> Dict[str, Any]:
    max_load = rules.get("max_load_kg", 5.0)
    max_squat_load = rules.get("max_squat_load_kg", 20.0)

    if experience == "Advanced":
        sets, reps = 4, "8-10 reps"
    elif experience == "Intermediate":
        sets, reps = 3, "10-12 reps"
    else:
        sets, reps = 3, "12 reps"

    details = {
        "name": name,
        "sets": sets,
        "reps": reps,
        "load": "Bodyweight",
        "notes": "Focus on strict form and control.",
    }

    if "Bench Press" in name or "Incline" in name:
        details["bench_angle"] = "180 deg (Flat)" if "Bench" in name else "135 deg (Incline)"
        details["load"] = f"{min(max_load, 15.0)} kg dumbbell pair"
        details["notes"] = "Maintain flat shoulder blades pinned to the bench."
    elif "Squat" in name and "Bodyweight" not in name:
        actual_load = min(max_squat_load, 20.0)
        if actual_load > 10.0:
            details["load"] = "10 kg dumbbell pair + Band resistance"
            details["notes"] = f"Combined load approximately {actual_load} kg. Clean dumbbells to chest safely."
        else:
            details["load"] = f"{actual_load} kg single dumbbell"
            details["notes"] = "Hold dumbbell vertically in goblet position at chest level."
    elif "Band" in name:
        details["load"] = "Medium Resistance Band"
        details["notes"] = "Focus on retraction of the shoulder blades."
    elif name == "Chair Sit-to-Stand":
        details["load"] = "Bodyweight + Chair support"
        details["notes"] = "Use the chair for support and move through a pain-free range only."
    elif name == "Supported March":
        details["load"] = "Bodyweight + Light support"
        details["notes"] = "Hold a stable surface and keep the march slow, tall, and controlled."
    elif name == "Standing Heel Raise":
        details["load"] = "Bodyweight + Light support"
        details["notes"] = "Use a wall or chair for balance and keep the movement smooth."
    elif name == "Wall Push-up":
        details["load"] = "Bodyweight (wall-assisted)"
        details["notes"] = "Stand closer to the wall to make the movement easier and keep tension low."
    elif "Row" in name:
        details["load"] = f"{min(max_load, 15.0)} kg dumbbell" if "Dumbbell" in name else "Medium Resistance Band"
        details["notes"] = "Drive the elbow back and keep the torso stable through every rep."
    elif "Romanian Deadlift" in name:
        details["load"] = f"{min(max_load, 10.0)} kg dumbbell pair"
        details["notes"] = "Hinge from the hips and keep the dumbbells close to the legs."
    elif "Step-Up" in name:
        details["load"] = "Bodyweight"
        details["notes"] = "Use a stable bench height and drive through the full foot on the working leg."
    elif "Pull-up" in name:
        details["load"] = "Bodyweight"
        details["notes"] = "Control the eccentric lowering phase."

    return details


def build_deterministic_plan(state: GraphState) -> Dict[str, Any]:
    rules = state.session_context.override.get("compiled_planning_rules", {})
    allowlist = rules.get("movement_allowlist", [])
    nickname = state.user_profile.nickname if state.user_profile else "Athlete"
    experience = state.user_profile.experience_level if state.user_profile else "Beginner"

    warm_up = _build_warmup_section(allowlist)
    selected_exercises = _select_strength_exercises(rules, state)
    strength_duration = rules.get("strength_duration_minutes", len(selected_exercises) * 10)

    strength_section = {
        "title": "Strength Circuit",
        "duration_minutes": strength_duration,
        "exercises": [
            _exercise_details(name, experience, rules)
            for name in selected_exercises
        ],
    }

    cardio_cfg = rules.get("post_strength_cardio", {})
    cardio_section = None
    if cardio_cfg.get("active", False):
        target_bpm = cardio_cfg.get("target_heart_rate_bpm", 130)
        cardio_section = {
            "title": f"Post-Strength conditioning finisher: {cardio_cfg.get('type', 'Aerobic Base Conditioning')}",
            "duration_minutes": cardio_cfg.get("duration_minutes", 60),
            "target_heart_rate_bpm": target_bpm,
            "instructions": (
                f"{cardio_cfg.get('instructions', '')} "
                f"Maintain target heart rate within {target_bpm - 5} - {target_bpm + 5} BPM."
            ).strip(),
        }

    total_duration = warm_up["duration_minutes"] + strength_section["duration_minutes"]
    if cardio_section:
        total_duration += cardio_section["duration_minutes"]

    result: Dict[str, Any] = {
        "athlete_nickname": nickname,
        "experience_level": experience,
        "estimated_duration_minutes": total_duration,
        "warm_up": warm_up,
        "strength_circuit": strength_section,
    }
    if cardio_section:
        result["cardio_finisher"] = cardio_section
    return result


def sanitize_generated_plan(plan_data: Dict[str, Any], state: GraphState) -> Dict[str, Any]:
    rules = state.session_context.override.get("compiled_planning_rules", {})
    allowlist = set(rules.get("movement_allowlist", []))
    expected_names = _select_strength_exercises(rules, state)
    expected_count = rules.get("max_strength_exercises", 0)
    experience = state.user_profile.experience_level if state.user_profile else "Beginner"

    warm_up = _build_warmup_section(rules.get("movement_allowlist", []))
    strength_exercises = plan_data.get("strength_circuit", {}).get("exercises", [])

    normalized_names: List[str] = []
    for exercise in strength_exercises:
        candidate = exercise.get("name")
        if candidate in allowlist and candidate not in normalized_names and candidate not in ("Shadow Boxing", "Burpees"):
            normalized_names.append(candidate)

    for name in expected_names:
        if len(normalized_names) >= expected_count:
            break
        if name not in normalized_names:
            normalized_names.append(name)

    normalized_names = normalized_names[:expected_count]
    sanitized_exercises = [_exercise_details(name, experience, rules) for name in normalized_names]

    strength_duration = rules.get("strength_duration_minutes", expected_count * 10)
    cardio_cfg = rules.get("post_strength_cardio", {})

    sanitized: Dict[str, Any] = {
        "athlete_nickname": state.user_profile.nickname if state.user_profile else "Athlete",
        "experience_level": experience,
        "warm_up": warm_up,
        "strength_circuit": {
            "title": "Strength Circuit",
            "duration_minutes": strength_duration,
            "exercises": sanitized_exercises,
        },
    }

    total_duration = warm_up["duration_minutes"] + strength_duration
    if cardio_cfg.get("active", False):
        target_bpm = cardio_cfg.get("target_heart_rate_bpm", 130)
        cardio_duration = cardio_cfg.get("duration_minutes", 60)
        sanitized["cardio_finisher"] = {
            "title": f"Post-Strength conditioning finisher: {cardio_cfg.get('type', 'Aerobic Base Conditioning')}",
            "duration_minutes": cardio_duration,
            "target_heart_rate_bpm": target_bpm,
            "instructions": (
                f"{cardio_cfg.get('instructions', '')} "
                f"Maintain target heart rate within {target_bpm - 5} - {target_bpm + 5} BPM."
            ).strip(),
        }
        total_duration += cardio_duration

    sanitized["estimated_duration_minutes"] = total_duration
    return sanitized


def generate_workout_plan(state: GraphState) -> Dict[str, Any]:
    """
    Compiles a structured workout plan based on the compiled constraints
    resolved by the PlanningNode in the GraphState.
    """
    rules = state.session_context.override.get("compiled_planning_rules", {})
    if not rules:
        return {"error": "Planning node constraints not compiled yet."}

    deterministic_plan = build_deterministic_plan(state)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return deterministic_plan

    try:
        from google import genai

        client = genai.Client()
        n_exercises = rules.get("max_strength_exercises", 0)
        strength_dur = rules.get("strength_duration_minutes", n_exercises * 10)
        cardio_cfg = rules.get("post_strength_cardio", {})
        cardio_active = cardio_cfg.get("active", False)
        cardio_dur_rule = cardio_cfg.get("duration_minutes", 0) if cardio_active else 0
        total_target = 5 + strength_dur + cardio_dur_rule

        system_instruction = (
            "You are a professional, motivating personal trainer. "
            "Generate a personalized workout plan in strict JSON format. "
            "Use only exercises from the provided movement_allowlist. "
            "Never violate bench angle, squat load, cardio timing, or blocked movement rules.\n"
            f"Warm-up must be exactly 5 minutes. Strength must contain exactly {n_exercises} exercises "
            f"for exactly {strength_dur} total minutes. Cardio finisher must be "
            f"{cardio_dur_rule} minutes if active. Total estimated duration must be {total_target}."
        )

        user_content = (
            f"Athlete Profile:\n"
            f"- Nickname: {state.user_profile.nickname if state.user_profile else 'Athlete'}\n"
            f"- Experience: {state.user_profile.experience_level if state.user_profile else 'Beginner'}\n"
            f"- Objectives: {state.user_profile.objectives if state.user_profile else []}\n"
            f"- Session Goals: {state.session_context.session_goals}\n"
            f"- Available Time: {rules.get('max_duration_minutes', '?')} minutes\n\n"
            f"Compiled Planning Constraints:\n{json.dumps(rules, indent=2)}"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_content,
            config={
                "system_instruction": system_instruction,
                "response_mime_type": "application/json",
            },
        )
        llm_plan = json.loads(response.text.strip())
        return sanitize_generated_plan(llm_plan, state)
    except Exception as llm_err:
        print(f"[LLM Generator Warning] Failed to generate LLM workout: {llm_err}. Falling back to deterministic...")
        return deterministic_plan
