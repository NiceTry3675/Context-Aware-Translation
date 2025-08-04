export interface StyleData {
  protagonist_name: string;
  narration_style_endings: string;
  tone_keywords: string;
  stylistic_rule: string;
}

export interface GlossaryTerm {
  term: string;
  translation: string;
}

export interface TranslationSettings {
  segmentSize: number;
  enableValidation: boolean;
  quickValidation: boolean;
  validationSampleRate: number;
  enablePostEdit: boolean;
}

export interface FileAnalysisResult {
  styleData: StyleData | null;
  glossaryData: GlossaryTerm[];
  error: string | null;
}

export interface TranslationJobRequest {
  file: File;
  apiKey: string;
  modelName: string;
  styleData: StyleData;
  glossaryData?: GlossaryTerm[];
  settings: TranslationSettings;
}