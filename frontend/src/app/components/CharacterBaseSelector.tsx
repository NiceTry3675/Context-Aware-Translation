'use client';

import React, { useEffect, useState } from 'react';
import { Box, Button, Card, CardMedia, CardContent, Typography, Stack, Radio, CircularProgress, Alert, TextField, IconButton, Collapse } from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Cancel';
import RefreshIcon from '@mui/icons-material/Refresh';
import { useAuth } from '@clerk/nextjs';
import { getCachedClerkToken } from '../utils/authToken';
import { getCharacterBases, generateCharacterBases, selectCharacterBase, CharacterProfileBody, analyzeCharacterAppearance, generateBasesFromPrompt, regenerateBase } from '../utils/api';
import type { ApiProvider } from '../hooks/useApiKey';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface CharacterBaseSelectorProps {
  jobId: string;
  apiProvider: ApiProvider;
  apiKey?: string; // required to generate bases
  providerConfig?: string;
  onChange?: () => void; // called after selection or generation
}

export default function CharacterBaseSelector({ jobId, apiProvider, apiKey, providerConfig, onChange }: CharacterBaseSelectorProps) {
  const { getToken } = useAuth();
  const [loading, setLoading] = useState(false);
  const [bases, setBases] = useState<any[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<CharacterProfileBody | null>(null);
  const [imageUrls, setImageUrls] = useState<Record<number, string>>({});
  const [nameInput, setNameInput] = useState<string>("");
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [appearancePrompts, setAppearancePrompts] = useState<string[]>([]);
  const [appearanceNotice, setAppearanceNotice] = useState<string | null>(null);

  // New states for prompt editing functionality
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [customPrompts, setCustomPrompts] = useState<{ [key: number]: string }>({});
  const [promptErrors, setPromptErrors] = useState<{ [key: number]: string }>({});

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await getCachedClerkToken(getToken);
      const data = await getCharacterBases(jobId, token || undefined);
      const list = data.bases || [];
      setBases(list);
      setSelectedIndex(typeof data.selected_index === 'number' ? data.selected_index : null);
      setProfile((data.profile as CharacterProfileBody) || null);

      // Sync custom prompts with server data so they persist across reloads
      setCustomPrompts(prev => {
        const next: { [key: number]: string } = { ...prev };
        list.forEach((base: any, idx: number) => {
          if (base && typeof base.prompt === 'string' && base.prompt.trim()) {
            next[idx] = base.prompt;
          }
        });
        return next;
      });

      // Load images or prompts for preview
      const timestamp = Date.now();

      const fetchWithRetry = async (index: number, attempts: number = 5, delayMs: number = 800) => {
        for (let attempt = 1; attempt <= attempts; attempt++) {
          try {
            const res = await fetch(`${API_BASE_URL}/api/v1/illustrations/${jobId}/character/base/${index}?t=${timestamp}`, {
              headers: {
                'Authorization': token ? `Bearer ${token}` : '',
              },
              cache: 'no-store',
            });
            if (res.ok) {
              const contentType = res.headers.get('content-type') || '';
              if (contentType.includes('image')) {
                const blob = await res.blob();
                return URL.createObjectURL(blob);
              }
            }
          } catch {
            // ignore and retry
          }
          if (attempt < attempts) {
            await new Promise(resolve => setTimeout(resolve, delayMs));
          }
        }
        return undefined;
      };

      const nextUrls: { [key: number]: string } = {};
      await Promise.all((list as any[]).map(async (_b: any, i: number) => {
        const url = await fetchWithRetry(i);
        if (url) {
          nextUrls[i] = url;
        }
      }));
      setImageUrls(nextUrls);
    } catch (e) {
      // ignore if none exist yet
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (jobId) load();
  }, [jobId]);

  const handleGenerate = async () => {
    if (apiProvider !== 'vertex' && !apiKey) {
      setError('API Key가 필요합니다. 설정에서 API 키를 입력하세요.');
      return;
    }
    if (apiProvider === 'vertex' && (!providerConfig || !providerConfig.trim())) {
      setError('Vertex 서비스 계정 JSON이 필요합니다. 설정에서 JSON을 입력하세요.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const token = await getCachedClerkToken(getToken);
      // Very simple default profile; UI form can be added later
      const defaultProfile: CharacterProfileBody = {
        name: nameInput && nameInput.trim() ? nameInput.trim() : (profile?.name || 'Protagonist'),
        // Keep only minimal style preference; avoid detailed attributes
        style: profile?.style || 'digital_art',
        extra_style_hints: profile?.extra_style_hints || 'clean linework, soft lighting'
      };
      await generateCharacterBases({
        jobId,
        token: token || undefined,
        profile: defaultProfile,
        referenceImage: referenceFile || undefined,
        apiProvider,
        apiKey,
        providerConfig,
      });
      await load();
      onChange?.();
    } catch (e: any) {
      setError(e?.message || '베이스 이미지 생성에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeAppearance = async () => {
    if (apiProvider !== 'vertex' && !apiKey) {
      setError('API Key가 필요합니다. 설정에서 API 키를 입력하세요.');
      return;
    }
    if (apiProvider === 'vertex' && (!providerConfig || !providerConfig.trim())) {
      setError('Vertex 서비스 계정 JSON이 필요합니다.');
      return;
    }
    setLoading(true);
    setError(null);
    setAppearanceNotice(null);
    try {
      const token = await getCachedClerkToken(getToken);
      const res = await analyzeCharacterAppearance({
        jobId,
        token: token || undefined,
        protagonistName: nameInput || undefined,
        apiProvider,
        apiKey,
        providerConfig,
      });
      setAppearancePrompts(res.prompts || []);
      setAppearanceNotice(res.notice || null);
    } catch (e: any) {
      setError(e?.message || '외형 분석에 실패했습니다.');
      setAppearancePrompts([]);
      setAppearanceNotice(null);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateFromPrompt = async (promptText: string) => {
    if (apiProvider !== 'vertex' && !apiKey) {
      setError('API Key가 필요합니다. 설정에서 API 키를 입력하세요.');
      return;
    }
    if (apiProvider === 'vertex' && (!providerConfig || !providerConfig.trim())) {
      setError('Vertex 서비스 계정 JSON이 필요합니다.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const token = await getCachedClerkToken(getToken);
      await generateBasesFromPrompt({
        jobId,
        token: token || undefined,
        prompts: [promptText],
        referenceImage: referenceFile || undefined,
        apiProvider,
        apiKey,
        providerConfig,
      });
      await load();
      onChange?.();
    } catch (e: any) {
      setError(e?.message || '프롬프트로 베이스 생성에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = async () => {
    if (selectedIndex === null) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getCachedClerkToken(getToken);
      await selectCharacterBase(jobId, token || undefined, selectedIndex);
      onChange?.();
    } catch (e: any) {
      setError(e?.message || '베이스 선택에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleStartEdit = (index: number, currentPrompt: string) => {
    setEditingIndex(index);
    setCustomPrompts(prev => ({
      ...prev,
      [index]: currentPrompt
    }));
    setPromptErrors(prev => ({ ...prev, [index]: '' }));
  };

  const handleCancelEdit = (index: number) => {
    setEditingIndex(null);
    setCustomPrompts(prev => {
      const newPrompts = { ...prev };
      delete newPrompts[index];
      return newPrompts;
    });
    setPromptErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[index];
      return newErrors;
    });
  };

  const handleSavePrompt = (index: number) => {
    const customPrompt = (customPrompts[index] || '').trim();
    if (!customPrompt) {
      setPromptErrors(prev => ({
        ...prev,
        [index]: '프롬프트는 비어있을 수 없습니다.'
      }));
      return;
    }

    if (customPrompt.length < 10) {
      setPromptErrors(prev => ({
        ...prev,
        [index]: '프롬프트는 최소 10자 이상이어야 합니다.'
      }));
      return;
    }

    setCustomPrompts(prev => ({
      ...prev,
      [index]: customPrompt,
    }));

    setBases(prev => {
      const next = [...prev];
      if (next[index]) {
        next[index] = { ...next[index], prompt: customPrompt };
      }
      return next;
    });

    setEditingIndex(null);
    setPromptErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[index];
      return newErrors;
    });
  };

  const handlePromptChange = (index: number, value: string) => {
    setCustomPrompts(prev => ({
      ...prev,
      [index]: value
    }));

    // Clear error when user starts typing
    if (promptErrors[index]) {
      setPromptErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[index];
        return newErrors;
      });
    }
  };

  const handleRegenerateBase = async (index: number) => {
    const customPrompt = customPrompts[index];
    if (!customPrompt || customPrompt.trim().length === 0) {
      setPromptErrors(prev => ({
        ...prev,
        [index]: '커스텀 프롬프트가 필요합니다.'
      }));
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const token = await getCachedClerkToken(getToken);
      await regenerateBase({
        jobId,
        baseIndex: index,
        customPrompt,
        token: token || undefined,
        apiProvider,
        apiKey: apiProvider === 'vertex' ? '' : (apiKey || ''),
        providerConfig,
      });
      console.log('Successfully regenerated base', index, 'with custom prompt');
      // Allow backend processing time before reloading assets
      await new Promise(resolve => setTimeout(resolve, 2500));
      await load(); // Reload to show updated base
      onChange?.();
    } catch (e: any) {
      setError(e?.message || '베이스 재생성에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p: 2, border: '1px solid', borderColor: 'grey.300', borderRadius: 1, mb: 2 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="subtitle1">캐릭터 베이스 이미지</Typography>
        <Button variant="outlined" onClick={handleGenerate} disabled={loading}>
          {bases.length ? '다시 생성' : '베이스 생성'}
        </Button>
      </Stack>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
        <Button component="label" variant="outlined" size="small">
          참조 이미지 선택
          <input
            type="file"
            accept="image/*"
            hidden
            onChange={(e) => {
              const file = e.target.files?.[0] || null;
              setReferenceFile(file);
            }}
          />
        </Button>
        {referenceFile && (
          <Typography variant="body2" color="text.secondary">
            선택됨: {referenceFile.name}
          </Typography>
        )}
      </Stack>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
        <TextField
          label="주인공 이름"
          placeholder="예: 아리아, 민준, 루카"
          value={nameInput}
          onChange={(e) => setNameInput(e.target.value)}
          size="small"
        />
        <Button variant="outlined" size="small" onClick={handleAnalyzeAppearance} disabled={loading}>
          외형 자동 분석
        </Button>
      </Stack>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
      )}
      {appearanceNotice && (
        <Alert severity="warning" sx={{ mb: 2 }}>{appearanceNotice}</Alert>
      )}
      {loading && (
        <Stack direction="row" alignItems="center" gap={1} sx={{ mb: 2 }}>
          <CircularProgress size={20} />
          <Typography>처리 중...</Typography>
        </Stack>
      )}
      {bases.length > 0 ? (
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(3, 1fr)' }, gap: 2 }}>
          {bases.map((b, i) => (
            <Card key={i} sx={{ border: selectedIndex === i ? '2px solid' : '1px solid', borderColor: selectedIndex === i ? 'primary.main' : 'grey.300' }}>
              {imageUrls[i] ? (
                <CardMedia component="img" height="240" image={imageUrls[i]} alt={`base ${i+1}`} sx={{ objectFit: 'contain', bgcolor: 'grey.50' }} />
              ) : (
                <Box sx={{ height: 240, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: 'grey.100' }}>
                  <Typography variant="body2" color="text.secondary">프롬프트만 생성됨</Typography>
                </Box>
              )}
              <CardContent>
                <Stack direction="row" alignItems="center" gap={1}>
                  <Radio checked={selectedIndex === i} onChange={() => setSelectedIndex(i)} />
                  <Typography variant="body2">베이스 {i+1}</Typography>
                  {b?.used_reference && (
                    <Box component="span" sx={{ ml: 1, px: 1, py: 0.2, bgcolor: 'primary.main', color: '#ffffff', borderRadius: 1, fontSize: '0.75rem' }}>
                      참조 사용
                    </Box>
                  )}
                </Stack>
                {typeof b?.prompt === 'string' && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="caption" gutterBottom sx={{ color: '#000000' }}>
                      프롬프트
                    </Typography>

                    {/* Edit mode */}
                    {editingIndex === i ? (
                      <Box sx={{ p: 1, bgcolor: 'grey.800', borderRadius: 1, border: '1px solid', borderColor: 'grey.700' }}>
                        <TextField
                          fullWidth
                          multiline
                          rows={6}
                          value={customPrompts[i] || ''}
                          onChange={(e) => handlePromptChange(i, e.target.value)}
                          placeholder="프롬프트를 입력하세요..."
                          variant="outlined"
                          size="small"
                          error={!!promptErrors[i]}
                          helperText={promptErrors[i] || `${customPrompts[i]?.length || 0}자`}
                          sx={{
                            '& .MuiOutlinedInput-root': {
                              bgcolor: 'grey.900',
                              color: '#ffffff',
                              fontSize: '0.75rem',
                            },
                            '& .MuiInputBase-input': {
                              color: '#ffffff',
                            },
                            '& textarea': {
                              color: '#ffffff',
                            },
                          }}
                        />
                        {promptErrors[i] && (
                          <Typography variant="caption" color="error" sx={{ mt: 0.5, display: 'block' }}>
                            {promptErrors[i]}
                          </Typography>
                        )}
                      </Box>
                    ) : (
                      <Box sx={{
                        p: 1,
                        bgcolor: expandedIndex === i ? 'grey.700' : 'grey.800',
                        borderRadius: 1,
                        border: '1px solid',
                        borderColor: expandedIndex === i ? 'primary.main' : 'grey.700',
                        transition: 'all 0.2s ease-in-out'
                      }}>
                        <Typography
                          variant="body2"
                          sx={{
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            display: '-webkit-box',
                            WebkitLineClamp: expandedIndex === i ? 'none' : 2,
                            WebkitBoxOrient: 'vertical',
                            color: '#ffffff',
                            minHeight: expandedIndex === i ? 'auto' : '3em',
                            whiteSpace: expandedIndex === i ? 'pre-wrap' : 'normal',
                            wordBreak: 'break-word',
                            lineHeight: 1.4,
                            fontSize: expandedIndex === i ? '0.875rem' : '0.75rem',
                          }}
                        >
                          {customPrompts[i] || b.prompt}
                        </Typography>
                      </Box>
                    )}

                    {/* Action buttons */}
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mt: 1 }}>
                      {editingIndex === i ? (
                        <>
                          <IconButton size="small" onClick={() => setExpandedIndex(expandedIndex === i ? null : i)} disabled={loading}>
                            {expandedIndex === i ? '감추기' : '자세히'}
                          </IconButton>
                          <IconButton size="small" onClick={() => handleSavePrompt(i)} color="primary" disabled={loading}>
                            <SaveIcon />
                          </IconButton>
                          <IconButton size="small" onClick={() => handleCancelEdit(i)} disabled={loading}>
                            <CancelIcon />
                          </IconButton>
                        </>
                      ) : (
                        <>
                          <IconButton size="small" onClick={() => setExpandedIndex(expandedIndex === i ? null : i)}>
                            {expandedIndex === i ? '감추기' : '자세히'}
                          </IconButton>
                          <IconButton size="small" onClick={() => handleStartEdit(i, b.prompt)} disabled={loading}>
                            <EditIcon />
                          </IconButton>
                          {customPrompts[i] && (
                            <IconButton size="small" onClick={() => handleRegenerateBase(i)} disabled={loading} color="secondary">
                              <RefreshIcon />
                            </IconButton>
                          )}
                        </>
                      )}
                    </Box>
                  </Box>
                )}
              </CardContent>
            </Card>
          ))}
        </Box>
      ) : (
        <Typography variant="body2" color="text.secondary">아직 생성된 베이스 이미지가 없습니다.</Typography>
      )}
      <Stack direction="row" justifyContent="flex-end" sx={{ mt: 2 }}>
        <Button variant="contained" disabled={selectedIndex === null || loading} onClick={handleSelect}>선택 완료</Button>
      </Stack>

      {appearancePrompts.length > 0 && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2" sx={{ mb: 1, color: '#000000' }}>분석된 외형 프롬프트</Typography>
          <Stack spacing={2}>
            {appearancePrompts.map((p, idx) => (
              <Box key={idx} sx={{ p: 1.5, border: '1px solid', borderColor: 'grey.700', borderRadius: 1, bgcolor: 'grey.800' }}>
                <TextField
                  multiline
                  minRows={3}
                  maxRows={10}
                  fullWidth
                  value={p}
                  onChange={(e) => {
                    const cp = [...appearancePrompts];
                    cp[idx] = e.target.value;
                    setAppearancePrompts(cp);
                  }}
                  sx={{
                    '& .MuiInputBase-root': {
                      bgcolor: 'transparent',
                      color: '#ffffff',
                    },
                    '& .MuiOutlinedInput-notchedOutline': {
                      borderColor: 'grey.700',
                    },
                    '&:hover .MuiOutlinedInput-notchedOutline': {
                      borderColor: 'grey.600',
                    },
                    '& .MuiInputBase-input': {
                      color: '#ffffff',
                    },
                    '& textarea': {
                      color: '#ffffff',
                    },
                  }}
                />
                <Stack direction="row" justifyContent="flex-end" spacing={1} sx={{ mt: 1 }}>
                  <Button size="small" variant="contained" onClick={() => handleGenerateFromPrompt(appearancePrompts[idx])} disabled={loading}>
                    이 프롬프트로 베이스 생성
                  </Button>
                </Stack>
              </Box>
            ))}
          </Stack>
        </Box>
      )}
    </Box>
  );
}
