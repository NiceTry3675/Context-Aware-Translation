'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  Tabs,
  Tab,
  Alert,
  AlertTitle,
  Stack,
  CircularProgress,
  Paper,
  Tooltip,
  Button,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import RefreshIcon from '@mui/icons-material/Refresh';
import StructuredValidationExplorer from '../validation/StructuredValidationExplorer';
import PostEditLogViewer from '../PostEditLogViewer';
import TranslationContentViewer from '../TranslationContentViewer';

// Import extracted components
import ValidationDialog from './ValidationDialog';
import PostEditDialog from './PostEditDialog';
import StatusChips from './StatusChips';
import ActionButtons from './ActionButtons';

// Import custom hooks
import { useTranslationData } from './hooks/useTranslationData';
import { useValidation } from './hooks/useValidation';
import { usePostEdit } from './hooks/usePostEdit';
import { useApiKey } from '../../hooks/useApiKey';

interface TranslationSidebarProps {
  open: boolean;
  onClose: () => void;
  jobId: string;
  jobStatus: string;
  validationStatus?: string;
  postEditStatus?: string;
  validationProgress?: number;
  postEditProgress?: number;
  onRefresh?: () => void;
}

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
      id={`sidebar-tabpanel-${index}`}
      aria-labelledby={`sidebar-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 2 }}>{children}</Box>}
    </div>
  );
}

export default function TranslationSidebar({
  open,
  onClose,
  jobId,
  jobStatus,
  validationStatus,
  postEditStatus,
  validationProgress,
  postEditProgress,
  onRefresh,
}: TranslationSidebarProps) {
  const [tabValue, setTabValue] = useState(0);
  const { apiProvider, selectedModel } = useApiKey();
  
  // Use custom hooks
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
  } = useTranslationData({ open, jobId, jobStatus, validationStatus, postEditStatus });

  // Structured case selection state (segment-indexed)
  const [selectedCases, setSelectedCases] = useState<Record<number, boolean[]>>({});
  const [modifiedCases, setModifiedCases] = useState<Record<number, Array<{ reason?: string; recommend_korean_sentence?: string }>>>({});
  const editTimersRef = useRef<Record<string, any>>({});
  const handleCaseSelectionChange = (segmentIndex: number, caseIndex: number, selected: boolean, totalCases: number) => {
    setSelectedCases(prev => {
      const next = { ...prev };
      const arr = next[segmentIndex] ? next[segmentIndex].slice() : new Array(totalCases).fill(true);
      arr[caseIndex] = selected;
      next[segmentIndex] = arr;
      return next;
    });
  };

  const validation = useValidation({ jobId, onRefresh, apiProvider, defaultModelName: selectedModel });
  const postEdit = usePostEdit({ jobId, onRefresh, selectedCases, modifiedCases, apiProvider, defaultModelName: selectedModel });

  // Combine loading states
  const loading = dataLoading || validation.loading || postEdit.loading;
  const error = dataError || validation.error || postEdit.error;

  // Auto-select validation tab when report is loaded
  useEffect(() => {
    if (validationReport && tabValue !== 0) {
      setTabValue(0);
    }
  }, [validationReport, tabValue]);

  // Keep UI light: do not auto-refresh validation sidebar; user clicks refresh when needed

  const canRunValidation = jobStatus === 'COMPLETED' && (!validationStatus || validationStatus === 'FAILED');
  const canRunPostEdit = validationStatus === 'COMPLETED' && (!postEditStatus || postEditStatus === 'FAILED');

  // Calculate selected case counts (structured-only)
  const selectedCounts = {
    total: Object.values(selectedCases).reduce((acc, arr) => acc + (arr?.filter(Boolean).length || 0), 0)
  };


  return (
    <>
      <Drawer
        anchor="right"
        open={open}
        onClose={onClose}
        sx={{
          '& .MuiDrawer-paper': {
            width: { xs: '100%', sm: '80%', md: '60%', lg: '50%' },
            maxWidth: '800px',
          },
        }}
      >
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          {/* Header */}
          <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Typography variant="h6">
                번역 작업 상세
              </Typography>
              <Stack direction="row" spacing={1}>
                <Tooltip title="새로고침">
                  <IconButton onClick={loadData}>
                    <RefreshIcon />
                  </IconButton>
                </Tooltip>
                <IconButton onClick={onClose}>
                  <CloseIcon />
                </IconButton>
              </Stack>
            </Stack>
            
            {/* Status Chips */}
            <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
              <StatusChips validationStatus={validationStatus} postEditStatus={postEditStatus} />
            </Stack>
          </Box>

          {/* Action Buttons */}
          <Paper elevation={0} sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
            <ActionButtons
              canRunValidation={canRunValidation}
              canRunPostEdit={canRunPostEdit}
              onValidationClick={() => validation.setValidationDialogOpen(true)}
              onPostEditClick={() => postEdit.setPostEditDialogOpen(true)}
              validationReport={validationReport}
              postEditLog={postEditLog}
              jobId={jobId}
              loading={loading}
              validationStatus={validationStatus}
              validationProgress={validationProgress}
              postEditStatus={postEditStatus}
              postEditProgress={postEditProgress}
            />
          </Paper>

          {/* Tabs */}
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
              <Tab 
                label="번역 결과"
                disabled={!translationContent && jobStatus !== 'COMPLETED'} 
              />
              <Tab 
                label="검증 결과"
                disabled={!validationReport && validationStatus !== 'COMPLETED'} 
              />
              <Tab 
                label="포스트 에디팅"
                disabled={!postEditLog && postEditStatus !== 'COMPLETED'} 
              />
            </Tabs>
          </Box>

          {/* Content */}
          <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
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
              {translationContent ? (
                <TranslationContentViewer 
                  content={translationContent} 
                  segments={translationSegments}
                  postEditLog={postEditLog}
                />
              ) : jobStatus === 'COMPLETED' ? (
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
              {loading && validationStatus === 'COMPLETED' && !validationReport ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                  <CircularProgress />
                  <Typography sx={{ ml: 2 }}>검증 보고서 불러오는 중...</Typography>
                </Box>
              ) : validationReport ? (
                <StructuredValidationExplorer 
                  report={validationReport}
                  onSegmentClick={(index) => console.log('Segment clicked:', index)}
                  selectedCases={selectedCases}
                  onCaseSelectionChange={handleCaseSelectionChange}
                  modifiedCases={modifiedCases}
                  onCaseEditChange={(segmentIndex, caseIndex, patch) => {
                    const key = `${segmentIndex}:${caseIndex}`;
                    if (editTimersRef.current[key]) clearTimeout(editTimersRef.current[key]);
                    editTimersRef.current[key] = setTimeout(() => {
                      setModifiedCases(prev => {
                        const next = { ...prev } as Record<number, Array<{ reason?: string; recommend_korean_sentence?: string }>>;
                        const arr = next[segmentIndex] ? next[segmentIndex].slice() : [];
                        while (arr.length <= caseIndex) arr.push({});
                        const current = { ...(arr[caseIndex] || {}) };
                        arr[caseIndex] = { ...current, ...patch };
                        next[segmentIndex] = arr;
                        return next;
                      });
                    }, 250);
                  }}
                />
              ) : validationStatus === 'COMPLETED' ? (
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
              {postEditLog && (
                <PostEditLogViewer 
                  log={postEditLog}
                  onSegmentClick={(index) => {
                    // Handle segment click if needed
                    console.log('Segment clicked:', index);
                  }}
                />
              )}
            </TabPanel>
          </Box>
        </Box>
      </Drawer>

      {/* Validation Options Dialog */}
      <ValidationDialog
        open={validation.validationDialogOpen}
        onClose={() => validation.setValidationDialogOpen(false)}
        onConfirm={validation.handleTriggerValidation}
        quickValidation={validation.quickValidation}
        onQuickValidationChange={validation.setQuickValidation}
        validationSampleRate={validation.validationSampleRate}
        onValidationSampleRateChange={validation.setValidationSampleRate}
        loading={validation.loading}
        apiProvider={validation.apiProvider}
        modelName={validation.modelName}
        onModelNameChange={validation.setModelName}
      />

      {/* Post-Edit Confirmation Dialog */}
      <PostEditDialog
        open={postEdit.postEditDialogOpen}
        onClose={() => postEdit.setPostEditDialogOpen(false)}
        onConfirm={postEdit.handleTriggerPostEdit}
        validationReport={validationReport}
        loading={postEdit.loading}
        selectedCounts={{ total: Object.values(selectedCases).reduce((acc, arr)=> acc + (arr?.filter(Boolean).length || 0), 0) }}
        apiProvider={postEdit.apiProvider}
        modelName={postEdit.modelName}
        onModelNameChange={postEdit.setModelName}
      />
    </>
  );
}
