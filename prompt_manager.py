class PromptManager:
    # Prompts for dynamic_config_builder.py
    EXTRACT_KEY_TERMS = """
Your task is to act as a data extractor for a literary translation project. From the text segment below, identify and extract key terms that are crucial for maintaining consistency.

**Focus on:**
- Proper Nouns: Names of people, specific locations, or organizations (e.g., "Gregor Samsa", "the Ministry").
- Unique Concepts or Objects: Items or ideas central to the plot or setting (e.g., "the Ungeziefer", "the golden apple").
- Important Recurring Roles: Titles or roles that appear frequently (e.g., "the chief clerk", "the boarder").

**Exclude:**
- Common, non-specific nouns (e.g., "bed", "door", "train").
- Temporary or generic characters or objects.

Do not translate or explain the terms. Provide a comma-separated list.

**Text Segment to Analyze:**
---
{segment_text}
---

**Comma-separated list of key terms:**
"""

    TRANSLATE_KEY_TERMS = """
You are the lead translator creating a definitive glossary for your team. For the following key terms, provide a single, contextually appropriate Korean translation that will be used consistently throughout the novel.

The format MUST be a simple list, with each term on a new line:
`Key Term: Korean Translation`

**Key Terms to Translate:**
{key_terms}

**Output:**
"""

    ANALYZE_STYLE_AND_TONE = """
You are a literary analyst providing a style guide for a translator. Analyze the text segment below and provide brief, actionable guidelines for the Korean translation.

**Text Segment:**
---
{segment_text}
---

**Translation Guidelines:**
- **Overall Tone & Mood:** (Describe the feeling of the text. E.g., "Detached and observational, creating a sense of unease," or "Fast-paced and anxious.")
- **Sentence Structure:** (Suggest a Korean sentence style. E.g., "Use longer, descriptive sentences (문어체) to match the author's prose," or "Employ short, simple sentences for clarity.")
- **Vocabulary:** (Suggest word choice. E.g., "Prefer formal, slightly archaic vocabulary," or "Use modern, everyday language.")
- **Dialogue Style (if any):**
  - **[Character Name]'s Speech:** (Describe their manner of speaking and suggest a Korean speech level. E.g., "Speaks in short, panicked phrases. Use a polite but anxious 해요체.")
"""

    # Prompt for prompt_builder.py
    MAIN_TRANSLATION = """
You are a master translator entrusted with the Korean translation of a critically acclaimed English novel. Your goal is to create a translation that is not only accurate but also preserves the unique literary voice of the original author.

**TRANSLATION PROTOCOL:**
You must follow this protocol in a hierarchical manner. Adherence to this is critical.

---
### **1. Glossary Terms (Mandatory)**
You MUST use these exact translations for the following key terms. This is non-negotiable for project consistency.
{glossary_terms}

---
### **2. Dynamic Style Guide (Mandatory)**
You MUST adopt the specific style and tone described below for this segment.
{dynamic_guidelines}

---
### **3. Global Style Guide (Reference)**
This is the general style for the entire novel. Use it as a baseline.
{style_guide}

---
### **4. Immediate Context (Flow and Cohesion)**
Ensure your translation flows seamlessly from the previously translated sentence.
- **Previous English Sentence (for context):** {prev_segment_en}
- **Previous Korean Translation (your starting point):** {prev_segment_ko}

---
### **5. Source Text to Translate**
This is the segment you need to translate now.
{source_segment}

---
**YOUR TASK:**

**Step 1: Pre-translation Analysis (Internal Monologue)**
First, briefly explain how you will apply the protocol to the source text. For example: "The source text contains the term 'Chief Clerk,' which I must translate as '사무장'. The tone is observational, so I will use a formal, descriptive 문어체. The previous sentence ended in -다, so I will start this one accordingly."

**Step 2: Final Korean Translation**
Now, provide the final, polished Korean translation of the source text.

**[Pre-translation Analysis]:**
<Your brief analysis here>

**[Korean Translation]:**
<Your final translation here>
"""
