/**
 * UI-specific type definitions that don't come from the API
 * These are local types used for frontend state management and components
 */

// Re-export API types that are commonly used
export type { Job } from '@/lib/api';

// UI-specific style configuration types
export interface StyleData {
  protagonist_name?: string;
  narration_style?: {
    description?: string;
    ending_style?: string;
  };
  core_tone_keywords?: string[];
  golden_rule?: string;
  character_styles?: Record<string, {
    speech_level: string;
    honorifics?: string;
    special_traits?: string[];
  }>;
}

// Glossary term for UI display
export interface GlossaryTerm {
  source: string;
  korean: string;
  category?: 'character' | 'place' | 'item' | 'other';
  note?: string;
}

// Translation settings for advanced configuration
export interface TranslationSettings {
  model_name: string;
  temperature?: number;
  top_p?: number;
  top_k?: number;
  custom_prompt?: string;
  chunk_size?: number;
  segmentSize: number;  // UI display name for chunk_size
  context_window?: number;
  thinkingLevel?: 'minimal' | 'low' | 'medium' | 'high';
  turboMode: boolean;
  enableValidation: boolean;  // UI property names
  validationSampleRate: number;
  quickValidation: boolean;
  enablePostEdit: boolean;
  // Illustration settings
  enableIllustrations: boolean;
  illustrationStyle?: 'realistic' | 'artistic' | 'watercolor' | 'digital_art' | 'sketch' | 'anime' | 'vintage' | 'minimalist';
  maxIllustrations?: number;
  illustrationsPerSegment?: number;
}

// Form data for new translation requests
export interface TranslationFormData {
  file: File | null;
  fileName?: string;
  apiKey: string;
  modelName: string;
  styleData?: StyleData;
  glossaryTerms?: GlossaryTerm[];
  advancedSettings?: TranslationSettings;
}

// Canvas state types
export interface CanvasState {
  activeJobId: string | null;
  isFullscreen: boolean;
  activeTab: 'translation' | 'validation' | 'postEdit';
  isLoading: boolean;
  error: string | null;
}

// Validation UI types (these wrap the core schemas)
export interface ValidationIssue {
  current_korean_sentence: string;
  problematic_source_sentence: string;
  reason: string;
  dimension: 'completeness' | 'accuracy' | 'addition' | 'name_consistency' | 'dialogue_style' | 'flow' | 'other';
  severity: '1' | '2' | '3';
  recommend_korean_sentence: string;
  tags?: string[];
}

export interface ValidationReport {
  job_id: number;
  validation_status: 'pending' | 'running' | 'completed' | 'failed';
  validation_issues?: ValidationIssue[];
  validation_error?: string;
  quick_validation?: boolean;
  validation_sample_rate?: number;
}

// Post-edit UI types
export interface PostEditSegment {
  segment_index: number;
  source_text: string;
  original_translation: string;
  edited_translation?: string;
  was_edited: boolean;
  validation_issues?: ValidationIssue[];
}

export interface PostEditLog {
  job_id: number;
  segments: PostEditSegment[];
  total_segments: number;
  edited_segments: number;
  timestamp: string;
}

// Helper type utilities
export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

// UI display helpers
export interface JobStatusDisplay {
  label: string;
  color: 'default' | 'primary' | 'secondary' | 'error' | 'warning' | 'info' | 'success';
  icon?: string;
}

// Re-export commonly used core schemas if needed
export type {
  ValidationCase,
  ValidationResponse,
  CharacterInteraction,
  DialogueAnalysisResult,
  NarrativeStyleDefinition,
  StyleDeviation
} from '@/core-schemas';
