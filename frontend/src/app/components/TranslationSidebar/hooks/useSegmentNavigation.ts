import { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ValidationReport, PostEditLog, TranslationSegments } from '../../../utils/api';

interface ErrorFilters {
  critical: boolean;
  missingContent: boolean;
  addedContent: boolean;
  nameInconsistencies: boolean;
}

interface UseSegmentNavigationProps {
  validationReport?: ValidationReport | null;
  postEditLog?: PostEditLog | null;
  translationSegments?: TranslationSegments | null;
  jobId?: string;
  errorFilters?: ErrorFilters;
}

interface UseSegmentNavigationReturn {
  currentSegmentIndex: number;
  totalSegments: number;
  setCurrentSegmentIndex: (index: number) => void;
  goToSegment: (index: number) => void;
  goToNextSegment: () => void;
  goToPreviousSegment: () => void;
  goToFirstSegment: () => void;
  goToLastSegment: () => void;
  segmentsWithErrors: number[];
  goToNextError: () => void;
  goToPreviousError: () => void;
  hasErrors: boolean;
  isFirstSegment: boolean;
  isLastSegment: boolean;
}

export function useSegmentNavigation({
  validationReport,
  postEditLog,
  translationSegments,
  jobId,
  errorFilters = {
    critical: true,
    missingContent: true,
    addedContent: true,
    nameInconsistencies: true,
  },
}: UseSegmentNavigationProps): UseSegmentNavigationReturn {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [currentSegmentIndex, setCurrentSegmentIndexState] = useState(0);
  const [isClient, setIsClient] = useState(false);

  // Calculate total segments
  const totalSegments = useMemo(() => {
    if (postEditLog?.segments) {
      return postEditLog.segments.length;
    }
    if (translationSegments?.segments && translationSegments.segments.length > 0) {
      return translationSegments.segments.length;
    }
    if (validationReport?.detailed_results) {
      return validationReport.detailed_results.length;
    }
    return 0;
  }, [postEditLog, translationSegments, validationReport]);

  // Calculate segments with errors based on filters
  const segmentsWithErrors = useMemo(() => {
    if (!validationReport) return [];
    
    return validationReport.detailed_results
      .filter((result) => {
        // Support both flat fields and nested validation_result
        const flat = {
          critical: result.critical_issues?.length || 0,
          missing: result.missing_content?.length || 0,
          added: result.added_content?.length || 0,
          names: result.name_inconsistencies?.length || 0,
        };
        const nested = result.validation_result || {} as any;
        const counts = {
          critical: flat.critical || (nested.critical_issues?.length || 0),
          missing: flat.missing || (nested.missing_content?.length || 0),
          added: flat.added || (nested.added_content?.length || 0),
          names: flat.names || (nested.name_inconsistencies?.length || 0),
        };

        const hasRelevantErrors =
          (errorFilters.critical && counts.critical > 0) ||
          (errorFilters.missingContent && counts.missing > 0) ||
          (errorFilters.addedContent && counts.added > 0) ||
          (errorFilters.nameInconsistencies && counts.names > 0);

        return result.status === 'FAIL' && hasRelevantErrors;
      })
      .map((result) => result.segment_index)
      .sort((a: number, b: number) => a - b);
  }, [validationReport, errorFilters]);

  // Load segment from URL on mount and when URL changes
  useEffect(() => {
    const segmentParam = searchParams.get('segment');
    if (segmentParam) {
      const segmentIndex = parseInt(segmentParam) - 1; // Convert to 0-based
      if (!isNaN(segmentIndex) && segmentIndex >= 0 && segmentIndex < totalSegments) {
        setCurrentSegmentIndexState(segmentIndex);
      }
    }
  }, [searchParams, totalSegments]);

  // Update URL when segment changes
  const updateURL = useCallback((index: number) => {
    if (!jobId) return;
    
    const params = new URLSearchParams(searchParams.toString());
    params.set('segment', (index + 1).toString()); // Convert to 1-based for URL
    
    const newUrl = `/?${params.toString()}`;
    router.replace(newUrl, { scroll: false });
  }, [jobId, searchParams, router]);

  // Set current segment index with URL update
  const setCurrentSegmentIndex = useCallback((index: number) => {
    if (index >= 0 && index < totalSegments) {
      setCurrentSegmentIndexState(index);
      updateURL(index);
      
      // Save to localStorage for persistence
      if (isClient && jobId) {
        localStorage.setItem(`segment_${jobId}`, index.toString());
      }
    }
  }, [totalSegments, updateURL, jobId, isClient]);

  // Navigation functions
  const goToSegment = useCallback((index: number) => {
    setCurrentSegmentIndex(index);
  }, [setCurrentSegmentIndex]);

  const goToNextSegment = useCallback(() => {
    if (currentSegmentIndex < totalSegments - 1) {
      setCurrentSegmentIndex(currentSegmentIndex + 1);
    }
  }, [currentSegmentIndex, totalSegments, setCurrentSegmentIndex]);

  const goToPreviousSegment = useCallback(() => {
    if (currentSegmentIndex > 0) {
      setCurrentSegmentIndex(currentSegmentIndex - 1);
    }
  }, [currentSegmentIndex, setCurrentSegmentIndex]);

  const goToFirstSegment = useCallback(() => {
    setCurrentSegmentIndex(0);
  }, [setCurrentSegmentIndex]);

  const goToLastSegment = useCallback(() => {
    if (totalSegments > 0) {
      setCurrentSegmentIndex(totalSegments - 1);
    }
  }, [totalSegments, setCurrentSegmentIndex]);

  // Error navigation functions
  const goToNextError = useCallback(() => {
    if (segmentsWithErrors.length === 0) return;
    
    const currentErrorIndex = segmentsWithErrors.indexOf(currentSegmentIndex);
    
    if (currentErrorIndex !== -1 && currentErrorIndex < segmentsWithErrors.length - 1) {
      // Go to next error in list
      setCurrentSegmentIndex(segmentsWithErrors[currentErrorIndex + 1]);
    } else {
      // Find next error after current position
      const nextErrors = segmentsWithErrors.filter((idx: number) => idx > currentSegmentIndex);
      if (nextErrors.length > 0) {
        setCurrentSegmentIndex(nextErrors[0]);
      } else if (segmentsWithErrors.length > 0) {
        // Wrap around to first error
        setCurrentSegmentIndex(segmentsWithErrors[0]);
      }
    }
  }, [segmentsWithErrors, currentSegmentIndex, setCurrentSegmentIndex]);

  const goToPreviousError = useCallback(() => {
    if (segmentsWithErrors.length === 0) return;
    
    const currentErrorIndex = segmentsWithErrors.indexOf(currentSegmentIndex);
    
    if (currentErrorIndex > 0) {
      // Go to previous error in list
      setCurrentSegmentIndex(segmentsWithErrors[currentErrorIndex - 1]);
    } else {
      // Find previous error before current position
      const previousErrors = segmentsWithErrors.filter((idx: number) => idx < currentSegmentIndex);
      if (previousErrors.length > 0) {
        setCurrentSegmentIndex(previousErrors[previousErrors.length - 1]);
      } else if (segmentsWithErrors.length > 0) {
        // Wrap around to last error
        setCurrentSegmentIndex(segmentsWithErrors[segmentsWithErrors.length - 1]);
      }
    }
  }, [segmentsWithErrors, currentSegmentIndex, setCurrentSegmentIndex]);

  // Load saved segment position from localStorage
  useEffect(() => {
    setIsClient(true);
    if (jobId && totalSegments > 0) {
      const savedSegment = localStorage.getItem(`segment_${jobId}`);
      if (savedSegment) {
        const index = parseInt(savedSegment);
        if (!isNaN(index) && index >= 0 && index < totalSegments) {
          setCurrentSegmentIndexState(index);
        }
      }
    }
  }, [jobId, totalSegments]);

  return {
    currentSegmentIndex,
    totalSegments,
    setCurrentSegmentIndex,
    goToSegment,
    goToNextSegment,
    goToPreviousSegment,
    goToFirstSegment,
    goToLastSegment,
    segmentsWithErrors,
    goToNextError,
    goToPreviousError,
    hasErrors: segmentsWithErrors.length > 0,
    isFirstSegment: currentSegmentIndex === 0,
    isLastSegment: currentSegmentIndex === totalSegments - 1,
  };
}