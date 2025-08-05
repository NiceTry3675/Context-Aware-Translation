'use client';

import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Stack,
  FormControlLabel,
  Checkbox,
  Typography,
  Alert,
  Chip,
  Box,
  Divider,
  CircularProgress,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import { ValidationReport } from '../../utils/api';

interface PostEditDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  selectedIssueTypes: {
    critical_issues: boolean;
    missing_content: boolean;
    added_content: boolean;
    name_inconsistencies: boolean;
  };
  onIssueTypeChange: (issueType: keyof PostEditDialogProps['selectedIssueTypes'], checked: boolean) => void;
  validationReport: ValidationReport | null;
  loading: boolean;
  selectedCounts?: {
    critical: number;
    missingContent: number;
    addedContent: number;
    nameInconsistencies: number;
    total: number;
  };
}

export default function PostEditDialog({
  open,
  onClose,
  onConfirm,
  selectedIssueTypes,
  onIssueTypeChange,
  validationReport,
  loading,
  selectedCounts,
}: PostEditDialogProps) {
  const isAnyIssueSelected = Object.values(selectedIssueTypes).some(v => v);

  return (
    <Dialog open={open} onClose={onClose}>
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
                <Chip 
                  size="small" 
                  label={selectedCounts && selectedCounts.critical < validationReport.summary.total_critical_issues 
                    ? `치명적 오류 ${selectedCounts.critical}/${validationReport.summary.total_critical_issues}개` 
                    : `치명적 오류 ${validationReport.summary.total_critical_issues}개`} 
                  color="error" 
                />
              )}
              {validationReport.summary.total_missing_content > 0 && (
                <Chip 
                  size="small" 
                  label={selectedCounts && selectedCounts.missingContent < validationReport.summary.total_missing_content 
                    ? `누락 내용 ${selectedCounts.missingContent}/${validationReport.summary.total_missing_content}개` 
                    : `누락 내용 ${validationReport.summary.total_missing_content}개`} 
                  color="warning" 
                />
              )}
              {validationReport.summary.total_added_content > 0 && (
                <Chip 
                  size="small" 
                  label={selectedCounts && selectedCounts.addedContent < validationReport.summary.total_added_content 
                    ? `추가 내용 ${selectedCounts.addedContent}/${validationReport.summary.total_added_content}개` 
                    : `추가 내용 ${validationReport.summary.total_added_content}개`} 
                  color="warning" 
                />
              )}
              {validationReport.summary.total_name_inconsistencies > 0 && (
                <Chip 
                  size="small" 
                  label={selectedCounts && selectedCounts.nameInconsistencies < validationReport.summary.total_name_inconsistencies 
                    ? `이름 불일치 ${selectedCounts.nameInconsistencies}/${validationReport.summary.total_name_inconsistencies}개` 
                    : `이름 불일치 ${validationReport.summary.total_name_inconsistencies}개`} 
                  color="info" 
                />
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
                        onChange={(e) => onIssueTypeChange('critical_issues', e.target.checked)}
                      />
                    }
                    label={selectedCounts && selectedCounts.critical < validationReport.summary.total_critical_issues
                      ? `치명적 오류 (${selectedCounts.critical}/${validationReport.summary.total_critical_issues}개 선택됨)`
                      : `치명적 오류 (${validationReport.summary.total_critical_issues}개)`}
                  />
                )}
                {validationReport.summary.total_missing_content > 0 && (
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={selectedIssueTypes.missing_content}
                        onChange={(e) => onIssueTypeChange('missing_content', e.target.checked)}
                      />
                    }
                    label={selectedCounts && selectedCounts.missingContent < validationReport.summary.total_missing_content
                      ? `누락된 내용 (${selectedCounts.missingContent}/${validationReport.summary.total_missing_content}개 선택됨)`
                      : `누락된 내용 (${validationReport.summary.total_missing_content}개)`}
                  />
                )}
                {validationReport.summary.total_added_content > 0 && (
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={selectedIssueTypes.added_content}
                        onChange={(e) => onIssueTypeChange('added_content', e.target.checked)}
                      />
                    }
                    label={selectedCounts && selectedCounts.addedContent < validationReport.summary.total_added_content
                      ? `추가된 내용 (${selectedCounts.addedContent}/${validationReport.summary.total_added_content}개 선택됨)`
                      : `추가된 내용 (${validationReport.summary.total_added_content}개)`}
                  />
                )}
                {validationReport.summary.total_name_inconsistencies > 0 && (
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={selectedIssueTypes.name_inconsistencies}
                        onChange={(e) => onIssueTypeChange('name_inconsistencies', e.target.checked)}
                      />
                    }
                    label={selectedCounts && selectedCounts.nameInconsistencies < validationReport.summary.total_name_inconsistencies
                      ? `이름 불일치 (${selectedCounts.nameInconsistencies}/${validationReport.summary.total_name_inconsistencies}개 선택됨)`
                      : `이름 불일치 (${validationReport.summary.total_name_inconsistencies}개)`}
                  />
                )}
              </Stack>
            </Box>
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>취소</Button>
        <Button 
          onClick={onConfirm} 
          variant="contained" 
          disabled={loading || !isAnyIssueSelected}
          startIcon={loading ? <CircularProgress size={16} /> : <PlayArrowIcon />}
        >
          포스트 에디팅 시작
        </Button>
      </DialogActions>
    </Dialog>
  );
}