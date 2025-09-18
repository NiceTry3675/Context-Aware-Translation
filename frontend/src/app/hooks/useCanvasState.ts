'use client';

import { useState, useEffect, useMemo } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { getCachedClerkToken } from '../utils/authToken';
import { useTranslationData } from '../components/TranslationSidebar/hooks/useTranslationData';
import { useTranslationJobs } from './useTranslationJobs';
import { useSegmentNavigation } from '../components/TranslationSidebar/hooks/useSegmentNavigation';
import { useApiKey } from './useApiKey';
import { useTranslationService } from './useTranslationService';
import { useJobActions } from './useJobActions';
import { Job, StyleData, GlossaryTerm, TranslationSettings } from '../types/ui';

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
  // Default to full view so users see entire source/translation side-by-side
  const [viewMode, setViewMode] = useState<'full' | 'segment'>('full');
  // Legacy error filter chips are not used in structured UI; keep no-op state
  const [errorFilters, setErrorFilters] = useState({
    critical: true,
    missingContent: true,
    addedContent: true,
    nameInconsistencies: true,
  });
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const { jobs, addJob, refreshJobs, refreshJobPublic } = useTranslationJobs({ apiUrl: API_URL });
  
  // Translation setup states
  const {
    apiKey,
    setApiKey,
    providerConfig,
    setProviderConfig,
    apiProvider,
    setApiProvider,
    selectedModel,
    setSelectedModel,
  } = useApiKey();
  const [taskModelOverrides, setTaskModelOverrides] = useState<{ styleModel?: string | null; glossaryModel?: string | null }>({});
  const [taskOverridesEnabled, setTaskOverridesEnabled] = useState<boolean>(false);
  const [file, setFile] = useState<File | null>(null);
  const [styleData, setStyleData] = useState<StyleData | null>(null);
  const [showStyleForm, setShowStyleForm] = useState<boolean>(false);
  const [glossaryData, setGlossaryData] = useState<GlossaryTerm[]>([]);
  const [glossaryAnalysisError, setGlossaryAnalysisError] = useState<string>('');
  
  // Translation settings
  const [translationSettings, setTranslationSettings] = useState<TranslationSettings>({
    model_name: 'gemini-2.5-flash',
    segmentSize: 15000,
    enableValidation: false,
    quickValidation: false,
    validationSampleRate: 100,
    enablePostEdit: false,
    enableIllustrations: false
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
    apiProvider,
    apiKey,
    providerConfig,
    selectedModel,
    selectedStyleModel: taskOverridesEnabled ? (taskModelOverrides.styleModel || selectedModel) : undefined,
    selectedGlossaryModel: taskOverridesEnabled ? (taskModelOverrides.glossaryModel || selectedModel) : undefined,
    onJobCreated: (job) => {
      addJob(job);
      setSelectedJob(job); // Immediately set the new job as selected
      setFile(null);
      setStyleData(null);
      setGlossaryData([]);
      setTaskModelOverrides({});
      setTaskOverridesEnabled(false);
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
      } else {
        // Clear selectedJob if jobId doesn't match any job
        setSelectedJob(null);
      }
    } else if (!jobId) {
      // Clear selectedJob if no jobId
      setSelectedJob(null);
    }
  }, [jobId, jobs]);
  
  // Use translation data hooks
  const {
    validationReport,
    postEditLog,
    translationContent,
    translationSegments,
    illustrationStatus,
    loading: dataLoading,
    error: dataError,
    loadData,
    loadMoreSegments,
  } = useTranslationData({ 
    open: true, 
    jobId: jobId || '', 
    jobStatus: selectedJob?.status || '', 
    validationStatus: selectedJob?.validation_status || undefined,
    postEditStatus: selectedJob?.post_edit_status || undefined,
    illustrationsStatus: selectedJob?.illustrations_status || undefined
  });

  // State for dialogs, managed centrally
  const [validationDialogOpen, setValidationDialogOpen] = useState(false);
  const [quickValidation, setQuickValidation] = useState(false);
  const [validationSampleRate, setValidationSampleRate] = useState(100);
  const [validationModelName, setValidationModelName] = useState<string>('');

  const [postEditDialogOpen, setPostEditDialogOpen] = useState(false);
  const [postEditModelName, setPostEditModelName] = useState<string>('');
  const [selectedCases, setSelectedCases] = useState<Record<number, boolean[]>>({});
  const [modifiedCases, setModifiedCases] = useState<Record<number, Array<{ reason?: string; recommend_korean_sentence?: string }>>>({});

  const [illustrationDialogOpen, setIllustrationDialogOpen] = useState(false);
  const [illustrationStyle, setIllustrationStyle] = useState<string>('digital_art');
  const [illustrationStyleHints, setIllustrationStyleHints] = useState<string>('');
  const [illustrationMinSegmentLength, setIllustrationMinSegmentLength] = useState(100);
  const [illustrationSkipDialogueHeavy, setIllustrationSkipDialogueHeavy] = useState(false);
  const [illustrationMaxCount, setIllustrationMaxCount] = useState(10);

  const { 
    handleTriggerValidation, 
    handleTriggerPostEdit,
    handleTriggerIllustration,
    loading: jobActionLoading,
    error: jobActionError,
  } = useJobActions({
    apiUrl: API_URL,
    apiProvider,
    apiKey,
    providerConfig,
    onSuccess: () => {
      if (jobId) {
        refreshJobPublic(parseInt(jobId, 10));
        // Reload data to fetch validation report or post-edit log
        setTimeout(() => {
          loadData();
        }, 2000); // Wait 2 seconds for backend to process
      }
    },
    onError: (error) => {
      // TODO: Show error in a snackbar
      console.error(error);
    }
  });

  const onConfirmValidation = () => {
    if (!jobId) return;
    handleTriggerValidation(parseInt(jobId, 10), {
      quick_validation: quickValidation,
      validation_sample_rate: validationSampleRate / 100,
      model_name: validationModelName || selectedModel,
    });
    setValidationDialogOpen(false);
  };

  const onConfirmPostEdit = () => {
    if (!jobId) return;
    const body: any = {
      selected_cases: selectedCases || {},
      modified_cases: modifiedCases || {},
      model_name: postEditModelName || selectedModel,
      default_select_all: true,
    };
    handleTriggerPostEdit(parseInt(jobId, 10), body as any);
    setPostEditDialogOpen(false);
    // Clear selectedCases after confirmation
    setSelectedCases({});
    // Keep modifiedCases in memory so user edits persist across dialogs
  };

  const onConfirmIllustration = () => {
    if (!jobId) return;
    const credential = apiProvider === 'vertex' ? '' : apiKey;
    if (apiProvider !== 'vertex' && !credential) {
      setTranslationError('일러스트 생성을 위해 API 키가 필요합니다.');
      return;
    }
    if (apiProvider === 'vertex' && (!providerConfig || !providerConfig.trim())) {
      setTranslationError('일러스트 생성을 위해 Vertex 서비스 계정 JSON이 필요합니다.');
      return;
    }
    handleTriggerIllustration(
      parseInt(jobId, 10),
      credential,
      {
        style: illustrationStyle,
        style_hints: illustrationStyleHints,
        min_segment_length: illustrationMinSegmentLength,
        skip_dialogue_heavy: illustrationSkipDialogueHeavy,
        cache_enabled: false,
      },
      illustrationMaxCount
    );
    setIllustrationDialogOpen(false);
  };
  
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
        .slice()
        .sort((a, b) => a.segment_index - b.segment_index)
        .map(segment => segment.source_text)
        .join('\n');
    }
    if (translationSegments?.segments && translationSegments.segments.length > 0) {
      return translationSegments.segments
        .slice()
        .sort((a, b) => a.segment_index - b.segment_index)
        .map(segment => segment.source_text)
        .join('\n');
    }
    return undefined;
  }, [translationContent, postEditLog, translationSegments]);

  // Auto-populate selectedCases when post-edit dialog opens with validation report
  useEffect(() => {
    if (postEditDialogOpen && validationReport?.detailed_results && Object.keys(selectedCases).length === 0) {
      // Auto-select all cases for post-editing when opening from canvas
      const newSelectedCases: Record<number, boolean[]> = {};
      validationReport.detailed_results.forEach((result: any) => {
        if (result.structured_cases && result.structured_cases.length > 0) {
          newSelectedCases[result.segment_index] = new Array(result.structured_cases.length).fill(true);
        }
      });
      setSelectedCases(newSelectedCases);
    }
  }, [postEditDialogOpen, validationReport]);

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

  // Lightweight auto-refresh for the currently selected job (no Clerk token)
  useEffect(() => {
    const anyInProgress = (
      selectedJob?.status === 'IN_PROGRESS' ||
      selectedJob?.validation_status === 'IN_PROGRESS' || 
      selectedJob?.post_edit_status === 'IN_PROGRESS' ||
      selectedJob?.illustrations_status === 'IN_PROGRESS'
    );
    if (!jobId || !anyInProgress) return;

    const interval = setInterval(() => {
      // Trigger a public refresh of the selected job only; no token required
      refreshJobPublic(jobId);
    }, 3000);
    return () => clearInterval(interval);
  }, [jobId, selectedJob?.status, selectedJob?.validation_status, selectedJob?.post_edit_status, selectedJob?.illustrations_status, refreshJobPublic]);

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
      setTaskModelOverrides({});
      setTaskOverridesEnabled(false);
    }
  };
  
  // Handle job deletion
  const handleJobDelete = async (jobIdToDelete: number) => {
    try {
      const token = await getCachedClerkToken(getToken);
      const response = await fetch(`${API_URL}/api/v1/jobs/${jobIdToDelete}`, {
        method: 'DELETE',
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
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

  // Selected counts are derived from selection UI per-view; keep minimal summary only if needed
  const selectedCounts = useMemo(() => ({ total: 0 }), []);
  
  // Combine loading states
  const loading = dataLoading || jobActionLoading;
  const isPolling = selectedJob?.status === 'IN_PROGRESS' || 
    selectedJob?.validation_status === 'IN_PROGRESS' || 
    selectedJob?.post_edit_status === 'IN_PROGRESS' ||
    selectedJob?.illustrations_status === 'IN_PROGRESS';
  const error = dataError || jobActionError || translationError;

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
    providerConfig,
    setProviderConfig,
    apiProvider,
    setApiProvider,
    selectedModel,
    setSelectedModel,
    taskOverridesEnabled,
    setTaskOverridesEnabled,
    taskModelOverrides,
    setTaskModelOverrides,
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
    illustrationStatus,
    fullSourceText,
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
    refreshJobPublic,
    loadData,
    loadMoreSegments,
    
    // Validation Dialog State and Handlers
    validationDialogOpen,
    setValidationDialogOpen,
    quickValidation,
    setQuickValidation,
    validationSampleRate,
    setValidationSampleRate,
    validationModelName,
    setValidationModelName,
    onConfirmValidation,

    // Post-Edit Dialog State and Handlers
    postEditDialogOpen,
    setPostEditDialogOpen,
    postEditModelName,
    setPostEditModelName,
    selectedCases,
    setSelectedCases,
    modifiedCases,
    setModifiedCases,
    onConfirmPostEdit,
    segmentNav,
    
    // Illustration Dialog State and Handlers
    illustrationDialogOpen,
    setIllustrationDialogOpen,
    illustrationStyle,
    setIllustrationStyle,
    illustrationStyleHints,
    setIllustrationStyleHints,
    illustrationMinSegmentLength,
    setIllustrationMinSegmentLength,
    illustrationSkipDialogueHeavy,
    setIllustrationSkipDialogueHeavy,
    illustrationMaxCount,
    setIllustrationMaxCount,
    onConfirmIllustration,
    
    // Navigation
    router,
    
    // Constants
    API_URL,
  };
}
