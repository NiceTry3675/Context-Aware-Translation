'use client';

import React, { useMemo } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControlLabel,
  Checkbox,
  Box,
  Typography,
  Slider,
  Alert,
  Stack,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  ListItemText,
  FormHelperText,
  SelectChangeEvent,
} from '@mui/material';
import BrushIcon from '@mui/icons-material/Brush';
import type { ApiProvider } from '../../hooks/useApiKey';
import {
  geminiModelOptions,
  openRouterModelOptions,
  vertexModelOptions,
  type ModelOption,
} from '../../utils/constants/models';

interface IllustrationDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  apiProvider?: ApiProvider;
  style?: string;
  onStyleChange?: (value: string) => void;
  styleHints?: string;
  onStyleHintsChange?: (value: string) => void;
  promptModelName?: string;
  onPromptModelNameChange?: (value: string) => void;
  minSegmentLength?: number;
  onMinSegmentLengthChange?: (value: number) => void;
  skipDialogueHeavy?: boolean;
  onSkipDialogueHeavyChange?: (value: boolean) => void;
  maxIllustrations?: number;
  onMaxIllustrationsChange?: (value: number) => void;
  loading?: boolean;
}

export default function IllustrationDialog({
  open,
  onClose,
  onConfirm,
  apiProvider = 'gemini',
  style = 'default',
  onStyleChange,
  styleHints = '',
  onStyleHintsChange,
  promptModelName = '',
  onPromptModelNameChange,
  minSegmentLength = 100,
  onMinSegmentLengthChange,
  skipDialogueHeavy = false,
  onSkipDialogueHeavyChange,
  maxIllustrations = 10,
  onMaxIllustrationsChange,
  loading = false,
}: IllustrationDialogProps) {
  const modelOptions = useMemo<ModelOption[]>(() => {
    const base = apiProvider === 'openrouter'
      ? openRouterModelOptions
      : apiProvider === 'vertex'
        ? vertexModelOptions
        : geminiModelOptions;

    if (promptModelName && !base.some((opt) => opt.value === promptModelName)) {
      return [
        ...base,
        {
          value: promptModelName,
          label: promptModelName,
          description: '사용자 정의 모델',
          chip: 'Custom',
          chipColor: 'info',
        },
      ];
    }

    return base;
  }, [apiProvider, promptModelName]);

  const handlePromptModelChange = (event: SelectChangeEvent<string>) => {
    const value = event.target.value;
    onPromptModelNameChange?.(value);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <BrushIcon color="primary" />
        삽화 생성 설정
      </DialogTitle>
      <DialogContent>
        <Stack spacing={3} sx={{ mt: 2 }}>
          <Alert severity="info">
            AI를 사용하여 번역된 텍스트의 주요 장면에 대한 삽화를 생성합니다.
          </Alert>

          <Box>
            <Typography gutterBottom>
              최대 삽화 개수: {maxIllustrations}개
            </Typography>
            <Slider
              value={maxIllustrations}
              onChange={(_, value) => onMaxIllustrationsChange?.(value as number)}
              min={1}
              max={50}
              step={1}
              valueLabelDisplay="auto"
              marks={[
                { value: 1, label: '1' },
                { value: 10, label: '10' },
                { value: 25, label: '25' },
                { value: 50, label: '50' },
              ]}
            />
          </Box>

          <FormControl fullWidth>
            <InputLabel id="style-select-label">삽화 스타일</InputLabel>
            <Select
              labelId="style-select-label"
              value={style}
              label="삽화 스타일"
              onChange={(e: SelectChangeEvent) => onStyleChange?.(e.target.value)}
            >
              <MenuItem value="default">미지정 (Default)</MenuItem>
              <MenuItem value="realistic">사실적 (Realistic)</MenuItem>
              <MenuItem value="artistic">예술적 (Artistic)</MenuItem>
              <MenuItem value="watercolor">수채화 (Watercolor)</MenuItem>
              <MenuItem value="digital_art">디지털 아트 (Digital Art)</MenuItem>
              <MenuItem value="sketch">스케치 (Sketch)</MenuItem>
              <MenuItem value="anime">애니메이션 (Anime)</MenuItem>
              <MenuItem value="vintage">빈티지 (Vintage)</MenuItem>
              <MenuItem value="minimalist">미니멀리즘 (Minimalist)</MenuItem>
            </Select>
          </FormControl>

          <FormControl fullWidth>
            <InputLabel id="prompt-model-select-label">프롬프트 생성 모델</InputLabel>
            <Select
              labelId="prompt-model-select-label"
              value={promptModelName || ''}
              label="프롬프트 생성 모델"
              onChange={handlePromptModelChange}
            >
              <MenuItem value="">
                <ListItemText
                  primary="번역 모델과 동일"
                  secondary="현재 번역에 사용 중인 모델을 그대로 사용합니다."
                />
              </MenuItem>
              {modelOptions.map((option) => (
                <MenuItem value={option.value} key={option.value}>
                  <ListItemText
                    primary={option.label}
                    secondary={option.description || option.value}
                  />
                </MenuItem>
              ))}
            </Select>
            <FormHelperText>
              삽화 프롬프트를 생성할 텍스트 모델입니다. 지정하지 않으면 번역 기본 모델을 사용합니다.
            </FormHelperText>
          </FormControl>

          <TextField
            label="스타일 힌트"
            placeholder="예: 수채화 스타일, 판타지 아트, 미니멀리즘..."
            value={styleHints}
            onChange={(e) => onStyleHintsChange?.(e.target.value)}
            fullWidth
            multiline
            rows={2}
            helperText="생성될 삽화의 아트 스타일을 설명하세요 (선택사항)"
          />

          <Box>
            <Typography gutterBottom>
              최소 세그먼트 길이: {minSegmentLength}자
            </Typography>
            <Slider
              value={minSegmentLength}
              onChange={(_, value) => onMinSegmentLengthChange?.(value as number)}
              min={50}
              max={500}
              step={50}
              valueLabelDisplay="auto"
              marks={[
                { value: 50, label: '50' },
                { value: 100, label: '100' },
                { value: 250, label: '250' },
                { value: 500, label: '500' },
              ]}
            />
            <Typography variant="caption" color="text.secondary">
              짧은 세그먼트는 삽화 생성에서 제외됩니다
            </Typography>
          </Box>

          <FormControlLabel
            control={
              <Checkbox
                checked={skipDialogueHeavy}
                onChange={(e) => onSkipDialogueHeavyChange?.(e.target.checked)}
              />
            }
            label="대화가 많은 세그먼트 건너뛰기"
          />

          <Alert severity="warning">
            삽화 생성은 별도의 API 키가 필요하며, 생성에 시간이 소요될 수 있습니다.
          </Alert>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>취소</Button>
        <Button
          onClick={onConfirm}
          variant="contained"
          disabled={loading}
          startIcon={<BrushIcon />}
        >
          삽화 생성 시작
        </Button>
      </DialogActions>
    </Dialog>
  );
}
