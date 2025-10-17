'use client';

import React, { Dispatch, SetStateAction, useMemo } from 'react';
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
import ModelSelector from '../translation/ModelSelector';
import type { ApiProvider } from '../../hooks/useApiKey';

const DIMENSION_LABELS: Record<string, string> = {
  completeness: '누락된 내용',
  addition: '불필요한 추가',
  accuracy: '정확성',
  name_consistency: '이름 일관성',
  dialogue_style: '대사 스타일',
  flow: '문장 흐름',
  terminology: '용어',
  other: '기타',
};

const normalizeDimension = (raw?: string | null) => {
  if (!raw) return 'other';
  const value = raw.toLowerCase();
  if (value.includes('complete')) return 'completeness';
  if (value.includes('addition') || value.includes('extra')) return 'addition';
  if (value.includes('accuracy') || value.includes('faithful')) return 'accuracy';
  if (value.includes('name')) return 'name_consistency';
  if (value.includes('dialogue') || value.includes('speech')) return 'dialogue_style';
  if (value.includes('flow') || value.includes('fluency')) return 'flow';
  if (value.includes('term')) return 'terminology';
  return value;
};

interface PostEditDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  validationReport: ValidationReport | null;
  loading: boolean;
  selectedCounts?: {
    total: number;
  };
  apiProvider?: ApiProvider;
  modelName?: string;
  onModelNameChange?: (model: string) => void;
  selectedCases?: Record<number, boolean[]>;
  setSelectedCases?: Dispatch<SetStateAction<Record<number, boolean[]>>>;
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
  onModelNameChange,
  selectedCases,
  setSelectedCases,
}: PostEditDialogProps) {
  const isAnyCaseSelected = (selectedCounts?.total ?? 0) > 0;

  const dimensionSummary = useMemo(() => {
    if (!validationReport?.detailed_results) return [] as Array<{
      dimension: string;
      label: string;
      total: number;
      selected: number;
    }>;

    const map = new Map<string, { total: number; selected: number }>();

    validationReport.detailed_results.forEach((result) => {
      const cases = Array.isArray(result.structured_cases) ? result.structured_cases : [];
      if (!cases.length) return;
      cases.forEach((c, caseIndex) => {
        const key = normalizeDimension(c.dimension);
        const current = map.get(key) || { total: 0, selected: 0 };
        current.total += 1;

        const segmentSelection = selectedCases?.[result.segment_index];
        const isSelected = Array.isArray(segmentSelection)
          ? segmentSelection[caseIndex] !== false
          : true;

        if (isSelected) {
          current.selected += 1;
        }

        map.set(key, current);
      });
    });

    return Array.from(map.entries()).map(([dimension, data]) => ({
      dimension,
      label: DIMENSION_LABELS[dimension] || dimension.replace(/_/g, ' '),
      ...data,
    }));
  }, [validationReport, selectedCases]);

  const handleToggleDimension = (dimension: string, checked: boolean) => {
    if (!setSelectedCases || !validationReport?.detailed_results) return;
    setSelectedCases((prev) => {
      const next = { ...prev };
      validationReport.detailed_results.forEach((result) => {
        const cases = Array.isArray(result.structured_cases) ? result.structured_cases : [];
        if (!cases.length) return;

        const segIndex = result.segment_index;
        const existing = next[segIndex] ? next[segIndex].slice() : new Array(cases.length).fill(true);
        let changed = false;

        cases.forEach((c, caseIndex) => {
          const dimKey = normalizeDimension(c.dimension);
          if (dimKey === dimension) {
            if (existing[caseIndex] !== checked) {
              existing[caseIndex] = checked;
              changed = true;
            }
          }
        });

        if (changed || next[segIndex]) {
          next[segIndex] = existing;
        }
      });
      return next;
    });
  };

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>포스트 에디팅 확인</DialogTitle>
      <DialogContent>
        <Alert severity="info" sx={{ mb: 2 }}>
          포스트 에디팅은 검증 결과를 바탕으로 AI가 자동으로 번역을 수정합니다.
        </Alert>
        {validationReport && (
          <Stack spacing={2}>
            {apiProvider && onModelNameChange && (
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>포스트 에디팅 모델 선택</Typography>
                <ModelSelector
                  apiProvider={apiProvider}
                  selectedModel={modelName || ''}
                  onModelChange={onModelNameChange}
                  hideTitle
                  restrictOpenRouterToGemini
                />
              </Box>
            )}
            <Typography variant="body2">
              발견된 문제(요약):
            </Typography>
            <Divider />
            <Typography variant="body2" color="text.secondary">
              포스트 에디팅은 현재 탭에서 체크한 케이스들만 적용합니다. 유형 선택 단계는 제거되었습니다.
            </Typography>
            {dimensionSummary.length > 0 ? (
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  수정 대상 오류 유형
                </Typography>
                <Stack spacing={1}>
                  {dimensionSummary.map(({ dimension, label, total, selected }) => (
                    <FormControlLabel
                      key={dimension}
                      control={
                        <Checkbox
                          checked={selected > 0 && selected === total}
                          indeterminate={selected > 0 && selected < total}
                          onChange={(event) => handleToggleDimension(dimension, event.target.checked)}
                          disabled={!setSelectedCases}
                        />
                      }
                      label={`${label} (${selected}/${total})`}
                    />
                  ))}
                </Stack>
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary">
                선택된 오류 유형이 없습니다. 검증 결과에서 수정할 케이스를 선택해 주세요.
              </Typography>
            )}
            <Box>
              <Chip
                color={isAnyCaseSelected ? 'primary' : 'default'}
                label={`선택된 케이스: ${selectedCounts?.total ?? 0}건`}
              />
            </Box>
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
