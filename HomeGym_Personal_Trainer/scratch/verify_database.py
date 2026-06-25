import sys
import os

# Add root directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.db import init_db, get_all_equipment, get_all_exercises
from src.graph.state import get_default_safe_state
from src.graph.validator_node import run_validator_node
from src.graph.planning_node import run_planning_node
from src.schemas.state import GraphState

def run_db_tests():
    print("==================================================")
    print("RUNNING ADK 2.0 GRAPH + SQLITE DB CROSS-REFERENCE TESTS")
    print("==================================================")
    
    # 1. Initialize and Seed DB
    print("\n[TEST 1] Initializing & Seeding SQLite Database...")
    init_db()
    
    equipment = get_all_equipment()
    exercises = get_all_exercises()
    print(f"Total Equipment Types Seeded: {len(equipment)}")
    print(f"Total Exercises Seeded: {len(exercises)}")
    
    assert len(equipment) == 5
    assert len(exercises) == 8
    print("-> Test 1 PASSED: Database seeded successfully.")

    # 2. Case A: Advanced User with limited equipment (Yoga Mat & Pull-up Bar)
    print("\n[TEST 2] Testing Case A: Advanced User with Yoga Mat + Pull-up Bar...")
    payload_a = {
        "nickname": "ProAthlete",
        "age": 30,
        "weight_kg": 80.0,
        "height_cm": 185.0,
        "experience_level": "Advanced",
        "training_preference": "Strength",
        "frequency": ">5 times/week",
        "equipment_list": ["yoga_mat", "pullup_bar"] # No dumbbells, no bench, no bands
    }
    
    state = get_default_safe_state()
    state, response = run_validator_node(state, payload_a)
    assert response["success"] is True
    
    planned_state = run_planning_node(state)
    rules = planned_state.session_context.override.get("compiled_planning_rules", {})
    allowlist = rules.get("movement_allowlist", [])
    
    print(f"User Level: {state.user_profile.experience_level}")
    print(f"User Equipment: {state.user_profile.equipment_list}")
    print(f"Resolved Movement Allowlist: {allowlist}")
    
    # Check expected movements
    assert "Pull-up" in allowlist          # Requires pullup_bar & Advanced (OK)
    assert "Bodyweight Squat" in allowlist  # Requires yoga_mat & Beginner (OK)
    assert "Shadow Boxing" in allowlist     # Requires [] & Beginner (OK)
    
    # Check blocked movements due to missing equipment
    assert "Dumbbell Bench Press" not in allowlist # Needs dumbbells + bench
    assert "Goblet Squat" not in allowlist          # Needs dumbbells
    assert "Band Pull-Apart" not in allowlist       # Needs bands
    
    print("-> Test 2 PASSED: Exercises successfully filtered by user inventory.")

    # 3. Case B: Beginner User with dumbbells and bench (but no pull-up bar or bands)
    print("\n[TEST 3] Testing Case B: Beginner User with Dumbbells + Bench + Yoga Mat...")
    payload_b = {
        "nickname": "StarterUser",
        "age": 22,
        "weight_kg": 70.0,
        "height_cm": 175.0,
        "experience_level": "Beginner",
        "training_preference": "Hybrid",
        "frequency": "1-2 times/week",
        "equipment_list": ["yoga_mat", "dumbbells", "adjustable_bench"] # No pullup_bar, no bands
    }
    
    state_b = get_default_safe_state()
    state_b, response_b = run_validator_node(state_b, payload_b)
    assert response_b["success"] is True
    
    planned_state_b = run_planning_node(state_b)
    rules_b = planned_state_b.session_context.override.get("compiled_planning_rules", {})
    allowlist_b = rules_b.get("movement_allowlist", [])
    
    print(f"User Level: {state_b.user_profile.experience_level}")
    print(f"User Equipment: {state_b.user_profile.equipment_list}")
    print(f"Resolved Movement Allowlist: {allowlist_b}")
    
    # Check expected movements
    assert "Dumbbell Bench Press" in allowlist_b # Requires bench + dumbbells & Beginner (OK)
    assert "Goblet Squat" in allowlist_b        # Requires dumbbells & Beginner (OK)
    assert "Bodyweight Squat" in allowlist_b    # Requires yoga_mat & Beginner (OK)
    
    # Check blocked movements due to experience level thresholds
    assert "Incline Dumbbell Press" not in allowlist_b # Needs Intermediate experience level
    assert "Burpees" not in allowlist_b                # Needs Intermediate experience level
    assert "Pull-up" not in allowlist_b                # Needs Advanced experience level
    
    # Check blocked movements due to missing equipment
    assert "Band Pull-Apart" not in allowlist_b        # Needs resistance_bands
    
    print("-> Test 3 PASSED: Exercises successfully filtered by user experience thresholds.")

    print("\n==================================================")
    print("ALL DATABASE INTEGRATION TESTS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    run_db_tests()
