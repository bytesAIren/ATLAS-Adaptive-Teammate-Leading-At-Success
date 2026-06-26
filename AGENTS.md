# ATLAS - Adaptive Teammate Leading At Success - System & Agent Specifications (ADK 2.0)

This document defines the current architecture, state management, validation rules, and domain-specific constraints for the ATLAS - Adaptive Teammate Leading At Success web application. It is intended to reflect the repository's present implementation rather than a future-state design.

---

## 1. ARCHITECTURAL STATE MANAGEMENT

### State Split
The ADK 2.0 Graph State is partitioned into a dual-layer structure to maintain historical consistency while allowing immediate, context-aware session flexibility.

*   **`UserProfile` (Baseline Profile Layer)**: 
    *   Stores validated onboarding data that acts as the baseline for planning decisions during the active application runtime.
    *   Fields include: Alphanumeric nickname, age, height (cm), weight (kg), general experience level, primary training type preference, and base frequency.
*   **`SessionContext` (Transient Layer)**:
    *   Stores local, single-session variables instantiated at the start of a workout session.
    *   Fields include: `current_energy`, `local_injuries`, `time_available`, `equipment_override`, and `session_goals`.
    *   This layer is recalculated and patched per session request and does not write back to `UserProfile`.

### Current Runtime Note
The current app keeps the active graph state in application memory for the running server process. The repository does not yet persist full user profiles or session history across restarts. SQLite is used for the exercise and equipment catalog rather than long-term user-state storage.

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
4.  **Immutability of Profile**: Overrides dynamically downscope the active planning constraints for the current graph traversal without mutating the baseline `UserProfile` values stored in the active runtime state.

### State Mutations
To protect the integrity of the active graph state and prevent accidental full replacements:
*   **Partial Patching (PATCH)**: All graph state mutations must utilize partial patching (`PATCH` semantics). 
*   **No Full Replacement (UPSERT)**: Complete state replacements (`UPSERT`) are strictly prohibited. Updates must merge incoming key-value pairs with the existing state dictionary, preserving all non-targeted fields.
*   **Conflict Resolution**: Invalid patch structures or schema-breaking updates must be rejected by the graph state patching layer, which raises a handled conflict exception instead of committing a bad state.

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
1.  **Catch & Return**: The graph intercepts the validation error and prevents the state update.
2.  **Clarification Response**: The validator returns a structured failure response with a human-readable clarification message.
3.  **Natural Language Prompting**: The system translates the raw Pydantic errors (e.g., `value is not a valid integer` or `ensure this value is less than or equal to 90`) into a clear, supportive feedback message.
    *   *Example Error*: `age: Value 95 is greater than max 90.`
    *   *Agent Output*: "It looks like the age entered (95) is outside our supported range of 16 to 90. Could you please double-check and provide your age again?"
4.  **Re-entry loop**: The system waits for corrected inputs while maintaining the existing pre-validation state in the background.

### Default Safe State
If a user attempts to bypass onboarding via prompt injection (e.g., *"Ignore the forms, let's start lifting"*), the graph enforces a sandbox lock:
*   **Sandbox Trigger**: Any session initiated without a validated `UserProfile` payload triggers the `DefaultSafeState`.
*   **Safe State Constraints**:
    *   `experience_level`: `Beginner`
    *   `max_load_capacity`: `5 kg`
    *   `movement_allowlist`: Low-impact, bodyweight, or light resistance exercises only (e.g., bodyweight squats, wall push-ups, light band pulls).
    *   `blocked_movements`: All high-velocity, overhead, or complex multi-joint loaded movements are completely locked.
    *   `training_preference`: Safe default onboarding state currently uses `Hybrid` in runtime, while still enforcing beginner-level safety constraints.
*   **Unlock Condition**: The sandbox remains active until a valid `OnboardingPayload` is successfully parsed, validated, and patched into the graph state.

---

## 3. DOMAIN KNOWLEDGE & EQUIPMENT LOCKS

The system's PlanningNode must strictly adhere to the physical realities of the user's home gym equipment configuration. Hallucinations of unavailable equipment or unsupported loads are hard-locked.

### Equipment Specifications & Load Limits
The seeded equipment catalog currently supports a broader home-gym inventory than the minimum ATLAS setup, including:
*   Adjustable bench
*   Dumbbells
*   Resistance bands
*   Yoga mat
*   Pull-up bar
*   Stationary bike / cyclette
*   Treadmill
*   Kettlebell
*   Jump rope

The planning rules still enforce hard locks for the primary strength equipment:
*   **Adjustable Bench**: Locked to angle settings between $180^\circ$ (flat) and $90^\circ$ (upright incline). Declines are physically locked out.
*   **Dumbbell Inventory**: The primary modeled dumbbell loads are pairs of:
    *   $15\text{ kg}$
    *   $10\text{ kg}$
    *   $8\text{ kg}$
    *   $5\text{ kg}$
*   **Resistance Bands**: Light, Medium, and Heavy bands. Used for accessory exercises or adding variable resistance.
*   **Squat Capacity Lock**:
    *   The planner assumes no squat rack is available for the primary home setup.
    *   The **maximum squat load** is strictly capped at $20\text{ kg}$.
    *   No single dumbbell squat or loaded squat movement can exceed this cumulative load of $20\text{ kg}$ to prevent neck, collarbone, or grip injury during un-racked loading.

### Post-Strength Cardio Protocol
To optimize metabolic conditioning and prevent unsupervised over-exertion, conditioning finishers are applied conditionally:
*   **Trigger Condition**: A cardio finisher is included when the user's `training_preference` is `"Cardio"` or `"Hybrid"`, or when onboarding objectives contain cardio-oriented goals such as `"60 minute ride"`, `"run a 5k"`, `"run a 10k"`, or other planner-recognized cardio signals.
*   **Sequence**: Must be executed immediately following the strength portion of the workout.
*   **Duration**: Cardio duration is dynamically budgeted based on objectives, session time, user experience, and safety adjustments. It is not fixed to a single universal length.
*   **Intensity**: The planner targets aerobic-base style conditioning, but heart-rate targets are dynamically adjusted. A fit advanced session may target around $130\text{ BPM}$, while protected or lower-capacity profiles may receive lower targets with wider tolerance.

### Dynamic Exercise Selection & Session Duration
The number of exercises selected for a workout is dynamically calculated by the `PlanningNode` based on user objectives and time availability:
*   **Strength Exercise Cost**: Each strength exercise is allocated a budget of 10 minutes (incorporating setup, warm-up sets, working sets, and recovery breaks).
*   **Cardio Buffer**: If the cardio protocol trigger condition is met, part of the session duration is allocated to the cardio finisher according to the planner's dynamic cardio configuration.
*   **Calculation Rule**:
    $$\text{Max Strength Exercises} = \left\lfloor \frac{\text{Time Available} - \text{Cardio Duration (if active)}}{\text{Strength Exercise Cost}} \right\rfloor$$
    *   *Example*: 90 minutes available with a cardio finisher leaves 30 minutes for strength $\implies$ maximum of 3 strength exercises.
    *   *Example*: 60 minutes available with no cardio finisher $\implies$ maximum of 6 strength exercises.
    *   *Default Minimum*: The plan will always contain at least 2 strength exercises if a strength portion is requested.

### Visible Trace And Review
The current implementation exposes an `agent_trace` in the session response so the frontend can show the major stages of the workflow. After composition, a critic layer reviews the plan and either approves it, normalizes it, or falls back to a deterministic rebuild when required by the hard constraints.

