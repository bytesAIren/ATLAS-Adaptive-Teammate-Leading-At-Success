import sys
import os

# Add root directory to python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

# Explicitly load .env from the project root regardless of where the script is run from
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, ".env"))
except ImportError:
    pass

from src.database.db import init_db
from src.graph.state import get_default_safe_state
from src.graph.validator_node import run_validator_node
from src.graph.planning_node import run_planning_node
from src.graph.generator import generate_workout_plan

def test_llm_integration():
    print("==================================================")
    print("RUNNING ADK 2.0 GRAPH + GEMINI INTEGRATION TESTS")
    print("==================================================")
    
    # 1. Initialize and Seed DB
    init_db()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        print(f"Status: GEMINI_API_KEY is active (length: {len(api_key)})")
        print("Generative LLM nodes will be used.")
    else:
        print("Status: GEMINI_API_KEY is not set.")
        print("Fallback deterministic nodes will be used.")

    # 2. Test Validator Node Clarification Prompt
    print("\n[TEST 1] Testing Onboarding Clarification Prompt...")
    invalid_payload = {
        "nickname": "Gym_Star!", # Invalid
        "age": 105,              # Invalid
        "weight_kg": 35.0,        # Invalid
        "height_cm": 250.0,       # Invalid
        "experience_level": "Elite", # Invalid
        "training_preference": "Strength",
        "frequency": "daily",
        "equipment_list": [],
        "objectives": []
    }
    
    state = get_default_safe_state()
    _, response = run_validator_node(state, invalid_payload)
    print("Onboarding Clarification Response:")
    print(f"\"\"\"\n{response.get('message')}\n\"\"\"")

    # 3. Test Workout Generation
    print("\n[TEST 2] Testing Workout Plan Generation...")
    valid_payload = {
        "nickname": "Alex",
        "age": 32,
        "weight_kg": 85.0,
        "height_cm": 180.0,
        "experience_level": "Intermediate",
        "training_preference": "Strength",
        "frequency": "3-5 times/week",
        "equipment_list": ["yoga_mat", "dumbbells", "adjustable_bench"],
        "objectives": ["healthy life", "run a 5k"] # Cardio finisher active
    }
    
    state, onboard_res = run_validator_node(state, valid_payload)
    assert onboard_res["success"] is True
    
    planned_state = run_planning_node(state)
    workout = generate_workout_plan(planned_state)
    
    import json
    print("\nWorkout Plan Output:")
    print(json.dumps(workout, indent=2))

    print("\n==================================================")
    print("GEMINI INTEGRATION TESTS FINISHED!")
    print("==================================================")

if __name__ == "__main__":
    test_llm_integration()
