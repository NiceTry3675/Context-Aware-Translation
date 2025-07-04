class PromptManager:
    # New, simplified prompts for a multi-step style guide generation
    DETERMINE_NARRATIVE_VOICE = """
You are a literary analyst. Read the following text and determine the primary narrative voice.
Your answer MUST be one of the following: '1st-person' or '3rd-person'.
Do not provide any other explanation or text.

**Sample Text:**
---
{sample_text}
---

**Narrative Voice:**
"""

    DETERMINE_SPEECH_LEVEL = """
You are a lead Korean translator. The narrative voice of the novel is **{narrative_voice}**.
Based on the sample text below, choose the single most appropriate Korean speech level for the main narration.
Your choice MUST be one of the following: '해라체 (haerache)', '해요체 (haeyoche)', or '하십시오체 (hasipsioche)'.
Provide only the chosen level and nothing else.

**Sample Text:**
---
{sample_text}
---

**Recommended Speech Level:**
"""

    # Prompts for dynamic_config_builder.py
    EXTRACT_KEY_TERMS = """
Your task is to act as a data extractor. From the text segment below, identify and extract key terms crucial for consistency.

**Focus on:**
- Proper Nouns (e.g., "Gregor Samsa").
- Unique Concepts or Objects (e.g., "the Ungeziefer").
- Important Recurring Roles (e.g., "the chief clerk").

**Exclude:** Common nouns.
Provide a comma-separated list.

**Text Segment to Analyze:**
---
{segment_text}
---
**Comma-separated list of key terms:**
"""

    TRANSLATE_KEY_TERMS = """
You are creating a glossary. Provide a single, contextually appropriate Korean translation for each key term.
The format MUST be: `Key Term: Korean Translation`

**Key Terms to Translate:**
{key_terms}

**Output:**
"""

    ANALYZE_STYLE_AND_TONE = """
You are a literary analyst. The core narrative voice for this book is **{core_narrative_voice}**.
Your task is to identify ONLY deviations or specific details for the segment below.

**DO NOT comment on the base narrative style.**

**Text Segment:**
---
{segment_text}
---

**Analysis Output (provide only if there are specific deviations):**
- **Tone/Mood Shift:** (e.g., "The tone becomes more frantic and panicked here.")
- **Specific Character Dialogue:**
  - **[Character Name]:** (Describe their speech style, e.g., "Speaks in short, clipped sentences. Use a blunt, informal speech level.")
- **Literary Devices:** (e.g., "Contains a long, internal monologue. Maintain the established core voice.")
"""

    # Prompt for prompt_builder.py
    MAIN_TRANSLATION = """
You are a master translator. Your work must be precise and absolutely consistent.

**TRANSLATION PROTOCOL:**

**RULE 1 (ABSOLUTE & NON-NEGOTIABLE): Core Narrative Voice**
The established narrative voice for this entire novel is **{core_narrative_voice}**. All narration MUST strictly adhere to this style. This rule overrides all other suggestions or contextual temptations. For example, if the core voice is '해라체', every narrative sentence must end accordingly (e.g., -다, -까, -라).

**RULE 2: Glossary Terms**
You MUST use these exact translations for the following terms:
{glossary_terms}

**RULE 3: Segment-Specific Style**
Follow these dynamic guidelines for this segment ONLY:
{dynamic_guidelines}

**RULE 4: English Context**
Use the previous English sentence for context, but NOT for style.
- **Previous English Sentence:** {prev_segment_en}

---
**Source Text to Translate:**
{source_segment}
---

**YOUR TASK:**
1.  **Pre-translation Analysis:** State the core voice and how you will apply it.
2.  **Final Korean Translation:** Provide the final, polished translation.
3.  **Final Check:** Before outputting, verify that every narrative sentence strictly follows RULE 1.

**[Pre-translation Analysis]:**
<Your brief analysis here>

**[Korean Translation]:**
<Your final translation here>
"""
