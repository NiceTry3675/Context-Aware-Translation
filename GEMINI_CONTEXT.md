# Gemini's Understanding of the Context-Aware Translation Project

This document summarizes my understanding of the project's architecture and logic to ensure consistent and context-aware assistance in the future.

## 1. Project Goal

The project is a "Context-Aware AI Novel Translator" that uses the Google Gemini API. It translates English novels into Korean, focusing on maintaining consistency in terminology, character voice, and narrative style, rather than performing a simple, literal translation.

## 2. Core Components (File Breakdown)

-   **`main.py`**: **Entry Point.** Parses command-line arguments (input file path), initializes all core components, and starts the `TranslationEngine`.
-   **`config_loader.py`**: **Configuration.** Loads the Gemini API key and model settings (like safety settings, temperature) from a `.env` file.
-   **`gemini_model.py`**: **API Wrapper.** A dedicated class to handle all communication with the Google Gemini API. It includes retry logic for robustness.
-   **`translation_job.py`**: **Job & State Management.** Represents a single translation task. It reads the source novel, splits it into manageable segments, and stores the state of the translation, including the original text, translated text, the evolving `glossary`, and `character_styles`. It also writes the final output.
-   **`prompt_manager.py`**: **Prompt Hub.** A static class that centralizes all prompt templates. This makes prompts easy to find and modify.
-   **`glossary_manager.py`**: **Terminology Consistency.** Extracts proper nouns (names, places) from the text, uses the AI to translate them, and maintains a consistent glossary.
-   **`character_style_manager.py`**: **Dialogue Consistency.** Analyzes the protagonist's dialogue to determine the correct Korean speech level (e.g., formal `존댓말` vs. informal `반말`) to use with other characters.
-   **`dynamic_config_builder.py`**: **Context Orchestrator.** Before translating each segment, this module runs the `GlossaryManager` and `CharacterStyleManager` to update the context. It also analyzes the segment for any deviations from the novel's main narrative style (e.g., a letter, a poem).
-   **`prompt_builder.py`**: **Final Prompt Construction.** Gathers all the dynamic context (core style, style deviations, glossary, character styles, previous sentences) and assembles the final, detailed prompt for the AI.
-   **`translation_engine.py`**: **Core Logic Engine.** Orchestrates the entire translation process from start to finish. It defines the novel's core style, then loops through each segment, invoking the builders and managers to create context-rich prompts and generate translations. It also handles all logging.

## 3. Overall Workflow

The system follows a sophisticated, stateful, segment-by-segment process:

1.  **Initialization**: `main.py` kicks things off. A `TranslationJob` is created, and the source novel is segmented.
2.  **Core Style Definition**: The `TranslationEngine` analyzes the first text segment to establish the novel's "Core Narrative Style" (e.g., 1st-person, literary tone). This serves as a baseline.
3.  **Translation Loop (for each segment)**:
    a.  **Build Dynamic Context**: The `DynamicConfigBuilder` analyzes the current segment's text to update the `glossary` and `character_styles` and to check for any `style_deviation`.
    b.  **Assemble Prompt**: The `PromptBuilder` takes all this context—the core style, deviation notes, glossary, character styles, and the last few sentences of the *previous* translation (for continuity)—and builds a comprehensive prompt.
    c.  **Translate**: The prompt is sent to the Gemini API via `GeminiModel`.
    d.  **Store and Persist**: The translation is saved to the output file. The updated `glossary` and `character_styles` are carried over to the next segment, ensuring the context evolves and grows.
4.  **Completion**: After the last segment is translated, the job is complete, and the final file is available in the `translated_novel/` directory.
