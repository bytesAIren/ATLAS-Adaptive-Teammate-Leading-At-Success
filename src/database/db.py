import sqlite3
import json
import os
from typing import List, Dict, Any

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "home_gym.db")
RUNTIME_DB_PATH = os.path.join(PROJECT_ROOT, "runtime_home_gym.db")


def resolve_db_path() -> str:
    """Resolves a writable database path for the current runtime."""
    explicit_path = os.environ.get("HOME_GYM_DB_PATH")
    if explicit_path:
        return explicit_path

    if os.path.exists(DEFAULT_DB_PATH):
        try:
            with open(DEFAULT_DB_PATH, "ab"):
                return DEFAULT_DB_PATH
        except OSError:
            return RUNTIME_DB_PATH

    return DEFAULT_DB_PATH

def get_connection():
    """Returns a connection to the SQLite database."""
    db_path = resolve_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema and seeds initial data."""
    conn = get_connection()
    cursor = conn.cursor()

    # Create Equipment Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipment (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            meta_specs TEXT
        )
    """)

    # Create Exercises Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            required_equipment TEXT NOT NULL, -- JSON list of equipment IDs
            min_experience TEXT NOT NULL,
            muscle_group TEXT NOT NULL,
            exercise_type TEXT NOT NULL
        )
    """)

    # Seed Equipment
    equipment_data = [
        ("adjustable_bench", "Adjustable Bench", "bench", json.dumps({"angles_degrees": [90, 180]})),
        ("dumbbells", "Dumbbells", "weights", json.dumps({"available_pairs_kg": [5, 8, 10, 15]})),
        ("resistance_bands", "Resistance Bands", "bands", json.dumps({"levels": ["light", "medium", "heavy"]})),
        ("yoga_mat", "Yoga Mat", "mats", json.dumps({})),
        ("pullup_bar", "Pull-up Bar", "bars", json.dumps({})),
        ("stationary_bike", "Stationary Bike / Cyclette", "cardio", json.dumps({"modality": "cycling"})),
        ("treadmill", "Treadmill", "cardio", json.dumps({"modality": "walking_running"})),
        ("kettlebell", "Kettlebell", "weights", json.dumps({"recommended_home_range_kg": [8, 12, 16]})),
        ("jump_rope", "Jump Rope", "cardio", json.dumps({})),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO equipment (id, name, category, meta_specs)
        VALUES (?, ?, ?, ?)
    """, equipment_data)

    # Seed Exercises
    exercises_data = [
        (
            "db_bench_press", 
            "Dumbbell Bench Press", 
            json.dumps(["adjustable_bench", "dumbbells"]), 
            "Beginner", 
            "Chest", 
            "Strength"
        ),
        (
            "db_incline_press", 
            "Incline Dumbbell Press", 
            json.dumps(["adjustable_bench", "dumbbells"]), 
            "Intermediate", 
            "Chest", 
            "Strength"
        ),
        (
            "bodyweight_squat", 
            "Bodyweight Squat", 
            json.dumps(["yoga_mat"]), 
            "Beginner", 
            "Legs", 
            "Strength"
        ),
        (
            "goblet_squat", 
            "Goblet Squat", 
            json.dumps(["dumbbells"]), 
            "Beginner", 
            "Legs", 
            "Strength"
        ),
        (
            "band_pull_apart", 
            "Band Pull-Apart", 
            json.dumps(["resistance_bands"]), 
            "Beginner", 
            "Back", 
            "Strength"
        ),
        (
            "pullup", 
            "Pull-up", 
            json.dumps(["pullup_bar"]), 
            "Advanced", 
            "Back", 
            "Strength"
        ),
        (
            "chair_sit_to_stand",
            "Chair Sit-to-Stand",
            json.dumps([]),
            "Beginner",
            "Legs",
            "Strength"
        ),
        (
            "wall_push_up",
            "Wall Push-up",
            json.dumps([]),
            "Beginner",
            "Chest",
            "Strength"
        ),
        (
            "supported_march",
            "Supported March",
            json.dumps([]),
            "Beginner",
            "Core",
            "Strength"
        ),
        (
            "standing_heel_raise",
            "Standing Heel Raise",
            json.dumps([]),
            "Beginner",
            "Legs",
            "Strength"
        ),
        (
            "db_row",
            "Single-Arm Dumbbell Row",
            json.dumps(["dumbbells", "adjustable_bench"]),
            "Beginner",
            "Back",
            "Strength"
        ),
        (
            "band_row",
            "Resistance Band Row",
            json.dumps(["resistance_bands"]),
            "Beginner",
            "Back",
            "Strength"
        ),
        (
            "db_rdl",
            "Dumbbell Romanian Deadlift",
            json.dumps(["dumbbells"]),
            "Intermediate",
            "Legs",
            "Strength"
        ),
        (
            "step_up",
            "Bench Step-Up",
            json.dumps(["adjustable_bench"]),
            "Beginner",
            "Legs",
            "Strength"
        ),
        (
            "burpee", 
            "Burpees", 
            json.dumps(["yoga_mat"]), 
            "Intermediate", 
            "Full Body", 
            "Cardio"
        ),
        (
            "shadow_boxing", 
            "Shadow Boxing", 
            json.dumps([]), 
            "Beginner", 
            "Full Body", 
            "Cardio"
        ),
        (
            "stationary_bike_ride",
            "Stationary Bike Ride",
            json.dumps(["stationary_bike"]),
            "Beginner",
            "Legs",
            "Cardio"
        ),
        (
            "treadmill_walk",
            "Treadmill Walk",
            json.dumps(["treadmill"]),
            "Beginner",
            "Legs",
            "Cardio"
        ),
        (
            "treadmill_jog",
            "Treadmill Jog",
            json.dumps(["treadmill"]),
            "Intermediate",
            "Legs",
            "Cardio"
        ),
        (
            "jump_rope_intervals",
            "Jump Rope Intervals",
            json.dumps(["jump_rope"]),
            "Intermediate",
            "Full Body",
            "Cardio"
        )
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO exercises (id, name, required_equipment, min_experience, muscle_group, exercise_type)
        VALUES (?, ?, ?, ?, ?, ?)
    """, exercises_data)

    conn.commit()
    conn.close()

def get_all_equipment() -> List[Dict[str, Any]]:
    """Retrieves all registered equipment."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM equipment")
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        result.append({
            "id": row["id"],
            "name": row["name"],
            "category": row["category"],
            "meta_specs": json.loads(row["meta_specs"]) if row["meta_specs"] else {}
        })
    return result

def get_all_exercises() -> List[Dict[str, Any]]:
    """Retrieves all registered exercises."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exercises")
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        result.append({
            "id": row["id"],
            "name": row["name"],
            "required_equipment": json.loads(row["required_equipment"]),
            "min_experience": row["min_experience"],
            "muscle_group": row["muscle_group"],
            "exercise_type": row["exercise_type"]
        })
    return result

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
