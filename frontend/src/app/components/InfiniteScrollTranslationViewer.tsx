'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Typography,
  Paper,
  Stack,
  Divider,
  IconButton,
  Tooltip,
  Grid,
  CircularProgress,
  Button,
  Alert,
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { TranslationContent, TranslationSegments, PostEditLog } from '../utils/api';

interface InfiniteScrollTranslationViewerProps {
  content: TranslationContent;
  sourceText?: string;
  segments?: TranslationSegments | null;
  postEditLog?: PostEditLog | null;
  jobId: string;
  onLoadMoreSegments: (offset: number, limit: number) => Promise<{
    segments: any[];
    has_more: boolean;
    total_segments: number;
  }>;
}

export default function InfiniteScrollTranslationViewer({
  content,
  sourceText,
  segments: initialSegments,
  postEditLog,
  jobId,
  onLoadMoreSegments,
}: InfiniteScrollTranslationViewerProps) {
  const [loadedSegments, setLoadedSegments] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalSegments, setTotalSegments] = useState(0);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const loadMoreTriggerRef = useRef<HTMLDivElement>(null);
  
  const loadMoreSegments = useCallback(async (offset: number) => {
    setIsLoading(true);
    setError(null);
    
    console.log('Loading segments from offset:', offset);
    
    try {
      // Use a larger page size to reduce perceived truncation
      const pageSize = 50;
      const result = await onLoadMoreSegments(offset, pageSize);
      
      console.log('Loaded segments:', result.segments.length, 'Has more:', result.has_more);
      
      if (offset === 0) {
        setLoadedSegments(result.segments);
      } else {
        setLoadedSegments(prev => [...prev, ...result.segments]);
      }
      
      setHasMore(result.has_more);
      // Some backends may not provide total; infer when needed
      setTotalSegments(result.total_segments || (result.has_more ? 0 : (offset + result.segments.length)));
    } catch (err) {
      console.error('Error loading segments:', err);
      setError(err instanceof Error ? err.message : 'Failed to load more segments');
    } finally {
      setIsLoading(false);
    }
  }, [onLoadMoreSegments]);
  
  // Initialize by loading first batch from API
  useEffect(() => {
    // Always load segments from API for dynamic loading
    // This ensures pagination works properly
    loadMoreSegments(0);
  }, [jobId]); // Only reload when job changes
  
  // Intersection Observer for infinite scrolling
  useEffect(() => {
    if (!loadMoreTriggerRef.current || !hasMore || isLoading) return;
    
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !isLoading) {
          loadMoreSegments(loadedSegments.length);
        }
      },
      {
        root: scrollContainerRef.current,
        rootMargin: '200px',
        threshold: 0.1,
      }
    );
    
    observer.observe(loadMoreTriggerRef.current);
    
    return () => observer.disconnect();
  }, [hasMore, isLoading, loadedSegments.length, loadMoreSegments]);
  
  // Merge translated text from loaded segments
  const mergedTranslatedText = React.useMemo(() => {
    if (loadedSegments.length > 0) {
      const segmentsSortedByIndex = loadedSegments
        .slice()
        .sort((a, b) => a.segment_index - b.segment_index);
      // Check if segments have post-edit data (edited_translation field)
      const firstSegment = segmentsSortedByIndex[0];
      const hasPostEditData = 'edited_translation' in firstSegment || 'original_translation' in firstSegment;

      if (hasPostEditData) {
        return segmentsSortedByIndex
          .map(segment => segment.edited_translation || segment.original_translation || segment.translated_text)
          .join('\n');
      }

      return segmentsSortedByIndex
        .map(segment => segment.translated_text)
        .join('\n');
    }
    
    // Fallback to content if no segments loaded yet
    return content.content;
  }, [loadedSegments, content.content]);
  
  // Merge source text from loaded segments
  const mergedSourceText = React.useMemo(() => {
    // Prefer reconstructing source from loaded segments for parity with translation
    if (loadedSegments.length > 0 && loadedSegments[0].source_text !== undefined) {
      return loadedSegments
        .slice()
        .sort((a, b) => a.segment_index - b.segment_index)
        .map(segment => segment.source_text)
        .join('\n');
    }
    // Fallbacks when segments not yet loaded
    if (sourceText) return sourceText;
    if (content.source_content) return content.source_content;
    return undefined;
  }, [sourceText, content.source_content, loadedSegments]);
  
  const handleCopyContent = () => {
    navigator.clipboard.writeText(mergedTranslatedText);
  };
  
  const handleCopySource = () => {
    if (mergedSourceText) {
      navigator.clipboard.writeText(mergedSourceText);
    }
  };
  
  const handleLoadAll = async () => {
    if (totalSegments <= loadedSegments.length) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      // Load remaining segments in batches to avoid very large single requests
      const batchSize = 100;
      let offset = loadedSegments.length;
      while (totalSegments === 0 || offset < totalSegments) {
        const remaining = totalSegments === 0 ? batchSize : Math.min(batchSize, totalSegments - offset);
        const result = await onLoadMoreSegments(offset, remaining);
        if (!result.segments.length) break;
        setLoadedSegments(prev => [...prev, ...result.segments]);
        offset += result.segments.length;
        if (!result.has_more) break;
      }
      setHasMore(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load all segments');
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <Stack spacing={2} sx={{ height: '100%', minHeight: 0 }}>
        {/* Removed header box as requested */}
        
        {/* Content display - side by side if source is available */}
        {mergedSourceText ? (
          <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Fixed headers */}
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid size={{ xs: 12, md: 6 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Typography variant="h6" color="text.secondary">
                    원문
                  </Typography>
                  <Tooltip title="원문 복사">
                    <IconButton onClick={handleCopySource} size="small">
                      <ContentCopyIcon />
                    </IconButton>
                  </Tooltip>
                </Stack>
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Typography variant="h6" color="text.secondary">
                    번역문
                  </Typography>
                  <Tooltip title="번역문 복사">
                    <IconButton onClick={handleCopyContent} size="small">
                      <ContentCopyIcon />
                    </IconButton>
                  </Tooltip>
                </Stack>
              </Grid>
            </Grid>
            
            {/* Shared scrollable content area */}
            <Box
              ref={scrollContainerRef}
              sx={{
                flex: 1,
                overflowY: 'auto',
                border: 1,
                borderColor: 'divider',
                borderRadius: 1,
              }}
            >
              <Grid container spacing={0}>
                {/* Source content */}
                <Grid size={{ xs: 12, md: 6 }}>
                  <Paper elevation={0} sx={{ p: 3, height: '100%', borderRadius: 0, borderRight: { md: 1 }, borderColor: 'divider' }}>
                    <Typography
                      variant="body2"
                      sx={{
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}
                    >
                      {mergedSourceText}
                    </Typography>
                  </Paper>
                </Grid>
                
                {/* Translated content */}
                <Grid size={{ xs: 12, md: 6 }}>
                  <Paper elevation={0} sx={{ p: 3, height: '100%', borderRadius: 0 }}>
                    <Typography
                      variant="body2"
                      sx={{
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}
                    >
                      {mergedTranslatedText}
                    </Typography>
                  </Paper>
                </Grid>
              </Grid>
              
              {/* Loading trigger and indicator */}
              <Box ref={loadMoreTriggerRef} sx={{ p: 2, textAlign: 'center' }}>
                {isLoading && (
                  <Stack spacing={1} alignItems="center">
                    <CircularProgress size={24} />
                    <Typography variant="caption" color="text.secondary">
                      더 많은 내용을 불러오는 중...
                    </Typography>
                  </Stack>
                )}
                {error && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    {error}
                  </Alert>
                )}
                {!hasMore && !isLoading && (totalSegments === 0 || totalSegments > 0) && (
                  <Typography variant="body2" color="text.secondary">
                    모든 내용을 불러왔습니다
                  </Typography>
                )}
              </Box>
            </Box>
          </Box>
        ) : (
          // Original single column view when no source text
          <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6" color="text.secondary">
                번역문
              </Typography>
              <Tooltip title="번역문 복사">
                <IconButton onClick={handleCopyContent} size="small">
                  <ContentCopyIcon />
                </IconButton>
              </Tooltip>
            </Stack>
            <Box
              ref={scrollContainerRef}
              sx={{
                flex: 1,
                overflowY: 'auto',
                border: 1,
                borderColor: 'divider',
                borderRadius: 1,
              }}
            >
              <Paper elevation={0} sx={{ p: 3, borderRadius: 0 }}>
                <Typography
                  variant="body2"
                  sx={{
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}
                >
                  {mergedTranslatedText}
                </Typography>
              </Paper>
              
              {/* Loading trigger and indicator */}
              <Box ref={loadMoreTriggerRef} sx={{ p: 2, textAlign: 'center' }}>
                {isLoading && (
                  <Stack spacing={1} alignItems="center">
                    <CircularProgress size={24} />
                    <Typography variant="caption" color="text.secondary">
                      더 많은 내용을 불러오는 중...
                    </Typography>
                  </Stack>
                )}
                {error && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    {error}
                  </Alert>
                )}
                {!hasMore && !isLoading && totalSegments > 0 && (
                  <Typography variant="body2" color="text.secondary">
                    모든 내용을 불러왔습니다
                  </Typography>
                )}
              </Box>
            </Box>
          </Box>
        )}
      </Stack>
    </Box>
  );
}
