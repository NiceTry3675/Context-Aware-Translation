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
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import FullscreenIcon from '@mui/icons-material/Fullscreen';
import FullscreenExitIcon from '@mui/icons-material/FullscreenExit';

// Import viewer components
import ValidationReportViewer from '../components/ValidationReportViewer';
import PostEditLogViewer from '../components/PostEditLogViewer';
import TranslationContentViewer from '../components/TranslationContentViewer';
import JobSidebar from '../components/canvas/JobSidebar';
import SegmentViewer from '../components/canvas/SegmentViewer';
import ErrorNavigationBar from '../components/canvas/ErrorNavigationBar';
import SegmentNavigation from '../components/canvas/SegmentNavigation';

// Import action components from sidebar
import ValidationDialog from '../components/TranslationSidebar/ValidationDialog';
import PostEditDialog from '../components/TranslationSidebar/PostEditDialog';

// Import hooks
import { useTranslationData } from '../components/TranslationSidebar/hooks/useTranslationData';
import { useValidation } from '../components/TranslationSidebar/hooks/useValidation';
import { usePostEdit } from '../components/TranslationSidebar/hooks/usePostEdit';
import { useTranslationJobs } from '../hooks/useTranslationJobs';
import { useSegmentNavigation } from '../components/TranslationSidebar/hooks/useSegmentNavigation';

// Types
import { Job } from '../types/job';

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
  const { isSignedIn } = useAuth();
  
  const jobId = searchParams.get('jobId');
  const [tabValue, setTabValue] = useState(0);
  const [fullscreen, setFullscreen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [viewMode, setViewMode] = useState<'full' | 'segment'>('segment'); // New view mode state
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const { jobs, refreshJobs } = useTranslationJobs({ apiUrl: API_URL });
  
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
    // Don't use validation report as it only has truncated source_preview
    return undefined;
  }, [translationContent, postEditLog]);

  // Combine loading states
  const loading = dataLoading || validation.loading || postEdit.loading;
  const error = dataError || validation.error || postEdit.error;

  // Load saved tab preference
  useEffect(() => {
    const savedTab = localStorage.getItem('canvasTabValue');
    if (savedTab) {
      setTabValue(parseInt(savedTab));
    }
  }, []);

  // Save tab preference
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    localStorage.setItem('canvasTabValue', newValue.toString());
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
    router.push(`/canvas?jobId=${newJobId}`);
  };
  
  // Handle new translation
  const handleNewTranslation = () => {
    router.push('/?action=new');
  };
  
  // Handle job deletion
  const handleJobDelete = async (jobIdToDelete: number) => {
    try {
      // Call delete API
      const response = await fetch(`${API_URL}/api/v1/jobs/${jobIdToDelete}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        refreshJobs();
        // If deleted job was selected, clear selection
        if (jobIdToDelete.toString() === jobId) {
          router.push('/canvas');
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
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="warning">
          <AlertTitle>로그인 필요</AlertTitle>
          이 페이지를 보려면 로그인이 필요합니다.
          <Button 
            variant="contained" 
            sx={{ ml: 2 }} 
            onClick={() => router.push('/')}
          >
            메인 페이지로 이동
          </Button>
        </Alert>
      </Container>
    );
  }

  // Remove the early return for no jobId - we'll handle it in the main layout

  return (
    <>
      <Box sx={{ 
        height: '100vh', 
        display: 'flex', 
        backgroundColor: 'background.default' 
      }}>
      {/* Left Sidebar */}
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
                    <IconButton onClick={() => { refreshJobs(); loadData(); }}>
                      <RefreshIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title={fullscreen ? "전체화면 종료" : "전체화면"}>
                    <IconButton onClick={() => setFullscreen(!fullscreen)}>
                      {fullscreen ? <FullscreenExitIcon /> : <FullscreenIcon />}
                    </IconButton>
                  </Tooltip>
                </Stack>
              </Stack>
            </Box>
          </Container>
        </Paper>

        {/* Main Content Area */}
        <Container maxWidth={false} sx={{ flex: 1, display: 'flex', py: 2, gap: 2, overflow: 'hidden' }}>
          {/* Check if job is selected */}
          {!jobId ? (
            <Paper sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Box sx={{ textAlign: 'center', p: 4 }}>
                <Typography variant="h5" gutterBottom>
                  번역 작업을 선택하거나 새로 시작하세요
                </Typography>
                <Typography color="text.secondary" paragraph>
                  왼쪽 사이드바에서 기존 작업을 선택하거나 &ldquo;새 번역 시작&rdquo; 버튼을 클릭하세요.
                </Typography>
                <Button
                  variant="contained"
                  size="large"
                  onClick={handleNewTranslation}
                  sx={{ mt: 2 }}
                >
                  새 번역 시작
                </Button>
              </Box>
            </Paper>
          ) : (
              <Paper sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                {/* Main Canvas */}
          {/* Tabs */}
          <Box sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}>
            <Tabs value={tabValue} onChange={handleTabChange}>
              <Tab 
                label="번역 결과"
                disabled={!translationContent && selectedJob?.status !== 'COMPLETED'} 
              />
              <Tab 
                label="검증 결과"
                disabled={!validationReport && selectedJob?.validation_status !== 'COMPLETED'} 
              />
              <Tab 
                label="포스트 에디팅"
                disabled={!postEditLog && selectedJob?.post_edit_status !== 'COMPLETED'} 
              />
            </Tabs>
          </Box>

          {/* Tab Content */}
          <Box sx={{ flex: 1, overflow: 'auto', position: 'relative' }}>
            {/* Error Navigation Bar (shows when in segment view and validation data exists) */}
            {viewMode === 'segment' && validationReport && tabValue === 1 && (
              <ErrorNavigationBar
                validationReport={validationReport}
                currentSegmentIndex={segmentNav.currentSegmentIndex}
                onSegmentChange={segmentNav.goToSegment}
              />
            )}
            
            {/* View Mode Toggle */}
            <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
              <Stack direction="row" spacing={1} alignItems="center">
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
            </Box>
            
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
              
              {!loading && !translationContent && !validationReport && !postEditLog && (
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
            
            {/* Segment Navigation (shows when in segment view) */}
            {viewMode === 'segment' && segmentNav.totalSegments > 0 && (
              <SegmentNavigation
                currentSegmentIndex={segmentNav.currentSegmentIndex}
                totalSegments={segmentNav.totalSegments}
                onSegmentChange={segmentNav.goToSegment}
              />
            )}
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