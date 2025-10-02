import { ValidationCase } from '@/core-schemas';
import type { components } from '@/types/api';
import { fetchWithRetry } from './fetchWithRetry';

// Type aliases for generated API types - exported for use in components
export type GlossaryAnalysisResponse = components['schemas']['GlossaryAnalysisResponse'];
export type TranslatedTerm = components['schemas']['TranslatedTerm'];

// Helper function to build auth headers conditionally
function buildAuthHeaders(token?: string): Record<string, string> {
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

// Local type definitions for structured reports (not yet in OpenAPI schema)
// TODO: These should be generated from backend/schemas.py once they're exported
export interface StructuredValidationReport {
  job_id: number;
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
  }>;
}

export interface PostEditSegment {
  segment_index: number;
  source_text: string;
  original_translation: string;
  edited_translation?: string;
  was_edited: boolean;
  validation_issues?: ValidationCase[];
}

export interface StructuredPostEditLog {
  job_id: number;
  segments: PostEditSegment[];
  total_segments: number;
  edited_segments: number;
  timestamp: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ValidationReport {
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
    structured_cases?: Array<{
      current_korean_sentence: string;
      problematic_source_sentence: string;
      reason: string;
      recommend_korean_sentence: string;
      dimension?: string;
      severity?: number;
      tags?: string[];
    }>;
    source_preview: string;
    translated_preview: string;
    // Some reports may nest results here; keep it permissive for parsing
    validation_result?: {
      structured_cases?: Array<{
        current_korean_sentence: string;
        problematic_source_sentence: string;
        reason: string;
        recommend_korean_sentence: string;
        dimension?: string;
        severity?: number;
        tags?: string[];
      }>;
    };
  }>;
}

export interface PostEditLog {
  summary: {
    segments_edited: number;
    total_segments: number;
    edit_percentage: number;
  };
  segments: Array<{
    segment_index: number;
    was_edited: boolean;
    source_text: string;
    original_translation: string;
    edited_translation: string;
    validation_status: string;
    structured_cases?: Array<{
      current_korean_sentence: string;
      problematic_source_sentence: string;
      reason: string;
      recommend_korean_sentence: string;
      dimension?: string;
      severity?: number;
      tags?: string[];
    }>;
    changes_made?: {
      text_changed?: boolean;
    };
  }>;
}

export async function fetchValidationReport(jobId: string, token?: string): Promise<ValidationReport | null> {
  try {
    console.log(`[fetchValidationReport] Fetching validation report for job ${jobId}`);
    const response = await fetchWithRetry(`${API_BASE_URL}/api/v1/validation/${jobId}/status`, {
      headers: buildAuthHeaders(token),
    }, { retries: 3, timeoutMs: 10000 });

    console.log(`[fetchValidationReport] Response status: ${response.status}`);

    if (!response.ok) {
      if (response.status === 404 || response.status === 400) {
        const errorData = await response.json();
        console.log(`[fetchValidationReport] Error response:`, errorData);
        // Return null for both 404 (report not found) and 400 (validation not completed)
        return null;
      }
      throw new Error(`Failed to fetch validation report: ${response.statusText}`);
    }

    const data = await response.json();
    console.log(`[fetchValidationReport] Response data:`, data);
    
    // Check if this is a "not_validated" response
    if (data.status === 'not_validated') {
      console.log(`[fetchValidationReport] Job not validated, returning null`);
      return null;
    }
    
    return data;
  } catch (error) {
    console.error('Error fetching validation report:', error);
    throw error;
  }
}

export async function fetchPostEditLog(jobId: string, token?: string): Promise<PostEditLog | null> {
  try {
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetchWithRetry(`${API_BASE_URL}/api/v1/post-edit/${jobId}/status`, {
      headers,
    }, { retries: 3, timeoutMs: 10000 });

    if (!response.ok) {
      if (response.status === 404 || response.status === 400) {
        // Return null for both 404 (log not found) and 400 (post-edit not completed)
        return null;
      }
      throw new Error(`Failed to fetch post-edit log: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching post-edit log:', error);
    throw error;
  }
}

export interface IllustrationStatus {
  job_id: number;
  status: string;
  progress: number | null;
  count: number;
  enabled: boolean;
  directory: string | null;
  has_character_base: boolean;
}

export async function fetchJobTasks(jobId: number, token?: string): Promise<components['schemas']['TaskExecutionResponse'][]> {
  const response = await fetchWithRetry(`${API_BASE_URL}/api/v1/tasks/job/${jobId}/tasks`, {
    headers: buildAuthHeaders(token),
  }, { retries: 3, timeoutMs: 8000 });
  if (!response.ok) {
    throw new Error(`Failed to fetch job tasks: ${response.statusText}`);
  }
  return await response.json();
}

export async function fetchIllustrationStatus(jobId: string, token?: string): Promise<IllustrationStatus | null> {
  try {
    const headers = token ? buildAuthHeaders(token) : undefined;
    const response = await fetchWithRetry(
      `${API_BASE_URL}/api/v1/illustrations/${jobId}/status`,
      headers ? { headers } : undefined,
      { retries: 1, timeoutMs: 8000 }
    );

    if (!response.ok) {
      if (response.status === 404 || response.status === 401) {
        return null;
      }
      throw new Error(`Failed to fetch illustration status: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching illustration status:', error);
    throw error;
  }
}

export interface TranslationContent {
  job_id: number;
  filename: string;
  content: string;
  source_content?: string;
  completed_at: string | null;
}

export interface TranslationSegments {
  job_id: number;
  filename: string;
  segments: Array<{
    segment_index: number;
    source_text: string;
    translated_text: string;
  }>;
  total_segments: number;
  completed_at: string | null;
  message?: string; // Optional message for jobs without segments
  has_more?: boolean; // For pagination
  offset?: number; // For pagination
  limit?: number; // For pagination
}

export async function fetchTranslationContent(jobId: string, token?: string): Promise<TranslationContent | null> {
  try {
    const response = await fetchWithRetry(`${API_BASE_URL}/api/v1/jobs/${jobId}/content`, {
      headers: buildAuthHeaders(token),
    }, { retries: 3, timeoutMs: 10000 });

    if (!response.ok) {
      if (response.status === 404 || response.status === 400) {
        return null;
      }
      throw new Error(`Failed to fetch translation content: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching translation content:', error);
    return null;
  }
}

export async function fetchTranslationSegments(
  jobId: string, 
  token?: string,
  offset?: number,
  limit?: number
): Promise<TranslationSegments | null> {
  try {
    const params = new URLSearchParams();
    if (offset !== undefined) params.append('offset', offset.toString());
    if (limit !== undefined) params.append('limit', limit.toString());
    
    const url = `${API_BASE_URL}/api/v1/jobs/${jobId}/segments${params.toString() ? '?' + params.toString() : ''}`;
    
    const response = await fetchWithRetry(url, {
      headers: buildAuthHeaders(token),
    }, { retries: 3, timeoutMs: 12000 });

    if (!response.ok) {
      if (response.status === 404 || response.status === 400) {
        // Return null for error statuses
        return null;
      }
      throw new Error(`Failed to fetch translation segments: ${response.statusText}`);
    }

    const data = await response.json();
    
    // Even if segments are empty, return the data structure
    // This allows the UI to handle empty segments appropriately
    return data;
  } catch (error) {
    console.error('Error fetching translation segments:', error);
    return null;
  }
}

export async function triggerValidation({
  jobId,
  token,
  body,
  apiProvider,
  apiKey,
  providerConfig,
}: {
  jobId: string;
  token?: string;
  body: components['schemas']['ValidationRequest'];
} & CredentialledParams): Promise<void> {
  const url = `${API_BASE_URL}/api/v1/jobs/${jobId}/validation`;
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  console.log('Triggering validation:', { url, body, hasToken: !!token });
  
  const response = await fetch(url, {
    method: 'PUT',
    headers,
    body: JSON.stringify({
      ...body,
      api_provider: apiProvider,
      api_key: apiProvider === 'vertex' ? '' : apiKey,
      ...(apiProvider === 'vertex' && providerConfig ? { provider_config: providerConfig } : {}),
    }),
  });
  
  console.log('Response status:', response.status, 'Response OK:', response.ok);

  if (!response.ok) {
    const errorText = await response.text();
    console.error('Validation error response:', errorText);
    throw new Error(`Failed to trigger validation: ${response.statusText} - ${errorText}`);
  }
  
  console.log('Validation triggered successfully');
}

export async function triggerPostEdit({
  jobId,
  token,
  body,
  apiProvider,
  apiKey,
  providerConfig,
}: {
  jobId: string;
  token?: string;
  body: components['schemas']['PostEditRequest'];
} & CredentialledParams): Promise<void> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetch(`${API_BASE_URL}/api/v1/post-edit/${jobId}`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      ...(body as any),
      api_provider: apiProvider,
      api_key: apiProvider === 'vertex' ? '' : apiKey,
      ...(apiProvider === 'vertex' && providerConfig ? { provider_config: providerConfig } : {}),
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Failed to trigger post-edit: ${response.status} ${text}`);
  }
}

export interface IllustrationGenerationParams {
  jobId: string;
  token?: string;
  apiProvider: 'gemini' | 'vertex' | 'openrouter';
  apiKey?: string;
  providerConfig?: string;
  config?: {
    style?: string;
    style_hints?: string;
    prompt_model_name?: string;
    min_segment_length?: number;
    skip_dialogue_heavy?: boolean;
    cache_enabled?: boolean;
  };
  maxIllustrations?: number;
  currentIllustrationsData?: any[];
  currentIllustrationsCount?: number;
}

export async function triggerIllustrationGeneration({
  jobId,
  token,
  apiProvider,
  apiKey,
  providerConfig,
  config,
  maxIllustrations,
  currentIllustrationsData = [],
  currentIllustrationsCount = 0,
}: IllustrationGenerationParams): Promise<void> {
  const payload: Record<string, unknown> = {
    api_provider: apiProvider,
    api_key: apiProvider === 'vertex' ? '' : apiKey,
    max_illustrations: maxIllustrations ?? null,
    config: {
      enabled: true,
      style: config?.style || 'digital_art',
      style_hints: config?.style_hints || '',
      prompt_model_name: config?.prompt_model_name || null,
      segments_per_illustration: 1,
      max_illustrations: maxIllustrations ?? null,
      min_segment_length: config?.min_segment_length || 100,
      skip_dialogue_heavy: config?.skip_dialogue_heavy || false,
      cache_enabled: config?.cache_enabled !== false,
    },
  };

  if (apiProvider === 'vertex' && providerConfig) {
    payload.provider_config = providerConfig;
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/illustrations/${jobId}/generate`, {
    method: 'POST',
    headers: {
      ...buildAuthHeaders(token),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to trigger illustration generation');
  }
}

interface RegenerateIllustrationParams {
  jobId: string;
  segmentIndex: number;
  token?: string;
  customPrompt?: string;
  apiProvider?: string;
  apiKey?: string;
  providerConfig?: string;
}

export async function regenerateIllustration({
  jobId,
  segmentIndex,
  token,
  customPrompt,
  apiProvider,
  apiKey,
  providerConfig,
}: RegenerateIllustrationParams): Promise<void> {
  const payload: Record<string, unknown> = {};

  if (customPrompt) {
    payload.custom_prompt = customPrompt;
  }

  if (apiProvider) {
    payload.api_provider = apiProvider;
  }

  if (apiKey) {
    payload.api_key = apiKey;
  }

  if (providerConfig) {
    payload.provider_config = providerConfig;
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/illustrations/${jobId}/regenerate/${segmentIndex}`, {
    method: 'POST',
    headers: {
      ...buildAuthHeaders(token),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Failed to regenerate illustration for segment ${segmentIndex}`);
  }
}

interface RegenerateBaseParams {
  jobId: string;
  baseIndex: number;
  customPrompt: string;
  token?: string;
  apiProvider?: string;
  apiKey?: string;
  providerConfig?: string;
}

export async function regenerateBase({
  jobId,
  baseIndex,
  customPrompt,
  token,
  apiProvider,
  apiKey,
  providerConfig,
}: RegenerateBaseParams): Promise<void> {
  const payload: Record<string, unknown> = {
    custom_prompt: customPrompt,
  };

  // Add API credentials to payload if provided
  if (apiProvider) payload.api_provider = apiProvider;
  if (apiKey) payload.api_key = apiKey;
  if (providerConfig) payload.provider_config = providerConfig;
  if (token) payload.api_token = token;

  const response = await fetch(`${API_BASE_URL}/api/v1/illustrations/${jobId}/character/base/${baseIndex}/regenerate`, {
    method: 'POST',
    headers: {
      ...buildAuthHeaders(token),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Failed to regenerate base image ${baseIndex}`);
  }
}

// ============= Character Base API Functions =============

export interface CharacterProfileBody {
  name?: string;
  gender?: string;
  age?: string;
  hair_color?: string;
  hair_style?: string;
  eye_color?: string;
  eye_shape?: string;
  skin_tone?: string;
  body_type?: string;
  clothing?: string;
  accessories?: string;
  style?: string; // matches backend enum values
  extra_style_hints?: string;
}

interface CredentialledParams {
  apiProvider: 'gemini' | 'vertex' | 'openrouter';
  apiKey?: string;
  providerConfig?: string;
}

export async function generateCharacterBases({
  jobId,
  token,
  profile,
  referenceImage,
  apiProvider,
  apiKey,
  providerConfig,
}: {
  jobId: string;
  token?: string;
  profile: CharacterProfileBody;
  referenceImage?: File;
} & CredentialledParams): Promise<{ bases: any[]; directory?: string }> {
  // Always use FormData since backend expects it
  const form = new FormData();
  form.append('api_provider', apiProvider);
  if (apiProvider === 'vertex') {
    form.append('api_key', '');
    if (providerConfig) {
      form.append('provider_config', providerConfig);
    }
  } else {
    form.append('api_key', apiKey || '');
  }
  form.append('profile_json', JSON.stringify(profile));
  if (referenceImage) {
    form.append('reference_image', referenceImage, referenceImage.name);
  }
  const response = await fetch(`${API_BASE_URL}/api/v1/illustrations/${jobId}/character/base/generate`, {
    method: 'POST',
    headers: buildAuthHeaders(token),
    body: form,
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to generate character bases');
  }
  return await response.json();
}

export async function analyzeCharacterAppearance({
  jobId,
  token,
  protagonistName,
  apiProvider,
  apiKey,
  providerConfig,
}: {
  jobId: string;
  token?: string;
  protagonistName?: string;
} & CredentialledParams): Promise<{ prompts: string[]; protagonist_name?: string; notice?: string; sample_size?: number }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/illustrations/${jobId}/character/appearance/analyze`, {
    method: 'POST',
    headers: {
      ...buildAuthHeaders(token),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      api_provider: apiProvider,
      api_key: apiProvider === 'vertex' ? '' : apiKey,
      ...(apiProvider === 'vertex' && providerConfig ? { provider_config: providerConfig } : {}),
      protagonist_name: protagonistName,
      model_name: 'gemini-flash-latest'
    }),
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'Failed to analyze character appearance');
  }
  return await response.json();
}

export async function generateBasesFromPrompt({
  jobId,
  token,
  prompts,
  referenceImage,
  apiProvider,
  apiKey,
  providerConfig,
}: {
  jobId: string;
  token?: string;
  prompts: string[];
  referenceImage?: File;
} & CredentialledParams): Promise<{ bases: any[]; directory?: string }> {
  // Always use FormData since backend expects it
  const form = new FormData();
  form.append('api_provider', apiProvider);
  if (apiProvider === 'vertex') {
    form.append('api_key', '');
    if (providerConfig) {
      form.append('provider_config', providerConfig);
    }
  } else {
    form.append('api_key', apiKey || '');
  }
  form.append('prompts_json', JSON.stringify(prompts));
  form.append('num_variations', '3');
  if (referenceImage) {
    form.append('reference_image', referenceImage, referenceImage.name);
  }
  const response = await fetch(`${API_BASE_URL}/api/v1/illustrations/${jobId}/character/base/generate-from-prompt`, {
    method: 'POST',
    headers: buildAuthHeaders(token),
    body: form,
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'Failed to generate base from prompt');
  }
  return await response.json();
}

export async function getCharacterBases(
  jobId: string,
  token: string | undefined,
): Promise<{ profile?: CharacterProfileBody; bases: any[]; selected_index?: number; directory?: string }>{
  const response = await fetch(`${API_BASE_URL}/api/v1/illustrations/${jobId}/character/base`, {
    headers: buildAuthHeaders(token),
  });
  if (!response.ok) {
    throw new Error('Failed to fetch character bases');
  }
  return await response.json();
}

export async function selectCharacterBase(
  jobId: string,
  token: string | undefined,
  selectedIndex: number
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/illustrations/${jobId}/character/base/select`, {
    method: 'POST',
    headers: {
      ...buildAuthHeaders(token),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ selected_index: selectedIndex }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to select character base');
  }
}



// ============= Structured API Functions =============

export async function fetchStructuredValidationReport(jobId: string, token?: string): Promise<StructuredValidationReport | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/validation/${jobId}/status?structured=true`, {
      headers: buildAuthHeaders(token),
    });

    if (!response.ok) {
      if (response.status === 404 || response.status === 400) {
        return null;
      }
      throw new Error(`Failed to fetch structured validation report: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching structured validation report:', error);
    throw error;
  }
}

export async function fetchStructuredPostEditLog(jobId: string, token?: string): Promise<StructuredPostEditLog | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/post-edit/${jobId}/status?structured=true`, {
      headers: buildAuthHeaders(token),
    });

    if (!response.ok) {
      if (response.status === 404 || response.status === 400) {
        return null;
      }
      throw new Error(`Failed to fetch structured post-edit log: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching structured post-edit log:', error);
    throw error;
  }
}

export async function fetchStructuredGlossary(jobId: string, token?: string): Promise<GlossaryAnalysisResponse | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}/glossary?structured=true`, {
      headers: buildAuthHeaders(token),
    });

    if (!response.ok) {
      if (response.status === 404 || response.status === 400) {
        return null;
      }
      throw new Error(`Failed to fetch structured glossary: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching structured glossary:', error);
    throw error;
  }
}
