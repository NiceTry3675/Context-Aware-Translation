/**
 * TypeScript interfaces matching core Python schemas
 * These types correspond to the structured output schemas from core/schemas
 */

// ============= Glossary Schemas =============

export interface TranslatedTerm {
  source: string;
  korean: string;
}

export interface ExtractedTerms {
  terms: string[];
}

export interface TranslatedTerms {
  translations: TranslatedTerm[];
}

// ============= Character Style Schemas =============

export interface CharacterInteraction {
  speaker: string;
  text: string;
  unique_patterns: string[];
}

export interface CharacterInteraction {
  character_name: string;
  speech_style: '반말' | '해요체' | '하십시오체';
}

export interface DialogueAnalysisResult {
  protagonist_name: string;
  interactions: CharacterInteraction[];
  has_dialogue: boolean;
}

// ============= Narrative Style Schemas =============

export interface NarrationStyle {
  description: string;
  ending_style: string;
}

export interface NarrativeStyleDefinition {
  protagonist_name: string;
  narration_style: NarrationStyle;
  core_tone_keywords: string[];
  golden_rule: string;
}

export interface StyleDeviation {
  has_deviation: boolean;
  starts_with?: string | null;
  instruction?: string | null;
}

// ============= Validation Schemas =============

export interface ValidationCase {
  current_korean_sentence: string;
  problematic_source_sentence: string;
  reason: string;
  dimension: 'completeness' | 'accuracy' | 'addition' | 'name_consistency' | 'dialogue_style' | 'flow' | 'other';
  severity: '1' | '2' | '3';  // 1=minor, 2=major, 3=critical
  corrected_korean_sentence?: string;
  tags?: string[];
}

export interface ValidationResponse {
  cases: ValidationCase[];
}

// ============= API Response Schemas =============

export interface StyleAnalysisResponse {
  protagonist_name: string;
  narration_style_endings: string;
  tone_keywords: string;
  stylistic_rule: string;
  narrative_style?: NarrativeStyleDefinition;
  character_styles?: DialogueAnalysisResult[];
}

export interface GlossaryAnalysisResponse {
  glossary: TranslatedTerm[];
  extracted_terms?: ExtractedTerms;
  translated_terms?: TranslatedTerms;
}

export interface StructuredValidationReport {
  summary: {
    total_segments: number;
    validated_segments: number;
    passed: number;
    failed: number;
    pass_rate: number;
    case_counts_by_severity: { '1': number; '2': number; '3': number };
    case_counts_by_dimension: Record<string, number>;
    segments_with_cases: number[];
  };
  detailed_results: Array<{
    segment_index: number;
    status: 'PASS' | 'FAIL';
    structured_cases?: ValidationCase[];
    source_preview: string;
    translated_preview: string;
  }>;
  validation_response?: ValidationResponse;
}

export interface PostEditSegment {
  segment_index: number;
  was_edited: boolean;
  source_text: string;
  original_translation: string;
  edited_translation: string;
  validation_status: string;
  structured_cases?: ValidationCase[];
  changes_made?: {
    text_changed?: boolean;
  };
}

export interface StructuredPostEditLog {
  summary: {
    segments_edited: number;
    total_segments: number;
    edit_percentage: number;
  };
  segments: PostEditSegment[];
  validation_cases_fixed?: ValidationCase[];
}

// ============= Translation Job with Structured Data =============

export interface TranslationJobWithStructuredData {
  id: number;
  filename: string;
  status: string;
  progress: number;
  segment_size: number;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
  owner_id: number | null;
  
  // Validation fields
  validation_enabled: boolean | null;
  validation_status: string | null;
  validation_progress: number | null;
  validation_sample_rate: number | null;
  quick_validation: boolean | null;
  validation_completed_at: string | null;
  
  // Post-edit fields
  post_edit_enabled: boolean | null;
  post_edit_status: string | null;
  post_edit_progress: number | null;
  post_edit_completed_at: string | null;
  
  // Structured glossary data
  final_glossary?: Record<string, any>;
  structured_glossary?: TranslatedTerms;
}