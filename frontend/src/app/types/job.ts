export interface Job {
  id: number;
  filename: string;
  status: string;
  progress: number;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
  validation_enabled: boolean;
  validation_status: string | null;
  validation_progress: number;
  validation_sample_rate: number;
  quick_validation: boolean;
  validation_completed_at: string | null;
  post_edit_enabled: boolean;
  post_edit_status: string | null;
  post_edit_progress: number;
  post_edit_completed_at: string | null;
}

export type JobStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
export type ValidationStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';
export type PostEditStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';