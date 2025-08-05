const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ValidationReport {
  summary: {
    total_segments: number;
    validated_segments: number;
    passed: number;
    failed: number;
    pass_rate: number;
    total_critical_issues: number;
    total_missing_content: number;
    total_added_content: number;
    total_name_inconsistencies: number;
    segments_with_issues: number[];
  };
  detailed_results: Array<{
    segment_index: number;
    status: 'PASS' | 'FAIL';
    critical_issues: string[];
    minor_issues: string[];
    missing_content: string[];
    added_content: string[];
    name_inconsistencies: string[];
    source_preview: string;
    translated_preview: string;
  }>;
}

export interface PostEditLog {
  summary: {
    segments_edited: number;
    total_segments: number;
    edit_percentage: number;
    issues_addressed: {
      critical: number;
      missing_content: number;
      added_content: number;
      name_inconsistencies: number;
    };
  };
  segments: Array<{
    segment_index: number;
    was_edited: boolean;
    source_text: string;
    original_translation: string;
    edited_translation: string;
    validation_status: string;
    issues: {
      critical: string[];
      missing_content: string[];
      added_content: string[];
      name_inconsistencies: string[];
    };
    changes_made: {
      text_changed: boolean;
      critical_fixed: boolean;
      missing_content_fixed: boolean;
      added_content_fixed: boolean;
      name_inconsistencies_fixed: boolean;
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
      if (response.status === 404) {
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
      if (response.status === 404) {
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

export async function triggerValidation(
  jobId: string,
  token?: string,
  quickValidation: boolean = false,
  validationSampleRate: number = 1.0
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}/validation`, {
    method: 'PUT',
    headers: {
      'Authorization': token ? `Bearer ${token}` : '',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      quick_validation: quickValidation,
      validation_sample_rate: validationSampleRate,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to trigger validation: ${response.statusText}`);
  }
}

export async function triggerPostEdit(
  jobId: string, 
  token?: string,
  selectedIssueTypes?: {
    critical_issues: boolean;
    missing_content: boolean;
    added_content: boolean;
    name_inconsistencies: boolean;
  },
  selectedIssues?: {
    [segmentIndex: number]: {
      [issueType: string]: boolean[]
    }
  }
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}/post-edit`, {
    method: 'PUT',
    headers: {
      'Authorization': token ? `Bearer ${token}` : '',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      selected_issue_types: selectedIssueTypes || {
        critical_issues: true,
        missing_content: true,
        added_content: true,
        name_inconsistencies: true,
      },
      selected_issues: selectedIssues
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to trigger post-edit: ${response.statusText}`);
  }
}

