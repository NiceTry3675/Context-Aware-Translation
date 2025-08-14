'use client';

import React, { useMemo, useState } from 'react';
import {
  Box,
  Paper,
  IconButton,
  Typography,
  Chip,
  Stack,
  Select,
  MenuItem,
  FormControl,
  Tooltip,
} from '@mui/material';
import {
  NavigateBefore as PrevIcon,
  NavigateNext as NextIcon,
  FirstPage as FirstIcon,
  LastPage as LastIcon,
  Error as CriticalIcon,
  ContentCopy as MissingIcon,
  AddCircle as AddedIcon,
  Person as NameIcon,
} from '@mui/icons-material';
import { ValidationReport } from '../../utils/api';

interface ErrorNavigationBarProps {
  validationReport: ValidationReport | null;
  currentSegmentIndex: number;
  onSegmentChange: (index: number) => void;
  onFilterChange?: (filters: ErrorFilters) => void;
}

export interface ErrorFilters {
  critical: boolean;
  missingContent: boolean;
  addedContent: boolean;
  nameInconsistencies: boolean;
}

export default function ErrorNavigationBar({
  validationReport,
  currentSegmentIndex,
  onSegmentChange,
  onFilterChange,
}: ErrorNavigationBarProps) {
  const [filters, setFilters] = useState<ErrorFilters>({
    critical: true,
    missingContent: true,
    addedContent: true,
    nameInconsistencies: true,
  });

  // Calculate segments with errors based on filters
  const segmentsWithErrors = useMemo(() => {
    if (!validationReport) return [];
    
    return validationReport.detailed_results
      .filter((result) => {
        const cases = (result as any).structured_cases || [];
        if (!Array.isArray(cases) || cases.length === 0) return false;

        const normalizeSeverity = (s: any) => {
          if (typeof s === 'number') return Math.max(1, Math.min(3, s));
          if (typeof s === 'string') {
            const t = s.toLowerCase();
            if (['critical', 'high', 'severe'].includes(t)) return 3;
            if (['major', 'medium', 'moderate', 'important'].includes(t)) return 2;
            if (['minor', 'low', 'trivial'].includes(t)) return 1;
            const n = parseInt(s, 10);
            if (!Number.isNaN(n)) return Math.max(1, Math.min(3, n));
          }
          return 2;
        };

        const hasCritical = cases.some((c: any) => normalizeSeverity(c.severity) === 3);
        const hasMissing = cases.some((c: any) => {
          const t = (c.dimension || '').toLowerCase();
          return t.includes('missing') || /누락/.test(c.reason || '');
        });
        const hasAdded = cases.some((c: any) => {
          const t = (c.dimension || '').toLowerCase();
          return t.includes('added') || /추가/.test(c.reason || '');
        });
        const hasName = cases.some((c: any) => {
          const t = (c.dimension || '').toLowerCase();
          return t.includes('name') || /이름|고유명/.test(c.reason || '');
        });

        const hasRelevantErrors =
          (filters.critical && hasCritical) ||
          (filters.missingContent && hasMissing) ||
          (filters.addedContent && hasAdded) ||
          (filters.nameInconsistencies && hasName);
        
        return result.status === 'FAIL' && hasRelevantErrors;
      })
      .map((result) => result.segment_index)
      .sort((a: number, b: number) => a - b);
  }, [validationReport, filters]);

  // Find current position in error list
  const currentErrorIndex = segmentsWithErrors.indexOf(currentSegmentIndex);
  const isOnErrorSegment = currentErrorIndex !== -1;

  // Calculate error counts by type
  const errorCounts = useMemo(() => {
    if (!validationReport) return { critical: 0, missing: 0, added: 0, names: 0 };
    
    // Use summary from report for counts (kept for backward compatibility)
    const sev = validationReport.summary.case_counts_by_severity || { '1': 0, '2': 0, '3': 0 };
    // critical≈3, missing/added/names는 차원 분포에서 유도 가능하지만, 여기선 간단히 표시만 유지
    const dim = validationReport.summary.case_counts_by_dimension || {};
    return {
      critical: sev['3'] || 0,
      missing: dim['completeness'] || 0,
      added: dim['addition'] || 0,
      names: dim['name_consistency'] || 0,
    };
  }, [validationReport]);

  // Navigation functions
  const goToFirstError = () => {
    if (segmentsWithErrors.length > 0) {
      onSegmentChange(segmentsWithErrors[0]);
    }
  };

  const goToLastError = () => {
    if (segmentsWithErrors.length > 0) {
      onSegmentChange(segmentsWithErrors[segmentsWithErrors.length - 1]);
    }
  };

  const goToPreviousError = () => {
    if (isOnErrorSegment && currentErrorIndex > 0) {
      onSegmentChange(segmentsWithErrors[currentErrorIndex - 1]);
    } else if (segmentsWithErrors.length > 0) {
      // Find the nearest previous error
      const previousErrors = segmentsWithErrors.filter((idx: number) => idx < currentSegmentIndex);
      if (previousErrors.length > 0) {
        onSegmentChange(previousErrors[previousErrors.length - 1]);
      } else {
        goToLastError(); // Wrap around
      }
    }
  };

  const goToNextError = () => {
    if (isOnErrorSegment && currentErrorIndex < segmentsWithErrors.length - 1) {
      onSegmentChange(segmentsWithErrors[currentErrorIndex + 1]);
    } else if (segmentsWithErrors.length > 0) {
      // Find the nearest next error
      const nextErrors = segmentsWithErrors.filter((idx: number) => idx > currentSegmentIndex);
      if (nextErrors.length > 0) {
        onSegmentChange(nextErrors[0]);
      } else {
        goToFirstError(); // Wrap around
      }
    }
  };

  // Handle filter changes
  const handleFilterChange = (filterType: keyof ErrorFilters) => {
    const newFilters = { ...filters, [filterType]: !filters[filterType] };
    setFilters(newFilters);
    onFilterChange?.(newFilters);
  };

  // Create error distribution mini-map
  const createErrorMap = () => {
    if (!validationReport) return null;
    
    const totalSegments = validationReport.detailed_results.length;
    const mapWidth = 200;
    const segmentWidth = mapWidth / totalSegments;
    
    return (
      <Box sx={{ position: 'relative', width: mapWidth, height: 20, bgcolor: 'grey.200', borderRadius: 1 }}>
        {validationReport.detailed_results.map((result, idx: number) => {
          const cases = (result as any).structured_cases || [];
          if (!Array.isArray(cases) || cases.length === 0) return null;

          const normalizeSeverity = (s: any) => {
            if (typeof s === 'number') return Math.max(1, Math.min(3, s));
            if (typeof s === 'string') {
              const t = s.toLowerCase();
              if (['critical', 'high', 'severe'].includes(t)) return 3;
              if (['major', 'medium', 'moderate', 'important'].includes(t)) return 2;
              if (['minor', 'low', 'trivial'].includes(t)) return 1;
              const n = parseInt(s, 10);
              if (!Number.isNaN(n)) return Math.max(1, Math.min(3, n));
            }
            return 2;
          };

          const hasRelevant = cases.some((c: any) => {
            const sev = normalizeSeverity(c.severity);
            const type = (c.dimension || '').toLowerCase();
            const isCritical = sev === 3;
            const isMissing = type.includes('missing') || /누락/.test(c.reason || '');
            const isAdded = type.includes('added') || /추가/.test(c.reason || '');
            const isName = type.includes('name') || /이름|고유명/.test(c.reason || '');
            return (
              (filters.critical && isCritical) ||
              (filters.missingContent && isMissing) ||
              (filters.addedContent && isAdded) ||
              (filters.nameInconsistencies && isName)
            );
          });

          if (!hasRelevant) return null;
          
          const severity = cases.some((c: any) => normalizeSeverity(c.severity) === 3) ? 'error' : 'warning';
          
          return (
            <Tooltip key={idx} title={`Segment ${idx + 1}: ${cases.length} issues`}>
              <Box
                sx={{
                  position: 'absolute',
                  left: idx * segmentWidth,
                  width: segmentWidth,
                  height: '100%',
                  bgcolor: severity === 'error' ? 'error.main' : 'warning.main',
                  opacity: idx === currentSegmentIndex ? 1 : 0.6,
                  cursor: 'pointer',
                  '&:hover': { opacity: 1 },
                }}
                onClick={() => onSegmentChange(idx)}
              />
            </Tooltip>
          );
        })}
        {/* Current position indicator */}
        <Box
          sx={{
            position: 'absolute',
            left: currentSegmentIndex * segmentWidth,
            width: 2,
            height: '100%',
            bgcolor: 'primary.main',
            zIndex: 1,
          }}
        />
      </Box>
    );
  };

  if (!validationReport) {
    return null;
  }

  return (
    <Paper 
      elevation={2} 
      sx={{ 
        p: 1.5, 
        mb: 2, 
        position: 'sticky', 
        top: 0, 
        zIndex: 10,
        bgcolor: 'background.paper',
      }}
    >
      <Stack direction="row" alignItems="center" spacing={2}>
        {/* Navigation Controls */}
        <Stack direction="row" spacing={0.5}>
          <Tooltip title="첫 번째 오류">
            <span>
              <IconButton 
                size="small"
                onClick={goToFirstError}
                disabled={segmentsWithErrors.length === 0}
              >
                <FirstIcon />
              </IconButton>
            </span>
          </Tooltip>
          
          <Tooltip title="이전 오류 (←)">
            <span>
              <IconButton 
                size="small"
                onClick={goToPreviousError}
                disabled={segmentsWithErrors.length === 0}
              >
                <PrevIcon />
              </IconButton>
            </span>
          </Tooltip>
          
          {/* Current Position */}
          <Box sx={{ minWidth: 100, textAlign: 'center', alignSelf: 'center' }}>
            {segmentsWithErrors.length > 0 ? (
              <Typography variant="body2">
                {isOnErrorSegment 
                  ? `${currentErrorIndex + 1} / ${segmentsWithErrors.length}`
                  : `Segment ${currentSegmentIndex + 1}`
                }
              </Typography>
            ) : (
              <Typography variant="body2" color="text.secondary">
                오류 없음
              </Typography>
            )}
          </Box>
          
          <Tooltip title="다음 오류 (→)">
            <span>
              <IconButton 
                size="small"
                onClick={goToNextError}
                disabled={segmentsWithErrors.length === 0}
              >
                <NextIcon />
              </IconButton>
            </span>
          </Tooltip>
          
          <Tooltip title="마지막 오류">
            <span>
              <IconButton 
                size="small"
                onClick={goToLastError}
                disabled={segmentsWithErrors.length === 0}
              >
                <LastIcon />
              </IconButton>
            </span>
          </Tooltip>
        </Stack>

        {/* Jump to Segment */}
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <Select
            value={currentSegmentIndex}
            onChange={(e) => onSegmentChange(Number(e.target.value))}
            displayEmpty
            size="small"
          >
            {segmentsWithErrors.map((segIdx: number) => (
              <MenuItem key={segIdx} value={segIdx}>
                Segment {segIdx + 1}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* Error Type Filters */}
        <Stack direction="row" spacing={1}>
          <Chip
            icon={<CriticalIcon />}
            label={`Critical (${errorCounts.critical})`}
            size="small"
            color={filters.critical ? 'error' : 'default'}
            onClick={() => handleFilterChange('critical')}
            variant={filters.critical ? 'filled' : 'outlined'}
          />
          <Chip
            icon={<MissingIcon />}
            label={`Missing (${errorCounts.missing})`}
            size="small"
            color={filters.missingContent ? 'warning' : 'default'}
            onClick={() => handleFilterChange('missingContent')}
            variant={filters.missingContent ? 'filled' : 'outlined'}
          />
          <Chip
            icon={<AddedIcon />}
            label={`Added (${errorCounts.added})`}
            size="small"
            color={filters.addedContent ? 'info' : 'default'}
            onClick={() => handleFilterChange('addedContent')}
            variant={filters.addedContent ? 'filled' : 'outlined'}
          />
          <Chip
            icon={<NameIcon />}
            label={`Names (${errorCounts.names})`}
            size="small"
            color={filters.nameInconsistencies ? 'secondary' : 'default'}
            onClick={() => handleFilterChange('nameInconsistencies')}
            variant={filters.nameInconsistencies ? 'filled' : 'outlined'}
          />
        </Stack>

        {/* Error Distribution Mini-map */}
        <Box sx={{ flex: 1, display: 'flex', justifyContent: 'flex-end' }}>
          {createErrorMap()}
        </Box>
      </Stack>
    </Paper>
  );
}