# AGENTS.md

This file provides guidance to coding Agent when working with code in this repository.

## Project Overview

Translate novels from various source languages into Korean, focusing on contextual consistency of **narrative style, terminology (glossary), and character voice**, not just literal translation.

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy  
- **Frontend**: Next.js, TypeScript, Material-UI (MUI)
- **Database**: SQLite (local), PostgreSQL (production)
- **AI Models**: Google Gemini (direct API), Google Vertex AI (service account JSON), OpenRouter
- **Deployment**: Backend on **Railway**, Frontend on **Vercel**

## Core Architecture

- **`frontend/`**: Next.js UI for file upload, progress monitoring, and download
- **`backend/`**: FastAPI server for API endpoints, job management (SQLite local / PostgreSQL prod), and background tasks
- **`core/`**: The translation brain
  - **`translation/translation_pipeline.py`**: Orchestrates the translation process
  - **`config/builder.py`**: Dynamically builds and manages **Glossary** and **Character Styles** for context
  - **`prompts/builder.py`**: Assembles context-rich prompts for the selected AI model API

## Key Workflow

1. **Upload & Analyze**: User uploads a file. Backend's `/api/v1/analysis/style` endpoint is called. AI analyzes initial text to determine **protagonist's name** and **core narrative style**
2. **User Confirmation**: Analysis result sent to frontend. User reviews and can modify protagonist's name and detailed style guide
3. **Job Creation**: User starts translation. Backend receives file and (potentially modified) style data, creates a `TranslationJob`, and starts background task
4. **Translation Loop (Segment by Segment)**:
   - Core engine uses user-confirmed protagonist name and style guide
   - Analyzes each text segment to build dynamic context (glossary, character dialogue styles)
   - Comprehensive prompt assembled and sent to the selected AI model API
   - Result saved and progress updated in database
5. **Validation (Optional)**: After the translation is complete, if the user enabled it, the `validator.py` module runs an AI-based quality check on the translated text, looking for issues like missing content, name inconsistencies, and style deviations. A validation report is generated.
6. **Post-Editing (Optional)**: If validation finds issues and the user enabled post-editing, the `post_editor.py` module attempts to automatically fix the identified errors.
7. **Completion**: Job status updated to `COMPLETED`. The user can then download the final translated file, as well as any validation or post-editing logs.

## Development Workflow

This project uses a `Makefile` to automate common development tasks and a code generation pipeline to ensure type safety between the backend and frontend.

- **`Makefile`**: Provides simple commands like `make codegen`, `make clean`, and `make verify` to streamline development. Use `make help` to see all available commands.
- **Codegen Pipeline**: Automatically generates TypeScript types for the frontend from the backend's Pydantic models. This eliminates manual updates and prevents data inconsistencies. When you change a backend model that affects the frontend, run `make codegen` and commit the updated files.

## Git Branching Strategy

- **`main`**: Production branch, deployed to the cloud
- **`dev`**: Main development branch. All feature branches merge into `dev`
