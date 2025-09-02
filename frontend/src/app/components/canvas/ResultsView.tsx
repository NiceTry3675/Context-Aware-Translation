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
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import EditIcon from '@mui/icons-material/Edit';
import BrushIcon from '@mui/icons-material/Brush';
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
import IllustrationViewer from '../IllustrationViewer';
import CharacterBaseSelector from '../CharacterBaseSelector';

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
  apiKey?: string;
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
  selectedCases: Record<number, boolean[]>;
  onCaseSelectionChange: (
    segmentIndex: number,
    caseIndex: number,
    selected: boolean,
    totalCases: number
  ) => void;
  onOpenValidationDialog: () => void;
  onOpenPostEditDialog: () => void;
  onOpenIllustrationDialog: () => void;
}

export default function ResultsView({
  jobId,
  selectedJob,
  tabValue,
  viewMode,
  apiKey,
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
  selectedCases,
  onCaseSelectionChange,
  onOpenValidationDialog,
  onOpenPostEditDialog,
  onOpenIllustrationDialog,
}: ResultsViewProps) {
  const handleCaseSelectionChange = React.useCallback((segmentIndex: number, caseIndex: number, selected: boolean, totalCases: number) => {
    onCaseSelectionChange(segmentIndex, caseIndex, selected, totalCases);
  }, [onCaseSelectionChange]);

  const canRunValidation = selectedJob?.status === 'COMPLETED' && (!selectedJob?.validation_status || selectedJob?.validation_status === 'FAILED');
  const canRunPostEdit = selectedJob?.validation_status === 'COMPLETED' && (!selectedJob?.post_edit_status || selectedJob?.post_edit_status === 'FAILED');
  const canGenerateIllustrations = selectedJob?.status === 'COMPLETED' && selectedJob?.illustrations_status !== 'IN_PROGRESS';

  return (
    <Paper sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Box sx={{ px: 2, pt: 1 }}>
        <Stack direction="row" spacing={1} alignItems="center">
          <Button
            variant="outlined"
            startIcon={<AddCircleIcon />}
            onClick={onShowNewTranslation}
            size="small"
            sx={{ mb: 1 }}
          >
            새 번역 시작
          </Button>
          <Tooltip title={canRunValidation ? '검증 실행' : '번역 완료 후 실행 가능'}>
            <span>
              <Button
                variant="contained"
                color="success"
                size="small"
                startIcon={<CheckCircleIcon />}
                onClick={onOpenValidationDialog}
                disabled={!canRunValidation || selectedJob?.validation_status === 'IN_PROGRESS'}
                sx={{ mb: 1 }}
              >
                검증 실행
              </Button>
            </span>
          </Tooltip>
          <Tooltip title={canRunPostEdit ? '포스트에디팅 실행' : '검증 완료 후 실행 가능'}>
            <span>
              <Button
                variant="contained"
                color="info"
                size="small"
                startIcon={<EditIcon />}
                onClick={onOpenPostEditDialog}
                disabled={!canRunPostEdit || selectedJob?.post_edit_status === 'IN_PROGRESS'}
                sx={{ mb: 1 }}
              >
                포스트 에디팅 실행
              </Button>
            </span>
          </Tooltip>
          <Tooltip title={canGenerateIllustrations ? '삽화 생성' : '번역 완료 후 실행 가능'}>
            <span>
              <Button
                variant="contained"
                color="secondary"
                size="small"
                startIcon={<BrushIcon />}
                onClick={onOpenIllustrationDialog}
                disabled={!canGenerateIllustrations || selectedJob?.illustrations_status === 'IN_PROGRESS'}
                sx={{ mb: 1 }}
              >
                삽화 생성
              </Button>
            </span>
          </Tooltip>
        </Stack>
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
          <Tab 
            label="삽화"
            disabled={!jobId || selectedJob?.status !== 'COMPLETED'} 
          />
        </Tabs>
      </Box>

      <Box sx={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        
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
                currentSegmentIndex={segmentNav.currentSegmentIndex}
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
          
          <TabPanel value={tabValue} index={3}>
            {jobId && (
              <CharacterBaseSelector jobId={jobId} apiKey={apiKey} />
            )}
            {selectedJob?.illustrations_enabled ? (
              <IllustrationViewer
                jobId={jobId || ''}
                illustrations={selectedJob?.illustrations_data || []}
                status={selectedJob?.illustrations_status}
                count={selectedJob?.illustrations_count || 0}
                onGenerateIllustrations={onOpenIllustrationDialog}
              />
            ) : (
              <Alert severity="info">
                이 번역 작업에는 삽화 기능이 활성화되지 않았습니다.
              </Alert>
            )}
          </TabPanel>
        </Box>
      </Box>
    </Paper>
  );
}
