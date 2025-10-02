# Prompts Configuration

This directory contains the prompt templates used by the Context-Aware Translation system.

## Structure

- `prompts.yaml` - Contains all prompt templates organized by category
- `manager.py` - Python class that loads and provides access to prompts
- `builder.py` - Utility for building prompts with variable substitution

## YAML Structure

The `prompts.yaml` file is organized into the following sections:

```yaml
glossary:
  extract_nouns: # Prompt for extracting proper nouns
  translate_terms: # Prompt for translating glossary terms

character_style:
  analyze_dialogue: # Prompt for analyzing character speech patterns

style_analysis:
  narrative_deviation: # Prompt for detecting style deviations
  define_narrative_style: # Prompt for defining the protagonist's name and the core narrative style

translation:
  main: # Main translation prompt template
  turbo: # Turbo translation (no style deviation or character styles)
```

## Usage

The prompts are accessed through the `PromptManager` class:

```python
from core.prompts.manager import PromptManager

# Access prompts as class attributes
prompt = PromptManager.MAIN_TRANSLATION.format(
    source_segment="Text to translate",
    core_narrative_style="Style description",
    # ... other variables
)
```

## Editing Prompts

To modify prompts:

1. Edit the `prompts.yaml` file directly

## Structured Output for Validation

The validation system uses Gemini Structured Output to return JSON per a response schema. Two lightweight prompt wrappers are provided:

- `validation.structured_comprehensive`
- `validation.structured_quick`

The actual schema is defined in `core/validation/structured.py`. The validator builds a minimal instruction prompt and relies on schema enforcement; results are mapped to the existing report fields to keep frontend compatibility.
2. Ensure all placeholder variables (e.g., `{segment_text}`) are preserved
3. Test that the prompts still work with the translation system

## Variable Placeholders

Each prompt contains placeholder variables that are filled in at runtime:

- `{segment_text}` - The text segment being analyzed
- `{protagonist_name}` - Name of the main character
- `{core_narrative_style}` - Description of the narrative style
- `{source_segment}` - Text to be translated
- etc.

When editing prompts, ensure all placeholders remain intact and properly formatted.
