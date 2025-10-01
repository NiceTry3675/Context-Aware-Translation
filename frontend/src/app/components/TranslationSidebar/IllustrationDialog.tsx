'use client';

import React from 'react';
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
  SelectChangeEvent,
} from '@mui/material';
import BrushIcon from '@mui/icons-material/Brush';

interface IllustrationDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  style?: string;
  onStyleChange?: (value: string) => void;
  styleHints?: string;
  onStyleHintsChange?: (value: string) => void;
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
  style = 'default',
  onStyleChange,
  styleHints = '',
  onStyleHintsChange,
  minSegmentLength = 100,
  onMinSegmentLengthChange,
  skipDialogueHeavy = false,
  onSkipDialogueHeavyChange,
  maxIllustrations = 10,
  onMaxIllustrationsChange,
  loading = false,
}: IllustrationDialogProps) {
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