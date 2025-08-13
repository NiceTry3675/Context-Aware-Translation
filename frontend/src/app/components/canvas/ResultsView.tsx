'use client';

import React from 'react';
import {
  Box,
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
  Chip,
  Tooltip,
} from '@mui/material';
import AddCircleIcon from '@mui/icons-material/AddCircle';
import RefreshIcon from '@mui/icons-material/Refresh';
import FirstPageIcon from '@mui/icons-material/FirstPage';
import LastPageIcon from '@mui/icons-material/LastPage';
import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import ErrorIcon from '@mui/icons-material/Error';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import PersonIcon from '@mui/icons-material/Person';
import StructuredValidationExplorer from '../validation/StructuredValidationExplorer';
import PostEditLogViewer from '../PostEditLogViewer';
import TranslationContentViewer from '../TranslationContentViewer';
import InfiniteScrollTranslationViewer from '../InfiniteScrollTranslationViewer';
import SegmentViewer from './SegmentViewer';

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
      style={{ height: '100%', display: value === index ? 'flex' : 'none', flexDirection: 'column' }}
      {...other}
    >
      {value === index && <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'auto' }}>{children}</Box>}
    </div>
  );
}

interface ResultsViewProps {
  jobId: string | null;
  selectedJob: any;
  tabValue: number;
  viewMode: 'full' | 'segment';
  errorFilters: {
    critical: boolean;
    missingContent: boolean;
    addedContent: boolean;
    nameInconsistencies: boolean;
  };
  isPolling: boolean;
  dataLoading: boolean;
  error: string | null;
  loading: boolean;
  validationReport: any;
  postEditLog: any;
  translationContent: any;
  translationSegments: any;
  fullSourceText: string | undefined;
  selectedIssues: any;
  segmentNav: any;
  onTabChange: (event: React.SyntheticEvent, newValue: number) => void;
  onViewModeChange: (mode: 'full' | 'segment') => void;
  onErrorFiltersChange: (filters: any) => void;
  onShowNewTranslation: () => void;
  onLoadData: () => void;
  onLoadMoreSegments?: (offset: number, limit: number) => Promise<{
    segments: any[];
    has_more: boolean;
    total_segments: number;
  }>;
  onIssueSelectionChange: (
    segmentIndex: number,
    issueType: string,
    issueIndex: number,
    selected: boolean
  ) => void;
  onSegmentClick: (index: number) => void;
}

export default function ResultsView({
  jobId,
  selectedJob,
  tabValue,
  viewMode,
  errorFilters,
  isPolling,
  dataLoading,
  error,
  loading,
  validationReport,
  postEditLog,
  translationContent,
  translationSegments,
  fullSourceText,
  selectedIssues,
  segmentNav,
  onTabChange,
  onViewModeChange,
  onErrorFiltersChange,
  onShowNewTranslation,
  onLoadData,
  onLoadMoreSegments,
  onIssueSelectionChange,
  onSegmentClick,
}: ResultsViewProps) {
  // Selection state for structured cases (segment-indexed)
  const [selectedCases, setSelectedCases] = React.useState<Record<number, boolean[]>>({});
  const handleCaseSelectionChange = React.useCallback((segmentIndex: number, caseIndex: number, selected: boolean, totalCases: number) => {
    setSelectedCases(prev => {
      const next = { ...prev };
      const arr = next[segmentIndex] ? next[segmentIndex].slice() : new Array(totalCases).fill(true);
      arr[caseIndex] = selected;
      next[segmentIndex] = arr;
      return next;
    });
  }, []);

  return (
    <Paper sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Box sx={{ px: 2, pt: 1 }}>
        <Button
          variant="outlined"
          startIcon={<AddCircleIcon />}
          onClick={onShowNewTranslation}
          size="small"
          sx={{ mb: 1 }}
        >
          새 번역 시작
        </Button>
      </Box>
      
      <Box sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}>
        <Tabs value={tabValue} onChange={onTabChange}>
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

      <Box sx={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {jobId && (
          <Box sx={{ borderBottom: 1, borderColor: 'divider', flexShrink: 0 }}>
            <Box sx={{ p: 2 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Stack direction="row" spacing={2} alignItems="center">
                  <Typography variant="body2" color="text.secondary">보기 모드:</Typography>
                  <Chip
                    label="전체 보기"
                    onClick={() => onViewModeChange('full')}
                    color={viewMode === 'full' ? 'primary' : 'default'}
                    variant={viewMode === 'full' ? 'filled' : 'outlined'}
                    size="small"
                  />
                  <Chip
                    label="세그먼트 보기"
                    onClick={() => onViewModeChange('segment')}
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
                          px: 2, 
                          py: 0.5, 
                          bgcolor: 'warning.main',
                          color: 'black',
                          borderRadius: 1,
                          fontSize: '0.75rem',
                          fontWeight: 'medium',
                          minWidth: 100,
                          textAlign: 'center',
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
                      minWidth: 100,
                      textAlign: 'center',
                    }}>
                      <Typography variant="body2" fontWeight="medium">
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
                  {(() => {
                    const sev = validationReport.summary.case_counts_by_severity || { '1': 0, '2': 0, '3': 0 };
                    const dim = validationReport.summary.case_counts_by_dimension || {};
                    return (
                      <>
                        <Chip
                          icon={<ErrorIcon />}
                          label={`중요 (${sev['3'] || 0})`}
                          size="small"
                          color={errorFilters.critical ? 'error' : 'default'}
                          onClick={() => onErrorFiltersChange({ ...errorFilters, critical: !errorFilters.critical })}
                          variant={errorFilters.critical ? 'filled' : 'outlined'}
                        />
                        <Chip
                          icon={<ContentCopyIcon />}
                          label={`누락 (${dim['completeness'] || 0})`}
                          size="small"
                          color={errorFilters.missingContent ? 'warning' : 'default'}
                          onClick={() => onErrorFiltersChange({ ...errorFilters, missingContent: !errorFilters.missingContent })}
                          variant={errorFilters.missingContent ? 'filled' : 'outlined'}
                        />
                        <Chip
                          icon={<AddCircleIcon />}
                          label={`추가 (${dim['addition'] || 0})`}
                          size="small"
                          color={errorFilters.addedContent ? 'info' : 'default'}
                          onClick={() => onErrorFiltersChange({ ...errorFilters, addedContent: !errorFilters.addedContent })}
                          variant={errorFilters.addedContent ? 'filled' : 'outlined'}
                        />
                        <Chip
                          icon={<PersonIcon />}
                          label={`이름 (${dim['name_consistency'] || 0})`}
                          size="small"
                          color={errorFilters.nameInconsistencies ? 'secondary' : 'default'}
                          onClick={() => onErrorFiltersChange({ ...errorFilters, nameInconsistencies: !errorFilters.nameInconsistencies })}
                          variant={errorFilters.nameInconsistencies ? 'filled' : 'outlined'}
                        />
                      </>
                    );
                  })()}
                </Stack>
              </Box>
            )}
          </Box>
        )}
        
        <Box sx={{ p: 3, flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          {isPolling && (
            <Alert severity="info" sx={{ mb: 2 }}>
              <AlertTitle>작업 진행 중</AlertTitle>
              {selectedJob?.status === 'IN_PROGRESS' && `번역 작업이 진행 중입니다... (${selectedJob?.progress || 0}%)`}
              {selectedJob?.validation_status === 'IN_PROGRESS' && `검증 작업이 진행 중입니다... (${selectedJob?.validation_progress || 0}%)`}
              {selectedJob?.post_edit_status === 'IN_PROGRESS' && `포스트에디팅 작업이 진행 중입니다... (${selectedJob?.post_edit_progress || 0}%)`}
            </Alert>
          )}

          {dataLoading && !isPolling && (
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
              onLoadMoreSegments && jobId ? (
                <InfiniteScrollTranslationViewer 
                  content={translationContent} 
                  sourceText={fullSourceText}
                  segments={translationSegments}
                  postEditLog={postEditLog}
                  jobId={jobId}
                  onLoadMoreSegments={onLoadMoreSegments}
                />
              ) : (
                <TranslationContentViewer 
                  content={translationContent} 
                  sourceText={fullSourceText}
                  segments={translationSegments}
                  postEditLog={postEditLog}
                />
              )
            ) : translationContent ? (
              <TranslationContentViewer 
                content={translationContent} 
                sourceText={fullSourceText}
                segments={translationSegments}
                postEditLog={postEditLog}
              />
            ) : selectedJob?.status === 'COMPLETED' ? (
              <Stack spacing={2}>
                <Alert severity="warning">
                  <AlertTitle>번역 결과를 찾을 수 없습니다</AlertTitle>
                  번역이 완료되었지만 결과를 불러올 수 없습니다.
                </Alert>
                <Button 
                  variant="contained" 
                  onClick={onLoadData}
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
            {validationReport ? (
              <StructuredValidationExplorer 
                report={validationReport}
                onSegmentClick={onSegmentClick}
                selectedCases={selectedCases}
                onCaseSelectionChange={handleCaseSelectionChange}
              />
            ) : selectedJob?.validation_status === 'COMPLETED' ? (
              <Stack spacing={2}>
                <Alert severity="warning">
                  <AlertTitle>검증 보고서를 찾을 수 없습니다</AlertTitle>
                  검증이 완료되었지만 보고서를 불러올 수 없습니다.
                </Alert>
                <Button 
                  variant="contained" 
                  onClick={onLoadData}
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
            {postEditLog ? (
              <PostEditLogViewer 
                log={postEditLog}
                onSegmentClick={onSegmentClick}
              />
            ) : null}
          </TabPanel>
        </Box>
      </Box>
    </Paper>
  );
}