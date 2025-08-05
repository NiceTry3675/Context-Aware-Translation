'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  Tabs,
  Tab,
  Button,
  CircularProgress,
  Alert,
  AlertTitle,
  Stack,
  Divider,
  Chip,
  DialogTitle,
  DialogContent,
  DialogActions,
  Dialog,
  TextField,
  FormControlLabel,
  Checkbox,
  Slider,
  Tooltip,
  Paper,
  LinearProgress,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import RefreshIcon from '@mui/icons-material/Refresh';
import DownloadIcon from '@mui/icons-material/Download';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import AssessmentIcon from '@mui/icons-material/Assessment';
import EditNoteIcon from '@mui/icons-material/EditNote';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import PendingIcon from '@mui/icons-material/Pending';
import ErrorIcon from '@mui/icons-material/Error';
import ValidationReportViewer from './ValidationReportViewer';
import PostEditLogViewer from './PostEditLogViewer';
import {
  ValidationReport,
  PostEditLog,
  fetchValidationReport,
  fetchPostEditLog,
  triggerValidation,
  triggerPostEdit,
} from '../utils/api';

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
  const [validationReport, setValidationReport] = useState<ValidationReport | null>(null);
  const [postEditLog, setPostEditLog] = useState<PostEditLog | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationDialogOpen, setValidationDialogOpen] = useState(false);
  const [postEditDialogOpen, setPostEditDialogOpen] = useState(false);
  const [quickValidation, setQuickValidation] = useState(false);
  const [validationSampleRate, setValidationSampleRate] = useState(100);
  const [selectedIssueTypes, setSelectedIssueTypes] = useState({
    critical_issues: true,
    missing_content: true,
    added_content: true,
    name_inconsistencies: true,
  });
  const [selectedIssues, setSelectedIssues] = useState<{
    [segmentIndex: number]: {
      [issueType: string]: boolean[]
    }
  }>({});
  const { getToken } = useAuth();

  // Load data when sidebar opens or job changes
  useEffect(() => {
    if (open && jobId) {
      loadData();
    }
  }, [open, jobId, validationStatus, postEditStatus]);
  
  // Reload data when validation completes
  useEffect(() => {
    if (validationStatus === 'COMPLETED' && !validationReport) {
      loadData();
    }
  }, [validationStatus]);
  
  // Auto-select validation tab when report is loaded and initialize selected issues
  useEffect(() => {
    if (validationReport) {
      if (tabValue !== 0) {
        setTabValue(0);
      }
      
      // Initialize all issues as selected by default
      const initialSelection: typeof selectedIssues = {};
      validationReport.detailed_results.forEach((result) => {
        if (result.status === 'FAIL') {
          initialSelection[result.segment_index] = {
            critical_issues: new Array(result.critical_issues.length).fill(true),
            missing_content: new Array(result.missing_content.length).fill(true),
            added_content: new Array(result.added_content.length).fill(true),
            name_inconsistencies: new Array(result.name_inconsistencies.length).fill(true),
            minor_issues: new Array(result.minor_issues.length).fill(true),
          };
        }
      });
      setSelectedIssues(initialSelection);
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

  const loadData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = await getToken();
      
      // Load validation report if available
      if (validationStatus === 'COMPLETED') {
        console.log('Loading validation report for job:', jobId);
        const report = await fetchValidationReport(jobId, token || undefined);
        console.log('Validation report loaded:', report);
        setValidationReport(report);
      }
      
      // Load post-edit log if available
      if (postEditStatus === 'COMPLETED') {
        const log = await fetchPostEditLog(jobId, token || undefined);
        setPostEditLog(log);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '데이터를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerValidation = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = await getToken();
      await triggerValidation(jobId, token || undefined, quickValidation, validationSampleRate / 100);
      setValidationDialogOpen(false);
      onRefresh?.();
      // Show success message
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '검증 시작 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerPostEdit = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = await getToken();
      await triggerPostEdit(jobId, token || undefined, selectedIssueTypes, selectedIssues);
      setPostEditDialogOpen(false);
      onRefresh?.();
      // Show success message
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '포스트 에디팅 시작 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusChip = (status?: string, type: 'validation' | 'postedit' = 'validation') => {
    const label = type === 'validation' ? '검증' : '포스트 에디팅';
    
    if (!status || status === 'PENDING') {
      return <Chip size="small" label={`${label} 대기`} icon={<PendingIcon />} />;
    }
    if (status === 'IN_PROGRESS') {
      return <Chip size="small" label={`${label} 진행중`} icon={<CircularProgress size={16} />} color="primary" />;
    }
    if (status === 'COMPLETED') {
      return <Chip size="small" label={`${label} 완료`} icon={<CheckCircleIcon />} color="success" />;
    }
    if (status === 'FAILED') {
      return <Chip size="small" label={`${label} 실패`} icon={<ErrorIcon />} color="error" />;
    }
    return null;
  };

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
              {getStatusChip(validationStatus, 'validation')}
              {getStatusChip(postEditStatus, 'postedit')}
            </Stack>
          </Box>

          {/* Action Buttons */}
          <Paper elevation={0} sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
            <Stack spacing={2}>
              <Stack direction="row" spacing={2}>
                <Button
                  variant="outlined"
                  startIcon={<AssessmentIcon />}
                  onClick={() => setValidationDialogOpen(true)}
                  disabled={!canRunValidation || loading}
                >
                  검증 실행
                </Button>
                
                <Button
                  variant="outlined"
                  startIcon={<EditNoteIcon />}
                  onClick={() => setPostEditDialogOpen(true)}
                  disabled={!canRunPostEdit || loading}
                >
                  포스트 에디팅 실행
                </Button>
              
              {validationReport && (
                <Button
                  variant="text"
                  startIcon={<DownloadIcon />}
                  onClick={() => {
                    // Download validation report
                    const blob = new Blob([JSON.stringify(validationReport, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `validation_report_${jobId}.json`;
                    a.click();
                  }}
                >
                  검증 보고서 다운로드
                </Button>
              )}
              
              {postEditLog && (
                <Button
                  variant="text"
                  startIcon={<DownloadIcon />}
                  onClick={() => {
                    // Download post-edit log
                    const blob = new Blob([JSON.stringify(postEditLog, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `postedit_log_${jobId}.json`;
                    a.click();
                  }}
                >
                  수정 로그 다운로드
                </Button>
              )}
              </Stack>
              
              {/* Validation Progress Bar */}
              {validationStatus === 'IN_PROGRESS' && (
                <Box sx={{ mt: 2 }}>
                  <Stack direction="row" alignItems="center" spacing={2}>
                    <Typography variant="body2" color="text.secondary">
                      검증 진행중: {validationProgress !== undefined ? `${validationProgress}%` : '계산중...'}
                    </Typography>
                  </Stack>
                  <LinearProgress 
                    variant={validationProgress !== undefined ? "determinate" : "indeterminate"} 
                    value={validationProgress} 
                    sx={{ mt: 1 }}
                  />
                </Box>
              )}
            </Stack>
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
                    setSelectedIssues(prev => ({
                      ...prev,
                      [segmentIndex]: {
                        ...prev[segmentIndex],
                        [issueType]: prev[segmentIndex][issueType].map((val, idx) => 
                          idx === issueIndex ? selected : val
                        )
                      }
                    }));
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
      <Dialog open={validationDialogOpen} onClose={() => setValidationDialogOpen(false)}>
        <DialogTitle>검증 옵션</DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 1, minWidth: 400 }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={quickValidation}
                  onChange={(e) => setQuickValidation(e.target.checked)}
                />
              }
              label="빠른 검증 (중요한 문제만 검사)"
            />
            
            <Box>
              <Typography gutterBottom>
                검증 샘플 비율: {validationSampleRate}%
              </Typography>
              <Slider
                value={validationSampleRate}
                onChange={(e, v) => setValidationSampleRate(v as number)}
                min={10}
                max={100}
                step={10}
                marks
                valueLabelDisplay="auto"
              />
              <Typography variant="caption" color="text.secondary">
                전체 세그먼트 중 {validationSampleRate}%만 검증합니다.
              </Typography>
            </Box>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setValidationDialogOpen(false)}>취소</Button>
          <Button 
            onClick={handleTriggerValidation} 
            variant="contained" 
            disabled={loading}
            startIcon={loading ? <CircularProgress size={16} /> : <PlayArrowIcon />}
          >
            검증 시작
          </Button>
        </DialogActions>
      </Dialog>

      {/* Post-Edit Confirmation Dialog */}
      <Dialog open={postEditDialogOpen} onClose={() => setPostEditDialogOpen(false)}>
        <DialogTitle>포스트 에디팅 확인</DialogTitle>
        <DialogContent>
          <Alert severity="info" sx={{ mb: 2 }}>
            포스트 에디팅은 검증 결과를 바탕으로 AI가 자동으로 번역을 수정합니다.
          </Alert>
          {validationReport && (
            <Stack spacing={2}>
              <Typography variant="body2">
                발견된 문제:
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {validationReport.summary.total_critical_issues > 0 && (
                  <Chip size="small" label={`치명적 오류 ${validationReport.summary.total_critical_issues}개`} color="error" />
                )}
                {validationReport.summary.total_missing_content > 0 && (
                  <Chip size="small" label={`누락 내용 ${validationReport.summary.total_missing_content}개`} color="warning" />
                )}
                {validationReport.summary.total_added_content > 0 && (
                  <Chip size="small" label={`추가 내용 ${validationReport.summary.total_added_content}개`} color="warning" />
                )}
                {validationReport.summary.total_name_inconsistencies > 0 && (
                  <Chip size="small" label={`이름 불일치 ${validationReport.summary.total_name_inconsistencies}개`} color="info" />
                )}
              </Stack>
              
              <Divider />
              
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  수정할 문제 유형 선택:
                </Typography>
                <Stack spacing={1}>
                  {validationReport.summary.total_critical_issues > 0 && (
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={selectedIssueTypes.critical_issues}
                          onChange={(e) => setSelectedIssueTypes({
                            ...selectedIssueTypes,
                            critical_issues: e.target.checked
                          })}
                        />
                      }
                      label={`치명적 오류 (${validationReport.summary.total_critical_issues}개)`}
                    />
                  )}
                  {validationReport.summary.total_missing_content > 0 && (
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={selectedIssueTypes.missing_content}
                          onChange={(e) => setSelectedIssueTypes({
                            ...selectedIssueTypes,
                            missing_content: e.target.checked
                          })}
                        />
                      }
                      label={`누락된 내용 (${validationReport.summary.total_missing_content}개)`}
                    />
                  )}
                  {validationReport.summary.total_added_content > 0 && (
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={selectedIssueTypes.added_content}
                          onChange={(e) => setSelectedIssueTypes({
                            ...selectedIssueTypes,
                            added_content: e.target.checked
                          })}
                        />
                      }
                      label={`추가된 내용 (${validationReport.summary.total_added_content}개)`}
                    />
                  )}
                  {validationReport.summary.total_name_inconsistencies > 0 && (
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={selectedIssueTypes.name_inconsistencies}
                          onChange={(e) => setSelectedIssueTypes({
                            ...selectedIssueTypes,
                            name_inconsistencies: e.target.checked
                          })}
                        />
                      }
                      label={`이름 불일치 (${validationReport.summary.total_name_inconsistencies}개)`}
                    />
                  )}
                </Stack>
              </Box>
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPostEditDialogOpen(false)}>취소</Button>
          <Button 
            onClick={handleTriggerPostEdit} 
            variant="contained" 
            disabled={loading || !Object.values(selectedIssueTypes).some(v => v)}
            startIcon={loading ? <CircularProgress size={16} /> : <PlayArrowIcon />}
          >
            포스트 에디팅 시작
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}