import { ValidationCase, StructuredValidationReport, StructuredPostEditLog, PostEditSegment } from '../types/core-schemas';

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
      corrected_korean_sentence?: string;
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
        corrected_korean_sentence?: string;
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
      corrected_korean_sentence?: string;
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
    const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}/validation-report`, {
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
      },
    });

    if (!response.ok) {
      if (response.status === 404 || response.status === 400) {
        // Return null for both 404 (report not found) and 400 (validation not completed)
        return null;
      }
      throw new Error(`Failed to fetch validation report: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching validation report:', error);
    throw error;
  }
}

export async function fetchPostEditLog(jobId: string, token?: string): Promise<PostEditLog | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}/post-edit-log`, {
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
      },
    });

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
    const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}/content`, {
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
      },
    });

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
    
    const response = await fetch(url, {
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
      },
    });

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

export async function triggerValidation(
  jobId: string,
  token?: string,
  quickValidation: boolean = false,
  validationSampleRate: number = 1.0,
  modelName?: string
): Promise<void> {
  const url = `${API_BASE_URL}/api/v1/jobs/${jobId}/validation`;
  const body = {
    quick_validation: quickValidation,
    validation_sample_rate: validationSampleRate,
    model_name: modelName,
  };
  
  const headers = {
    'Authorization': token ? `Bearer ${token}` : '',
    'Content-Type': 'application/json',
  };
  
  console.log('Triggering validation:', { url, body, hasToken: !!token, authHeader: headers.Authorization?.substring(0, 30) });
  
  const response = await fetch(url, {
    method: 'PUT',
    headers,
    body: JSON.stringify(body),
  });
  
  console.log('Response status:', response.status, 'Response OK:', response.ok);

  if (!response.ok) {
    const errorText = await response.text();
    console.error('Validation error response:', errorText);
    throw new Error(`Failed to trigger validation: ${response.statusText} - ${errorText}`);
  }
  
  console.log('Validation triggered successfully');
}

export async function triggerPostEdit(
  jobId: string, 
  token?: string,
  selectedCases?: Record<number, boolean[]>,
  modelName?: string
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}/post-edit`, {
    method: 'PUT',
    headers: {
      'Authorization': token ? `Bearer ${token}` : '',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      selected_cases: selectedCases || {},
      model_name: modelName,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to trigger post-edit: ${response.statusText}`);
  }
}



// ============= Structured API Functions =============

export async function fetchStructuredValidationReport(jobId: string, token?: string): Promise<StructuredValidationReport | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}/validation-report?structured=true`, {
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
      },
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
    const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}/post-edit-log?structured=true`, {
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
      },
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

export async function fetchStructuredGlossary(jobId: string, token?: string): Promise<import('../types/core-schemas').GlossaryAnalysisResponse | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}/glossary?structured=true`, {
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
      },
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
