'use client';

import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Container,
  Stack,
  Typography,
} from '@mui/material';
import NoSsr from '@mui/material/NoSsr';
import SaveIcon from '@mui/icons-material/Save';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

import { getCachedClerkToken } from '../utils/authToken';
import { fetchWithRetry } from '../utils/fetchWithRetry';
import ApiSetup from '../components/ApiConfiguration/ApiSetup';
import type { ApiProvider } from '../hooks/useApiKey';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ApiConfiguration {
  api_provider: ApiProvider | null;
  api_key: string | null;
  provider_config: string | null;
  gemini_model: string | null;
  vertex_model: string | null;
  openrouter_model: string | null;
}

export default function SettingsPage() {
  const router = useRouter();
  const { getToken, isLoaded, isSignedIn } = useAuth();

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // API configuration state
  const [apiProvider, setApiProvider] = useState<ApiProvider>('gemini');
  const [apiKey, setApiKey] = useState('');
  const [providerConfig, setProviderConfig] = useState('');
  const [geminiModel, setGeminiModel] = useState('gemini-2.0-flash-exp');
  const [vertexModel, setVertexModel] = useState('gemini-2.0-flash-exp');
  const [openrouterModel, setOpenrouterModel] = useState('google/gemini-2.0-flash-exp:free');

  const fetchConfig = useCallback(async () => {
    if (!isSignedIn) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const token = await getCachedClerkToken(getToken);
      if (!token) {
        throw new Error('인증 토큰을 가져오지 못했습니다. 다시 로그인해 주세요.');
      }

      const response = await fetchWithRetry(
        `${API_BASE_URL}/api/v1/users/me/api-config`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
        { retries: 2, timeoutMs: 8000 }
      );

      if (!response.ok) {
        throw new Error('API 설정을 불러오지 못했습니다.');
      }

      const config: ApiConfiguration = await response.json();

      // Update state with fetched config
      const provider = config.api_provider || 'gemini';
      setApiProvider(provider);
      setApiKey(config.api_key ?? '');
      setProviderConfig(config.provider_config ?? '');
      if (config.gemini_model) {
        setGeminiModel(config.gemini_model);
      }
      if (config.vertex_model) {
        setVertexModel(config.vertex_model);
      }
      if (config.openrouter_model) {
        setOpenrouterModel(config.openrouter_model);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'API 설정을 불러오는 중 오류가 발생했습니다.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [getToken, isSignedIn]);

  const saveConfig = useCallback(async () => {
    if (!isSignedIn) {
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      const token = await getCachedClerkToken(getToken);
      if (!token) {
        throw new Error('인증 토큰을 가져오지 못했습니다. 다시 로그인해 주세요.');
      }

      const payload: ApiConfiguration = {
        api_provider: apiProvider,
        api_key: apiKey || null,
        provider_config: providerConfig || null,
        gemini_model: geminiModel,
        vertex_model: vertexModel,
        openrouter_model: openrouterModel,
      };

      const response = await fetchWithRetry(
        `${API_BASE_URL}/api/v1/users/me/api-config`,
        {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        },
        { retries: 2, timeoutMs: 8000 }
      );

      if (!response.ok) {
        throw new Error('API 설정을 저장하지 못했습니다.');
      }

      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'API 설정을 저장하는 중 오류가 발생했습니다.';
      setError(message);
    } finally {
      setSaving(false);
    }
  }, [getToken, isSignedIn, apiProvider, apiKey, providerConfig, geminiModel, vertexModel, openrouterModel]);

  useEffect(() => {
    if (!isLoaded) {
      return;
    }

    if (!isSignedIn) {
      router.replace('/about');
      return;
    }

    void fetchConfig();
  }, [isLoaded, isSignedIn, router, fetchConfig]);

  const handleModelChange = (model: string) => {
    if (apiProvider === 'gemini') {
      setGeminiModel(model);
    } else if (apiProvider === 'vertex') {
      setVertexModel(model);
    } else if (apiProvider === 'openrouter') {
      setOpenrouterModel(model);
    }
  };

  const selectedModel =
    apiProvider === 'gemini' ? geminiModel : apiProvider === 'vertex' ? vertexModel : openrouterModel;

  return (
    <NoSsr>
      <Container maxWidth="md" sx={{ py: { xs: 4, md: 6 } }}>
        <Stack spacing={4}>
          <Stack
            direction={{ xs: 'column', md: 'row' }}
            justifyContent="space-between"
            spacing={2}
            alignItems={{ xs: 'stretch', md: 'center' }}
          >
            <Box>
              <Typography variant="h4" fontWeight={700} gutterBottom>
                API 설정
              </Typography>
              <Typography variant="body2" color="text.secondary">
                LLM API 제공자와 인증 정보를 관리하세요. 설정은 자동으로 저장되며 모든 번역 작업에 적용됩니다.
              </Typography>
            </Box>
            <Stack direction="row" spacing={1} justifyContent="flex-end">
              <Button
                variant="outlined"
                color="inherit"
                startIcon={<ArrowBackIcon />}
                onClick={() => router.push('/')}
              >
                작업 공간으로 이동
              </Button>
            </Stack>
          </Stack>

          {success && <Alert severity="success">API 설정이 성공적으로 저장되었습니다!</Alert>}
          {error && <Alert severity="error">{error}</Alert>}

          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 240 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Card sx={{ borderRadius: 2 }}>
              <CardContent>
                <Stack spacing={3}>
                  <Typography variant="h6" fontWeight={600}>
                    LLM API 설정
                  </Typography>

                  <ApiSetup
                    apiProvider={apiProvider}
                    apiKey={apiKey}
                    providerConfig={providerConfig}
                    selectedModel={selectedModel}
                    onProviderChange={setApiProvider}
                    onApiKeyChange={setApiKey}
                    onProviderConfigChange={setProviderConfig}
                    onModelChange={handleModelChange}
                  />

                  <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
                    <Button
                      variant="contained"
                      size="large"
                      startIcon={<SaveIcon />}
                      onClick={saveConfig}
                      disabled={saving}
                    >
                      {saving ? '저장 중...' : '설정 저장'}
                    </Button>
                  </Box>
                </Stack>
              </CardContent>
            </Card>
          )}

          <Alert severity="info" sx={{ borderRadius: 2 }}>
            <Typography variant="body2" fontWeight={600} gutterBottom>
              보안 안내
            </Typography>
            <Typography variant="body2">
              API 키는 암호화되어 안전하게 저장됩니다. 저장된 API 키는 번역 작업 생성 시 자동으로 사용되므로 매번 입력할 필요가 없습니다.
            </Typography>
          </Alert>
        </Stack>
      </Container>
    </NoSsr>
  );
}
