# AGENTS.md

This file provides guidance to coding Agent when working with code in this repository.

## Project Overview

Translate English novels into Korean, focusing on contextual consistency of **narrative style, terminology (glossary), and character voice**, not just literal translation.

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy  
- **Frontend**: Next.js, TypeScript, Tailwind CSS
- **Database**: PostgreSQL
- **AI Model**: Google Gemini (user-selectable model)
- **Deployment**: Backend on **Railway**, Frontend on **Vercel**

## Core Architecture

- **`frontend/`**: Next.js UI for file upload, progress monitoring, and download
- **`backend/`**: FastAPI server for API endpoints, job management (PostgreSQL), and background tasks
- **`core/`**: The translation brain
  - **`translation/engine.py`**: Orchestrates the translation process
  - **`config/builder.py`**: Dynamically builds and manages **Glossary** and **Character Styles** for context
  - **`prompts/builder.py`**: Assembles context-rich prompts for the Gemini API

## Key Workflow

1. **Upload & Analyze**: User uploads a file. Backend's `/api/v1/analyze-style` endpoint is called. AI analyzes initial text to determine **protagonist's name** and **core narrative style**
2. **User Confirmation**: Analysis result sent to frontend. User reviews and can modify protagonist's name and detailed style guide
3. **Job Creation**: User starts translation. Backend receives file and (potentially modified) style data, creates a `TranslationJob`, and starts background task
4. **Translation Loop (Segment by Segment)**:
   - Core engine uses user-confirmed protagonist name and style guide
   - Analyzes each text segment to build dynamic context (glossary, character dialogue styles)
   - Comprehensive prompt assembled and sent to Gemini API
   - Result saved and progress updated in database
5.  **Validation (Optional)**: After the translation is complete, if the user enabled it, the `validator.py` module runs an AI-based quality check on the translated text, looking for issues like missing content, name inconsistencies, and style deviations. A validation report is generated.
6.  **Post-Editing (Optional)**: If validation finds issues and the user enabled post-editing, the `post_editor.py` module attempts to automatically fix the identified errors.
5. **Completion**: Job status updated to `COMPLETED`. The user can then download the final translated file, as well as any validation or post-editing logs.

## Git Branching Strategy

- **`main`**: Production branch, deployed to the cloud
- **`dev`**: Main development branch. All feature branches merge into `dev`
