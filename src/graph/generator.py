import os
import json
from src.schemas.state import GraphState
from typing import Dict, Any, List

def generate_workout_plan(state: GraphState) -> Dict[str, Any]:
    """
    Compiles a structured workout plan based on the compiled constraints 
    resolved by the PlanningNode in the GraphState.
    
    Returns a dictionary detailing:
    - user_nickname
    - target_duration
    - warm_up (5 mins)
    - strength_workout (list of exercise sets/reps/load details)
    - cardio_finisher (details if active)
    """
    rules = state.session_context.override.get("compiled_planning_rules", {})
    if not rules:
        return {"error": "Planning node constraints not compiled yet."}

    nickname = state.user_profile.nickname if state.user_profile else "Athlete"
    experience = state.user_profile.experience_level if state.user_profile else "Beginner"
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            from google import genai
            client = genai.Client()
            
            n_exercises = rules.get("max_strength_exercises", 3)
            strength_dur = rules.get("strength_duration_minutes", n_exercises * 10)
            cardio_cfg = rules.get("post_strength_cardio", {})
            cardio_active = cardio_cfg.get("active", False)
            cardio_dur_rule = cardio_cfg.get("duration_minutes", 0) if cardio_active else 0
            total_target = 5 + strength_dur + cardio_dur_rule

            system_instruction = (
                "You are a professional, motivating personal trainer. "
                "Generate a personalized workout plan in strict JSON format. "
                "CRITICAL TIMING RULES — you MUST follow these exactly:\n"
                f"  • Warm-up: exactly 5 minutes\n"
                f"  • Strength circuit: exactly {n_exercises} exercises, each ~10 minutes → total {strength_dur} minutes\n"
                f"  • Cardio finisher: {'active, exactly ' + str(cardio_dur_rule) + ' minutes' if cardio_active else 'NOT included (cardio_active is False)'}\n"
                f"  • Total estimated_duration_minutes MUST equal {total_target}\n"
                "MOVEMENT RULES: only use exercises from the movement_allowlist in the constraints. "
                "Respect all load caps, bench angles, and squat limits.\n"
                "Return ONLY a JSON object with this exact schema:\n"
                "{\n"
                "  \"athlete_nickname\": \"string\",\n"
                "  \"experience_level\": \"string\",\n"
                f"  \"estimated_duration_minutes\": {total_target},\n"
                "  \"warm_up\": { \"title\": \"Warm-Up\", \"duration_minutes\": 5, \"instructions\": [\"string\"] },\n"
                f"  \"strength_circuit\": {{ \"title\": \"Strength Circuit\", \"duration_minutes\": {strength_dur}, \"exercises\": [EXACTLY {n_exercises} exercise objects] }},\n"
                "  each exercise: { \"name\": str, \"sets\": int, \"reps\": str, \"load\": str, \"bench_angle\": str (optional), \"notes\": str }\n"
                + (f"  \"cardio_finisher\": {{ \"title\": str, \"duration_minutes\": {cardio_dur_rule}, \"target_heart_rate_bpm\": int, \"instructions\": str }}\n" if cardio_active else "")
                + "}"
            )

            user_content = (
                f"Athlete Profile:\n"
                f"- Nickname: {nickname}\n"
                f"- Experience: {experience}\n"
                f"- Objectives: {state.user_profile.objectives if state.user_profile else []}\n"
                f"- Session Goals: {state.session_context.session_goals}\n"
                f"- Available Time: {rules.get('max_duration_minutes', '?')} minutes\n\n"
                f"Compiled Planning Constraints (follow strictly):\n"
                f"{json.dumps(rules, indent=2)}"
            )

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_content,
                config={
                    "system_instruction": system_instruction,
                    "response_mime_type": "application/json"
                }
            )
            
            plan_data = json.loads(response.text.strip())

            # ── Post-generation enforcement layer ──────────────────────────────
            # Always override LLM timing values with the authoritative rule values.
            # The LLM picks exercises and coaching cues; WE control the numbers.
            enforced_strength_dur = rules.get("strength_duration_minutes", 0)
            enforced_cardio_dur   = cardio_cfg.get("duration_minutes", 0) if cardio_active else 0

            if "strength_circuit" in plan_data and plan_data["strength_circuit"]:
                plan_data["strength_circuit"]["duration_minutes"] = enforced_strength_dur

            if "cardio_finisher" in plan_data and plan_data["cardio_finisher"]:
                plan_data["cardio_finisher"]["duration_minutes"] = enforced_cardio_dur
            elif cardio_active and cardio_cfg:
                # LLM omitted cardio section — add it deterministically
                c_type = cardio_cfg.get("type", "Power Walk")
                c_hr   = cardio_cfg.get("target_heart_rate_bpm", 120)
                c_instr = cardio_cfg.get("instructions", "Maintain steady aerobic pace.")
                plan_data["cardio_finisher"] = {
                    "title": f"Post-Strength conditioning finisher: {c_type}",
                    "duration_minutes": enforced_cardio_dur,
                    "target_heart_rate_bpm": c_hr,
                    "instructions": f"{c_instr} Maintain target heart rate within {c_hr - 5}–{c_hr + 5} BPM."
                }

            # Recalculate total so it is always consistent
            warmup_dur_v = plan_data.get("warm_up", {}).get("duration_minutes", 5)
            s_dur_v = plan_data.get("strength_circuit", {}).get("duration_minutes", 0)
            c_dur_v = plan_data.get("cardio_finisher", {}).get("duration_minutes", 0)
            plan_data["estimated_duration_minutes"] = warmup_dur_v + s_dur_v + c_dur_v

            return plan_data

        except Exception as llm_err:
            print(f"[LLM Generator Warning] Failed to generate LLM workout: {llm_err}. Falling back to deterministic...")
            # Let code execution drop down to the deterministic generator block
            pass

    # 1. Warm-up (5 mins)

    warmup_movements = []
    allowlist = rules.get("movement_allowlist", [])
    
    if "Shadow Boxing" in allowlist:
        warmup_movements.append("3 mins Shadow Boxing")
    if "Bodyweight Squat" in allowlist:
        warmup_movements.append("2 mins Bodyweight Squats")
    else:
        warmup_movements.append("5 mins dynamic joint mobility (shoulder rolls, knee pulls)")
        
    warm_up_section = {
        "title": "Warm-Up",
        "duration_minutes": 5,
        "instructions": warmup_movements
    }

    # 2. Strength Section
    max_exercises = rules.get("max_strength_exercises", 3)
    # Use the authoritative strength_duration_minutes from planning rules
    strength_duration = rules.get("strength_duration_minutes", max_exercises * 10)
    max_load = rules.get("max_load_kg", 5.0)
    max_squat_load = rules.get("max_squat_load_kg", 20.0)

    # Select exercises from allowlist (exclude pure cardio/warmup movements)
    strength_pool = [ex for ex in allowlist if ex not in ("Shadow Boxing", "Burpees")]
    selected_exercises = strength_pool[:max_exercises]

    # Pad with defaults if pool is too small
    fallback_pool = ["Bodyweight Squat", "Push-up", "Glute Bridge", "Plank", "Lunge", "Mountain Climber"]
    i = 0
    while max_exercises > 0 and len(selected_exercises) < max_exercises and i < len(fallback_pool):
        if fallback_pool[i] not in selected_exercises:
            selected_exercises.append(fallback_pool[i])
        i += 1

    if max_exercises == 0:
        selected_exercises = []

    strength_movements = []

    # Establish reps & sets based on experience level
    if experience == "Advanced":
        sets, reps = 4, "8-10 reps"
    elif experience == "Intermediate":
        sets, reps = 3, "10-12 reps"
    else:
        sets, reps = 3, "12 reps"

    for ex_name in selected_exercises:
        ex_details = {
            "name": ex_name,
            "sets": sets,
            "reps": reps,
            "notes": ""
        }

        # Enforce specific equipment locks and notes
        if "Bench Press" in ex_name or "Incline" in ex_name:
            ex_details["bench_angle"] = "180° (Flat)" if "Bench" in ex_name else "135° (Incline)"
            ex_details["load"] = f"{min(max_load, 15.0)} kg dumbbell pair"
            ex_details["notes"] = "Maintain flat shoulder blades pinned to the bench."
        elif "Squat" in ex_name and "Bodyweight" not in ex_name:
            actual_load = min(max_squat_load, 20.0)
            if actual_load > 10.0:
                ex_details["load"] = "10 kg dumbbell pair + Band resistance"
                ex_details["notes"] = f"Combined load ~{actual_load} kg. Clean dumbbells to chest safely."
            else:
                ex_details["load"] = f"{actual_load} kg single dumbbell"
                ex_details["notes"] = "Hold dumbbell vertically in goblet position at chest level."
        elif "Band" in ex_name:
            ex_details["load"] = "Medium Resistance Band"
            ex_details["notes"] = "Focus on retraction of the shoulder blades."
        elif "Pull-up" in ex_name:
            ex_details["load"] = "Bodyweight"
            ex_details["notes"] = "Control the eccentric lowering phase."
        else:
            ex_details["load"] = "Bodyweight"
            ex_details["notes"] = "Focus on strict form and control."

        strength_movements.append(ex_details)

    strength_section = {
        "title": "Strength Circuit",
        "duration_minutes": strength_duration,
        "exercises": strength_movements
    }

    # 3. Cardio Finisher
    cardio_section = None
    cardio_cfg = rules.get("post_strength_cardio", {})
    
    if cardio_cfg.get("active", False):
        c_type = cardio_cfg.get("type", "Power Walk")
        c_dur = cardio_cfg.get("duration_minutes", 20)
        c_hr = cardio_cfg.get("target_heart_rate_bpm", 120)
        c_instr = cardio_cfg.get("instructions", "")
        
        cardio_section = {
            "title": f"Post-Strength conditioning finisher: {c_type}",
            "duration_minutes": c_dur,
            "target_heart_rate_bpm": c_hr,
            "instructions": f"{c_instr} Maintain target heart rate within {c_hr - 5} - {c_hr + 5} BPM."
        }
    else:
        c_dur = 0

    # Calculate estimated duration
    total_duration = 5 + strength_duration + c_dur

    res = {
        "athlete_nickname": nickname,
        "experience_level": experience,
        "estimated_duration_minutes": total_duration,
        "warm_up": warm_up_section
    }
    
    if max_exercises > 0 and strength_movements:
        res["strength_circuit"] = strength_section
    if cardio_section:
        res["cardio_finisher"] = cardio_section
        
    return res
