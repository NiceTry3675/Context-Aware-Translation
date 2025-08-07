'use client';

import { useState, useEffect, useMemo } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { useTranslationData } from '../components/TranslationSidebar/hooks/useTranslationData';
import { useValidation } from '../components/TranslationSidebar/hooks/useValidation';
import { usePostEdit } from '../components/TranslationSidebar/hooks/usePostEdit';
import { useTranslationJobs } from './useTranslationJobs';
import { useSegmentNavigation } from '../components/TranslationSidebar/hooks/useSegmentNavigation';
import { useApiKey } from './useApiKey';
import { useTranslationService } from './useTranslationService';
import { Job } from '../types/job';
import { StyleData, GlossaryTerm, TranslationSettings } from '../types/translation';

export function useCanvasState() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { isSignedIn, getToken } = useAuth();
  const jobId = searchParams.get('jobId');
  
  // UI state
  const [tabValue, setTabValue] = useState(0);
  const [showNewTranslation, setShowNewTranslation] = useState(false);
  const [isClient, setIsClient] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [viewMode, setViewMode] = useState<'full' | 'segment'>('segment');
  const [errorFilters, setErrorFilters] = useState({
    critical: true,
    missingContent: true,
    addedContent: true,
    nameInconsistencies: true,
  });
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const { jobs, addJob, refreshJobs } = useTranslationJobs({ apiUrl: API_URL });
  
  // Translation setup states
  const { apiKey, setApiKey, apiProvider, setApiProvider, selectedModel, setSelectedModel } = useApiKey();
  const [file, setFile] = useState<File | null>(null);
  const [styleData, setStyleData] = useState<StyleData | null>(null);
  const [showStyleForm, setShowStyleForm] = useState<boolean>(false);
  const [glossaryData, setGlossaryData] = useState<GlossaryTerm[]>([]);
  const [glossaryAnalysisError, setGlossaryAnalysisError] = useState<string>('');
  
  // Translation settings
  const [translationSettings, setTranslationSettings] = useState<TranslationSettings>({
    segmentSize: 15000,
    enableValidation: false,
    quickValidation: false,
    validationSampleRate: 100,
    enablePostEdit: false
  });
  
  // Translation service hook
  const {
    analyzeFile,
    startTranslation,
    isAnalyzing,
    isAnalyzingGlossary,
    uploading,
    error: translationError,
    setError: setTranslationError
  } = useTranslationService({
    apiUrl: API_URL,
    apiKey,
    selectedModel,
    onJobCreated: (job) => {
      addJob(job);
      setFile(null);
      setStyleData(null);
      setGlossaryData([]);
      setShowStyleForm(false);
      router.push(`/?jobId=${job.id}`);
      setTabValue(0);
      setShowNewTranslation(false);
    }
  });
  
  // Find the current job from the jobs list
  useEffect(() => {
    if (jobId && jobs.length > 0) {
      const job = jobs.find(j => j.id.toString() === jobId);
      if (job) {
        setSelectedJob(job);
      }
    }
  }, [jobId, jobs]);
  
  // Use translation data hooks
  const {
    validationReport,
    postEditLog,
    translationContent,
    translationSegments,
    loading: dataLoading,
    error: dataError,
    selectedIssues,
    setSelectedIssues,
    loadData,
  } = useTranslationData({ 
    open: true, 
    jobId: jobId || '', 
    jobStatus: selectedJob?.status || '', 
    validationStatus: selectedJob?.validation_status || undefined,
    postEditStatus: selectedJob?.post_edit_status || undefined
  });

  const validation = useValidation({ jobId: jobId || '', onRefresh: refreshJobs });
  const postEdit = usePostEdit({ jobId: jobId || '', onRefresh: refreshJobs, selectedIssues });
  
  // Segment navigation hook
  const segmentNav = useSegmentNavigation({
    validationReport,
    postEditLog,
    translationSegments,
    jobId: jobId || undefined,
    errorFilters,
  });

  // Extract full source text from translation content or post-edit log
  const fullSourceText = useMemo(() => {
    if (translationContent?.source_content) {
      return translationContent.source_content;
    }
    if (postEditLog?.segments) {
      return postEditLog.segments
        .sort((a, b) => a.segment_index - b.segment_index)
        .map(segment => segment.source_text)
        .join('\n');
    }
    if (translationSegments?.segments && translationSegments.segments.length > 0) {
      return translationSegments.segments
        .sort((a, b) => a.segment_index - b.segment_index)
        .map(segment => segment.source_text)
        .join('\n');
    }
    return undefined;
  }, [translationContent, postEditLog, translationSegments]);

  // Load saved tab preference only on client side
  useEffect(() => {
    setIsClient(true);
    const savedTab = localStorage.getItem('canvasTabValue');
    if (savedTab) {
      setTabValue(parseInt(savedTab));
    }
    setShowNewTranslation(!jobId);
  }, [jobId]);

  // Save tab preference
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    if (isClient) {
      localStorage.setItem('canvasTabValue', newValue.toString());
    }
  };

  // Auto-refresh when translation, validation, or post-edit is in progress
  useEffect(() => {
    if (
      selectedJob?.status === 'IN_PROGRESS' ||
      selectedJob?.validation_status === 'IN_PROGRESS' || 
      selectedJob?.post_edit_status === 'IN_PROGRESS'
    ) {
      const interval = setInterval(() => {
        console.log('Refreshing job status...');
        refreshJobs();
        loadData();
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [selectedJob?.status, selectedJob?.validation_status, selectedJob?.post_edit_status, refreshJobs, loadData]);

  // Handle job selection change
  const handleJobChange = (newJobId: string) => {
    router.push(`/?jobId=${newJobId}`);
    setFile(null);
    setStyleData(null);
    setGlossaryData([]);
    setShowStyleForm(false);
  };
  
  // Handle new translation
  const handleNewTranslation = () => {
    setShowNewTranslation(!showNewTranslation);
    if (!showNewTranslation) {
      setFile(null);
      setStyleData(null);
      setGlossaryData([]);
      setShowStyleForm(false);
    }
  };
  
  // Handle job deletion
  const handleJobDelete = async (jobIdToDelete: number) => {
    try {
      const response = await fetch(`${API_URL}/api/v1/jobs/${jobIdToDelete}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${await getToken()}`,
        },
      });
      
      if (response.ok) {
        refreshJobs();
        if (jobIdToDelete.toString() === jobId) {
          router.push('/');
        }
      }
    } catch (error) {
      console.error('Failed to delete job:', error);
    }
  };

  // File analysis handler
  const handleFileSelect = async (selectedFile: File, analyzeGlossary: boolean) => {
    setFile(selectedFile);
    setGlossaryAnalysisError('');
    
    const result = await analyzeFile(selectedFile, analyzeGlossary);
    
    if (result.styleData) {
      setStyleData(result.styleData);
      setGlossaryData(result.glossaryData);
      setShowStyleForm(true);
    }
    
    if (result.error) {
      setGlossaryAnalysisError(result.error);
    }
    
    return result;
  };

  // Start translation handler
  const handleStartTranslation = async () => {
    if (!file || !styleData) {
      setTranslationError("번역을 시작할 파일과 스타일 정보가 필요합니다.");
      return;
    }

    await startTranslation(file, styleData, glossaryData, translationSettings);
  };

  const handleCancelStyleEdit = () => {
    setShowStyleForm(false);
    setFile(null);
    setStyleData(null);
    setGlossaryData([]);
    const fileInput = document.getElementById('file-upload-input') as HTMLInputElement;
    if (fileInput) fileInput.value = '';
  };

  // Calculate selected issue counts
  const calculateSelectedCounts = () => {
    let critical = 0;
    let missingContent = 0;
    let addedContent = 0;
    let nameInconsistencies = 0;

    if (validationReport) {
      validationReport.detailed_results.forEach((result) => {
        const segmentSelection = selectedIssues?.[result.segment_index];
        
        if (segmentSelection) {
          critical += segmentSelection.critical?.filter(selected => selected).length || 0;
          missingContent += segmentSelection.missing_content?.filter(selected => selected).length || 0;
          addedContent += segmentSelection.added_content?.filter(selected => selected).length || 0;
          nameInconsistencies += segmentSelection.name_inconsistencies?.filter(selected => selected).length || 0;
        } else {
          critical += result.critical_issues.length;
          missingContent += result.missing_content.length;
          addedContent += result.added_content.length;
          nameInconsistencies += result.name_inconsistencies.length;
        }
      });
    }

    return {
      critical,
      missingContent,
      addedContent,
      nameInconsistencies,
      total: critical + missingContent + addedContent + nameInconsistencies
    };
  };

  const selectedCounts = calculateSelectedCounts();
  
  // Combine loading states
  const loading = validation.loading || postEdit.loading;
  const isPolling = selectedJob?.status === 'IN_PROGRESS' || 
    selectedJob?.validation_status === 'IN_PROGRESS' || 
    selectedJob?.post_edit_status === 'IN_PROGRESS';
  const error = dataError || validation.error || postEdit.error || translationError;

  return {
    // Auth state
    isSignedIn,
    getToken,
    
    // Job state
    jobId,
    selectedJob,
    jobs,
    
    // UI state
    tabValue,
    setTabValue,
    handleTabChange,
    showNewTranslation,
    setShowNewTranslation,
    isClient,
    fullscreen,
    setFullscreen,
    viewMode,
    setViewMode,
    errorFilters,
    setErrorFilters,
    
    // Translation setup state
    apiKey,
    setApiKey,
    apiProvider,
    setApiProvider,
    selectedModel,
    setSelectedModel,
    file,
    setFile,
    styleData,
    setStyleData,
    showStyleForm,
    setShowStyleForm,
    glossaryData,
    setGlossaryData,
    glossaryAnalysisError,
    setGlossaryAnalysisError,
    translationSettings,
    setTranslationSettings,
    
    // Translation data
    validationReport,
    postEditLog,
    translationContent,
    translationSegments,
    fullSourceText,
    selectedIssues,
    setSelectedIssues,
    selectedCounts,
    
    // Loading states
    loading,
    dataLoading,
    isPolling,
    error,
    isAnalyzing,
    isAnalyzingGlossary,
    uploading,
    translationError,
    setTranslationError,
    
    // Handlers
    handleJobChange,
    handleNewTranslation,
    handleJobDelete,
    handleFileSelect,
    handleStartTranslation,
    handleCancelStyleEdit,
    refreshJobs,
    loadData,
    
    // Hooks
    validation,
    postEdit,
    segmentNav,
    
    // Navigation
    router,
    
    // Constants
    API_URL,
  };
}