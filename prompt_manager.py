class PromptManager:
    """
    Manages all prompts used in the translation system.
    This centralized approach makes it easy to view, edit, and manage prompts.
    """

    # --- Glossary Manager Prompts ---
    GLOSSARY_EXTRACT_NOUNS = """
Your task is to act as a data extractor. From the text segment below, identify and extract only proper nouns that could be confusing if translated inconsistently.

**CRITICAL RULES:**
1.  **EXTRACT ONLY FROM THE PROVIDED TEXT.** Do not invent or infer any names or terms that are not explicitly written in the text.
2.  **FOCUS EXCLUSIVELY ON:**
    - People's names (e.g., "John Doe", "Jane Smith").
    - Place names (e.g., "Springfield").
    - Unique, named objects or concepts (e.g., "the Monolith").
3.  **STRICTLY EXCLUDE:**
    - Common nouns (e.g., "father", "room", "apple").
    - Roles unless used as a proper name (e.g., extract "Chief Clerk" but not "the chief clerk").

If no proper nouns are found in the text, you MUST return an empty string.

**Text Segment to Analyze:**
---
{segment_text}
---
**Comma-separated list of proper nouns found ONLY in the text above:**
"""

    GLOSSARY_TRANSLATE_TERMS = """
You are creating a glossary for a novel translation. Provide a single, contextually appropriate Korean translation for each term.
The format MUST be: `Key Term: Korean Translation`
Each entry must be on a new line.

**Terms to Translate:**
{key_terms}

**Output:**
"""

    # --- Character Style Manager Prompts ---
    CHARACTER_ANALYZE_DIALOGUE = """
You are a literary analyst focusing on dialogue. In the text below, identify who the protagonist, **{protagonist_name}**, speaks to.
Determine if **{protagonist_name}** uses formal speech (존댓말) or informal speech (반말) towards them.

**Your Task:**
- List only the characters the protagonist speaks to.
- For each character, specify the speech style used by the protagonist.
- The output format MUST be: `Character Name: 존댓말` or `Character Name: 반말`.
- If there are no direct dialogues involving the protagonist, or if it's impossible to tell, respond with "N/A".

**Text Segment to Analyze:**
---
{segment_text}
---

**Analysis (Protagonist's Speech Style Towards Others):**
"""

    # --- Translation Engine Prompt ---
    MAIN_TRANSLATION = """
You are a master translator specializing in literature. Your task is to translate the following text segment into Korean with absolute precision and consistency, following the provided rules.

**RULE 1: Narration (서술)**
- All narration MUST be translated into a standard, neutral literary style ('평서체', e.g., ending in -다, -라, -까). This is the default voice of the book.

**RULE 2: Glossary (용어집)**
- You MUST use these exact Korean translations for all terms in this list. This is non-negotiable.
{glossary_terms}

**RULE 3: Protagonist's Dialogue (주인공 대화)**
- The protagonist's speech MUST follow these specific rules. This list shows who the protagonist speaks to and what style to use.
{character_speech_styles}

**RULE 4: Other Characters' Dialogue (기타 인물 대화)**
- For all other characters, or if a specific interaction is not in the list above, translate their dialogue naturally based on the context of the scene.

**RULE 5: Context is Key**
- Use the previous sentences for immediate context and style continuity.
- **Previous English Sentence:** {prev_segment_en}
- **Previous Korean Translation:** {prev_segment_ko}
- Your new translation should flow naturally from the previous Korean translation.

---
**Translate the following text into Korean, adhering strictly to all rules above:**
---
{source_segment}
"""