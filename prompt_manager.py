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

    # --- Dynamic Style Analysis Prompts ---
    ANALYZE_NARRATIVE_DEVIATION = """
You are a literary analyst. The established core narrative style for this novel is:
---
{core_narrative_style}
---

Your task is to analyze the following text **segment**. This is just a piece of the full text.
Determine if this specific segment deviates from the core style. Focus only on clear, structural changes.

**Look for:**
- Direct quotes from other sources (e.g., a book, a poem).
- Text formatted as a letter, a diary entry, or a newspaper article.
- A dream sequence with a distinctly different tone.
- Sudden shifts into verse/poetry.

**Instructions:**
- If a clear deviation exists, describe it briefly (e.g., "The segment is a formal letter.", "This is a dream sequence with a hazy, surreal tone.").
- If there is no clear deviation from the core style, you MUST respond with "N/A".

**Text Segment to Analyze:**
---
{segment_text}
---

**Detected Style Deviation:**
"""

    # --- Translation Engine Prompts ---

    DEFINE_NARRATIVE_STYLE = """
You are a master literary analyst. Your task is to analyze the provided text and define its core narrative style for Korean translation by filling out the following report.
The report MUST be concise and use the specified terms.

**Analysis Report Template:**
1.  **Narrative Perspective:** (Choose one: 1st-person, 3rd-person)
2.  **Primary Speech Level:** (Choose the most fitting: 해라체, 해요체, 하오체, 하십시오체, 해체 etc.)
3.  **Tone (Written/Spoken):** (Choose one: 문어체 (Literary/Written), 구어체 (Colloquial/Spoken))

**Sample Text:**
---
{sample_text}
---

**Instructions:**
Fill out the report based on your analysis of the sample text.

**Analysis Report:**
"""

    MAIN_TRANSLATION = """
You are a master translator specializing in literature. Your task is to translate the following text segment into Korean with absolute precision and consistency, following the provided rules.

**RULE 1: Core Narrative Style (기본 서술)**
- The core narrative style for this novel is defined below. This is the default style you should use for all standard narration.
---
{core_narrative_style}
---

**RULE 2: Segment-Specific Style Deviation (세그먼트 예외 스타일)**
- **This is the most important rule for this specific segment.**
- An analysis has determined that this segment has a special style. You MUST prioritize the following instruction over the core style.
- **Deviation Instruction:** {style_deviation_info}

**RULE 3: Glossary (용어집)**
- You MUST use these exact Korean translations for all terms in this list. This is non-negotiable.
{glossary_terms}

**RULE 4: Protagonist's Dialogue (주인공 대화)**
- The protagonist's speech SHOULD GENERALLY follow these rules.
- **However, you have the autonomy to deviate if the immediate context (e.g., a moment of extreme anger, intimacy, or sarcasm) makes the established style unnatural.**
{character_speech_styles}

**RULE 5: Other Characters' Dialogue (기타 인물 대화)**
- For all other characters, or if a specific interaction is not in the list above, translate their dialogue naturally based on the context of the scene.

**RULE 6: Context is Key**
- Use the previous sentences for immediate context and style continuity.
- **Previous English Sentence:** {prev_segment_en}
- **Previous Korean Translation:** {prev_segment_ko}
- Your new translation should flow naturally from the previous Korean translation.

---
**Translate the following text into Korean, adhering strictly to all rules above:**
---
{source_segment}
"""