import sqlite3
import json
import os
from typing import List, Dict, Any

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "home_gym.db"))

def get_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
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
        ("pullup_bar", "Pull-up Bar", "bars", json.dumps({}))
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
