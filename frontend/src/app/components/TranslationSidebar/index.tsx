'use client';

import React, { useState, useEffect } from 'react';
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
import ValidationReportViewer from '../ValidationReportViewer';
import PostEditLogViewer from '../PostEditLogViewer';

// Import extracted components
import ValidationDialog from './ValidationDialog';
import PostEditDialog from './PostEditDialog';
import StatusChips from './StatusChips';
import ActionButtons from './ActionButtons';

// Import custom hooks
import { useTranslationData } from './hooks/useTranslationData';
import { useValidation } from './hooks/useValidation';
import { usePostEdit } from './hooks/usePostEdit';

interface TranslationSidebarProps {
  open: boolean;
  onClose: () => void;
  jobId: string;
  jobStatus: string;
  validationStatus?: string;
  postEditStatus?: string;
  validationProgress?: number;
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
  onRefresh,
}: TranslationSidebarProps) {
  const [tabValue, setTabValue] = useState(0);
  
  // Use custom hooks
  const {
    validationReport,
    postEditLog,
    loading: dataLoading,
    error: dataError,
    selectedIssues,
    setSelectedIssues,
    loadData,
  } = useTranslationData({ open, jobId, validationStatus, postEditStatus });

  const validation = useValidation({ jobId, onRefresh });
  const postEdit = usePostEdit({ jobId, onRefresh, selectedIssues });

  // Combine loading states
  const loading = dataLoading || validation.loading || postEdit.loading;
  const error = dataError || validation.error || postEdit.error;

  // Auto-select validation tab when report is loaded
  useEffect(() => {
    if (validationReport && tabValue !== 0) {
      setTabValue(0);
    }
  }, [validationReport]);

  // Auto-refresh when validation is in progress
  useEffect(() => {
    if (validationStatus === 'IN_PROGRESS' && onRefresh) {
      const interval = setInterval(() => {
        onRefresh();
      }, 2000); // Poll every 2 seconds

      return () => clearInterval(interval);
    }
  }, [validationStatus, onRefresh]);

  const canRunValidation = jobStatus === 'COMPLETED' && (!validationStatus || validationStatus === 'FAILED');
  const canRunPostEdit = validationStatus === 'COMPLETED' && (!postEditStatus || postEditStatus === 'FAILED');

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
            />
          </Paper>

          {/* Tabs */}
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
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
            
            {!loading && !validationReport && !postEditLog && (
              <Alert severity="info">
                <AlertTitle>데이터 없음</AlertTitle>
                아직 검증이나 포스트 에디팅이 수행되지 않았습니다.
                상단의 버튼을 사용하여 작업을 시작하세요.
              </Alert>
            )}
            
            <TabPanel value={tabValue} index={0}>
              {loading && validationStatus === 'COMPLETED' && !validationReport ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                  <CircularProgress />
                  <Typography sx={{ ml: 2 }}>검증 보고서 불러오는 중...</Typography>
                </Box>
              ) : validationReport ? (
                <ValidationReportViewer 
                  report={validationReport}
                  selectedIssues={selectedIssues}
                  onIssueSelectionChange={(segmentIndex, issueType, issueIndex, selected) => {
                    setSelectedIssues(prev => {
                      const newState = { ...prev };
                      
                      // Ensure the segment exists in the state
                      if (!newState[segmentIndex]) {
                        // Initialize the segment if it doesn't exist
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
                    // Handle segment click if needed
                    console.log('Segment clicked:', index);
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
            
            <TabPanel value={tabValue} index={1}>
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
      />

      {/* Post-Edit Confirmation Dialog */}
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
      />
    </>
  );
}