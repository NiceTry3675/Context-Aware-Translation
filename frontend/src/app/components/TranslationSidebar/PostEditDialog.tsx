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
import { FormControl, InputLabel, Select, MenuItem, SelectChangeEvent } from '@mui/material';
import { geminiModelOptions, openRouterModelOptions } from '../../utils/constants/models';

interface PostEditDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  validationReport: ValidationReport | null;
  loading: boolean;
  selectedCounts?: {
    total: number;
  };
  apiProvider?: 'gemini' | 'openrouter';
  modelName?: string;
  onModelChange?: (model: string) => void;
  disableModelSelect?: boolean;
}

export default function PostEditDialog({
  open,
  onClose,
  onConfirm,
  validationReport,
  loading,
  selectedCounts,
  apiProvider,
  modelName,
  onModelChange,
  disableModelSelect,
}: PostEditDialogProps) {
  const isAnyCaseSelected = (selectedCounts?.total ?? 0) > 0;

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>포스트 에디팅 확인</DialogTitle>
      <DialogContent>
        <Alert severity="info" sx={{ mb: 2 }}>
          포스트 에디팅은 검증 결과를 바탕으로 AI가 자동으로 번역을 수정합니다.
        </Alert>
        {apiProvider && modelName && onModelChange && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom>후편집 모델 선택</Typography>
            <FormControl fullWidth size="small" disabled={!!disableModelSelect}>
              <InputLabel id="postedit-model-select-label">후편집 모델</InputLabel>
              <Select
                labelId="postedit-model-select-label"
                value={modelName}
                label="후편집 모델"
                onChange={(e: SelectChangeEvent<string>) => onModelChange(e.target.value as string)}
              >
                {(apiProvider === 'gemini' ? geminiModelOptions : openRouterModelOptions).map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        )}
        {validationReport && (
          <Stack spacing={2}>
            <Typography variant="body2">
              발견된 문제(요약):
            </Typography>
            <Divider />
            <Typography variant="body2" color="text.secondary">
              포스트 에디팅은 현재 탭에서 체크한 케이스들만 적용합니다. 유형 선택 단계는 제거되었습니다.
            </Typography>
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>취소</Button>
        <Button 
          onClick={onConfirm} 
          variant="contained" 
          disabled={loading || !isAnyCaseSelected}
          startIcon={loading ? <CircularProgress size={16} /> : <PlayArrowIcon />}
        >
          포스트 에디팅 시작
        </Button>
      </DialogActions>
    </Dialog>
  );
}
