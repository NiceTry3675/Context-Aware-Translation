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
You are a literary analyst specializing in Korean translation.
Your task is to analyze the dialogue in the following text segment to determine the speech style of the protagonist, **{protagonist_name}**.

**Analysis Guidelines:**
- Identify who the protagonist speaks to (by name or by a concise role).
- Determine the appropriate Korean speech style (존댓말 or 반말).
- **Important:** Consider standard Korean social etiquette (e.g., student to teacher) alongside the character's personality and the specific context.

List only the characters the protagonist speaks to.                                                                                                                                        
- For each character, specify the speech style used by the protagonist.                                                                                                                      
- The output format MUST be: `Character Name: 존댓말` or `Character Name: 반말`.    
- If there are no direct dialogues involving the protagonist, or if it's impossible to tell, respond with "N/A". 

**Text Segment to Analyze:**
---
{segment_text}
---

**Analysis of {protagonist_name}'s Speech Style:**
"""

    # --- Dynamic Style Analysis Prompts ---
    ANALYZE_NARRATIVE_DEVIATION = """
You are a literary analyst. The established core narrative style for this novel is:
---
{core_narrative_style}
---

Your task is to analyze the following text **segment** to see if it contains any parts that deviate from the core style.
This is just a piece of the full text, so focus on clear structural changes **within the segment**.

**Consider looking for:**
- A letter, diary entry, or poem that starts *within* this segment.
- A dream sequence with a distinctly different tone.
- A direct quote from another source.

**Instructions:**
- If a clear deviation exists, **describe the deviation AND specify where it starts** (e.g., "A letter begins with the line 'My Dearest,'. It should be translated in a more formal style.", "A dream sequence starts here, use a hazy and surreal tone.").
- If there is no deviation, please respond with "N/A".

**Text Segment to Analyze:**
---
{segment_text}
---

**Analysis of Style Deviation:**
"""

    # --- Translation Engine Prompts ---

    DEFINE_NARRATIVE_STYLE = """
You are a master literary analyst. Your task is to analyze the provided text and define its core narrative style for Korean translation by filling out the following report.
Your suggestions should be concise and use the specified terms.

**Analysis Report Template:**
1.  **Narrative Perspective:** (Suggest one: 1st-person, 3rd-person)
2.  **Primary Speech Level:** (Suggest the most fitting: 해라체, 해요체, 하오체, 하십시오체, 해체 etc.)
3.  **Tone (Written/Spoken):** (Suggest one: 문어체 (Literary/Written), 구어체 (Colloquial/Spoken))

**Sample Text:**
---
{sample_text}
---

**Instructions:**
Fill out the report based on your analysis of the sample text.

**Analysis Report:**
"""

    MAIN_TRANSLATION = """
You are a master translator specializing in literature. Your task is to translate the following text segment into Korean.
Please follow these guidelines to ensure consistency and quality.

**GUIDELINE 1: Core Narrative Style (기본 서술)**
- The core narrative style for this novel is defined below. This is the default style you need to follow for standard narration.
---
{core_narrative_style}
---

**GUIDELINE 2: Segment-Specific Style Deviation (세그먼트 내 예외 스타일)**
- **Please pay close attention to this guideline for this specific segment.**
- An analysis suggests this segment may contain a special style. You should prioritize the following instruction.
- If the instruction is "N/A", this guideline2 MUST be ignored.
- **Deviation Instruction:** {style_deviation_info}

**GUIDELINE 3: Glossary (용어집)**
- For consistency, please use these exact Korean translations for all terms in this list.
{glossary_terms}

**GUIDELINE 4: Protagonist's Dialogue (주인공 대화)**
- The protagonist's speech should generally follow these established styles.
- However, you have the autonomy to deviate if the immediate context (e.g., a moment of extreme anger, intimacy, or sarcasm) makes the established style unnatural.
{character_speech_styles}

**GUIDELINE 5: Other Characters' Dialogue (기타 인물 대화)**
- For all other characters, or if a specific interaction is not in the list above, please translate their dialogue naturally based on the context of the scene.

**GUIDELINE 6: Context is Key**
- Use the previous sentences for immediate context and style continuity.
- **Previous English Sentence:** {prev_segment_en}
- **Previous Korean Translation:** {prev_segment_ko}
- Your new translation should flow naturally from the previous Korean translation.

---
**Translate the following text into Korean, adhering to the guidelines above:**
---
{source_segment}
"""