'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import {
  Box,
  Container,
  Paper,
  Typography,
  Tabs,
  Tab,
  IconButton,
  Button,
  Stack,
  Alert,
  AlertTitle,
  CircularProgress,
  Tooltip,
  Chip,
  Card,
  CardContent,
} from '@mui/material';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import RefreshIcon from '@mui/icons-material/Refresh';
import FullscreenIcon from '@mui/icons-material/Fullscreen';
import FullscreenExitIcon from '@mui/icons-material/FullscreenExit';
import FirstPageIcon from '@mui/icons-material/FirstPage';
import LastPageIcon from '@mui/icons-material/LastPage';
import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';

// Import viewer components
import ValidationReportViewer from './components/ValidationReportViewer';
import PostEditLogViewer from './components/PostEditLogViewer';
import TranslationContentViewer from './components/TranslationContentViewer';
import JobSidebar from './components/canvas/JobSidebar';
import SegmentViewer from './components/canvas/SegmentViewer';
import ErrorIcon from '@mui/icons-material/Error';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import AddCircleIcon from '@mui/icons-material/AddCircle';
import PersonIcon from '@mui/icons-material/Person';
import KeyboardArrowLeftIcon from '@mui/icons-material/KeyboardArrowLeft';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';

// Import translation setup components
import ApiSetup from './components/ApiConfiguration/ApiSetup';
import FileUploadSection from './components/FileUpload/FileUploadSection';
import TranslationSettings from './components/AdvancedSettings/TranslationSettings';
import StyleConfigForm from './components/StyleConfiguration/StyleConfigForm';

// Import action components from sidebar
import ValidationDialog from './components/TranslationSidebar/ValidationDialog';
import PostEditDialog from './components/TranslationSidebar/PostEditDialog';

// Import hooks
import { useTranslationData } from './components/TranslationSidebar/hooks/useTranslationData';
import { useValidation } from './components/TranslationSidebar/hooks/useValidation';
import { usePostEdit } from './components/TranslationSidebar/hooks/usePostEdit';
import { useTranslationJobs } from './hooks/useTranslationJobs';
import { useSegmentNavigation } from './components/TranslationSidebar/hooks/useSegmentNavigation';
import { useApiKey } from './hooks/useApiKey';
import { useTranslationService } from './hooks/useTranslationService';
import { useJobActions } from './hooks/useJobActions';

// Types
import { Job } from './types/job';
import { 
  StyleData, 
  GlossaryTerm, 
  TranslationSettings as TSettings 
} from './types/translation';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index, ...other }: TabPanelProps) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`canvas-tabpanel-${index}`}
      aria-labelledby={`canvas-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ height: '100%' }}>{children}</Box>}
    </div>
  );
}

function CanvasContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { isSignedIn, getToken } = useAuth();

  useEffect(() => {
    if (isSignedIn === false) {
      router.push('/about');
    }
  }, [isSignedIn, router]);
  
  const mainContainerRef = React.useRef<HTMLDivElement>(null);

  const handleToggleFullscreen = () => {
    if (!document.fullscreenElement) {
      mainContainerRef.current?.requestFullscreen().catch(err => {
        console.error(`Error attempting to enable full-screen mode: ${err.message} (${err.name})`);
      });
    } else {
      document.exitFullscreen();
    }
  };

  useEffect(() => {
    const handleFullscreenChange = () => {
      setFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);
  
  const jobId = searchParams.get('jobId');
  const [tabValue, setTabValue] = useState(0);
  const [showNewTranslation, setShowNewTranslation] = useState(false);
  const [isClient, setIsClient] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [viewMode, setViewMode] = useState<'full' | 'segment'>('segment'); // New view mode state
  const [errorFilters, setErrorFilters] = useState({
    critical: true,
    missingContent: true,
    addedContent: true,
    nameInconsistencies: true,
  });
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const { jobs, addJob, deleteJob, refreshJobs } = useTranslationJobs({ apiUrl: API_URL });
  
  // Translation setup states (moved from main page)
  const { apiKey, setApiKey, apiProvider, setApiProvider, selectedModel, setSelectedModel } = useApiKey();
  const [file, setFile] = useState<File | null>(null);
  const [styleData, setStyleData] = useState<StyleData | null>(null);
  const [showStyleForm, setShowStyleForm] = useState<boolean>(false);
  const [glossaryData, setGlossaryData] = useState<GlossaryTerm[]>([]);
  const [glossaryAnalysisError, setGlossaryAnalysisError] = useState<string>('');
  
  // Translation settings
  const [translationSettings, setTranslationSettings] = useState<TSettings>({
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
      // Navigate to the new job in canvas
      router.push(`/?jobId=${job.id}`);
      // Switch to the translation result tab
      setTabValue(0);
      // Collapse the new translation form
      setShowNewTranslation(false);
    }
  });
  
  // Job actions hook
  const jobActions = useJobActions({
    apiUrl: API_URL,
    onError: setTranslationError,
    onSuccess: refreshJobs
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
  const fullSourceText = React.useMemo(() => {
    // First priority: use source_content from translation content if available
    if (translationContent?.source_content) {
      return translationContent.source_content;
    }
    // Second priority: use post-edit log segments if available (has full source_text)
    if (postEditLog?.segments) {
      return postEditLog.segments
        .sort((a, b) => a.segment_index - b.segment_index)
        .map(segment => segment.source_text)
        .join(' '); // Join with single space for natural flow
    }
    // Third priority: use translation segments if available
    if (translationSegments?.segments && translationSegments.segments.length > 0) {
      return translationSegments.segments
        .sort((a, b) => a.segment_index - b.segment_index)
        .map(segment => segment.source_text)
        .join(' '); // Join with single space for natural flow
    }
    // Don't use validation report as it only has truncated source_preview
    return undefined;
  }, [translationContent, postEditLog, translationSegments]);

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

  // Wrapper function for job validation
  const handleTriggerValidation = (jobId: number) => {
    return jobActions.handleTriggerValidation(
      jobId,
      translationSettings.quickValidation,
      translationSettings.validationSampleRate
    );
  };

  // Combine loading states
  const loading = dataLoading || validation.loading || postEdit.loading;
  const error = dataError || validation.error || postEdit.error || translationError;

  // Load saved tab preference only on client side
  useEffect(() => {
    setIsClient(true);
    const savedTab = localStorage.getItem('canvasTabValue');
    if (savedTab) {
      setTabValue(parseInt(savedTab));
    }
    // Show new translation form if no job is selected, or hide it if a job is selected.
    setShowNewTranslation(!jobId);
  }, [jobId]);

  // Save tab preference
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    if (isClient) {
      localStorage.setItem('canvasTabValue', newValue.toString());
    }
  };

  // Auto-refresh when validation/post-edit is in progress
  useEffect(() => {
    if (selectedJob?.validation_status === 'IN_PROGRESS' || selectedJob?.post_edit_status === 'IN_PROGRESS') {
      const interval = setInterval(() => {
        refreshJobs();
        loadData();
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [selectedJob?.validation_status, selectedJob?.post_edit_status, refreshJobs, loadData]);

  // Handle job selection change
  const handleJobChange = (newJobId: string) => {
    router.push(`/?jobId=${newJobId}`);
    // Reset translation form when switching jobs
    setFile(null);
    setStyleData(null);
    setGlossaryData([]);
    setShowStyleForm(false);
  };
  
  // Handle new translation - now toggles the new translation form
  const handleNewTranslation = () => {
    setShowNewTranslation(!showNewTranslation);
    // Reset form state when opening
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
      // Call delete API
      const response = await fetch(`${API_URL}/api/v1/jobs/${jobIdToDelete}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${await getToken()}`,
        },
      });
      
      if (response.ok) {
        refreshJobs();
        // If deleted job was selected, clear selection
        if (jobIdToDelete.toString() === jobId) {
          router.push('/');
        }
      }
    } catch (error) {
      console.error('Failed to delete job:', error);
    }
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

  if (!isSignedIn) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  // Remove the early return for no jobId - we'll handle it in the main layout

  return (
    <>
      <Box sx={{ 
        height: '100vh', 
        display: 'flex', 
        backgroundColor: 'background.default' 
      }}
      ref={mainContainerRef}
      >
      <JobSidebar
        jobs={jobs}
        selectedJobId={jobId}
        onJobSelect={handleJobChange}
        onJobDelete={handleJobDelete}
        onNewTranslation={handleNewTranslation}
        onRefreshJobs={refreshJobs}
        loading={dataLoading}
      />
      
      {/* Main Content Area */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <Paper elevation={1} sx={{ borderRadius: 0 }}>
          <Container maxWidth={false}>
            <Box sx={{ py: 2 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                {/* Left side - Navigation */}
                <Stack direction="row" spacing={2} alignItems="center">
                  <Typography variant="h6" component="h1">
                    번역 캔버스
                  </Typography>
                  {selectedJob && (
                    <Chip
                      label={selectedJob.filename}
                      size="small"
                      sx={{ maxWidth: 300 }}
                    />
                  )}
                </Stack>

                {/* Right side - Actions */}
                <Stack direction="row" spacing={1} alignItems="center">
                  <Tooltip title="새로고침">
                    <IconButton onClick={() => window.location.reload()}>
                      <RefreshIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="About">
                    <IconButton onClick={() => router.push('/about')}>
                      <InfoOutlinedIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title={fullscreen ? "전체화면 종료" : "전체화면"}>
                    <IconButton onClick={handleToggleFullscreen}>
                      {fullscreen ? <FullscreenExitIcon /> : <FullscreenIcon />}
                    </IconButton>
                  </Tooltip>
                </Stack>
              </Stack>
            </Box>
          </Container>
        </Paper>

        {/* Main Content Area */}
        <Container maxWidth={false} sx={{ flex: 1, display: 'flex', flexDirection: 'column', py: 2, gap: 2, overflow: 'hidden' }}>
          {showNewTranslation ? (
            // New Translation View
            <Paper sx={{ p: 3, overflowY: 'auto', height: '100%' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">새 번역 시작</Typography>
                {jobId && ( // Only show close button if there's a job to go back to
                  <IconButton onClick={() => setShowNewTranslation(false)} size="small">
                    <KeyboardArrowLeftIcon />
                  </IconButton>
                )}
              </Box>
              <Card sx={{ maxWidth: '100%' }}>
                <CardContent>
                  {/* API Configuration */}
                  <ApiSetup
                    apiProvider={apiProvider}
                    apiKey={apiKey}
                    selectedModel={selectedModel}
                    onProviderChange={setApiProvider}
                    onApiKeyChange={setApiKey}
                    onModelChange={setSelectedModel}
                  />

                  {/* File Upload */}
                  <FileUploadSection
                    isAnalyzing={isAnalyzing}
                    isAnalyzingGlossary={isAnalyzingGlossary}
                    uploading={uploading}
                    error={translationError}
                    onFileSelect={handleFileSelect}
                  />
                </CardContent>

                {/* Advanced Settings */}
                <CardContent sx={{ borderTop: 1, borderColor: 'divider', mt: 2 }}>
                  <TranslationSettings
                    settings={translationSettings}
                    onChange={setTranslationSettings}
                  />
                </CardContent>

                {/* Style & Glossary Configuration */}
                {showStyleForm && styleData && (
                  <CardContent sx={{ borderTop: 1, borderColor: 'divider', mt: 2 }}>
                    <StyleConfigForm
                      styleData={styleData}
                      glossaryData={glossaryData}
                      isAnalyzingGlossary={isAnalyzingGlossary}
                      glossaryAnalysisError={glossaryAnalysisError}
                      uploading={uploading}
                      onStyleChange={setStyleData}
                      onGlossaryChange={setGlossaryData}
                      onSubmit={handleStartTranslation}
                      onCancel={handleCancelStyleEdit}
                    />
                  </CardContent>
                )}
              </Card>
            </Paper>
          ) : (
            // Results View
            <Paper sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <Box sx={{ px: 2, pt: 1 }}>
                <Button
                  variant="outlined"
                  startIcon={<AddCircleIcon />}
                  onClick={() => setShowNewTranslation(true)}
                  size="small"
                  sx={{ mb: 1 }}
                >
                  새 번역 시작
                </Button>
              </Box>
              
              <Box sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}>
                <Tabs value={tabValue} onChange={handleTabChange}>
                  <Tab 
                    label="번역 결과"
                    disabled={!jobId || (!translationContent && selectedJob?.status !== 'COMPLETED')} 
                  />
                  <Tab 
                    label="검증 결과"
                    disabled={!jobId || (!validationReport && selectedJob?.validation_status !== 'COMPLETED')} 
                  />
                  <Tab 
                    label="포스트 에디팅"
                    disabled={!jobId || (!postEditLog && selectedJob?.post_edit_status !== 'COMPLETED')} 
                  />
                </Tabs>
              </Box>

              {/* Tab Content */}
              <Box sx={{ flex: 1, overflow: 'auto', position: 'relative' }}>
                {/* View Mode Toggle and Segment Navigation */}
                {jobId && (
                  <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                    <Box sx={{ p: 2 }}>
                      <Stack direction="row" justifyContent="space-between" alignItems="center">
                        <Stack direction="row" spacing={2} alignItems="center">
                          <Typography variant="body2" color="text.secondary">보기 모드:</Typography>
                          <Chip
                            label="전체 보기"
                            onClick={() => setViewMode('full')}
                            color={viewMode === 'full' ? 'primary' : 'default'}
                            variant={viewMode === 'full' ? 'filled' : 'outlined'}
                            size="small"
                          />
                          <Chip
                            label="세그먼트 보기"
                            onClick={() => setViewMode('segment')}
                            color={viewMode === 'segment' ? 'primary' : 'default'}
                            variant={viewMode === 'segment' ? 'filled' : 'outlined'}
                            size="small"
                            disabled={!validationReport && !postEditLog && (!translationSegments?.segments || translationSegments.segments.length === 0)}
                          />
                        </Stack>
                        
                        {viewMode === 'segment' && segmentNav.totalSegments > 0 && (
                          <Stack direction="row" spacing={1} alignItems="center">
                            {tabValue === 1 && validationReport && segmentNav.hasErrors && (
                              <>
                                <Tooltip title="이전 오류">
                                  <IconButton 
                                    onClick={segmentNav.goToPreviousError}
                                    disabled={segmentNav.segmentsWithErrors.length === 0}
                                    size="small"
                                    color="warning"
                                  >
                                    <NavigateBeforeIcon />
                                  </IconButton>
                                </Tooltip>
                                <Box sx={{ 
                                  px: 1.5, 
                                  py: 0.5, 
                                  bgcolor: 'warning.main',
                                  color: 'white',
                                  borderRadius: 1,
                                  fontSize: '0.75rem',
                                  fontWeight: 'medium',
                                }}>
                                  오류 {segmentNav.segmentsWithErrors.indexOf(segmentNav.currentSegmentIndex) + 1}/{segmentNav.segmentsWithErrors.length}
                                </Box>
                                <Tooltip title="다음 오류">
                                  <IconButton 
                                    onClick={segmentNav.goToNextError}
                                    disabled={segmentNav.segmentsWithErrors.length === 0}
                                    size="small"
                                    color="warning"
                                  >
                                    <NavigateNextIcon />
                                  </IconButton>
                                </Tooltip>
                                <Box sx={{ width: 1, height: 24, borderLeft: 1, borderColor: 'divider', mx: 0.5 }} />
                              </>
                            )}
                            
                            <IconButton 
                              onClick={() => segmentNav.goToSegment(0)}
                              disabled={segmentNav.currentSegmentIndex === 0}
                              size="small"
                            >
                              <FirstPageIcon />
                            </IconButton>
                            <IconButton 
                              onClick={() => segmentNav.goToSegment(Math.max(0, segmentNav.currentSegmentIndex - 1))}
                              disabled={segmentNav.currentSegmentIndex === 0}
                              size="small"
                            >
                              <NavigateBeforeIcon />
                            </IconButton>
                            <Box sx={{ 
                              px: 2, 
                              py: 0.5, 
                              bgcolor: 'primary.main',
                              color: 'primary.contrastText',
                              borderRadius: 1,
                              minWidth: 80,
                              textAlign: 'center',
                            }}>
                              <Typography variant="caption" fontWeight="medium">
                                {segmentNav.currentSegmentIndex + 1} / {segmentNav.totalSegments}
                              </Typography>
                            </Box>
                            <IconButton 
                              onClick={() => segmentNav.goToSegment(Math.min(segmentNav.totalSegments - 1, segmentNav.currentSegmentIndex + 1))}
                              disabled={segmentNav.currentSegmentIndex >= segmentNav.totalSegments - 1}
                              size="small"
                            >
                              <NavigateNextIcon />
                            </IconButton>
                            <IconButton 
                              onClick={() => segmentNav.goToSegment(segmentNav.totalSegments - 1)}
                              disabled={segmentNav.currentSegmentIndex >= segmentNav.totalSegments - 1}
                              size="small"
                            >
                              <LastPageIcon />
                            </IconButton>
                          </Stack>
                        )}
                      </Stack>
                    </Box>
                    
                    {tabValue === 1 && viewMode === 'segment' && validationReport && (
                      <Box sx={{ px: 2, pb: 2 }}>
                        <Stack direction="row" spacing={1} alignItems="center">
                          <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>
                            오류 필터:
                          </Typography>
                          <Chip
                            icon={<ErrorIcon />}
                            label={`중요 (${validationReport.summary.total_critical_issues})`}
                            size="small"
                            color={errorFilters.critical ? 'error' : 'default'}
                            onClick={() => setErrorFilters(prev => ({ ...prev, critical: !prev.critical }))}
                            variant={errorFilters.critical ? 'filled' : 'outlined'}
                          />
                          <Chip
                            icon={<ContentCopyIcon />}
                            label={`누락 (${validationReport.summary.total_missing_content})`}
                            size="small"
                            color={errorFilters.missingContent ? 'warning' : 'default'}
                            onClick={() => setErrorFilters(prev => ({ ...prev, missingContent: !prev.missingContent }))}
                            variant={errorFilters.missingContent ? 'filled' : 'outlined'}
                          />
                          <Chip
                            icon={<AddCircleIcon />}
                            label={`추가 (${validationReport.summary.total_added_content})`}
                            size="small"
                            color={errorFilters.addedContent ? 'info' : 'default'}
                            onClick={() => setErrorFilters(prev => ({ ...prev, addedContent: !prev.addedContent }))}
                            variant={errorFilters.addedContent ? 'filled' : 'outlined'}
                          />
                          <Chip
                            icon={<PersonIcon />}
                            label={`이름 (${validationReport.summary.total_name_inconsistencies})`}
                            size="small"
                            color={errorFilters.nameInconsistencies ? 'secondary' : 'default'}
                            onClick={() => setErrorFilters(prev => ({ ...prev, nameInconsistencies: !prev.nameInconsistencies }))}
                            variant={errorFilters.nameInconsistencies ? 'filled' : 'outlined'}
                          />
                        </Stack>
                      </Box>
                    )}
                  </Box>
                )}
                
                <Box sx={{ p: 3 }}>
                  {loading && (
                    <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                      <CircularProgress />
                    </Box>
                  )}
                  
                  {error && (
                    <Alert severity="error" sx={{ mb: 2 }}>
                      <AlertTitle>오류</AlertTitle>
                      {error}
                    </Alert>
                  )}
                  
                  {!loading && !translationContent && !validationReport && !postEditLog && tabValue !== 0 && (
                    <Alert severity="info">
                      <AlertTitle>데이터 없음</AlertTitle>
                      번역이 아직 완료되지 않았습니다.
                    </Alert>
                  )}
                  
                  <TabPanel value={tabValue} index={0}>
                    {viewMode === 'segment' ? (
                      validationReport || postEditLog || (translationSegments?.segments && translationSegments.segments.length > 0) ? (
                        <SegmentViewer
                          mode="translation"
                          currentSegmentIndex={segmentNav.currentSegmentIndex}
                          validationReport={validationReport}
                          postEditLog={postEditLog}
                          translationContent={translationContent?.content || null}
                          translationSegments={translationSegments}
                        />
                      ) : (
                        <Alert severity="info">
                          <AlertTitle>세그먼트 보기 사용 불가</AlertTitle>
                          이 번역 작업은 세그먼트 저장 기능이 구현되기 전에 완료되었습니다. 
                          세그먼트 보기를 사용하려면 검증(Validation) 또는 포스트 에디팅을 실행해 주세요.
                        </Alert>
                      )
                    ) : viewMode === 'full' && translationContent ? (
                      <TranslationContentViewer 
                        content={translationContent} 
                        sourceText={fullSourceText}
                      />
                    ) : translationContent ? (
                      <TranslationContentViewer 
                        content={translationContent} 
                        sourceText={fullSourceText}
                      />
                    ) : selectedJob?.status === 'COMPLETED' ? (
                      <Stack spacing={2}>
                        <Alert severity="warning">
                          <AlertTitle>번역 결과를 찾을 수 없습니다</AlertTitle>
                          번역이 완료되었지만 결과를 불러올 수 없습니다.
                        </Alert>
                        <Button 
                          variant="contained" 
                          onClick={loadData}
                          startIcon={<RefreshIcon />}
                        >
                          결과 다시 불러오기
                        </Button>
                      </Stack>
                    ) : (
                      <Alert severity="info">
                        번역이 완료되면 결과가 여기에 표시됩니다.
                      </Alert>
                    )}
                  </TabPanel>
                  
                  <TabPanel value={tabValue} index={1}>
                    {viewMode === 'segment' && validationReport ? (
                      <SegmentViewer
                        mode="validation"
                        currentSegmentIndex={segmentNav.currentSegmentIndex}
                        validationReport={validationReport}
                        postEditLog={postEditLog}
                        translationSegments={translationSegments}
                        errorFilters={errorFilters}
                      />
                    ) : validationReport ? (
                      <ValidationReportViewer 
                        report={validationReport}
                        selectedIssues={selectedIssues}
                        onIssueSelectionChange={(segmentIndex, issueType, issueIndex, selected) => {
                          setSelectedIssues(prev => {
                            const newState = { ...prev };
                            
                            if (!newState[segmentIndex]) {
                              const segment = validationReport?.detailed_results.find(r => r.segment_index === segmentIndex);
                              if (!segment) return prev;
                              
                              newState[segmentIndex] = {
                                critical: new Array(segment.critical_issues.length).fill(true),
                                missing_content: new Array(segment.missing_content.length).fill(true),
                                added_content: new Array(segment.added_content.length).fill(true),
                                name_inconsistencies: new Array(segment.name_inconsistencies.length).fill(true),
                                minor: new Array(segment.minor_issues.length).fill(true),
                              };
                            }
                            
                            if (!newState[segmentIndex][issueType]) {
                              return prev;
                            }
                            
                            newState[segmentIndex] = {
                              ...newState[segmentIndex],
                              [issueType]: newState[segmentIndex][issueType].map((val, idx) => 
                                idx === issueIndex ? selected : val
                              )
                            };
                            
                            return newState;
                          });
                        }}
                        onSegmentClick={(index) => {
                          setViewMode('segment');
                          segmentNav.goToSegment(index);
                        }}
                      />
                    ) : selectedJob?.validation_status === 'COMPLETED' ? (
                      <Stack spacing={2}>
                        <Alert severity="warning">
                          <AlertTitle>검증 보고서를 찾을 수 없습니다</AlertTitle>
                          검증이 완료되었지만 보고서를 불러올 수 없습니다.
                        </Alert>
                        <Button 
                          variant="contained" 
                          onClick={loadData}
                          startIcon={<RefreshIcon />}
                        >
                          보고서 다시 불러오기
                        </Button>
                      </Stack>
                    ) : (
                      <Alert severity="info">
                        검증을 실행하면 결과가 여기에 표시됩니다.
                      </Alert>
                    )}
                  </TabPanel>
                  
                  <TabPanel value={tabValue} index={2}>
                    {viewMode === 'segment' && postEditLog ? (
                      <SegmentViewer
                        mode="post-edit"
                        currentSegmentIndex={segmentNav.currentSegmentIndex}
                        validationReport={validationReport}
                        postEditLog={postEditLog}
                        translationSegments={translationSegments}
                      />
                    ) : postEditLog ? (
                      <PostEditLogViewer 
                        log={postEditLog}
                        onSegmentClick={(index) => {
                          setViewMode('segment');
                          segmentNav.goToSegment(index);
                        }}
                      />
                    ) : null}
                  </TabPanel>
                </Box>
              </Box>
            </Paper>
          )}
        </Container>
      </Box>
    </Box>

    {/* Dialogs */}
    <ValidationDialog
        open={validation.validationDialogOpen}
        onClose={() => validation.setValidationDialogOpen(false)}
        onConfirm={validation.handleTriggerValidation}
        quickValidation={validation.quickValidation}
        onQuickValidationChange={validation.setQuickValidation}
        validationSampleRate={validation.validationSampleRate}
        onValidationSampleRateChange={validation.setValidationSampleRate}
        loading={validation.loading}
      />

      <PostEditDialog
        open={postEdit.postEditDialogOpen}
        onClose={() => postEdit.setPostEditDialogOpen(false)}
        onConfirm={postEdit.handleTriggerPostEdit}
        selectedIssueTypes={postEdit.selectedIssueTypes}
        onIssueTypeChange={(issueType, checked) => 
          postEdit.setSelectedIssueTypes({ ...postEdit.selectedIssueTypes, [issueType]: checked })
        }
        validationReport={validationReport}
        loading={postEdit.loading}
        selectedCounts={selectedCounts}
    />
  </>
  );
}

export default function CanvasPage() {
  return (
    <Suspense fallback={
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    }>
      <CanvasContent />
    </Suspense>
  );
}
