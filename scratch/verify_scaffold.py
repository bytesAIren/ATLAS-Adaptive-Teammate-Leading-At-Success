import sys
import os

# Add root directory to python path to allow imports from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.state import get_default_safe_state, patch_state, StateConflictError
from src.graph.safety_node import run_safety_node
from src.graph.validator_node import run_validator_node
from src.graph.planning_node import run_planning_node
from src.schemas.state import GraphState

def run_tests():
    print("==================================================")
    print("RUNNING ADK 2.0 GRAPH ARCHITECTURE VERIFICATION")
    print("==================================================")
    
    # 1. Test DefaultSafeState and Sandbox Lock
    print("\n[TEST 1] Initializing Default Safe State & Safety Sandbox Lock...")
    initial_state = GraphState() # Not onboarded
    print(f"Initial onboard status: {initial_state.is_onboarded}")
    
    sandboxed_state = run_safety_node(initial_state)
    print(f"After Safety Node (not onboarded) - Onboard status: {sandboxed_state.is_onboarded}")
    print(f"Sandboxed Level: {sandboxed_state.user_profile.experience_level}")
    print(f"Sandboxed Max Load: {sandboxed_state.session_context.override.get('max_load_capacity')}")
    
    # Assert sandboxed conditions
    assert sandboxed_state.user_profile.experience_level == "Beginner"
    assert sandboxed_state.session_context.override.get("max_load_capacity") == "5 kg"
    print("-> Test 1 PASSED: Sandbox successfully locks unonboarded state.")

    # 2. Test Onboarding Gating - ValidationError Handling
    print("\n[TEST 2] Testing Validator Node with Invalid Payload (Conversational Fallback)...")
    invalid_payload = {
        "nickname": "Gym_Master!", # Contains special characters
        "age": 95,                  # Too old
        "weight_kg": 35.0,          # Too light
        "height_cm": 250.0,         # Too tall
        "experience_level": "Pro",  # Invalid choice
        "training_preference": "Strength",
        "frequency": "daily"        # Invalid choice
    }
    
    unmodified_state, error_response = run_validator_node(sandboxed_state, invalid_payload)
    print(f"Validation Success status: {error_response['success']}")
    print(f"Fallback Natural Language Prompt:\n\"\"\"\n{error_response['message']}\n\"\"\"")
    
    # Assert state remains unchanged and error response contains fallback message
    assert error_response["success"] is False
    assert error_response["error_type"] == "ValidationError"
    assert unmodified_state.is_onboarded is False
    print("-> Test 2 PASSED: Validation errors successfully caught and mapped to natural language.")

    # 3. Test Onboarding Gating - Valid Payload
    print("\n[TEST 3] Testing Validator Node with Valid Payload...")
    valid_payload = {
        "nickname": "GymHero",
        "age": 28,
        "weight_kg": 78.5,
        "height_cm": 180.0,
        "experience_level": "Intermediate",
        "training_preference": "Strength",
        "frequency": "3-5 times/week"
    }
    
    onboarded_state, success_response = run_validator_node(sandboxed_state, valid_payload)
    print(f"Validation Success status: {success_response['success']}")
    print(f"Validator message: {success_response['message']}")
    print(f"Updated UserProfile Nickname: {onboarded_state.user_profile.nickname}")
    print(f"Onboard status: {onboarded_state.is_onboarded}")
    
    # Assert state updated and sandbox unlocked
    assert success_response["success"] is True
    assert onboarded_state.is_onboarded is True
    assert onboarded_state.user_profile.nickname == "GymHero"
    
    unlocked_state = run_safety_node(onboarded_state)
    print(f"After Safety Node (onboarded) - Onboard status: {unlocked_state.is_onboarded}")
    print(f"Unlocked Level: {unlocked_state.user_profile.experience_level}")
    assert unlocked_state.user_profile.experience_level == "Intermediate"
    print("-> Test 3 PASSED: Valid payload successfully unlocks sandbox and updates state.")

    # 4. Test State Patching (PATCH semantics) and Conflict Resolution
    print("\n[TEST 4] Testing Partial State Patching & Conflict Protection...")
    # Attempt a partial patch: update energy and time available in session context
    session_patch = {
        "session_context": {
            "current_energy": 8,
            "time_available": 60,
            "override": {
                "max_load_kg": 8.0 # Temporary session limit (downscoping)
            }
        }
    }
    
    patched_state = patch_state(unlocked_state, session_patch)
    print(f"Patched session context - Energy: {patched_state.session_context.current_energy}")
    print(f"Patched session context - Time available: {patched_state.session_context.time_available}")
    print(f"Patched session context - Override max_load_kg: {patched_state.session_context.override.get('max_load_kg')}")
    
    assert patched_state.session_context.current_energy == 8
    assert patched_state.session_context.time_available == 60
    assert patched_state.session_context.override.get("max_load_kg") == 8.0
    
    # Attempting full replacement (e.g. passing a non-dict to user_profile)
    print("Testing upsert protection (full replacement block)...")
    try:
        patch_state(patched_state, {"user_profile": "invalid_string_instead_of_dict"})
        print("FAIL: Full replacement was not blocked!")
        assert False
    except StateConflictError as e:
        print(f"SUCCESS: Blocked full replacement with StateConflictError: {e}")
        
    print("-> Test 4 PASSED: State patching operates under strict PATCH and conflict semantics.")

    # 5. Test Planning Node - Downscoping and Equipment Locks
    print("\n[TEST 5] Testing Planning Node Downscoping & Hard Equipment Locks...")
    # Setup state with a user profile (Intermediate: baseline max load 10.0kg)
    # and a session override of max load 8.0kg
    planned_state = run_planning_node(patched_state)
    rules = planned_state.session_context.override.get("compiled_planning_rules", {})
    
    print(f"Baseline Experience Level: {planned_state.user_profile.experience_level}")
    print(f"Downscoped Session Max Load: {rules.get('max_load_kg')} kg (Expected: 8.0 kg)")
    print(f"Adjustable Bench Lock Incline range: {rules.get('bench_angles_range_degrees')}")
    print(f"Dumbbell Inventory Pairs: {rules.get('available_dumbbell_pairs_kg')} kg")
    print(f"Max Squat Load Cap: {rules.get('max_squat_load_kg')} kg (Expected: 8.0 kg)")
    print(f"Mandatory Post-Strength Cardio: {rules.get('post_strength_cardio')}")
    
    # Assert planning rules are correctly compiled and downscoped
    assert rules.get("max_load_kg") == 8.0
    assert rules.get("max_squat_load_kg") == 8.0 # Cap is 8.0 since 8.0 < 20.0
    assert rules.get("bench_angles_range_degrees")["decline_allowed"] is False
    assert rules.get("post_strength_cardio")["duration_minutes"] == 60
    assert rules.get("post_strength_cardio")["target_heart_rate_bpm"] == 130
    
    print("-> Test 5 PASSED: Planning Node successfully compiles downscoped limits and enforces equipment locks.")

    print("\n==================================================")
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
