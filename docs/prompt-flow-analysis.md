# Prompt Flow Analysis: Context-Aware Translation System

## Executive Summary

The Context-Aware Translation System uses a sophisticated prompt orchestration architecture that manages AI interactions across multiple tasks: translation, validation, post-editing, and illustration generation. All prompts are centrally defined in `prompts.yaml` and dynamically enriched with context as they flow through the pipeline.

## 1. Prompt Architecture Overview

### 1.1 Central Management System

```
core/prompts/
├── prompts.yaml          # Single source of truth for all prompt templates
├── manager.py            # Loads and distributes prompts to components
├── builder.py            # Constructs final prompts with context injection
└── sanitizer.py          # Cleans and validates prompt content
```

**Key Design Principles:**
- **Single Source of Truth**: All prompt templates defined in `prompts.yaml`
- **Lazy Loading**: Prompts loaded once at class level by `PromptManager`
- **Dynamic Composition**: Context injected at runtime via `PromptBuilder`
- **Separation of Concerns**: Templates separate from execution logic

### 1.2 PromptManager Class

The `PromptManager` serves as the central distribution hub:

```python
# core/prompts/manager.py
class PromptManager:
    # Static loading at class level
    _prompts = yaml.safe_load("prompts.yaml")

    # Exposed as class attributes
    MAIN_TRANSLATION = _prompts["translation"]["main"]
    VALIDATION_STRUCTURED_COMPREHENSIVE = _prompts["validation"]["structured_comprehensive"]
    # ... etc
```

## 2. Prompt Categories and Their Purposes

### 2.1 Translation Prompts

| Prompt | Purpose | Key Context Variables |
|--------|---------|----------------------|
| `translation.main` | Primary translation prompt | `{core_narrative_style}`, `{glossary_terms}`, `{character_speech_styles}`, `{source_segment}` |
| `translation.soft_retry` | Fallback for content policy violations | Simplified context without potentially problematic content |

### 2.2 Context Analysis Prompts

| Prompt | Purpose | Output Format |
|--------|---------|---------------|
| `world_atmosphere.analyze` | Extract world-building & atmospheric elements | Structured JSON (WorldAtmosphereAnalysis schema) |
| `style_analysis.define_narrative_style` | Establish core narrative voice | Text description |
| `style_analysis.narrative_deviation` | Detect style changes in segments | Structured JSON (StyleDeviation schema) |

### 2.3 Glossary Management Prompts

| Prompt | Purpose | Processing |
|--------|---------|------------|
| `glossary.extract_nouns` | Identify proper nouns from text | Comma-separated list |
| `glossary.translate_terms` | Provide consistent Korean translations | Key-value pairs |

### 2.4 Character Analysis Prompts

| Prompt | Purpose | Output |
|--------|---------|--------|
| `character_style.analyze_dialogue` | Determine speech formality levels | Character: Speech Style mapping |

### 2.5 Quality Assurance Prompts

| Prompt | Purpose | Response Format |
|--------|---------|-----------------|
| `validation.structured_comprehensive` | Full quality check | Structured JSON (ValidationResult schema) |
| `validation.structured_quick` | Quick validation (30% sample) | Structured JSON (ValidationResult schema) |
| `post_edit.correction` | Fix identified issues | Corrected Korean text |

### 2.6 Illustration Prompts

| Prompt | Purpose | Usage |
|--------|---------|-------|
| `illustration.analyze_visual_elements` | Extract visual scene details | Structured JSON (VisualElements schema) |
| `illustration.generate_illustration_prompt` | Create image generation prompt | Cinematic prompt text for Gemini 2.5 Flash |

## 3. Data Flow Through Major Tasks

### 3.1 Translation Pipeline Flow

```
Document Input
    ↓
[1. Style Analysis]
    - Prompt: style_analysis.define_narrative_style
    - Output: Core narrative style description
    ↓
For Each Segment:
    ↓
[2. Dynamic Context Building]
    ├─[2a. Glossary Update]
    │   ├─ Prompt: glossary.extract_nouns
    │   └─ Prompt: glossary.translate_terms
    ├─[2b. Character Style Update]
    │   └─ Prompt: character_style.analyze_dialogue
    └─[2c. Style Deviation Check]
        └─ Prompt: style_analysis.narrative_deviation
    ↓
[3. Translation]
    - Prompt: translation.main (enriched with all context)
    - Fallback: translation.soft_retry (on content policy violation)
    ↓
[4. Optional Illustration]
    ├─ (On-demand) Prompt: world_atmosphere.analyze – scene snapshot used exclusively for illustration context
    ├─ Prompt: illustration.analyze_visual_elements
    └─ Prompt: illustration.generate_illustration_prompt
    ↓
Output: Translated Segment + Optional Illustration
```

### 3.2 Validation Flow

```
Translated Document
    ↓
For Each Segment (or sample):
    ↓
[1. Validation Check]
    - Prompt: validation.structured_comprehensive/quick
    - Context: Source, Translation, Glossary
    - Output: Structured JSON with issues
    ↓
[2. Issue Aggregation]
    - Categorize by dimension and severity
    - Generate validation report
    ↓
Output: validation_report.json
```

### 3.3 Post-Edit Flow

```
Validation Report
    ↓
[1. Issue Selection]
    - Filter segments needing correction
    - Apply user selections/modifications
    ↓
For Each Problematic Segment:
    ↓
[2. Generate Correction]
    - Prompt: post_edit.correction
    - Context: Source, Current Translation, Issues, Glossary
    - Output: Corrected Korean text
    ↓
[3. Logging]
    - Record changes and rationale
    ↓
Output: Post-edited Document + Change Log
```

## 4. Context Enrichment Process

### 4.1 Progressive Context Accumulation

Each segment's translation prompt receives cumulative context:

1. **Static Context** (Document-level):
   - Core narrative style
   - Protagonist name
   - Initial glossary (user-provided)

2. **Dynamic Context** (Segment-level):
   - Updated glossary (accumulated from previous segments)
   - Character speech styles (accumulated)
   - Style deviation for current segment
   - World/atmosphere analysis for current segment

3. **Immediate Context**:
   - Previous segment source (last 1500 chars)
   - Previous segment translation (last 500 chars)

### 4.2 Context Injection via PromptBuilder

```python
# core/prompts/builder.py
class PromptBuilder:
    def build_translation_prompt(self, ...):
        context_data = {
            "core_narrative_style": core_narrative_style,
            "style_deviation_info": style_deviation_info,
            "glossary_terms": glossary_string,
            "character_speech_styles": character_styles_string,
            "prev_segment_source": prev_segment_source,
            "prev_segment_ko": prev_segment_ko,
            "source_segment": source_segment,
            "protagonist_name": protagonist_name,
        }
        return self.template.format(**context_data)
```

### 4.3 World & Atmosphere Integration

The world/atmosphere analysis enriches prompts with:
- **Physical Setting**: Location, architecture, technology level
- **Atmospheric Qualities**: Mood, tension, sensory details
- **Visual Mood**: Lighting, colors, weather
- **Cultural Context**: Social dynamics, customs
- **Narrative Elements**: Focus, dramatic weight, symbolism

This context flows into:
1. Translation prompts (for word choice and tone)
2. Illustration prompts (for scene visualization)

## 5. Structured Output Integration

### 5.1 Schema-Driven Responses

Several prompts use structured output for deterministic JSON:

```python
# Example: World Atmosphere Analysis
schema = make_world_atmosphere_schema()  # Generates JSON Schema
response = model.generate_structured(prompt, schema)
world_atmosphere = parse_world_atmosphere_response(response)
```

### 5.2 Structured Output Prompts

| Prompt | Schema | Benefit |
|--------|--------|---------|
| `world_atmosphere.analyze` | WorldAtmosphereAnalysis | Consistent context extraction |
| `style_analysis.narrative_deviation` | StyleDeviation | Deterministic style detection |
| `validation.structured_*` | ValidationResult | Machine-readable issue format |
| `illustration.analyze_visual_elements` | VisualElements | Systematic scene analysis |

## 6. Error Handling and Fallbacks

### 6.1 Content Policy Violations

```
Primary Prompt Fails (ProhibitedException)
    ↓
[Fallback Strategy]
├─ Translation: Use soft_retry prompt
├─ Analysis: Return "N/A" or None
└─ Log to: logs/jobs/{job_id}/prohibited_content/
```

### 6.2 API Failures

- Exponential backoff retry logic
- Graceful degradation (skip optional features)
- Comprehensive error logging

## 7. Prompt Logging and Debugging

### 7.1 Log Locations

```
logs/jobs/{job_id}/
├── prompts/
│   ├── debug_prompts.txt         # All prompts sent to AI
│   ├── translation_prompts.txt   # Translation-specific prompts
│   └── illustration_prompts.txt  # Illustration generation prompts
├── context/
│   └── context_log.txt          # Context data for each segment
├── validation/
│   └── validation_report.json   # Structured validation results
└── postedit/
    └── postedit_changes.json    # Post-edit modifications
```

### 7.2 Debug Output Example

```
--- PROMPT FOR SEGMENT 1 ---
You are an expert literary translator...

**World & Atmosphere Context:**
- Setting: Gregor Samsa's bedroom
- Atmosphere: Anxiety, confusion, helplessness...
- Visual: Dull, overcast morning light...
- Focus: Gregor Samsa's immediate physical transformation...

**GUIDELINE 3: Glossary (용어집)**
- Gregor Samsa: 그레고르 잠자
- Samsa: 잠자
...
```

## 8. Key Implementation Files

### 8.1 Core Components

| File | Role | Key Functions |
|------|------|---------------|
| `core/prompts/prompts.yaml` | Prompt templates | All prompt definitions |
| `core/prompts/manager.py` | Distribution | Load and expose prompts |
| `core/prompts/builder.py` | Composition | Inject context into templates |
| `core/config/builder.py` | Context orchestration | Coordinate all analysis managers |
| `core/translation/translation_pipeline.py` | Main workflow | Orchestrate entire process |

### 8.2 Specialized Handlers

| Component | File | Prompts Used |
|-----------|------|--------------|
| Glossary | `core/config/glossary.py` | `extract_nouns`, `translate_terms` |
| Character | `core/config/character_style.py` | `analyze_dialogue` |
| Style | `core/translation/style_analyzer.py` | `define_narrative_style`, `narrative_deviation` |
| Validation | `core/translation/validator.py` | `structured_comprehensive`, `structured_quick` |
| Post-Edit | `core/translation/post_editor.py` | `correction` |
| Illustration | `core/translation/illustration_generator.py` | `analyze_visual_elements`, `generate_illustration_prompt` |

## 9. Performance Considerations

### 9.1 Prompt Optimization

- **Context Filtering**: Only include relevant glossary terms for each segment
- **Lazy Loading**: Prompts loaded once at module import
- **Caching**: World/atmosphere analysis results cached per segment
- **Batching**: Multiple analyses can run in parallel

### 9.2 Token Management

- Segment size carefully managed (~2000-3000 tokens)
- Previous context limited (1500 chars source, 500 chars translation)
- Glossary filtered to contextual terms only

## 10. Future Enhancements

### 10.1 Potential Improvements

1. **Prompt Versioning**: Track prompt evolution over time
2. **A/B Testing**: Compare prompt variations
3. **Dynamic Prompt Selection**: Choose prompts based on content type
4. **Prompt Compression**: Optimize token usage
5. **Multi-Model Support**: Different prompts for different AI models

### 10.2 Monitoring Opportunities

1. Track prompt effectiveness metrics
2. Analyze prompt-response patterns
3. Identify prompt optimization opportunities
4. Monitor token usage by prompt type

## Conclusion

The Context-Aware Translation System's prompt architecture demonstrates sophisticated orchestration of AI interactions. By centralizing prompt management, progressively enriching context, and leveraging structured outputs, the system achieves high-quality literary translation while maintaining consistency, preserving narrative voice, and generating contextually appropriate illustrations.

The modular design allows for easy prompt modification without code changes, while comprehensive logging enables debugging and optimization. This architecture provides a robust foundation for AI-powered translation that respects both the technical requirements and artistic nuances of literary work.

