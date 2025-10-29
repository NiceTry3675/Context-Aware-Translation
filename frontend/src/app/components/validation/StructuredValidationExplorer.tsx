'use client';

import React, { useEffect, useMemo, useState } from 'react';
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
  Collapse,
  useMediaQuery,
  Drawer,
  AppBar,
  Toolbar,
} from '@mui/material';
import Checkbox from '@mui/material/Checkbox';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import InfoIcon from '@mui/icons-material/Info';
import FilterAltIcon from '@mui/icons-material/FilterAlt';
import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore';
import NavigateNextIcon from '@mui/icons-material/NavigateNext';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import MenuIcon from '@mui/icons-material/Menu';
import ListIcon from '@mui/icons-material/List';
import { ValidationReport } from '../../utils/api';
import { ValidationCase } from '@/core-schemas';
type StructuredCase = ValidationCase;

interface StructuredValidationExplorerProps {
  report: ValidationReport;
  onSegmentClick?: (index: number) => void;
  selectedCases?: Record<number, boolean[]>;
  onCaseSelectionChange?: (segmentIndex: number, caseIndex: number, selected: boolean, totalCases: number) => void;
  currentSegmentIndex?: number;
  // Inline edit support
  modifiedCases?: Record<number, Array<{ reason?: string; recommend_korean_sentence?: string }>>;
  onCaseEditChange?: (
    segmentIndex: number,
    caseIndex: number,
    patch: { reason?: string; recommend_korean_sentence?: string }
  ) => void;
}

// Legacy arrays removed: expect structured_cases only

function severityColor(theme: any, s: number) {
  if (s >= 3) return { fg: theme.palette.error.main, bg: alpha(theme.palette.error.main, 0.08), icon: <ErrorIcon fontSize="small" /> };
  if (s === 2) return { fg: theme.palette.warning.main, bg: alpha(theme.palette.warning.main, 0.1), icon: <WarningIcon fontSize="small" /> };
  return { fg: theme.palette.info.main, bg: alpha(theme.palette.info.main, 0.08), icon: <InfoIcon fontSize="small" /> };
}

export default function StructuredValidationExplorer({ report, onSegmentClick, selectedCases, onCaseSelectionChange, currentSegmentIndex, modifiedCases, onCaseEditChange }: StructuredValidationExplorerProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedSegment, setSelectedSegment] = useState<number>(report?.detailed_results?.[0]?.segment_index ?? 0);
  const [severityFilter, setSeverityFilter] = useState<{ [k: number]: boolean }>({ 3: true, 2: true, 1: true });
  const [dimensionFilter, setDimensionFilter] = useState<Record<string, boolean>>({});
  const [expandedSet, setExpandedSet] = useState<Set<number>>(new Set());

  const segments = report?.detailed_results || [];

  const segmentIndexToCases: Record<number, StructuredCase[]> = useMemo(() => {
    const map: Record<number, StructuredCase[]> = {};
    segments.forEach((seg: any) => {
      const idx = seg.segment_index;
      const cases: StructuredCase[] = Array.isArray(seg.structured_cases) ? seg.structured_cases : [];
      map[idx] = cases;
    });
    return map;
  }, [segments]);

  const allDimensions: string[] = useMemo(() => {
    const set = new Set<string>();
    Object.values(segmentIndexToCases).forEach((cases) => {
      cases.forEach((c: any) => {
        const dim = (c.dimension || 'other') as string;
        if (dim) set.add(dim);
      });
    });
    if (set.size === 0) {
      // Provide sensible defaults if none detected
      ['completeness', 'accuracy', 'addition', 'name_consistency', 'dialogue_style', 'flow', 'other'].forEach((d) => set.add(d));
    }
    return Array.from(set);
  }, [segmentIndexToCases]);

  // Sync with external current segment index when provided
  useEffect(() => {
    if (!segments || segments.length === 0) return;
    if (typeof currentSegmentIndex === 'number' && segments.some((s: any) => s.segment_index === currentSegmentIndex)) {
      if (currentSegmentIndex !== selectedSegment) {
        setSelectedSegment(currentSegmentIndex);
        setExpandedSet(new Set());
      }
      return;
    }
    // Fallback: auto-select the first segment that has any cases
    const first = segments.find((s: any) => (segmentIndexToCases[s.segment_index] || []).length > 0);
    if (first && first.segment_index !== selectedSegment) {
      setSelectedSegment(first.segment_index);
      setExpandedSet(new Set());
    }
  }, [segments, segmentIndexToCases, currentSegmentIndex, selectedSegment]);

  function normalizeSeverity(raw: unknown): number {
    if (typeof raw === 'number') {
      if (raw >= 1 && raw <= 3) return raw;
      return 2;
    }
    if (typeof raw === 'string') {
      const s = raw.toLowerCase();
      if (['critical', 'high', 'severe'].includes(s)) return 3;
      if (['major', 'medium', 'moderate', 'important'].includes(s)) return 2;
      if (['minor', 'low', 'trivial'].includes(s)) return 1;
      const n = parseInt(raw, 10);
      if (!Number.isNaN(n)) return Math.max(1, Math.min(3, n));
      return 2;
    }
    return 2;
  }

  const filteredCasesFor = (idx: number): StructuredCase[] => {
    const list = segmentIndexToCases[idx] || [];
    return list.filter((c) => {
      const sev = normalizeSeverity((c as any).severity);
      const dim = ((c as any).dimension || 'other') as string;
      return (
        (severityFilter[sev] !== false) &&
        (dimensionFilter[dim] !== false) &&
        (!query || (c.reason || '').toLowerCase().includes(query.toLowerCase()))
      );
    });
  };

  const allCases = segmentIndexToCases[selectedSegment] || [];
  const currentCases = filteredCasesFor(selectedSegment);
  const currentSelection = selectedCases?.[selectedSegment];
  const isExpanded = (absIdx: number) => expandedSet.has(absIdx);
  const toggleExpanded = (absIdx: number) => {
    setExpandedSet(prev => {
      const next = new Set(prev);
      if (next.has(absIdx)) next.delete(absIdx); else next.add(absIdx);
      return next;
    });
  };

  const handleSegmentSelect = (idx: number) => {
    setSelectedSegment(idx);
    onSegmentClick?.(idx);
    if (isMobile) {
      setMobileDrawerOpen(false);
    }
  };

  const goPrev = () => {
    const pos = segments.findIndex((s: any) => s.segment_index === selectedSegment);
    if (pos > 0) {
      const target = segments[pos - 1].segment_index;
      setSelectedSegment(target);
      setExpandedSet(new Set());
      onSegmentClick?.(target);
    }
  };
  const goNext = () => {
    const pos = segments.findIndex((s: any) => s.segment_index === selectedSegment);
    if (pos >= 0 && pos < segments.length - 1) {
      const target = segments[pos + 1].segment_index;
      setSelectedSegment(target);
      setExpandedSet(new Set());
      onSegmentClick?.(target);
    }
  };

  const segmentListContent = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Box sx={{ p: { xs: 1, sm: 1.5 }, borderBottom: 1, borderColor: 'divider', display: 'flex', gap: 1 }}>
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
      <Box sx={{ p: { xs: 1, sm: 1.5 }, borderBottom: 1, borderColor: 'divider', display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        {[3, 2, 1].map((s) => (
          <Chip
            key={s}
            size="small"
            label={s === 3 ? '치명(3)' : s === 2 ? '중요(2)' : '경미(1)'}
            color={severityFilter[s] ? (s === 3 ? 'error' : s === 2 ? 'warning' : 'info') : 'default'}
            variant={severityFilter[s] ? 'filled' : 'outlined'}
            onClick={() => setSeverityFilter({ ...severityFilter, [s]: !severityFilter[s] })}
            sx={{ fontSize: { xs: '0.7rem', sm: '0.8125rem' } }}
          />
        ))}
      </Box>

      {/* Segment items */}
      <Box sx={{ overflow: 'auto', flex: 1 }}>
        {segments.map((seg: any) => {
          const idx = seg.segment_index;
          const cases = filteredCasesFor(idx);
          const sevMax = Math.max(0, ...cases.map((c) => normalizeSeverity((c as any).severity)));
          const sevInfo = severityColor(theme, sevMax || 1);
          const isSelected = idx === selectedSegment;
          return (
            <Box
              key={idx}
              onClick={() => handleSegmentSelect(idx)}
              sx={{
                p: { xs: 1, sm: 1.5 },
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
                  <Typography variant="body2" sx={{ fontSize: { xs: '0.8rem', sm: '0.875rem' } }}>
                    세그먼트 {idx + 1}
                  </Typography>
                </Stack>
                <Stack direction="row" spacing={0.5}>
                  <Chip
                    size="small"
                    variant="outlined"
                    color="error"
                    label={cases.filter(c => normalizeSeverity((c as any).severity) === 3).length}
                    sx={{ fontSize: '0.7rem', height: { xs: 18, sm: 20 } }}
                  />
                  <Chip
                    size="small"
                    variant="outlined"
                    color="warning"
                    label={cases.filter(c => normalizeSeverity((c as any).severity) === 2).length}
                    sx={{ fontSize: '0.7rem', height: { xs: 18, sm: 20 } }}
                  />
                  <Chip
                    size="small"
                    variant="outlined"
                    color="info"
                    label={cases.filter(c => normalizeSeverity((c as any).severity) === 1).length}
                    sx={{ fontSize: '0.7rem', height: { xs: 18, sm: 20 } }}
                  />
                </Stack>
              </Stack>
            </Box>
          );
        })}
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', gap: { xs: 0, md: 2 }, height: '100%' }}>
      {/* Left: Segment list - Drawer on mobile, Paper on desktop */}
      {isMobile ? (
        <Drawer
          variant="temporary"
          open={mobileDrawerOpen}
          onClose={() => setMobileDrawerOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            '& .MuiDrawer-paper': {
              width: { xs: '85%', sm: 320 },
              maxWidth: 400,
            },
          }}
        >
          {segmentListContent}
        </Drawer>
      ) : (
        <Paper sx={{ width: { md: 320, lg: 360 }, flexShrink: 0, height: '100%' }}>
          {segmentListContent}
        </Paper>
      )}

      {/* Right: Detail */}
      <Paper sx={{ flex: 1, height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <Box sx={{ p: { xs: 1, sm: 1.5 }, display: 'flex', alignItems: 'center', gap: { xs: 0.5, sm: 1 }, borderBottom: 1, borderColor: 'divider', flexWrap: 'wrap' }}>
          {isMobile && (
            <IconButton
              size="small"
              onClick={() => setMobileDrawerOpen(true)}
              aria-label="세그먼트 목록 열기"
            >
              <ListIcon />
            </IconButton>
          )}
          <IconButton onClick={goPrev} size="small">
            <NavigateBeforeIcon />
          </IconButton>
          <IconButton onClick={goNext} size="small">
            <NavigateNextIcon />
          </IconButton>
          {/* Show segment counter on mobile next to navigation */}
          {isMobile && (
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              {selectedSegment + 1}/{segments.length}
            </Typography>
          )}
          <Divider orientation="vertical" flexItem sx={{ mx: { xs: 0.5, sm: 1 }, display: { xs: 'none', sm: 'block' } }} />
          {/* Severity summary */}
          {([3,2,1] as const).map(s => (
            <Chip
              key={`sev-${s}`}
              size="small"
              variant="outlined"
              label={`S${s}: ${Object.values(segmentIndexToCases).flat().filter((c:any)=>normalizeSeverity(c.severity)===s).length}`}
              color={s===3?'error':s===2?'warning':'info'}
              sx={{ fontSize: { xs: '0.7rem', sm: '0.8125rem' }, display: { xs: 'none', sm: 'inline-flex' } }}
            />
          ))}
          <Divider orientation="vertical" flexItem sx={{ mx: 1, display: { xs: 'none', md: 'block' } }} />
          {/* Dimension filters */}
          {allDimensions.map((dim) => {
            const isOn = dimensionFilter[dim] !== false;
            const count = Object.values(segmentIndexToCases).flat().filter((c:any)=> (c.dimension||'other')===dim).length;
            return (
              <Chip
                key={dim}
                size="small"
                label={`${dim} (${count})`}
                color={isOn ? 'primary' : 'default'}
                variant={isOn ? 'filled' : 'outlined'}
                onClick={() => setDimensionFilter({ ...dimensionFilter, [dim]: !isOn })}
                sx={{ fontSize: { xs: '0.7rem', sm: '0.8125rem' }, display: { xs: 'none', md: 'inline-flex' } }}
              />
            );
          })}
        </Box>

        <Box sx={{ p: { xs: 1, sm: 1.5, md: 2 }, overflow: 'auto', flex: 1 }}>
          {currentCases.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ fontSize: { xs: '0.8rem', sm: '0.875rem' } }}>표시할 문제가 없습니다. 필터를 확인하세요.</Typography>
          ) : (
            <Stack spacing={{ xs: 1, sm: 1.5 }}>
              {currentCases.map((c, i) => {
                const sevNum = normalizeSeverity((c as any).severity);
                const sev = severityColor(theme, sevNum);
                const dim = ((c as any).dimension || 'other') as string;
                const absIndex = allCases.indexOf(c);
                const absoluteIndex = absIndex >= 0 ? absIndex : i;
                const checked = currentSelection ? (currentSelection[absoluteIndex] !== false) : true;
                const src = c.problematic_source_sentence || '';
                const cur = c.current_korean_sentence || '';
                const overrideArr = modifiedCases?.[selectedSegment];
                const override = Array.isArray(overrideArr) ? overrideArr[absoluteIndex] : undefined;
                const fixOrig = (c as any).recommend_korean_sentence || '';
                const fix = (override?.recommend_korean_sentence ?? fixOrig);
                const reasonId = `reason-${selectedSegment}-${absoluteIndex}`;
                return (
                  <Box key={i} sx={{ p: { xs: 1, sm: 1.5 }, border: `1px solid ${sev.fg}`, bgcolor: sev.bg, borderRadius: 1 }} onClick={() => toggleExpanded(absoluteIndex)} role="button" aria-expanded={isExpanded(absoluteIndex)} aria-controls={reasonId} tabIndex={0}>
                    {/* Header */}
                    <Stack direction="row" spacing={{ xs: 0.5, sm: 1 }} alignItems="center" sx={{ mb: { xs: 0.75, sm: 1 }, flexWrap: 'wrap' }}>
                      <Checkbox
                        size="small"
                        checked={checked}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) => {
                          const next = e.target.checked;
                          onCaseSelectionChange?.(selectedSegment, absoluteIndex, next, allCases.length);
                        }}
                      />
                      {sev.icon}
                      <Chip size="small" label={dim} color="default" variant="outlined" sx={{ fontSize: { xs: '0.7rem', sm: '0.8125rem' }, height: { xs: 20, sm: 24 } }} />
                      {c.tags && c.tags.length > 0 && (
                        <Chip size="small" label={c.tags.join(', ')} variant="outlined" sx={{ fontSize: { xs: '0.7rem', sm: '0.8125rem' }, height: { xs: 20, sm: 24 } }} />
                      )}
                      <Box sx={{ flex: 1 }} />
                      <IconButton size="small" onClick={(e) => { e.stopPropagation(); toggleExpanded(absoluteIndex); }}>
                        <ExpandMoreIcon fontSize="small" sx={{ transform: isExpanded(absoluteIndex) ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }} />
                      </IconButton>
                    </Stack>

                    {/* Main content: Source -> Current -> Suggestion (vertical) */}
                    <Stack direction="column" spacing={{ xs: 0.75, sm: 1.25 }} alignItems="stretch">
                      <Box sx={{ p: { xs: 0.75, sm: 1 }, border: '1px dashed', borderColor: sev.fg, borderRadius: 1, bgcolor: 'background.paper' }}>
                        <Typography variant="caption" color="text.secondary" sx={{ fontSize: { xs: '0.7rem', sm: '0.75rem' } }}>원문</Typography>
                        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: { xs: '0.8rem', sm: '0.875rem' } }}>{src || '-'}</Typography>
                      </Box>
                      <Box sx={{ p: { xs: 0.75, sm: 1 }, border: '1px dashed', borderColor: sev.fg, borderRadius: 1, bgcolor: 'background.paper' }}>
                        <Typography variant="caption" color="text.secondary" sx={{ fontSize: { xs: '0.7rem', sm: '0.75rem' } }}>현재 번역</Typography>
                        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: { xs: '0.8rem', sm: '0.875rem' } }}>{cur || '-'}</Typography>
                      </Box>
                      <Box sx={{ p: { xs: 0.75, sm: 1 }, border: '1px dashed', borderColor: sev.fg, borderRadius: 1, bgcolor: 'background.paper', position: 'relative' }}>
                        <Typography variant="caption" color="text.secondary" sx={{ fontSize: { xs: '0.7rem', sm: '0.75rem' } }}>수정 제안</Typography>
                        <TextField
                          size="small"
                          fullWidth
                          multiline
                          minRows={2}
                          key={`fix-${selectedSegment}-${absoluteIndex}`}
                          defaultValue={fix}
                          onClick={(e) => e.stopPropagation()}
                          onChange={(e) => onCaseEditChange?.(selectedSegment, absoluteIndex, { recommend_korean_sentence: e.target.value })}
                          placeholder={fixOrig || '-'}
                          sx={{
                            '& .MuiInputBase-root': {
                              fontSize: { xs: '0.8rem', sm: '0.875rem' }
                            }
                          }}
                        />
                        {fix && (
                          <Tooltip title="수정안 복사">
                            <IconButton size="small" onClick={(e) => { e.stopPropagation(); navigator.clipboard?.writeText(fix); }} sx={{ position: 'absolute', top: { xs: 1, sm: 2 }, right: { xs: 1, sm: 2 } }}>
                              <ContentCopyIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                      </Box>
                      {/* Easier reason toggle */}
                      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                        <Button
                          size="small"
                          variant="text"
                          startIcon={<ExpandMoreIcon sx={{ transform: isExpanded(absoluteIndex) ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }} />}
                          onClick={(e) => { e.stopPropagation(); toggleExpanded(absoluteIndex); }}
                          sx={{ fontSize: { xs: '0.7rem', sm: '0.875rem' } }}
                        >
                          {isExpanded(absoluteIndex) ? '이유 접기' : '이유 보기'}
                        </Button>
                      </Box>
                    </Stack>

                    {/* Reason (expand on click) */}
                    <Collapse in={isExpanded(absoluteIndex)} timeout="auto" unmountOnExit id={reasonId}>
                      <Divider sx={{ my: { xs: 0.75, sm: 1 } }} />
                      <Typography variant="subtitle2" gutterBottom sx={{ fontSize: { xs: '0.8rem', sm: '0.875rem' } }}>이유</Typography>
                      <TextField
                        size="small"
                        fullWidth
                        multiline
                        minRows={2}
                        key={`reason-${selectedSegment}-${absoluteIndex}`}
                        defaultValue={override?.reason ?? (c.reason || '')}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) => onCaseEditChange?.(selectedSegment, absoluteIndex, { reason: e.target.value })}
                        placeholder={c.reason || '-'}
                        sx={{
                          '& .MuiInputBase-root': {
                            fontSize: { xs: '0.8rem', sm: '0.875rem' }
                          }
                        }}
                      />
                    </Collapse>
                  </Box>
                );
              })}
            </Stack>
          )}
        </Box>

        <Box sx={{ p: { xs: 1, sm: 1.5 }, borderTop: 1, borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
          {/* Hide segment counter on mobile (shown in header instead) */}
          <Typography variant="caption" color="text.secondary" sx={{ display: { xs: 'none', sm: 'block' } }}>
            총 세그먼트: {segments.length} | 현재: {selectedSegment + 1}
          </Typography>
          <Stack direction="row" spacing={{ xs: 0.5, sm: 1 }} sx={{ flexWrap: 'wrap', gap: { xs: 0.5, sm: 1 } }}>
            <Button size="small" variant="text" onClick={() => {
              // toggle visible cases to true
              currentCases.forEach((c) => {
                const absIndex = allCases.indexOf(c);
                const absoluteIndex = absIndex >= 0 ? absIndex : 0;
                onCaseSelectionChange?.(selectedSegment, absoluteIndex, true, allCases.length);
              });
            }} sx={{ fontSize: { xs: '0.7rem', sm: '0.875rem' } }}>전체 선택</Button>
            <Button size="small" variant="text" onClick={() => {
              currentCases.forEach((c) => {
                const absIndex = allCases.indexOf(c);
                const absoluteIndex = absIndex >= 0 ? absIndex : 0;
                onCaseSelectionChange?.(selectedSegment, absoluteIndex, false, allCases.length);
              });
            }} sx={{ fontSize: { xs: '0.7rem', sm: '0.875rem' } }}>전체 해제</Button>
            <Button
              size="small"
              variant="outlined"
              onClick={goPrev}
              startIcon={<NavigateBeforeIcon />}
              disabled={segments.findIndex((s: any) => s.segment_index === selectedSegment) <= 0}
              sx={{ fontSize: { xs: '0.7rem', sm: '0.875rem' }, display: { xs: 'none', sm: 'inline-flex' } }}
            >이전</Button>
            <Button
              size="small"
              variant="contained"
              onClick={goNext}
              endIcon={<NavigateNextIcon />}
              disabled={segments.findIndex((s: any) => s.segment_index === selectedSegment) >= segments.length - 1}
              sx={{ fontSize: { xs: '0.7rem', sm: '0.875rem' }, display: { xs: 'none', sm: 'inline-flex' } }}
            >다음</Button>
          </Stack>
        </Box>
      </Paper>
    </Box>
  );
}
