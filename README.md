# Novel Writing Skill System

This repository hosts the **novel-writing** skill configuration and automation toolset for the Hermes Agent environment. 
It facilitates an autonomous 8-stage pipeline to outline, generate, review, and refine long-form fantasy/web novels using hybrid dual-model setups (e.g., Hermes + agy / Claude + Gemini).

## Key Features & Frameworks
- **Structured 8-Stage Novel Pipeline**: From initial material analysis to outline structure, fine-detailed scene outline generation (Beats), context tracing, dual-model generation, automated validations, and output delivery.
- **Novel SOP (open-novel-fanqie Integration)**:
  - **Beats-based Micro-Scene Generation**: Breaks chapters down into 2-4 individual narrative moments (1k–1.5k words each) before splicing, preventing AI pacing collapse.
  - **Ledger/Stat Tracking**: Systematizes game/cultivation mechanics by keeping a logical and mathematical balance book (deducting spiritual power, items, cash in context files).
  - **POV Limit (PoVL-3)**: Strict 3rd-person limited perspective rules ensuring no telepathic scene hops or narrator monologues.
- **Auto Validations (`novel_pipeline.py`)**: Runs layout, length, character profile consistency checks automatically.
