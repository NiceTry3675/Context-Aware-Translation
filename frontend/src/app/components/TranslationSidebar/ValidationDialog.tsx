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
  Slider,
  Typography,
  Box,
  CircularProgress,
} from '@mui/material';
import { FormControl, InputLabel, Select, MenuItem, SelectChangeEvent } from '@mui/material';
import { geminiModelOptions, openRouterModelOptions } from '../../utils/constants/models';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';

interface ValidationDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  quickValidation: boolean;
  onQuickValidationChange: (checked: boolean) => void;
  validationSampleRate: number;
  onValidationSampleRateChange: (rate: number) => void;
  loading: boolean;
  apiProvider?: 'gemini' | 'openrouter';
  modelName?: string;
  onModelChange?: (model: string) => void;
  disableModelSelect?: boolean;
}

export default function ValidationDialog({
  open,
  onClose,
  onConfirm,
  quickValidation,
  onQuickValidationChange,
  validationSampleRate,
  onValidationSampleRateChange,
  loading,
  apiProvider,
  modelName,
  onModelChange,
  disableModelSelect,
}: ValidationDialogProps) {
  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>검증 옵션</DialogTitle>
      <DialogContent>
        <Stack spacing={3} sx={{ mt: 1, minWidth: 400 }}>
          {apiProvider && modelName && onModelChange && (
            <Box>
              <Typography variant="subtitle1" gutterBottom>검증 모델 선택</Typography>
              <FormControl fullWidth size="small" disabled={!!disableModelSelect}>
                <InputLabel id="validation-model-select-label">검증 모델</InputLabel>
                <Select
                  labelId="validation-model-select-label"
                  value={modelName}
                  label="검증 모델"
                  onChange={(e: SelectChangeEvent<string>) => onModelChange(e.target.value as string)}
                >
                  {(apiProvider === 'gemini' ? geminiModelOptions : openRouterModelOptions).map((opt) => (
                    <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
          )}
          <FormControlLabel
            control={
              <Checkbox
                checked={quickValidation}
                onChange={(e) => onQuickValidationChange(e.target.checked)}
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
              onChange={(e, v) => onValidationSampleRateChange(v as number)}
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
        <Button onClick={onClose}>취소</Button>
        <Button 
          onClick={onConfirm} 
          variant="contained" 
          disabled={loading}
          startIcon={loading ? <CircularProgress size={16} /> : <PlayArrowIcon />}
        >
          검증 시작
        </Button>
      </DialogActions>
    </Dialog>
  );
}
