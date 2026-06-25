from pydantic import BaseModel, Field
from typing import List

class OnboardingPayload(BaseModel):
    nickname: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9]+$",
        min_length=2,
        max_length=15,
        description="Alphanumeric nickname between 2 and 15 characters"
    )
    age: int = Field(..., ge=16, le=90, description="Age must be between 16 and 90")
    weight_kg: float = Field(..., ge=40.0, le=200.0, description="Weight in kg must be between 40.0 and 200.0")
    height_cm: float = Field(..., ge=130.0, le=220.0, description="Height in cm must be between 130.0 and 220.0")
    experience_level: str = Field(
        ...,
        pattern=r"^(Beginner|Intermediate|Advanced)$",
        description="Experience level must be Beginner, Intermediate, or Advanced"
    )
    training_preference: str = Field(
        ...,
        pattern=r"^(Strength|Cardio|Hybrid)$",
        description="Training type preference must be Strength, Cardio, or Hybrid"
    )
    frequency: str = Field(
        ...,
        pattern=r"^(1-2 times/week|3-5 times/week|>5 times/week)$",
        description="Frequency must be 1-2 times/week, 3-5 times/week, or >5 times/week"
    )
    equipment_list: List[str] = Field(
        ...,
        description="List of owned equipment IDs"
    )
    objectives: List[str] = Field(
        ...,
        description="List of user fitness objectives (e.g. 'run a 5k', 'healthy life', '10k steps a day', '60 minute ride')"
    )


