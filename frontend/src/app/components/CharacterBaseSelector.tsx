'use client';

import React, { useEffect, useState } from 'react';
import { Box, Button, Card, CardMedia, CardContent, Typography, Stack, Radio, CircularProgress, Alert, TextField } from '@mui/material';
import { useAuth } from '@clerk/nextjs';
import { getCachedClerkToken } from '../utils/authToken';
import { getCharacterBases, generateCharacterBases, selectCharacterBase, CharacterProfileBody } from '../utils/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface CharacterBaseSelectorProps {
  jobId: string;
  apiKey?: string; // required to generate bases
  onChange?: () => void; // called after selection or generation
}

export default function CharacterBaseSelector({ jobId, apiKey, onChange }: CharacterBaseSelectorProps) {
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
      // Load images or prompts for preview
      const urls: Record<number, string> = {};
      await Promise.all((list as any[]).map(async (b: any, i: number) => {
        try {
          const res = await fetch(`${API_BASE_URL}/api/v1/illustrations/${jobId}/character/base/${i}`, {
            headers: {
              'Authorization': token ? `Bearer ${token}` : '',
            }
          });
          const contentType = res.headers.get('content-type') || '';
          if (res.ok && contentType.includes('image')) {
            const blob = await res.blob();
            urls[i] = URL.createObjectURL(blob);
          }
        } catch {
          // ignore
        }
      }));
      setImageUrls(urls);
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
    if (!apiKey) {
      setError('API Key가 필요합니다. 설정에서 API 키를 입력하세요.');
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
      await generateCharacterBases(jobId, apiKey, token || undefined, defaultProfile, referenceFile || undefined);
      await load();
      onChange?.();
    } catch (e: any) {
      setError(e?.message || '베이스 이미지 생성에 실패했습니다.');
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
      </Stack>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
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
                    {expandedIndex === i ? (
                      <Box sx={{ p: 1, bgcolor: 'grey.800', borderRadius: 1, fontFamily: 'monospace', fontSize: '0.8rem', whiteSpace: 'pre-wrap', color: '#ffffff', border: '1px solid', borderColor: 'grey.700' }}>
                        {b.prompt}
                      </Box>
                    ) : (
                      <Box sx={{ p: 1, bgcolor: 'grey.800', borderRadius: 1, border: '1px solid', borderColor: 'grey.700' }}>
                        <Typography
                          variant="body2"
                          sx={{
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                            color: '#ffffff'
                          }}
                        >
                          {b.prompt}
                        </Typography>
                      </Box>
                    )}
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 1 }}>
                      <Button size="small" onClick={() => setExpandedIndex(expandedIndex === i ? null : i)}>
                        {expandedIndex === i ? '감추기' : '자세히'}
                      </Button>
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
    </Box>
  );
}
