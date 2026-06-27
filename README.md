<h1 align="center">ATLAS - Adaptive Teammate Leading At Success</h1>

<p align="center">
  <img src="media_gallery/atlas-cover.png" alt="ATLAS cover image" width="800" />
</p>

<p align="center"><em><strong>
  A safety-first workout planner powered by an agent-inspired workflow.
</strong></em></p>

## Overview

ATLAS - Adaptive Teammate Leading At Success is a home-workout planning application designed to help people train more safely with limited equipment, changing daily constraints, and uneven confidence about what is appropriate to do.

The project combines a lightweight web interface with an agent-inspired backend workflow. Instead of relying on free-form generation alone, ATLAS validates user input, applies safety guardrails, compiles session constraints, generates a workout plan, and reviews the output before returning it to the user.

This repository was built as a Kaggle AI Agents capstone submission. The goal was not to build the largest possible fitness platform in two weeks, but to demonstrate how staged reasoning, deterministic safety enforcement, and selective AI support can create a useful, working product around a real-world problem.

## The Problem

Training at home sounds simple, but in practice it is often messy.

Many people face one or more of these challenges:

- limited time and inconsistent routines
- uncertainty about which exercises are appropriate for their body and equipment
- risk of overdoing movements that are unsafe for their current condition
- lack of personalized structure when training alone

A generic workout generator often fails because it ignores context. A beginner with a sore knee, a bench, and a short session window should not receive the same plan as an advanced user with more equipment and no physical limitations.

ATLAS is designed to address that gap by making planning adaptive, conservative, and practical.

## Why This Needed More Than A Simple Generator

A useful fitness system cannot just output exercises that sound plausible. It needs to:

- validate what the user entered
- adapt to the realities of the current session
- respect equipment and safety constraints
- review the final recommendation before presenting it

That makes this a strong fit for an agent-inspired workflow. The value is not unconstrained creativity. The value is judgment under constraints.

## Why Agents

ATLAS is not presented as a full autonomous multi-agent platform. Instead, it uses a single-agent workflow with specialized stages:

- `validator`: checks onboarding input and converts it into structured state
- `safety sandbox`: protects the user when onboarding is incomplete
- `planning node`: compiles profile data, session context, injuries, time, and equipment into hard constraints
- `generator`: composes a workout plan inside those boundaries
- `critic`: reviews the output and normalizes it if anything drifts outside the rules

This structure is what makes the system feel agentic. The project combines AI-assisted clarification and constrained plan generation with deterministic safety enforcement.

## Workflow Overview

<p align="center">
  <img src="media_gallery/Safety-First_Agentic_Workflow_Overview.png" alt="ATLAS safety-first agentic workflow overview" width="800" />
</p>

<p align="center"><em>
  ATLAS turns user input into a constrained workout plan through validation, safety sandboxing, planning, generation, and critic review.
</em></p>

## How ATLAS Works

ATLAS follows a concrete five-step workflow:

1. **Onboarding validation**  
   The user provides profile details such as age, experience level, training preference, available equipment, and objectives. Pydantic validation checks that the data is usable and within safe bounds.

2. **Safe default state**  
   If onboarding is incomplete or invalid, the app falls back to a conservative default-safe state. In that mode, higher-risk movements remain locked.

3. **Session constraint patching**  
   The user configures a workout session with local context such as energy, temporary injuries, goals, and available time. These session constraints downscope the profile rather than overwrite it.

4. **Planning and workout composition**  
   The planner compiles the effective rules for the session, including time budget, movement allowlists, injury-related restrictions, squat load limits, cardio behavior, and equipment availability. The generator then builds a plan inside those limits.

5. **Critic review before return**  
   Before the plan is returned, a critic layer checks it against the compiled rules. If needed, the output is normalized or replaced by a deterministic fallback.

The session response also includes an `agent_trace`, allowing the UI to show the major stages behind the recommendation.

## A Concrete Example Of Value

Consider a user with limited time, a bench, dumbbells, and lower-back discomfort.

A generic workout generator might still propose a risky hinge pattern, an unrealistic cardio block, or too much lower-body volume. ATLAS instead validates the user profile, applies temporary restrictions, checks effective equipment, narrows the movement pool, respects hard load limits, and composes a session that still feels practical and actionable.

That is the core behavior of the system: not simply producing a workout, but narrowing the plan through safety and context until it becomes realistic for the person using it.

## Architecture

The backend is organized around a small set of role-based modules:

1. **Validation**
   - validates onboarding payloads with Pydantic
   - returns natural-language clarification when inputs are invalid

2. **Safety**
   - activates the default-safe state when onboarding is incomplete
   - blocks unsafe recommendations before planning proceeds

3. **Planning**
   - combines `UserProfile` and `SessionContext`
   - applies downscoping rules for injuries, equipment, and time
   - compiles hard constraints such as squat load and cardio budget

4. **Generation**
   - creates a structured workout plan inside the compiled limits
   - uses Gemini to power the richer constrained generation path

5. **Critic Review**
   - checks the plan against the authoritative rules
   - approves, normalizes, or rebuilds the output when required

6. **Frontend**
   - provides onboarding, session setup, and workout review through a lightweight static UI
   - surfaces active constraints and planning trace data from the backend

## Project Structure

```text
ATLAS-Adaptive_Teammate_Leading_At_Success/
|-- index.html                # GitHub Pages landing page
|-- src/
|   |-- api.py
|   |-- runtime_bootstrap.py
|   |-- database/
|   |-- graph/
|   `-- schemas/
|-- static/
|   |-- index.html            # interactive frontend app shell
|   |-- css/
|   `-- js/
|-- media_gallery/            # screenshots, cover image, and submission video
|-- scratch/
|-- requirements.txt
`-- run_api.py
```

## Key Features

- structured onboarding flow with validation and clarification feedback
- personalized workout planning based on user profile and session constraints
- injury-aware, equipment-aware, and time-aware planning logic
- safe default state for incomplete or unvalidated onboarding
- visible planning trace and critic review feedback in the session response
- deterministic fallback behavior when AI assistance is unavailable

## Technical Stack

- Python
- FastAPI
- Pydantic
- SQLite-backed exercise and equipment catalog
- HTML/CSS/JavaScript
- Google Gemini for natural-language clarification and constrained workout generation

## Current Implementation Notes

- The active graph state is stored in application memory for the running server process.
- SQLite is currently used for the exercise and equipment catalog, not as full long-term user-state persistence.
- ATLAS can run without a Gemini API key by falling back to deterministic validation messaging and deterministic workout composition rules, but the richer agentic generation path is enabled when Gemini is available.

## Why This Fits The Kaggle Capstone

This project was intentionally shaped to align with the capstone brief:

- it addresses a meaningful real-world personal-use problem
- it includes a working interactive application rather than a concept-only demo
- it demonstrates visible agent concepts through staged reasoning and review
- it emphasizes safety-aware design instead of unconstrained output generation
- it provides reproducible local setup and clear project documentation

The project is especially well suited to the `Concierge Agents` framing because it tackles an everyday personal challenge in a way that is practical, supportive, and safety-conscious.

## Setup Instructions

### Prerequisites

- Python 3.10+
- pip

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the app

```bash
python run_api.py
```

The application will be available locally through the FastAPI server at `http://127.0.0.1:8000`.

## Environment Variables

Gemini is strongly recommended for the full ATLAS experience.

ATLAS can run without a Gemini API key in a deterministic fallback mode that preserves validation, planning, safety enforcement, and critic review. Enabling Gemini unlocks the richer agentic path for natural-language clarification and constrained workout generation.

```bash
export GEMINI_API_KEY="your_api_key_here"
```

On Windows PowerShell:

```powershell
$env:GEMINI_API_KEY="your_api_key_here"
```

## Demo And Public Assets

- [index.html](index.html) is a GitHub Pages-friendly landing page for the project.
- The full interactive experience requires the Python backend to be running.
- If a fully hosted public demo is not available, this repository is intended to satisfy the capstone requirement for a public project link with reproducible setup instructions.

## Kaggle Submission Assets

To keep the Kaggle submission organized, the repository includes a dedicated folder for public assets:

- Media Gallery: [media_gallery](media_gallery/)
- Cover image: [media_gallery/atlas-cover.png](media_gallery/atlas-cover.png)
- Workflow infographic: [media_gallery/Safety-First_Agentic_Workflow_Overview.png](media_gallery/Safety-First_Agentic_Workflow_Overview.png)
- Screenshots:
  - [media_gallery/Screenshot 2026-06-26 214151.png](media_gallery/Screenshot%202026-06-26%20214151.png)
  - [media_gallery/Screenshot 2026-06-26 214309.png](media_gallery/Screenshot%202026-06-26%20214309.png)
  - [media_gallery/Screenshot 2026-06-26 214405.png](media_gallery/Screenshot%202026-06-26%20214405.png)
  - [media_gallery/Screenshot 2026-06-26 214416.png](media_gallery/Screenshot%202026-06-26%20214416.png)
  - [media_gallery/Screenshot 2026-06-26 214427.png](media_gallery/Screenshot%202026-06-26%20214427.png)
- Submission video: [media_gallery/ATLAS__Concierge_Agent.mp4](media_gallery/ATLAS__Concierge_Agent.mp4)

## Safety And Design Choices

Safety is central to the project rather than an afterthought. The system is intentionally conservative when user information is incomplete or invalid, and it avoids generating unsafe plans by default.

That makes the application more useful for real users, especially in a domain where poor recommendations can lead to frustration, overtraining, or injury risk.

## Future Directions

With modest additional time, ATLAS could grow in a few practical directions:

- a natural-language session interpreter that converts free-form requests into structured session constraints
- richer explanation layers that show why exercises were included, removed, or downgraded
- better session memory for short-term progression and variety
- stronger public-demo packaging and deployment polish

With more time and resources, it could expand further:

- persistent user history and progression tracking
- recovery-aware planning across multiple sessions
- wearable integrations
- more advanced coaching feedback loops
- deeper multi-agent collaboration for interpretation, planning, and critique

## Conclusion

ATLAS - Adaptive Teammate Leading At Success is a focused, working prototype that demonstrates how agent-inspired workflows can be practical, safe, and genuinely helpful. It combines staged reasoning, constrained AI support, and deterministic guardrails to turn a messy real-world fitness problem into a cleaner and more actionable user experience.
