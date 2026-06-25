import sys
import os
import time
import subprocess
import json
import urllib.request
import urllib.error

# Add root directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

API_URL = "http://127.0.0.1:8000"

def query_endpoint(endpoint: str, data: dict = None, method: str = "GET") -> tuple:
    url = f"{API_URL}{endpoint}"
    req_data = None
    headers = {"Content-Type": "application/json"}
    
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"URLError: {e.reason}")
        return 0, {}

def run_api_tests():
    print("==================================================")
    print("RUNNING FASTAPI SERVER VERIFICATION SUITE")
    print("==================================================")
    
    # 1. Start uvicorn server as a background process
    print("\nStarting FastAPI server in background...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to boot up
    time.sleep(3)
    
    try:
        # 2. Test GET /api/equipment
        print("\n[TEST 1] Querying /api/equipment...")
        status, body = query_endpoint("/api/equipment")
        print(f"Status: {status}, Total equipment types: {len(body)}")
        assert status == 200
        assert len(body) == 5
        print("-> Test 1 PASSED.")
        
        # 3. Test GET /api/state (initial unonboarded)
        print("\n[TEST 2] Querying /api/state...")
        status, body = query_endpoint("/api/state")
        print(f"Status: {status}, Is Onboarded: {body['is_onboarded']}")
        assert status == 200
        assert body["is_onboarded"] is False
        print("-> Test 2 PASSED.")
        
        # 4. Test POST /api/onboard (invalid)
        print("\n[TEST 3] Querying /api/onboard with invalid data (gating check)...")
        invalid_payload = {
            "nickname": "ProAthlete!",
            "age": 99,
            "weight_kg": 30.0,
            "height_cm": 250.0,
            "experience_level": "Pro",
            "training_preference": "Strength",
            "frequency": "daily",
            "equipment_list": [],
            "objectives": []
        }
        status, body = query_endpoint("/api/onboard", data=invalid_payload, method="POST")
        print(f"Status: {status}, Success response: {body.get('success')}")
        print(f"Validation message:\n{body.get('message')}")
        assert body.get("success") is False
        print("-> Test 3 PASSED.")
        
        # 5. Test POST /api/onboard (valid - Cardio Objective)
        print("\n[TEST 4] Querying /api/onboard with valid data...")
        valid_payload = {
            "nickname": "GymStar",
            "age": 25,
            "weight_kg": 75.0,
            "height_cm": 178.0,
            "experience_level": "Intermediate",
            "training_preference": "Strength",
            "frequency": "3-5 times/week",
            "equipment_list": ["yoga_mat", "dumbbells", "adjustable_bench"],
            "objectives": ["60 minute ride", "healthy life"] # Contains cardio objectives
        }
        status, body = query_endpoint("/api/onboard", data=valid_payload, method="POST")
        print(f"Status: {status}, Success response: {body.get('success')}")
        print(f"Validator message: {body.get('message')}")
        assert body.get("success") is True
        print("-> Test 4 PASSED.")
        
        # 6. Test POST /api/session (90 min limit + Cardio finisher check)
        print("\n[TEST 5] Requesting workout session (90 mins time limit, cardio finisher)...")
        session_payload = {
            "current_energy": 8,
            "local_injuries": [],
            "time_available": 90,
            "session_goals": "Focus on chest and legs strength"
        }
        status, body = query_endpoint("/api/session", data=session_payload, method="POST")
        print(f"Status: {status}, Success: {body.get('success')}")
        
        plan = body.get("workout_plan", {})
        print(f"Warmup: {plan.get('warm_up')}")
        print(f"Strength circuit exercise count: {len(plan.get('strength_circuit', {}).get('exercises', []))}")
        print(f"Selected Exercises: {[ex.get('name') for ex in plan.get('strength_circuit', {}).get('exercises', [])]}")
        print(f"Cardio Finisher Active: {plan.get('cardio_finisher') is not None}")
        
        # Assertions:
        # Cardio Finisher should be active (objectives contained "60 minute ride")
        assert plan.get("cardio_finisher") is not None
        # Strength count = (90 available - 60 cardio) // 10 = 3 exercises
        assert len(plan.get("strength_circuit", {}).get("exercises", [])) == 3
        print("-> Test 5 PASSED: Cardio finisher triggered and strength exercises scaled correctly.")
        
        # 7. Test POST /api/session (30 min limit + Cardio finisher check)
        print("\n[TEST 6] Requesting workout session (30 mins time limit)...")
        session_payload_short = {
            "current_energy": 6,
            "local_injuries": [],
            "time_available": 30,
            "session_goals": "Quick session"
        }
        status, body = query_endpoint("/api/session", data=session_payload_short, method="POST")
        plan_short = body.get("workout_plan", {})
        
        print(f"Strength circuit exercise count: {len(plan_short.get('strength_circuit', {}).get('exercises', []))}")
        print(f"Selected Exercises: {[ex.get('name') for ex in plan_short.get('strength_circuit', {}).get('exercises', [])]}")
        print(f"Cardio Finisher Active: {plan_short.get('cardio_finisher') is not None}")
        
        # Assertions:
        # For 30 mins total time, since cardio takes 60 mins, cardio is active, but remaining strength time is -30 mins.
        # Max strength exercises resolves to the minimum default: 2.
        assert len(plan_short.get("strength_circuit", {}).get("exercises", [])) == 2
        print("-> Test 6 PASSED: Short session correctly scales to minimum strength limits.")

        # 8. Test POST /api/reset
        print("\n[TEST 7] Testing session reset...")
        status, body = query_endpoint("/api/reset", method="POST")
        print(f"Status: {status}, Reset is_onboarded status: {body['state']['is_onboarded']}")
        assert status == 200
        assert body["state"]["is_onboarded"] is False
        print("-> Test 7 PASSED.")
        
        print("\n==================================================")
        print("ALL API ENDPOINT TESTS COMPLETED SUCCESSFULLY!")
        print("==================================================")
        
    except Exception as e:
        print(f"FAIL: Verification suite encountered an error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        print("\nShutting down FastAPI background server...")
        server_process.terminate()
        server_process.wait()
        print("FastAPI server shut down successfully.")

if __name__ == "__main__":
    run_api_tests()
