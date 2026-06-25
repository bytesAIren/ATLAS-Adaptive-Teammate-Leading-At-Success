# ATLAS - Adaptive Teammate Leading At Success - System & Agent Specifications (ADK 2.0)

This document defines the core architecture, state management, validation rules, and domain-specific constraints for the ATLAS - Adaptive Teammate Leading At Success web application using ADK 2.0.

---

## 1. ARCHITECTURAL STATE MANAGEMENT

### State Split
The ADK 2.0 Graph State is partitioned into a dual-layer structure to maintain historical consistency while allowing immediate, context-aware session flexibility.

*   **`UserProfile` (Persistent Layer)**: 
    *   Stores static and semi-static user data captured during onboarding or explicitly modified in profile settings.
    *   Fields include: Alphanumeric nickname, age, height (cm), weight (kg), general experience level, primary training type preference, and base frequency.
*   **`SessionContext` (Transient Layer)**:
    *   Stores local, single-session variables instantiated at the start of a workout session.
    *   Fields include: `current_energy`, `local_injuries`, `time_available`, `equipment_override`, and `session_goals`.
    *   This layer is discarded upon session termination and does not write back to `UserProfile` unless explicitly confirmed by the user.

```mermaid
graph TD
    A[User Input] --> B{Input Type}
    B -- Profile Edit --> C[UserProfile Update]
    B -- Session Chat --> D[SessionContext Override]
    C --> E[PlanningNode]
    D --> E
    E --> F[Workout Plan Generation]
```

### Precedence Rules
During the compilation of a session plan, the `PlanningNode` must evaluate both state layers using a **downscoping filter**:

1.  **Read Both**: The `PlanningNode` must fetch the latest `UserProfile` and the active `SessionContext`.
2.  **Override Application**: Any constraint specified in `SessionContext.override` (e.g., `"shoulder pain"`, `"lower back stiffness"`, or `"only 30 minutes available"`) acts as a **restrictive mask** over the baseline capabilities defined in the `UserProfile`.
3.  **Downscoping Limit**: Overrides can only *decrease* intensity, *exclude* movements, or *shorten* duration compared to the `UserProfile` baseline. They can never dynamically scale the plan beyond the physical limits established in the `UserProfile` (e.g., a "Beginner" session override cannot request a high-volume advanced barbell routine).
4.  **Immutability of Profile**: Overrides dynamically downscope the active planning constraints for the current graph traversal without mutating the historical `UserProfile` record.

### State Mutations
To protect the integrity of the persistent user profile and prevent catastrophic data loss during concurrent or partial updates:
*   **Partial Patching (PATCH)**: All graph state mutations must utilize partial patching (`PATCH` semantics). 
*   **No Full Replacement (UPSERT)**: Complete state replacements (`UPSERT`) are strictly prohibited. Updates must merge incoming key-value pairs with the existing state dictionary, preserving all non-targeted fields.
*   **Conflict Resolution**: If a PATCH payload contains conflicting keys, the graph's StateResolver node must reject the update, raise a handled state conflict exception, and rollback to the last known healthy state.

---

## 2. INPUT VALIDATION & DETERMINISTIC GATING

### Gating Layer & Pydantic Constraints
An intermediate, deterministic validation layer intercepts all data payloads before they commit to the ADK Graph State. This is enforced via Pydantic schema validation:

```python
from pydantic import BaseModel, Field, constr

class OnboardingPayload(BaseModel):
    nickname: constr(regex=r"^[a-zA-Z0-9]+$", min_length=2, max_length=15)
    age: int = Field(ge=16, le=90)
    weight_kg: float = Field(ge=40.0, le=200.0)
    height_cm: float = Field(ge=130.0, le=220.0)
    experience_level: str = Field(regex="^(Beginner|Intermediate|Advanced)$")
    training_preference: str = Field(regex="^(Strength|Cardio|Hybrid)$")
    frequency: str = Field(regex="^(1-2 times/week|3-5 times/week|>5 times/week)$")
    equipment_list: List[str]
    objectives: List[str]

```

### Exception Handling & Conversational Fallbacks
When the validation layer encounters a `ValidationError`, the graph execution must handle the error gracefully to prevent conversational deadlocks or system crashes:
1.  **Catch & Route**: The graph intercepts the validation error and prevents the state update.
2.  **Fallback State Activation**: The active node routes execution to a `ClarificationNode`.
3.  **Natural Language Prompting**: The system translates the raw Pydantic errors (e.g., `value is not a valid integer` or `ensure this value is less than or equal to 90`) into a clear, supportive feedback message.
    *   *Example Error*: `age: Value 95 is greater than max 90.`
    *   *Agent Output*: "It looks like the age entered (95) is outside our supported range of 16 to 90. Could you please double-check and provide your age again?"
4.  **Re-entry loop**: The system waits for the corrected inputs, maintaining the existing pre-validation state in the background.

### Default Safe State
If a user attempts to bypass onboarding via prompt injection (e.g., *"Ignore the forms, let's start lifting"*), the graph enforces a sandbox lock:
*   **Sandbox Trigger**: Any session initiated without a validated `UserProfile` payload triggers the `DefaultSafeState`.
*   **Safe State Constraints**:
    *   `experience_level`: `Beginner`
    *   `max_load_capacity`: `5 kg`
    *   `movement_allowlist`: Low-impact, bodyweight, or light resistance exercises only (e.g., bodyweight squats, wall push-ups, light band pulls).
    *   `blocked_movements`: All high-velocity, overhead, or complex multi-joint loaded movements are completely locked.
*   **Unlock Condition**: The sandbox remains active until a valid `OnboardingPayload` is successfully parsed, validated, and patched into the graph state.

---

## 3. DOMAIN KNOWLEDGE & EQUIPMENT LOCKS

The system's PlanningNode must strictly adhere to the physical realities of the user's home gym equipment configuration. Hallucinations of unavailable equipment or unsupported loads are hard-locked.

### Equipment Specifications & Load Limits
*   **Adjustable Bench**: Locked to angle settings between $180^\circ$ (flat) and $90^\circ$ (upright incline). Declines ($< 180^\circ$) are physically locked out.
*   **Dumbbell Inventory**: The only available loads are pairs of:
    *   $15\text{ kg}$
    *   $10\text{ kg}$
    *   $8\text{ kg}$
    *   $5\text{ kg}$
*   **Resistance Bands**: Light, Medium, and Heavy bands. Used for accessory exercises or adding variable resistance.
*   **Squat Capacity Lock**:
    *   The home gym lacks a squat rack.
    *   The **maximum squat load** is strictly capped at $20\text{ kg}$ (achieved using the user's $10\text{ kg} + 10\text{ kg}$ dumbbell pair combined with band assistance).
    *   No single dumbbell squat or loaded squat movement can exceed this cumulative load of $20\text{ kg}$ to prevent neck, collarbone, or grip injury during un-racked loading.

### Post-Strength Cardio Protocol
To optimize metabolic conditioning and prevent unsupervised over-exertion, conditioning finishers are applied conditionally:
*   **Trigger Condition**: A cardio finisher is only included if the user's `training_preference` is `"Cardio"` or `"Hybrid"`, OR their onboarding `objectives` contains cardio goals (e.g. `"60 minute ride"`, `"run a 5k"`, `"run a 10k"`).
*   **Sequence**: Must be executed immediately following the strength portion of the workout.
*   **Duration**: Strictly locked to a $60\text{-minute}$ continuous block.
*   **Intensity**: Target heart rate is locked at $130\text{ BPM}$ (aerobic base training). The system must instruct the user to monitor their heart rate and adjust their pace to stay within $\pm 5\text{ BPM}$ of the target.

### Dynamic Exercise Selection & Session Duration
The number of exercises selected for a workout is dynamically calculated by the `PlanningNode` based on user objectives and time availability:
*   **Strength Exercise Cost**: Each strength exercise is allocated a budget of 10 minutes (incorporating setup, warm-up sets, working sets, and recovery breaks).
*   **Cardio Buffer**: If the cardio protocol trigger condition is met, 60 minutes of the session duration is strictly allocated to the cardio finisher.
*   **Calculation Rule**:
    $$\text{Max Strength Exercises} = \left\lfloor \frac{\text{Time Available} - \text{Cardio Duration (if active)}}{\text{Strength Exercise Cost}} \right\rfloor$$
    *   *Example*: 90 minutes available with a cardio finisher leaves 30 minutes for strength $\implies$ maximum of 3 strength exercises.
    *   *Example*: 60 minutes available with no cardio finisher $\implies$ maximum of 6 strength exercises.
    *   *Default Minimum*: The plan will always contain at least 2 strength exercises if a strength portion is requested.

