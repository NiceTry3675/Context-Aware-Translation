'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Card,
  CardMedia,
  CardContent,
  Typography,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Alert,
  Tooltip,
  Chip,
  Stack,
  TextField,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import DeleteIcon from '@mui/icons-material/Delete';
import DownloadIcon from '@mui/icons-material/Download';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import AddPhotoAlternateIcon from '@mui/icons-material/AddPhotoAlternate';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Cancel';
import StorageIcon from '@mui/icons-material/Storage';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { useAuth } from '@clerk/nextjs';
import { buildOptionalAuthHeader, clearCachedClerkToken, getCachedClerkToken } from '../utils/authToken';
import { illustrationStorage } from '../utils/illustrationStorage';
import IllustrationStorageManager from './IllustrationStorageManager';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface IllustrationData {
  type?: 'image' | 'base64_image' | 'prompt' | string;
  data?: string;
  mime_type?: string;
  prompt?: string;
  timestamp?: number;
  [key: string]: unknown;
}

interface Illustration {
  segment_index: number;
  illustration_path?: string;
  prompt: string;
  success: boolean;
  type?: string;  // 'image' or 'prompt'
  reference_used?: boolean;
  illustration_data?: IllustrationData;
  world_atmosphere_used?: boolean;  // Track if text analysis was used
}

type PromptPayload = IllustrationData | { prompt: string };

interface IllustrationViewerProps {
  jobId: string;
  illustrations?: Illustration[];
  status?: string;
  count?: number;
  onGenerateIllustrations?: () => void;
  onRegenerateIllustration?: (segmentIndex: number, customPrompt?: string) => void; // Updated to support custom prompt
  onDeleteIllustration?: (segmentIndex: number) => void;
  onIllustrationsUpdate?: (newIllustrations: Illustration[]) => void; // New prop for efficient updates
}

export default function IllustrationViewer({
  jobId,
  illustrations = [],
  status,
  count = 0,
  onGenerateIllustrations,
  onRegenerateIllustration,
  onDeleteIllustration,
  onIllustrationsUpdate: _onIllustrationsUpdate,
}: IllustrationViewerProps) {
  const { getToken } = useAuth();
  const [selectedImage, setSelectedImage] = useState<Illustration | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadedImages, setLoadedImages] = useState<Record<number, string>>({});
  const [loadedPrompts, setLoadedPrompts] = useState<Record<number, PromptPayload>>({});
  // Tracks version signatures (not literal timestamps) to detect fresh data
  const [imageTimestamps, setImageTimestamps] = useState<{ [key: number]: number }>({});
  const [promptTimestamps, setPromptTimestamps] = useState<{ [key: number]: number }>({});
  const [useClientStorage, setUseClientStorage] = useState<boolean | null>(null);
  const pendingFetchRef = useRef<Set<number>>(new Set());

  // New states for prompt editing functionality
  const [editingPrompt, setEditingPrompt] = useState<number | null>(null);
  const [customPrompts, setCustomPrompts] = useState<{ [key: number]: string }>({});
  const [promptErrors, setPromptErrors] = useState<{ [key: number]: string }>({});
  const [storageManagerOpen, setStorageManagerOpen] = useState(false);

  // Check if we should use client-side storage
  useEffect(() => {
    const checkConfig = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/illustrations/config`);
        if (response.ok) {
          const config = await response.json();
          setUseClientStorage(config.client_side_storage);
        }
      } catch (error) {
        console.error('Failed to fetch illustration config:', error);
        setUseClientStorage(false); // Default to server storage on error
      }
    };
    checkConfig();
  }, []);

  const loadIllustrations = useCallback(async () => {
    if (!jobId || useClientStorage === null) {
      return; // Wait for config to be loaded
    }

    const computeSignature = (value: string | null | undefined): number => {
      if (!value) return 0;
      let hash = 0;
      const step = Math.max(1, Math.floor(value.length / 64));
      for (let i = 0; i < value.length; i += step) {
        hash = (hash * 31 + value.charCodeAt(i)) >>> 0;
      }
      return hash;
    };

    let mergedImages = { ...loadedImages };
    let mergedPrompts = { ...loadedPrompts };
    let mergedImageVersions = { ...imageTimestamps };
    let mergedPromptVersions = { ...promptTimestamps };
    let imagesChanged = false;
    let promptsChanged = false;

    if (useClientStorage) {
      const storedIllustrations = await illustrationStorage.getJobIllustrations(jobId);

      for (const stored of storedIllustrations) {
        const segmentIndex = stored.segmentIndex;
        const signature = computeSignature(stored.data);

        if (stored.type === 'image') {
          const shouldUpdate = !mergedImages[segmentIndex] || mergedImageVersions[segmentIndex] !== signature;
          if (shouldUpdate) {
            try {
              const blobUrl = illustrationStorage.base64ToBlobUrl(
                stored.data,
                stored.mimeType
              );
              mergedImages = { ...mergedImages, [segmentIndex]: blobUrl };
              mergedImageVersions = { ...mergedImageVersions, [segmentIndex]: signature };
              imagesChanged = true;
            } catch (error) {
              console.error(`Failed to convert stored illustration ${segmentIndex} to blob:`, error);
            }
          }
        } else {
          const shouldUpdate = !mergedPrompts[segmentIndex] || mergedPromptVersions[segmentIndex] !== signature;
          if (shouldUpdate) {
            try {
              const parsed = JSON.parse(stored.data) as PromptPayload;
              mergedPrompts = { ...mergedPrompts, [segmentIndex]: parsed };
              mergedPromptVersions = { ...mergedPromptVersions, [segmentIndex]: signature };
              promptsChanged = true;
            } catch (error) {
              console.error(`Failed to parse stored prompt ${segmentIndex}:`, error);
            }
          }
        }
      }
    }

    for (const ill of illustrations) {
      if (!ill || !ill.success) continue;

    const segmentIndex = ill.segment_index;
    const inlineData = ill.illustration_data;
      const inlineType = inlineData?.type || ill.type;

      if ((inlineType === 'image' || inlineType === 'base64_image') && typeof inlineData?.data === 'string') {
        const base64Data: string = inlineData.data;
        const signature = computeSignature(base64Data);
        const shouldUpdate = !mergedImages[segmentIndex] || mergedImageVersions[segmentIndex] !== signature;

        if (shouldUpdate) {
          try {
            const blobUrl = illustrationStorage.base64ToBlobUrl(
              base64Data,
              inlineData?.mime_type || 'image/png'
            );
            mergedImages = { ...mergedImages, [segmentIndex]: blobUrl };
            mergedImageVersions = { ...mergedImageVersions, [segmentIndex]: signature };
            imagesChanged = true;
          } catch (error) {
            console.error(`Failed to convert inline illustration ${segmentIndex} to blob:`, error);
          }
        }

        if (useClientStorage) {
          try {
            await illustrationStorage.storeIllustration(
              jobId,
              segmentIndex,
              {
                ...inlineData,
                type: 'image',
                data: base64Data,
                mime_type: inlineData?.mime_type || 'image/png'
              },
              'image'
            );
          } catch (error) {
            console.error(`Failed to persist inline illustration ${segmentIndex}:`, error);
          }
        }
      }

      const promptPayload: PromptPayload | null = (() => {
        if (inlineData && inlineType && inlineType !== 'image' && inlineType !== 'base64_image') {
          return inlineData as PromptPayload;
        }
        if (inlineData && inlineData.type === 'prompt') {
          return inlineData as PromptPayload;
        }
        if (typeof inlineData?.prompt === 'string') {
          return { prompt: inlineData.prompt };
        }
        if (ill.prompt) {
          return { prompt: ill.prompt };
        }
        return null;
      })();

      if (promptPayload) {
        const normalizedPrompt = promptPayload as PromptPayload;
        const promptString = JSON.stringify(normalizedPrompt);
        const signature = computeSignature(promptString);
        const shouldUpdate = !mergedPrompts[segmentIndex] || mergedPromptVersions[segmentIndex] !== signature;

        if (shouldUpdate) {
          mergedPrompts = {
            ...mergedPrompts,
            [segmentIndex]: normalizedPrompt,
          };
          mergedPromptVersions = { ...mergedPromptVersions, [segmentIndex]: signature };
          promptsChanged = true;
        }

        if (useClientStorage) {
          try {
            await illustrationStorage.storeIllustration(jobId, segmentIndex, normalizedPrompt, 'prompt');
          } catch (error) {
            console.error(`Failed to persist inline prompt ${segmentIndex}:`, error);
          }
        }
      }
    }

    const missingIllustrations = illustrations.filter(ill => {
      if (!ill.success) return false;

      const expectsImage = ill.type === 'base64_image' || ill.type === 'image' ||
        (typeof ill.illustration_path === 'string' && ill.illustration_path.endsWith('.png'));

      const hasImage = !!mergedImages[ill.segment_index];
      const hasPrompt = !!mergedPrompts[ill.segment_index];
      const hasInline = Boolean(ill.illustration_data?.data);
      const isPending = pendingFetchRef.current.has(ill.segment_index);

      if (expectsImage) {
        return !hasImage && !hasInline && !isPending;
      }

      return !hasPrompt && !isPending;
    });

    if (missingIllustrations.length === 0) {
      if (imagesChanged) {
        setLoadedImages(mergedImages);
        setImageTimestamps(mergedImageVersions);
      }
      if (promptsChanged) {
        setLoadedPrompts(mergedPrompts);
        setPromptTimestamps(mergedPromptVersions);
      }
      return;
    }

    console.log(`Loading ${missingIllustrations.length} new illustrations out of ${illustrations.length} total`);

    let authHeaders = buildOptionalAuthHeader();
    let attemptedRefresh = false;

    const fetchWithAuth = async (segmentIndex: number): Promise<Response | null> => {
      const url = `${API_BASE_URL}/api/v1/illustrations/${jobId}/illustration/${segmentIndex}`;

      const requestWithCurrentAuth = () =>
        fetch(url, authHeaders.Authorization ? { headers: authHeaders } : undefined);

      try {
        let response = await requestWithCurrentAuth();

        if (response.status === 401 && !attemptedRefresh) {
          attemptedRefresh = true;
          clearCachedClerkToken();
          const freshToken = await getCachedClerkToken(getToken);
          if (freshToken) {
            authHeaders = { Authorization: `Bearer ${freshToken}` };
            response = await fetch(url, { headers: authHeaders });
          }
        }

        if (response.status === 401) {
          console.warn(`Unauthorized fetching illustration ${segmentIndex}; skipping.`);
          return null;
        }

        return response;
      } catch (error) {
        console.error(`Failed to load illustration ${segmentIndex}:`, error);
        return null;
      }
    };

    missingIllustrations.forEach(ill => pendingFetchRef.current.add(ill.segment_index));

    const illustrationPromises = missingIllustrations.map(async (ill) => {
      try {
        const response = await fetchWithAuth(ill.segment_index);
        if (!response || !response.ok) {
          return null;
        }

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('image')) {
          const blob = await response.blob();
          const url = URL.createObjectURL(blob);
          return { index: ill.segment_index, type: 'image' as const, data: url };
        }

        const data = await response.json();

        if (useClientStorage && data.type === 'image' && data.data) {
          try {
            await illustrationStorage.storeIllustration(
              jobId,
              ill.segment_index,
              data,
              'image'
            );
            const blobUrl = illustrationStorage.base64ToBlobUrl(
              data.data,
              data.mime_type || 'image/png'
            );
            return { index: ill.segment_index, type: 'image' as const, data: blobUrl };
          } catch (error) {
            console.error(`Failed to store illustration ${ill.segment_index} in IndexedDB:`, error);
            const blobUrl = illustrationStorage.base64ToBlobUrl(
              data.data,
              data.mime_type || 'image/png'
            );
            return { index: ill.segment_index, type: 'image' as const, data: blobUrl };
          }
        }

        if (useClientStorage) {
          try {
            await illustrationStorage.storeIllustration(
              jobId,
              ill.segment_index,
              data,
              'prompt'
            );
          } catch (error) {
            console.error(`Failed to store prompt ${ill.segment_index} in IndexedDB:`, error);
          }
        }

        return { index: ill.segment_index, type: 'prompt' as const, data };
      } finally {
        pendingFetchRef.current.delete(ill.segment_index);
      }
    });

    const results = await Promise.all(illustrationPromises);

    results.forEach((result) => {
      if (!result) return;

      if (result.type === 'image') {
        mergedImages = { ...mergedImages, [result.index]: result.data };
        mergedImageVersions = { ...mergedImageVersions, [result.index]: Date.now() };
        imagesChanged = true;
      } else {
        mergedPrompts = { ...mergedPrompts, [result.index]: result.data };
        mergedPromptVersions = { ...mergedPromptVersions, [result.index]: Date.now() };
        promptsChanged = true;
      }
    });

    if (imagesChanged) {
      setLoadedImages(mergedImages);
      setImageTimestamps(mergedImageVersions);
    }
    if (promptsChanged) {
      setLoadedPrompts(mergedPrompts);
      setPromptTimestamps(mergedPromptVersions);
    }
  }, [getToken, illustrations, jobId, imageTimestamps, loadedImages, loadedPrompts, promptTimestamps, useClientStorage]);

  // Load illustrations from API with caching to prevent redundant Clerk API calls
  useEffect(() => {
    if (jobId && illustrations.length > 0) {
      loadIllustrations();
    }
  }, [jobId, illustrations, loadIllustrations]);

  const handleDownload = (illustration: Illustration) => {
    // Check if we have an image first
    const imageUrl = loadedImages[illustration.segment_index];
    if (imageUrl) {
      const link = document.createElement('a');
      link.href = imageUrl;
      link.download = `segment_${illustration.segment_index}_illustration.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } else {
      // Fall back to prompt download
      const promptData = loadedPrompts[illustration.segment_index];
      if (promptData) {
        const blob = new Blob([JSON.stringify(promptData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `segment_${illustration.segment_index}_prompt.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      }
    }
  };

  const handleRegenerate = async (segmentIndex: number) => {
    if (onRegenerateIllustration) {
      setLoading(true);
      const customPrompt = customPrompts[segmentIndex];
      await onRegenerateIllustration(segmentIndex, customPrompt);
      setLoading(false);
    }
  };

  const handleStartEdit = (segmentIndex: number, currentPrompt: string) => {
    setEditingPrompt(segmentIndex);
    setCustomPrompts(prev => ({
      ...prev,
      [segmentIndex]: currentPrompt
    }));
    setPromptErrors(prev => ({ ...prev, [segmentIndex]: '' }));
  };

  const handleCancelEdit = (segmentIndex: number) => {
    setEditingPrompt(null);
    setCustomPrompts(prev => {
      const newPrompts = { ...prev };
      delete newPrompts[segmentIndex];
      return newPrompts;
    });
    setPromptErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[segmentIndex];
      return newErrors;
    });
  };

  const handleSavePrompt = (segmentIndex: number) => {
    const customPrompt = customPrompts[segmentIndex];
    if (!customPrompt || customPrompt.trim().length === 0) {
      setPromptErrors(prev => ({
        ...prev,
        [segmentIndex]: '프롬프트는 비어있을 수 없습니다.'
      }));
      return;
    }

    if (customPrompt.trim().length < 10) {
      setPromptErrors(prev => ({
        ...prev,
        [segmentIndex]: '프롬프트는 최소 10자 이상이어야 합니다.'
      }));
      return;
    }

    setEditingPrompt(null);
    setPromptErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[segmentIndex];
      return newErrors;
    });
  };

  const handlePromptChange = (segmentIndex: number, value: string) => {
    setCustomPrompts(prev => ({
      ...prev,
      [segmentIndex]: value
    }));

    // Clear error when user starts typing
    if (promptErrors[segmentIndex]) {
      setPromptErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[segmentIndex];
        return newErrors;
      });
    }
  };

  const handleDelete = async (segmentIndex: number) => {
    if (onDeleteIllustration) {
      await onDeleteIllustration(segmentIndex);
      // Remove from loaded images and prompts
      setLoadedImages(prev => {
        const newLoadedImages = { ...prev };
        delete newLoadedImages[segmentIndex];
        return newLoadedImages;
      });
      setImageTimestamps(prev => {
        const next = { ...prev };
        delete next[segmentIndex];
        return next;
      });

      setLoadedPrompts(prev => {
        const newLoadedPrompts = { ...prev };
        delete newLoadedPrompts[segmentIndex];
        return newLoadedPrompts;
      });
      setPromptTimestamps(prev => {
        const next = { ...prev };
        delete next[segmentIndex];
        return next;
      });
    }
  };

  const handleImageClick = (illustration: Illustration) => {
    setSelectedImage(illustration);
  };

  const handleCloseDialog = () => {
    setSelectedImage(null);
  };

  if (status === 'NOT_STARTED' || !status) {
    return (
      <Box sx={{ p: { xs: 1.5, sm: 2, md: 3 } }}>
        <Alert severity="info" sx={{ mb: 2 }}>
          삽화가 아직 생성되지 않았습니다.
        </Alert>
        {onGenerateIllustrations && (
          <Button
            variant="contained"
            startIcon={<AddPhotoAlternateIcon />}
            onClick={onGenerateIllustrations}
            color="primary"
          >
            삽화 생성 시작
          </Button>
        )}
      </Box>
    );
  }

  if (status === 'IN_PROGRESS') {
    return (
      <Box sx={{ p: { xs: 1.5, sm: 2, md: 3 }, display: 'flex', alignItems: 'center', gap: 2 }}>
        <CircularProgress />
        <Typography>삽화 생성 중입니다...</Typography>
      </Box>
    );
  }

  if (status === 'FAILED') {
    return (
      <Box sx={{ p: { xs: 1.5, sm: 2, md: 3 } }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          삽화 생성 중 오류가 발생했습니다.
        </Alert>
        {onGenerateIllustrations && (
          <Button
            variant="contained"
            startIcon={<RefreshIcon />}
            onClick={onGenerateIllustrations}
            color="primary"
          >
            다시 시도
          </Button>
        )}
      </Box>
    );
  }

  return (
    <Box sx={{ p: { xs: 1.5, sm: 2, md: 3 } }}>
      <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'stretch', sm: 'center' }} sx={{ mb: { xs: 2, sm: 3 }, gap: 1 }}>
        <Typography variant="h6" sx={{ fontSize: { xs: '1.1rem', sm: '1.25rem' } }}>
          생성된 삽화 ({count}개)
        </Typography>
        <Stack direction="row" spacing={1}>
          {useClientStorage && (
            <Tooltip title="Manage local storage">
              <Button
                variant="outlined"
                startIcon={<StorageIcon />}
                onClick={() => setStorageManagerOpen(true)}
                size="small"
              >
                Storage
              </Button>
            </Tooltip>
          )}
          {onGenerateIllustrations && (
            <Button
              variant="outlined"
              startIcon={<AddPhotoAlternateIcon />}
              onClick={onGenerateIllustrations}
              size="small"
            >
              추가 생성
            </Button>
          )}
        </Stack>
      </Stack>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(3, 1fr)', lg: 'repeat(4, 1fr)' }, gap: { xs: 1.5, sm: 2, md: 3 } }}>
        {illustrations.map((illustration) => (
          <Card key={illustration.segment_index} sx={{ height: '100%', display: 'flex', flexDirection: 'column', position: 'relative' }}>
              {loadedImages[illustration.segment_index] ? (
                <>
                  <CardMedia
                    component="img"
                    height="200"
                    image={loadedImages[illustration.segment_index]}
                    alt={`Segment ${illustration.segment_index} illustration`}
                    sx={{ cursor: 'pointer', objectFit: 'cover' }}
                    onClick={() => handleImageClick(illustration)}
                  />
                  {illustration.world_atmosphere_used === false && (
                    <Tooltip title="기본 프롬프트 사용됨 (검열, API 제한 등으로 인해 텍스트 분석 실패)" arrow>
                      <InfoOutlinedIcon
                        sx={{
                          fontSize: 16,
                          opacity: 0.4,
                          position: 'absolute',
                          bottom: 8,
                          right: 8,
                          color: 'white',
                          backgroundColor: 'rgba(0, 0, 0, 0.3)',
                          borderRadius: '50%',
                          padding: '2px',
                          '&:hover': {
                            opacity: 0.8,
                          }
                        }}
                      />
                    </Tooltip>
                  )}
                </>
              ) : loadedPrompts[illustration.segment_index] ? (
                <Box
                  sx={{
                    height: 200,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    bgcolor: 'grey.100',
                    p: 2,
                    cursor: 'pointer',
                    border: '1px solid',
                    borderColor: 'grey.300',
                    '&:hover': {
                      bgcolor: 'grey.200',
                    },
                  }}
                  onClick={() => handleImageClick(illustration)}
                >
                  <Typography variant="h3" color="primary" sx={{ mb: 1 }}>📝</Typography>
                  <Typography variant="body2" color="text.secondary">
                    프롬프트만 생성됨
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    (이미지 생성 실패)
                  </Typography>
                </Box>
              ) : (
                <Box
                  sx={{
                    height: 200,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    bgcolor: 'grey.200',
                  }}
                >
                  {illustration.success ? (
                    <CircularProgress />
                  ) : (
                    <Typography color="text.secondary">생성 실패</Typography>
                  )}
                </Box>
              )}
              <CardContent sx={{ flexGrow: 1 }}>
                <Stack spacing={1}>
                  <Typography variant="subtitle2" gutterBottom>
                    세그먼트 {illustration.segment_index}
                  </Typography>
                  {loadedImages[illustration.segment_index] ? (
                    <Stack direction="row" spacing={1}>
                      <Chip label="이미지 생성 완료" color="success" size="small" />
                      {illustration.reference_used && (
                        <Chip label="참조 사용" color="primary" size="small" />
                      )}
                    </Stack>
                  ) : illustration.success ? (
                    <Chip label="프롬프트만 생성됨" color="warning" size="small" />
                  ) : (
                    <Chip label="생성 실패" color="error" size="small" />
                  )}

                  {/* Prompt editing section */}
                  {editingPrompt === illustration.segment_index ? (
                    <Box sx={{ mt: 1 }}>
                      {illustration.world_atmosphere_used === false && (
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5, fontStyle: 'italic' }}>
                          ℹ️ 이 삽화는 기본 프롬프트로 생성되었습니다 (검열, API 제한 등으로 인해 텍스트 분석 실패)
                        </Typography>
                      )}
                      <TextField
                        fullWidth
                        multiline
                        rows={3}
                        value={customPrompts[illustration.segment_index] || ''}
                        onChange={(e) => handlePromptChange(illustration.segment_index, e.target.value)}
                        placeholder="프롬프트를 입력하세요..."
                        variant="outlined"
                        size="small"
                        error={!!promptErrors[illustration.segment_index]}
                        helperText={promptErrors[illustration.segment_index] || `${customPrompts[illustration.segment_index]?.length || 0}자`}
                        sx={{
                          '& .MuiOutlinedInput-root': {
                            fontSize: '0.75rem',
                          }
                        }}
                      />
                      {promptErrors[illustration.segment_index] && (
                        <Typography variant="caption" color="error" sx={{ mt: 0.5, display: 'block' }}>
                          {promptErrors[illustration.segment_index]}
                        </Typography>
                      )}
                    </Box>
                  ) : (
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        minHeight: '2.5em',
                      }}
                    >
                      {customPrompts[illustration.segment_index] || illustration.prompt}
                    </Typography>
                  )}
                </Stack>
              </CardContent>
              <Box sx={{ p: 1, display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                {/* Edit mode buttons */}
                {editingPrompt === illustration.segment_index ? (
                  <>
                    <Tooltip title="저장">
                      <IconButton
                        size="small"
                        onClick={() => handleSavePrompt(illustration.segment_index)}
                        color="primary"
                        disabled={loading}
                      >
                        <SaveIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="취소">
                      <IconButton
                        size="small"
                        onClick={() => handleCancelEdit(illustration.segment_index)}
                        disabled={loading}
                      >
                        <CancelIcon />
                      </IconButton>
                    </Tooltip>
                  </>
                ) : (
                  <>
                    <Tooltip title="확대">
                      <IconButton
                        size="small"
                        onClick={() => handleImageClick(illustration)}
                        disabled={!illustration.success}
                      >
                        <ZoomInIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="다운로드">
                      <IconButton
                        size="small"
                        onClick={() => handleDownload(illustration)}
                        disabled={!illustration.success}
                      >
                        <DownloadIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="프롬프트 편집">
                      <IconButton
                        size="small"
                        onClick={() => handleStartEdit(illustration.segment_index, illustration.prompt)}
                        disabled={loading}
                      >
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                    {onRegenerateIllustration && (
                      <Tooltip title={customPrompts[illustration.segment_index] ? "커스텀 프롬프트로 재생성" : "재생성"}>
                        <IconButton
                          size="small"
                          onClick={() => handleRegenerate(illustration.segment_index)}
                          disabled={loading}
                          color={customPrompts[illustration.segment_index] ? "secondary" : "default"}
                        >
                          <RefreshIcon />
                        </IconButton>
                      </Tooltip>
                    )}
                    {onDeleteIllustration && (
                      <Tooltip title="삭제">
                        <IconButton
                          size="small"
                          onClick={() => handleDelete(illustration.segment_index)}
                          color="error"
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    )}
                  </>
                )}
              </Box>
            </Card>
        ))}
      </Box>

      {/* Image Dialog */}
      <Dialog
        open={!!selectedImage}
        onClose={handleCloseDialog}
        maxWidth="lg"
        fullWidth
      >
        {selectedImage && (
          <>
            <DialogTitle>
              세그먼트 {selectedImage.segment_index} 삽화
            </DialogTitle>
            <DialogContent>
              {loadedImages[selectedImage.segment_index] ? (
                <Box sx={{ textAlign: 'center' }}>
                  <img
                    src={loadedImages[selectedImage.segment_index]}
                    alt={`Segment ${selectedImage.segment_index}`}
                    style={{
                      maxWidth: '100%',
                      maxHeight: '70vh',
                      objectFit: 'contain',
                    }}
                  />
                  <Typography
                    variant="body2"
                    sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1, color: '#000000' }}
                  >
                    프롬프트: {selectedImage.prompt}
                  </Typography>
                </Box>
              ) : (
                <Box sx={{ p: 2 }}>
                  <Typography variant="h6" gutterBottom sx={{ color: '#000000' }}>
                    생성된 프롬프트
                  </Typography>
                  <Box
                    sx={{
                      p: 2,
                      bgcolor: 'grey.50',
                      borderRadius: 1,
                      border: '1px solid',
                      borderColor: 'grey.300',
                      mb: 2,
                    }}
                  >
                    <Typography
                      variant="body1"
                      sx={{
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        color: '#000000',
                      }}
                    >
                      {selectedImage.prompt}
                    </Typography>
                  </Box>
                  {loadedPrompts[selectedImage.segment_index] && (
                    <Box>
                      <Typography variant="subtitle2" gutterBottom sx={{ color: '#000000' }}>
                        프롬프트 세부 정보
                      </Typography>
                      <Box
                        sx={{
                          p: 2,
                          bgcolor: 'grey.100',
                          borderRadius: 1,
                          fontFamily: 'monospace',
                          fontSize: '0.85rem',
                          whiteSpace: 'pre-wrap',
                          overflowX: 'auto',
                          color: '#000000',
                        }}
                      >
                        {JSON.stringify(loadedPrompts[selectedImage.segment_index], null, 2)}
                      </Box>
                    </Box>
                  )}
                  <Alert severity="warning" sx={{ mt: 2 }}>
                    이미지 생성에 실패했습니다. 이 프롬프트를 다른 이미지 생성 서비스에서 사용할 수 있습니다.
                  </Alert>
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => handleDownload(selectedImage)}>다운로드</Button>
              <Button onClick={handleCloseDialog}>닫기</Button>
            </DialogActions>
          </>
        )}
      </Dialog>

      {/* Storage Manager */}
      <IllustrationStorageManager
        open={storageManagerOpen}
        onClose={() => setStorageManagerOpen(false)}
        currentJobId={jobId}
      />
    </Box>
  );
}
