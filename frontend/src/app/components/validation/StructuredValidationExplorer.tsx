'use client';

import React, { useMemo, useState } from 'react';
import {
  Box,
  Paper,
  Stack,
  Typography,
  Chip,
  Divider,
  TextField,
  IconButton,
  Tooltip,
  Button,
  alpha,
  useTheme,
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import InfoIcon from '@mui/icons-material/Info';
import FilterAltIcon from '@mui/icons-material/FilterAlt';
import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import { ValidationReport } from '../../utils/api';

type StructuredCase = {
  dimension: string;
  severity: number;
  tags?: string[];
  problematic_source_sentence?: string;
  current_korean_sentence?: string;
  reason: string;
  corrected_korean_sentence?: string;
};

interface StructuredValidationExplorerProps {
  report: ValidationReport;
  onSegmentClick?: (index: number) => void;
}

function deriveCasesFromLegacy(segment: any): StructuredCase[] {
  const cases: StructuredCase[] = [];
  const pushAll = (arr: string[] | undefined, dimension: string, severity: number) => {
    (arr || []).forEach((reason) => cases.push({ dimension, severity, reason }));
  };
  // Heuristics to convert legacy arrays into structured cases for display
  pushAll(segment.critical_issues, 'accuracy', 3);
  pushAll(segment.missing_content, 'completeness', 2);
  pushAll(segment.added_content, 'addition', 2);
  pushAll(segment.name_inconsistencies, 'name_consistency', 2);
  pushAll(segment.minor_issues, 'other', 1);
  return cases;
}

function severityColor(theme: any, s: number) {
  if (s >= 3) return { fg: theme.palette.error.main, bg: alpha(theme.palette.error.main, 0.08), icon: <ErrorIcon fontSize="small" /> };
  if (s === 2) return { fg: theme.palette.warning.main, bg: alpha(theme.palette.warning.main, 0.1), icon: <WarningIcon fontSize="small" /> };
  return { fg: theme.palette.info.main, bg: alpha(theme.palette.info.main, 0.08), icon: <InfoIcon fontSize="small" /> };
}

export default function StructuredValidationExplorer({ report, onSegmentClick }: StructuredValidationExplorerProps) {
  const theme = useTheme();
  const [query, setQuery] = useState('');
  const [selectedSegment, setSelectedSegment] = useState<number>(report?.detailed_results?.[0]?.segment_index ?? 0);
  const [severityFilter, setSeverityFilter] = useState<{ [k: number]: boolean }>({ 3: true, 2: true, 1: true });
  const [dimensionFilter, setDimensionFilter] = useState<Record<string, boolean>>({
    completeness: true,
    accuracy: true,
    addition: true,
    name_consistency: true,
    dialogue_style: true,
    flow: true,
    other: true,
  });

  const segments = report?.detailed_results || [];

  const segmentIndexToCases: Record<number, StructuredCase[]> = useMemo(() => {
    const map: Record<number, StructuredCase[]> = {};
    segments.forEach((seg: any) => {
      const idx = seg.segment_index;
      const cases: StructuredCase[] = Array.isArray(seg.structured_cases) && seg.structured_cases.length > 0
        ? seg.structured_cases
        : deriveCasesFromLegacy(seg);
      map[idx] = cases;
    });
    return map;
  }, [segments]);

  const filteredCasesFor = (idx: number): StructuredCase[] => {
    const list = segmentIndexToCases[idx] || [];
    return list.filter((c) =>
      severityFilter[c.severity] &&
      dimensionFilter[c.dimension] &&
      (!query || c.reason.toLowerCase().includes(query.toLowerCase()))
    );
  };

  const currentCases = filteredCasesFor(selectedSegment);

  const goPrev = () => {
    const pos = segments.findIndex((s: any) => s.segment_index === selectedSegment);
    if (pos > 0) setSelectedSegment(segments[pos - 1].segment_index);
  };
  const goNext = () => {
    const pos = segments.findIndex((s: any) => s.segment_index === selectedSegment);
    if (pos >= 0 && pos < segments.length - 1) setSelectedSegment(segments[pos + 1].segment_index);
  };

  return (
    <Box sx={{ display: 'flex', gap: 2, height: '100%' }}>
      {/* Left: Segment list */}
      <Paper sx={{ width: 360, flexShrink: 0, height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <Box sx={{ p: 1.5, borderBottom: 1, borderColor: 'divider', display: 'flex', gap: 1 }}>
          <TextField
            size="small"
            fullWidth
            placeholder="이유(reason) 검색"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <Tooltip title="필터">
            <FilterAltIcon color="action" />
          </Tooltip>
        </Box>

        {/* Severity filter chips */}
        <Box sx={{ p: 1.5, borderBottom: 1, borderColor: 'divider', display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          {[3, 2, 1].map((s) => (
            <Chip
              key={s}
              size="small"
              label={s === 3 ? '치명(3)' : s === 2 ? '중요(2)' : '경미(1)'}
              color={severityFilter[s] ? (s === 3 ? 'error' : s === 2 ? 'warning' : 'info') : 'default'}
              variant={severityFilter[s] ? 'filled' : 'outlined'}
              onClick={() => setSeverityFilter({ ...severityFilter, [s]: !severityFilter[s] })}
            />
          ))}
        </Box>

        {/* Segment items */}
        <Box sx={{ overflow: 'auto', flex: 1 }}>
          {segments.map((seg: any) => {
            const idx = seg.segment_index;
            const cases = filteredCasesFor(idx);
            const sevMax = Math.max(0, ...cases.map((c) => c.severity));
            const sevInfo = severityColor(theme, sevMax || 1);
            const isSelected = idx === selectedSegment;
            return (
              <Box
                key={idx}
                onClick={() => {
                  setSelectedSegment(idx);
                  onSegmentClick?.(idx);
                }}
                sx={{
                  p: 1.5,
                  cursor: 'pointer',
                  borderBottom: 1,
                  borderColor: 'divider',
                  bgcolor: isSelected ? alpha(theme.palette.primary.main, 0.06) : 'transparent',
                }}
              >
                <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Box sx={{ width: 24, height: 24, borderRadius: '50%', bgcolor: sevInfo.bg, color: sevInfo.fg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      {sevInfo.icon}
                    </Box>
                    <Typography variant="body2">세그먼트 {idx + 1}</Typography>
                  </Stack>
                  <Stack direction="row" spacing={0.5}>
                    <Chip size="small" variant="outlined" color="error" label={cases.filter(c => c.severity === 3).length} />
                    <Chip size="small" variant="outlined" color="warning" label={cases.filter(c => c.severity === 2).length} />
                    <Chip size="small" variant="outlined" color="info" label={cases.filter(c => c.severity === 1).length} />
                  </Stack>
                </Stack>
              </Box>
            );
          })}
        </Box>
      </Paper>

      {/* Right: Detail */}
      <Paper sx={{ flex: 1, height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <Box sx={{ p: 1.5, display: 'flex', alignItems: 'center', gap: 1, borderBottom: 1, borderColor: 'divider' }}>
          <IconButton onClick={goPrev} size="small">
            <NavigateBeforeIcon />
          </IconButton>
          <IconButton onClick={goNext} size="small">
            <NavigateNextIcon />
          </IconButton>
          <Divider orientation="vertical" flexItem sx={{ mx: 1 }} />
          {/* Dimension filters */}
          {Object.keys(dimensionFilter).map((dim) => (
            <Chip
              key={dim}
              size="small"
              label={dim}
              color={dimensionFilter[dim] ? 'primary' : 'default'}
              variant={dimensionFilter[dim] ? 'filled' : 'outlined'}
              onClick={() => setDimensionFilter({ ...dimensionFilter, [dim]: !dimensionFilter[dim] })}
            />
          ))}
        </Box>

        <Box sx={{ p: 2, overflow: 'auto', flex: 1 }}>
          {currentCases.length === 0 ? (
            <Typography variant="body2" color="text.secondary">표시할 문제가 없습니다. 필터를 확인하세요.</Typography>
          ) : (
            <Stack spacing={1.5}>
              {currentCases.map((c, i) => {
                const sev = severityColor(theme, c.severity || 1);
                return (
                  <Box key={i} sx={{ p: 1.5, border: `1px solid ${sev.fg}`, bgcolor: sev.bg, borderRadius: 1 }}>
                    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                      {sev.icon}
                      <Chip size="small" label={c.dimension} color="default" variant="outlined" />
                      {c.tags && c.tags.length > 0 && (
                        <Chip size="small" label={c.tags.join(', ')} variant="outlined" />
                      )}
                    </Stack>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{c.reason}</Typography>
                    {c.problematic_source_sentence && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                        원문: {c.problematic_source_sentence}
                      </Typography>
                    )}
                    {c.current_korean_sentence && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                        현재 번역: {c.current_korean_sentence}
                      </Typography>
                    )}
                    {c.corrected_korean_sentence && (
                      <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1 }}>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>수정 제안:</Typography>
                        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', flex: 1 }}>{c.corrected_korean_sentence}</Typography>
                        <Tooltip title="수정안 복사">
                          <IconButton size="small" onClick={() => navigator.clipboard?.writeText(c.corrected_korean_sentence || '')}>
                            <ContentCopyIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Stack>
                    )}
                  </Box>
                );
              })}
            </Stack>
          )}
        </Box>

        <Box sx={{ p: 1.5, borderTop: 1, borderColor: 'divider', display: 'flex', justifyContent: 'space-between' }}>
          <Typography variant="caption" color="text.secondary">
            총 세그먼트: {segments.length} | 현재: {selectedSegment + 1}
          </Typography>
          <Stack direction="row" spacing={1}>
            <Button size="small" variant="outlined" onClick={goPrev} startIcon={<NavigateBeforeIcon />}>이전</Button>
            <Button size="small" variant="contained" onClick={goNext} endIcon={<NavigateNextIcon />}>다음</Button>
          </Stack>
        </Box>
      </Paper>
    </Box>
  );
}


