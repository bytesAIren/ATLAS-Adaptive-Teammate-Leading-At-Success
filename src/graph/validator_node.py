import os
from pydantic import ValidationError
from typing import Dict, Any, Tuple, List
from src.schemas.onboarding import OnboardingPayload
from src.schemas.state import GraphState, UserProfile
from src.graph.state import patch_state


EQUIPMENT_ALIAS_MAP = {
    "bench": "adjustable_bench",
    "adjustable bench": "adjustable_bench",
    "dumbbell": "dumbbells",
    "dumbbells": "dumbbells",
    "weights": "dumbbells",
    "resistance band": "resistance_bands",
    "resistance bands": "resistance_bands",
    "bands": "resistance_bands",
    "pull up bar": "pullup_bar",
    "pull-up bar": "pullup_bar",
    "chin up bar": "pullup_bar",
    "chin-up bar": "pullup_bar",
    "bike": "stationary_bike",
    "exercise bike": "stationary_bike",
    "stationary bike": "stationary_bike",
    "cyclette": "stationary_bike",
    "spin bike": "stationary_bike",
    "treadmill": "treadmill",
    "walking pad": "treadmill",
    "kettlebell": "kettlebell",
    "kettlebells": "kettlebell",
    "jump rope": "jump_rope",
    "skipping rope": "jump_rope",
}

OBJECTIVE_ALIAS_MAP = {
    "run 5k": "run a 5k",
    "5k": "run a 5k",
    "run a 5k": "run a 5k",
    "run 10k": "run a 10k",
    "10k": "run a 10k",
    "run a 10k": "run a 10k",
    "60 minute ride": "60 minute ride",
    "60 min ride": "60 minute ride",
    "60-minute ride": "60 minute ride",
    "ride 60 minutes": "60 minute ride",
    "healthy life": "healthy life",
    "healthy lifestyle": "healthy life",
    "lose weight": "lose weight",
    "weight loss": "lose weight",
    "fat loss": "lose weight",
    "burn fat": "lose weight",
    "gain muscle": "gain muscle",
    "build muscle": "gain muscle",
    "hypertrophy": "gain muscle",
    "10k steps": "10k steps a day",
    "10k steps a day": "10k steps a day",
}


def _split_free_text_list(raw_value: Any) -> List[str]:
    if not raw_value or not isinstance(raw_value, str):
        return []
    normalized = raw_value.replace(";", ",").replace("\n", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


def _dedupe_preserve_order(values: List[str]) -> List[str]:
    unique_values: List[str] = []
    seen = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            unique_values.append(value)
    return unique_values


def _normalize_equipment_entries(values: List[str]) -> List[str]:
    normalized: List[str] = []
    for value in values:
        key = value.strip().lower()
        if not key:
            continue
        normalized.append(EQUIPMENT_ALIAS_MAP.get(key, key.replace(" ", "_")))
    return _dedupe_preserve_order(normalized)


def _normalize_objective_entries(values: List[str]) -> List[str]:
    normalized: List[str] = []
    for value in values:
        key = value.strip().lower()
        if not key:
            continue
        normalized.append(OBJECTIVE_ALIAS_MAP.get(key, key))
    return _dedupe_preserve_order(normalized)


def _normalize_onboarding_payload(input_payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized_payload = dict(input_payload)
    preset_equipment = normalized_payload.get("equipment_list", []) or []
    preset_objectives = normalized_payload.get("objectives", []) or []
    custom_equipment = _split_free_text_list(normalized_payload.get("custom_equipment"))
    custom_objectives = _split_free_text_list(normalized_payload.get("custom_objectives"))

    normalized_payload["equipment_list"] = _normalize_equipment_entries(
        [str(item) for item in preset_equipment] + custom_equipment
    )
    normalized_payload["objectives"] = _normalize_objective_entries(
        [str(item) for item in preset_objectives] + custom_objectives
    )
    return normalized_payload

def format_validation_error_to_nl(error: ValidationError) -> str:
    """
    Translates raw Pydantic ValidationErrors into clear, supportive natural language.
    Specifically targets age, nickname, and categorical options range and regexes.
    """
    error_messages = []
    for err in error.errors():
        field = err["loc"][0]
        msg = err["msg"]
        
        if field == "nickname":
            error_messages.append("Nicknames must be alphanumeric (no spaces or symbols) and between 2 and 15 characters.")
        elif field == "age":
            error_messages.append("Age must be a number between 16 and 90.")
        elif field == "weight_kg":
            error_messages.append("Weight must be a number between 40.0 kg and 200.0 kg.")
        elif field == "height_cm":
            error_messages.append("Height must be a number between 130.0 cm and 220.0 cm.")
        elif field == "experience_level":
            error_messages.append("Experience level must be either 'Beginner', 'Intermediate', or 'Advanced'.")
        elif field == "training_preference":
            error_messages.append("Training preference must be either 'Strength', 'Cardio', or 'Hybrid'.")
        elif field == "frequency":
            error_messages.append("Training frequency must be either '1-2 times/week', '3-5 times/week', or '>5 times/week'.")
        else:
            error_messages.append(f"Invalid input on field '{field}': {msg}")
            
    nl_prompt = "It looks like some onboarding details need correction:\n"
    nl_prompt += "\n".join(f"- {msg}" for msg in error_messages)
    nl_prompt += "\nCould you please double-check and provide your info again?"
    return nl_prompt

def run_validator_node(state: GraphState, input_payload: Dict[str, Any]) -> Tuple[GraphState, Dict[str, Any]]:
    """
    Intermediate validation layer node as specified in Section 2 of AGENTS.md.
    
    Responsibilities:
    - Intercepts input payloads.
    - Validates them against the OnboardingPayload schema.
    - Gracefully catches ValidationError to prevent graph crashes.
    - Returns a tuple of (updated_state, response_payload).
      - If valid: updates UserProfile and sets is_onboarded=True.
      - If invalid: maintains previous state, sets fallback details, and provides NL prompt.
    """
    try:
        # Validate input payload using Pydantic onboarding model
        normalized_payload = _normalize_onboarding_payload(input_payload)
        validated_payload = OnboardingPayload(**normalized_payload)
        
        # Patch validated data into UserProfile
        profile_patch = {
            "user_profile": validated_payload.model_dump(),
            "is_onboarded": True
        }
        
        updated_state = patch_state(state, profile_patch)
        
        response = {
            "success": True,
            "message": f"Welcome, {validated_payload.nickname}! Your profile has been successfully set up."
        }
        return updated_state, response

    except ValidationError as e:
        # Prevent graph crash, capture error context, format natural language fallback prompt
        api_key = os.environ.get("GEMINI_API_KEY")
        nl_clarification = ""
        
        if api_key:
            try:
                from google import genai
                client = genai.Client()
                
                # Format raw error details to pass to LLM
                raw_errors = [f"Field: {err['loc'][0]}, Error: {err['msg']}" for err in e.errors()]
                
                system_instruction = (
                    "You are a supportive, friendly personal trainer. "
                    "Your client tried to onboarding, but their form inputs failed validation. "
                    "Analyze the user's inputs and the validation errors. "
                    "Write a friendly, polite, conversational response pointing out the errors "
                    "and asking them to correct them. Do not use bullet lists, write it "
                    "naturally as a human coach would text a client in a single short paragraph."
                )
                
                user_content = f"User inputs: {normalized_payload}\nValidation errors: {raw_errors}"
                
                response_text = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=user_content,
                    config={"system_instruction": system_instruction}
                ).text
                
                nl_clarification = response_text.strip()
            except Exception as llm_err:
                print(f"[LLM Validator Warning] Failed to generate LLM response: {llm_err}. Falling back...")
                nl_clarification = format_validation_error_to_nl(e)
        else:
            nl_clarification = format_validation_error_to_nl(e)
        
        # Maintain previous pre-validation state (no state mutation occurs)
        response = {
            "success": False,
            "error_type": "ValidationError",
            "message": nl_clarification,
            "raw_errors": e.errors()
        }
        
        return state, response
