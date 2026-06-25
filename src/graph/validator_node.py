import os
from pydantic import ValidationError
from typing import Dict, Any, Tuple
from src.schemas.onboarding import OnboardingPayload
from src.schemas.state import GraphState, UserProfile
from src.graph.state import patch_state

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
        validated_payload = OnboardingPayload(**input_payload)
        
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
                
                user_content = f"User inputs: {input_payload}\nValidation errors: {raw_errors}"
                
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

