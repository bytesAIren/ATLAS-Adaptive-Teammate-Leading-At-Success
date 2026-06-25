# ATLAS - Adaptive Teammate Leading At Success

![ATLAS cover image](ATLAS-Adaptive_Teammate_Leading_At_Success/media_gallery/ATLAS%20—%20Adaptive%20Teammate%20Leading%20At%20Success.png)

A safe, adaptive AI coaching experience for home workouts built with agent-style planning, validation, and safety checks.

## Overview

ATLAS - Adaptive Teammate Leading At Success is a practical AI agent system designed to help people train safely at home with limited equipment and changing constraints. The project combines a lightweight web interface with an agent-inspired backend that validates user input, compiles workout rules, and produces a personalized session plan.

This project was built as a Kaggle AI Agents capstone submission and is intended to demonstrate how agent-based design can turn a simple fitness idea into a usable, structured, and safety-aware experience.

## The Problem

Many people want to exercise at home, but they often face one or more of the following challenges:

- limited time and inconsistent routines
- uncertainty about which exercises are appropriate for their body and equipment
- risk of overtraining or using movements that are unsafe for their current condition
- lack of personalized guidance when training alone at home

A generic workout app often fails to account for these real-world constraints. ATLAS - Adaptive Teammate Leading At Success tries to address this by making planning adaptive, conservative, and transparent.

## The Solution

ATLAS - Adaptive Teammate Leading At Success acts like a personal trainer assistant that:

- collects user profile information during onboarding
- validates the input to prevent invalid or unsafe configurations
- applies session-specific constraints such as injuries, time availability, and equipment limits
- generates a workout plan that is safe, practical, and tailored to the user
- uses a layered architecture of validation, planning, and safety nodes to make decisions more structured and explainable

The system is intentionally designed to be more than a static workout generator. It behaves like a small multi-step agent workflow where each component has a clear role in producing a safer and more useful outcome.

## Why This Project Fits the Kaggle Capstone

This submission demonstrates several core ideas from the AI agents course:

- agent-style workflow design
- state management and structured decision-making
- validation and safety guardrails
- deterministic planning with user-specific constraints
- practical deployment as a web app

The project focuses on a meaningful real-world problem and shows how agent-based systems can provide value beyond a simple demo.

## Architecture

The project is organized around a simple but effective agent-inspired architecture:

1. Onboarding and Validation
   - collects and validates user information
   - converts raw input into a structured profile

2. Safety Layer
   - ensures the user starts in a safe baseline state when onboarding is incomplete
   - blocks risky or inappropriate movements based on context

3. Planning Layer
   - compiles constraints from the user profile and the active session
   - downscopes the plan to respect injuries, time availability, and equipment

4. Generation and Review
   - creates a workout plan
   - reviews it against the rules to ensure the output stays within safe boundaries

5. Web Interface
   - presents the experience through a lightweight front end
   - exposes the backend through a FastAPI service

## Project Structure

```text
ATLAS-Adaptive_Teammate_Leading_At_Success/
├── src/
│   ├── api.py
│   ├── runtime_bootstrap.py
│   ├── database/
│   ├── graph/
│   └── schemas/
├── static/
│   ├── index.html
│   ├── css/
│   └── js/
├── scratch/
├── requirements.txt
└── run_api.py
```

## Key Features

- onboarding flow with structured validation
- personalized workout planning based on user profile and session constraints
- injury-aware and equipment-aware logic
- safe default state for incomplete or unvalidated onboarding
- lightweight web app experience
- deterministic and explainable planning rules

## Technical Stack

- Python
- FastAPI
- Pydantic
- SQLite
- HTML/CSS/JavaScript
- Google Gemini integration for natural-language validation and coaching support

## How It Works

1. A user provides personal information and training preferences.
2. The validation layer checks that the input is structurally valid.
3. The system builds a safe state and compiles the active workout constraints.
4. The planning layer determines what is appropriate for the current session.
5. A workout plan is generated and returned to the user in a structured format.

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

The application will be available locally through the FastAPI server.

## Environment Variables

The app expects a Gemini API key to be available in the environment.

```bash
export GEMINI_API_KEY="your_api_key_here"
```

## Safety and Design Choices

Safety is a central part of this project rather than an afterthought. The system is intentionally conservative when user information is incomplete or invalid, and it avoids generating unsafe plans by default.

This design choice makes the project more useful for real users, especially in contexts where a poor recommendation could lead to injury or frustration.

## Why It Matters

This project shows that AI agents do not need to be overly complex to deliver value. A well-structured workflow with clear roles, guardrails, and practical outcomes can solve a real problem in a way that is understandable, safe, and deployable.

## Future Directions

Possible next steps include:

- adding a richer conversational coaching experience
- integrating a more advanced planner or multi-agent workflow
- expanding the exercise and injury logic
- improving the frontend experience and visual feedback
- adding persistent user history and better personalization

## Kaggle submission assets

To keep the Kaggle submission organized, the project now includes dedicated folders for the required public assets:

- Media Gallery: [media_gallery](ATLAS-Adaptive_Teammate_Leading_At_Success/media_gallery/) — add screenshots, architecture diagrams, and the final cover image here.
- Public Video: [videos](ATLAS-Adaptive_Teammate_Leading_At_Success/videos/) — upload the final 5-minute public video here. Once the video is published on YouTube, replace the placeholder link in the Kaggle writeup.
- Attached Project Link: [public_site](ATLAS-Adaptive_Teammate_Leading_At_Success/public_site/) — use this folder for the public demo bundle or deployment artifacts. Later, add the final public URL here (GitHub Pages, Google Cloud, or another hosting option).

These folders are meant to be placeholders for now and will be filled in before the final submission.

## Conclusion

ATLAS - Adaptive Teammate Leading At Success is a compact but meaningful example of how AI agents can be used to create a helpful, safe, and practical assistant for everyday fitness. It demonstrates the value of combining structured reasoning, safety constraints, and real-world usability in one coherent system.
