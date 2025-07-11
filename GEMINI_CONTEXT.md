# Gemini's Understanding of the Context-Aware Translation Project

This document summarizes my understanding of the project's architecture and logic to ensure consistent and context-aware assistance in the future.

## 1. Project Goal

The project is a "Context-Aware AI Novel Translator" that uses the Google Gemini API. It translates English novels into Korean, focusing on maintaining consistency in terminology, character voice, and narrative style, rather than performing a simple, literal translation.

## 2. Core Architecture (Modular Design)

The `core` logic is organized into distinct, feature-based packages, promoting modularity and maintainability.

-   **`core/translation`**: Contains the central components responsible for the translation process.
    -   `engine.py` (**TranslationEngine**): The main orchestrator. It manages the entire translation workflow, from initial setup to processing each text segment.
    -   `job.py` (**TranslationJob**): Represents a single translation task. It handles file I/O, segmenting the source text, and storing the state (original text, translated text, etc.).
    -   `models/gemini.py` (**GeminiModel**): A dedicated wrapper for the Google Gemini API, handling all API communication, including robust retry mechanisms.

-   **`core/config`**: Manages all configuration aspects, both static and dynamic.
    -   `loader.py` (**load_config**): Loads static configuration (API keys, model settings) from the `.env` file.
    -   `builder.py` (**DynamicConfigBuilder**): The primary context orchestrator. Before translating each segment, it analyzes the text to identify and prepare dynamic context elements like glossary terms and character styles.
    -   `glossary.py` (**GlossaryManager**): Extracts key terms (proper nouns, etc.), translates them consistently, and maintains the project's glossary.
    -   `character_style.py` (**CharacterStyleManager**): Analyzes dialogue to determine and maintain consistent speech levels (e.g., formal vs. informal Korean) for each character.

-   **`core/prompts`**: Manages the creation and formatting of prompts sent to the AI.
    -   `manager.py` (**PromptManager**): A centralized hub for all prompt templates, making them easy to find and manage.
    -   `builder.py` (**PromptBuilder**): Assembles the final, context-rich prompt by combining the core narrative style, dynamic context (glossary, character styles), and conversational history.
    -   `sanitizer.py` (**PromptSanitizer**): Cleans and formats the final prompt to prevent injection or formatting issues.

-   **`core/utils`**: Provides shared utilities used across the system.
    -   `file_parser.py` (**parse_document**): A utility to parse different file formats (like `.txt`, `.epub`) into a consistent text format.
    -   `retry.py`: Contains specialized decorator functions (`@retry_with_softer_prompt`, etc.) to handle API errors and content policy violations gracefully.

-   **`core/errors`**: Defines custom exception types for predictable error handling throughout the application.

-   **`backend`**: The FastAPI web server that exposes the translation functionality through a REST API.
    -   `main.py`: Defines API endpoints for file uploads (`/uploadfile/`), status checks (`/status/{job_id}`), and downloads (`/download/{job_id}`). It uses background tasks to run the `TranslationEngine` without blocking the server.

## 3. Overall Workflow

The system follows a sophisticated, stateful, segment-by-segment process:

1.  **API Request**: The user uploads a file and their API key via the frontend. The `backend/main.py` receives the request.
2.  **Initialization**: A `TranslationJob` is created, and the source novel is parsed and segmented using `utils.file_parser`. The job is stored in the database with a `PENDING` status.
3.  **Background Processing**: A background task is initiated. The `TranslationEngine` takes over.
4.  **Core Style Definition**: The engine analyzes the first text segment to establish the novel's "Core Narrative Style" (e.g., 1st-person, literary tone). This serves as a baseline.
5.  **Translation Loop (for each segment)**:
    a.  **Build Dynamic Context**: The `config.DynamicConfigBuilder` analyzes the current segment's text. It uses `config.GlossaryManager` and `config.CharacterStyleManager` to update the context.
    b.  **Assemble Prompt**: The `prompts.PromptBuilder` gathers all context—the core style, glossary, character styles, and previous sentences—and builds a comprehensive prompt using templates from `prompts.PromptManager`.
    c.  **Translate**: The prompt is sent to the Gemini API via `translation.models.GeminiModel`. The database is updated with the current progress.
    d.  **Store and Persist**: The translation is saved to the output file. The updated context is carried over to the next segment.
6.  **Completion/Failure**: After the loop, the job status in the database is updated to `COMPLETED` or `FAILED`. If it fails, the error message is recorded.
7.  **Frontend Polling**: The frontend periodically calls the `/status/{job_id}` endpoint to get the latest job status, progress, and error information, updating the UI accordingly.
8.  **Download**: Once complete, the user can download the final file via the `/download/{job_id}` endpoint.