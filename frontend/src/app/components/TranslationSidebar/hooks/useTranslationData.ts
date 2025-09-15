'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@clerk/nextjs';
import { getCachedClerkToken } from '../../../utils/authToken';
import {
  ValidationReport,
  PostEditLog,
  TranslationContent,
  TranslationSegments,
  IllustrationStatus,
  fetchValidationReport,
  fetchPostEditLog,
  fetchTranslationContent,
  fetchTranslationSegments,
  fetchIllustrationStatus,
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
  illustrationsStatus,
}: UseTranslationDataProps & { illustrationsStatus?: string }) {
  const [validationReport, setValidationReport] = useState<ValidationReport | null>(null);
  const [postEditLog, setPostEditLog] = useState<PostEditLog | null>(null);
  const [translationContent, setTranslationContent] = useState<TranslationContent | null>(null);
  const [translationSegments, setTranslationSegments] = useState<TranslationSegments | null>(null);
  const [illustrationStatus, setIllustrationStatus] = useState<IllustrationStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const { getToken } = useAuth();

  // Track the latest jobId to prevent race conditions when switching jobs quickly
  const jobIdRef = useRef(jobId);
  useEffect(() => {
    jobIdRef.current = jobId;
  }, [jobId]);

  const loadData = useCallback(async () => {
    // Skip only when jobId is missing
    if (!jobId) {
      console.log('[useTranslationData] Skipping loadData - missing jobId');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const token = await getCachedClerkToken(getToken);
      
      // Load translation content and segments whenever available.
      // Even if post-edit is in progress and job status changes, content should remain accessible.
      console.log('[useTranslationData] Loading content and segments for job:', { jobId, jobStatus });
      const [content, segments] = await Promise.all([
        fetchTranslationContent(jobId, token || undefined),
        fetchTranslationSegments(jobId, token || undefined, 0, 200)
      ]);
      // Guard against stale responses after job switch
      if (jobIdRef.current !== jobId) return;
      setTranslationContent(content || null);
      setTranslationSegments(segments || null);
      
      // Load validation report if validation is completed (independent of jobStatus)
      console.log('[useTranslationData] Checking validation load conditions:', { jobId, jobStatus, validationStatus });
      if (validationStatus === 'COMPLETED') {
        console.log('Loading validation report for job:', jobId);
        const report = await fetchValidationReport(jobId, token || undefined);
        if (jobIdRef.current !== jobId) return;
        setValidationReport(report || null);
      } else {
        // Clear stale validation report when status is not completed
        setValidationReport(null);
      }
      
      // Load post-edit log if available
      if (postEditStatus === 'COMPLETED') {
        const log = await fetchPostEditLog(jobId, token || undefined);
        if (jobIdRef.current !== jobId) return;
        setPostEditLog(log || null);
      } else {
        // Clear stale post-edit log when status is not completed
        setPostEditLog(null);
      }
      
      // Load illustration status if illustrations are enabled or in progress
      if (jobStatus === 'COMPLETED' && (illustrationsStatus === 'IN_PROGRESS' || illustrationsStatus === 'COMPLETED')) {
        console.log('[useTranslationData] Loading illustration status for job:', jobId);
        const status = await fetchIllustrationStatus(jobId, token || undefined);
        if (jobIdRef.current !== jobId) return;
        setIllustrationStatus(status || null);
      } else {
        setIllustrationStatus(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '데이터를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  }, [jobId, jobStatus, validationStatus, postEditStatus, illustrationsStatus, getToken]);

  // Function to load more segments with pagination
  const loadMoreSegments = useCallback(async (offset: number, limit: number) => {
    const token = await getCachedClerkToken(getToken);
    const result = await fetchTranslationSegments(jobId, token || undefined, offset, limit);
    
    if (!result) {
      throw new Error('Failed to load segments');
    }
    
    return {
      segments: result.segments,
      has_more: result.has_more || false,
      total_segments: result.total_segments || 0,
    };
  }, [jobId, getToken]);

  // Load data when sidebar opens or job changes
  useEffect(() => {
    if (open && jobId) {
      // Clear all data when switching jobs to avoid showing stale results
      setValidationReport(null);
      setPostEditLog(null);
      setTranslationContent(null);
      setTranslationSegments(null);
      setIllustrationStatus(null);
      loadData();
    }
  }, [open, jobId, loadData]);
  
  // Reload data when validation completes
  useEffect(() => {
    if (validationStatus === 'COMPLETED' && !validationReport) {
      loadData();
    }
  }, [validationStatus, validationReport, loadData]);

  // Reload data when post-edit completes
  useEffect(() => {
    if (postEditStatus === 'COMPLETED' && !postEditLog) {
      loadData();
    }
  }, [postEditStatus, postEditLog, loadData]);

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
          changes: segment.changes_made,
        };
      }
    }
    
    // Fall back to validation report (structured-only flow: provide previews)
    if (validationReport?.detailed_results) {
      const result = validationReport.detailed_results.find(r => r.segment_index === segmentIndex);
      if (result) {
        return {
          sourceText: result.source_preview,
          translatedText: result.translated_preview,
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
    translationSegments,
    illustrationStatus,
    loading,
    error,
    loadData,
    loadMoreSegments,
    getSegmentData,
    totalSegments,
  };
}
