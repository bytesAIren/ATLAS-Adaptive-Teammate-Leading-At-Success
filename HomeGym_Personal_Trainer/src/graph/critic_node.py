from typing import Any, Dict, List

from src.graph.generator import build_deterministic_plan, sanitize_generated_plan
from src.schemas.state import GraphState


VALID_BENCH_ANGLES = {"180 deg (Flat)", "135 deg (Incline)"}
SAFE_FALLBACK_EXERCISES = {
    "Chair Sit-to-Stand",
    "Wall Push-up",
    "Supported March",
    "Standing Heel Raise",
    "Push-up",
    "Glute Bridge",
    "Plank",
    "Lunge",
    "Mountain Climber",
}


def _contains_blocked_keyword(name: str, blocked_keywords: List[str]) -> bool:
    lowered = name.lower()
    return any(keyword in lowered for keyword in blocked_keywords)


def review_workout_plan(plan: Dict[str, Any], state: GraphState) -> Dict[str, Any]:
    """
    Explicit critic/reviewer node.

    Reviews the composed workout against the compiled planning rules and either:
    - approves the plan as-is
    - normalizes it through the deterministic sanitizer
    - falls back to a fully deterministic rebuild if critical violations are found
    """
    rules = state.session_context.override.get("compiled_planning_rules", {})
    expected_count = rules.get("max_strength_exercises", 0)
    expected_strength_duration = rules.get("strength_duration_minutes", 0)
    cardio_cfg = rules.get("post_strength_cardio", {})
    allowlist = set(rules.get("movement_allowlist", []))
    critic_allowlist = allowlist.union(SAFE_FALLBACK_EXERCISES)
    blocked_movements = set(rules.get("blocked_movements", []))
    blocked_keywords = rules.get("blocked_keywords", [])

    findings: List[str] = []
    corrected = False
    fallback_used = False

    warm_up = plan.get("warm_up", {})
    if warm_up.get("duration_minutes") != 5:
        findings.append("Warm-up duration was corrected to the locked 5-minute protocol.")

    strength = plan.get("strength_circuit", {})
    exercises = strength.get("exercises", [])
    if len(exercises) != expected_count:
        findings.append(
            f"Strength circuit exercise count did not match the planning node output ({expected_count})."
        )

    for exercise in exercises:
        name = exercise.get("name", "")
        if name in blocked_movements or _contains_blocked_keyword(name, blocked_keywords):
            findings.append(f"Blocked exercise detected during review: {name}.")
        if name and critic_allowlist and name not in critic_allowlist:
            findings.append(f"Exercise outside allowlist detected during review: {name}.")

        if "bench_angle" in exercise and exercise["bench_angle"] not in VALID_BENCH_ANGLES:
            findings.append(f"Invalid bench angle detected during review: {exercise['bench_angle']}.")

    if strength.get("duration_minutes") != expected_strength_duration:
        findings.append("Strength duration did not match the authoritative planning rules.")

    if cardio_cfg.get("active", False):
        cardio_section = plan.get("cardio_finisher")
        if not cardio_section:
            findings.append("Required cardio finisher was missing from the composed plan.")
        elif cardio_section.get("duration_minutes") != cardio_cfg.get("duration_minutes", 60):
            findings.append("Cardio finisher duration did not match the planning rules.")
        elif cardio_section.get("target_heart_rate_bpm") != cardio_cfg.get("target_heart_rate_bpm", 130):
            findings.append("Cardio finisher heart-rate target did not match the planning rules.")
    elif "cardio_finisher" in plan:
        findings.append("Unexpected cardio finisher detected for a non-cardio session.")

    if findings:
        corrected = True
        normalized_plan = sanitize_generated_plan(plan, state)
        normalized_findings: List[str] = []

        normalized_strength = normalized_plan.get("strength_circuit", {})
        normalized_exercises = normalized_strength.get("exercises", [])
        if len(normalized_exercises) != expected_count:
            normalized_findings.append("Normalized plan still had an unexpected exercise count.")
        for exercise in normalized_exercises:
            name = exercise.get("name", "")
            if name in blocked_movements or _contains_blocked_keyword(name, blocked_keywords):
                normalized_findings.append(f"Normalized plan still contains blocked exercise: {name}.")
            if name and critic_allowlist and name not in critic_allowlist:
                normalized_findings.append(f"Normalized plan still contains non-allowlisted exercise: {name}.")
            if "bench_angle" in exercise and exercise["bench_angle"] not in VALID_BENCH_ANGLES:
                normalized_findings.append("Normalized plan still contains an invalid bench angle.")

        normalized_cardio = normalized_plan.get("cardio_finisher")
        if cardio_cfg.get("active", False):
            if not normalized_cardio:
                normalized_findings.append("Normalized plan is still missing the required cardio finisher.")
            elif normalized_cardio.get("target_heart_rate_bpm") != cardio_cfg.get("target_heart_rate_bpm", 130):
                normalized_findings.append("Normalized plan still contains the wrong cardio heart-rate target.")

        if normalized_findings:
            fallback_used = True
            plan = build_deterministic_plan(state)
            findings.extend(normalized_findings)
            findings.append("Critic node replaced the plan with the deterministic fallback.")
        else:
            plan = normalized_plan
            findings.append("Critic node normalized the plan to match the hard constraints.")

    return {
        "plan": plan,
        "critic_report": {
            "reviewed": True,
            "approved": not findings,
            "corrected": corrected,
            "fallback_used": fallback_used,
            "findings": findings,
        },
    }
