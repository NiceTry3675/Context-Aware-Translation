'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';
import {
  ValidationReport,
  PostEditLog,
  TranslationContent,
  fetchValidationReport,
  fetchPostEditLog,
  fetchTranslationContent,
} from '../../../utils/api';

interface UseTranslationDataProps {
  open: boolean;
  jobId: string;
  jobStatus: string;
  validationStatus?: string;
  postEditStatus?: string;
}

export function useTranslationData({
  open,
  jobId,
  jobStatus,
  validationStatus,
  postEditStatus,
}: UseTranslationDataProps) {
  const [validationReport, setValidationReport] = useState<ValidationReport | null>(null);
  const [postEditLog, setPostEditLog] = useState<PostEditLog | null>(null);
  const [translationContent, setTranslationContent] = useState<TranslationContent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIssues, setSelectedIssues] = useState<{
    [segmentIndex: number]: {
      [issueType: string]: boolean[]
    }
  }>({});
  
  const { getToken } = useAuth();

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = await getToken();
      
      // Load translation content if job is completed
      if (jobStatus === 'COMPLETED') {
        const content = await fetchTranslationContent(jobId, token || undefined);
        setTranslationContent(content);
      }
      
      // Load validation report if available
      if (validationStatus === 'COMPLETED') {
        console.log('Loading validation report for job:', jobId);
        const report = await fetchValidationReport(jobId, token || undefined);
        console.log('Validation report loaded:', report);
        
        if (report) {
          // Initialize selected issues immediately when setting the report
          const initialSelection: typeof selectedIssues = {};
          report.detailed_results.forEach((result) => {
            if (result.status === 'FAIL') {
              initialSelection[result.segment_index] = {
                critical: new Array(result.critical_issues.length).fill(true),
                missing_content: new Array(result.missing_content.length).fill(true),
                added_content: new Array(result.added_content.length).fill(true),
                name_inconsistencies: new Array(result.name_inconsistencies.length).fill(true),
                minor: new Array(result.minor_issues.length).fill(true),
              };
            }
          });
          
          setValidationReport(report);
          setSelectedIssues(initialSelection);
        }
      }
      
      // Load post-edit log if available
      if (postEditStatus === 'COMPLETED') {
        const log = await fetchPostEditLog(jobId, token || undefined);
        setPostEditLog(log);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '데이터를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  }, [jobId, jobStatus, validationStatus, postEditStatus, getToken]);

  // Load data when sidebar opens or job changes
  useEffect(() => {
    if (open && jobId) {
      loadData();
    }
  }, [open, jobId, loadData]);
  
  // Reload data when validation completes
  useEffect(() => {
    if (validationStatus === 'COMPLETED' && !validationReport) {
      loadData();
    }
  }, [validationStatus, validationReport, loadData]);

  // Helper function to get segment data
  const getSegmentData = useCallback((segmentIndex: number) => {
    // Try to get from post-edit log first (most complete data)
    if (postEditLog?.segments) {
      const segment = postEditLog.segments.find(s => s.segment_index === segmentIndex);
      if (segment) {
        return {
          sourceText: segment.source_text,
          translatedText: segment.original_translation,
          editedText: segment.edited_translation,
          wasEdited: segment.was_edited,
          issues: segment.issues,
          changes: segment.changes_made,
        };
      }
    }
    
    // Fall back to validation report
    if (validationReport?.detailed_results) {
      const result = validationReport.detailed_results.find(r => r.segment_index === segmentIndex);
      if (result) {
        return {
          sourceText: result.source_preview,
          translatedText: result.translated_preview,
          issues: {
            critical: result.critical_issues,
            missingContent: result.missing_content,
            addedContent: result.added_content,
            nameInconsistencies: result.name_inconsistencies,
            minor: result.minor_issues,
          },
        };
      }
    }
    
    return null;
  }, [validationReport, postEditLog]);
  
  // Get total number of segments
  const totalSegments = postEditLog?.segments?.length || 
                       validationReport?.detailed_results?.length || 
                       0;

  return {
    validationReport,
    postEditLog,
    translationContent,
    loading,
    error,
    selectedIssues,
    setSelectedIssues,
    loadData,
    getSegmentData,
    totalSegments,
  };
}