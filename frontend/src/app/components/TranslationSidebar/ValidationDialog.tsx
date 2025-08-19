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
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import ModelSelector from '../translation/ModelSelector';

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
  onModelNameChange?: (model: string) => void;
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
  onModelNameChange,
}: ValidationDialogProps) {
  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>검증 옵션</DialogTitle>
      <DialogContent>
        <Stack spacing={3} sx={{ mt: 1, minWidth: 400 }}>
          {apiProvider && onModelNameChange && (
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>검증 모델 선택</Typography>
              <ModelSelector
                apiProvider={apiProvider}
                selectedModel={modelName || ''}
                onModelChange={onModelNameChange}
                hideTitle
              />
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
