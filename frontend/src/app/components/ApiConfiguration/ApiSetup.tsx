'use client';

import { useRef, useState, useEffect } from 'react';
import { Typography, ToggleButtonGroup, ToggleButton, TextField, Box, Link, Stack, Button, FormHelperText } from '@mui/material';
import { OpenInNew as OpenInNewIcon, UploadFile as UploadFileIcon } from '@mui/icons-material';
import ModelSelector from '../translation/ModelSelector';
import type { ApiProvider } from '../../hooks/useApiKey';

interface ApiSetupProps {
  apiProvider: ApiProvider;
  apiKey: string;
  providerConfig: string;
  onProviderConfigChange: (value: string) => void;
  selectedModel: string;
  onProviderChange: (provider: ApiProvider) => void;
  onApiKeyChange: (key: string) => void;
  onModelChange: (model: string) => void;
}

export default function ApiSetup({
  apiProvider,
  apiKey,
  providerConfig,
  selectedModel,
  onProviderChange,
  onApiKeyChange,
  onProviderConfigChange,
  onModelChange,
}: ApiSetupProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [vertexError, setVertexError] = useState('');

  const validateVertexConfig = (value: string) => {
    if (!value.trim()) {
      setVertexError('');
      return;
    }
    try {
      JSON.parse(value);
      setVertexError('');
    } catch (error) {
      setVertexError('유효한 JSON 형식이 아닙니다.');
    }
  };

  const handleVertexConfigChange = (value: string) => {
    onProviderConfigChange(value);
    validateVertexConfig(value);
  };

  const handleVertexFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      const text = typeof reader.result === 'string' ? reader.result : '';
      handleVertexConfigChange(text);
    };
    reader.onerror = () => {
      setVertexError('JSON 파일을 읽는 중 오류가 발생했습니다.');
    };
    reader.readAsText(file, 'utf-8');
  };

  useEffect(() => {
    if (apiProvider === 'vertex') {
      validateVertexConfig(providerConfig);
    } else {
      setVertexError('');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiProvider]);

  return (
    <>
      {/* Step 1: API Provider Selection */}
      <Typography variant="h5" component="h3" gutterBottom>
        1. API 제공자 선택
      </Typography>
      <ToggleButtonGroup
        value={apiProvider}
        exclusive
        onChange={(_, newProvider) => { 
          if (newProvider) onProviderChange(newProvider);
        }}
        aria-label="API Provider"
        fullWidth
        sx={{ mb: 4 }}
      >
        <ToggleButton value="gemini" aria-label="Gemini">
          Google Gemini
        </ToggleButton>
        <ToggleButton value="vertex" aria-label="Vertex AI">
          Google Vertex AI
        </ToggleButton>
        <ToggleButton value="openrouter" aria-label="OpenRouter">
          OpenRouter
        </ToggleButton>
      </ToggleButtonGroup>

      {/* Step 2: Model Selection */}
      <ModelSelector
        apiProvider={apiProvider}
        selectedModel={selectedModel}
        onModelChange={onModelChange}
      />

      {apiProvider === 'vertex' ? (
        <Box sx={{ mb: 4 }}>
          <Typography variant="h5" component="h3" gutterBottom>
            3. Vertex 서비스 계정 JSON 입력
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Google Cloud에서 다운로드한 서비스 계정 키를 붙여넣거나 업로드하세요. 지역과 기본 모델이 포함된 래핑 JSON도 지원합니다.
          </Typography>
          <Stack spacing={1.5}>
            <TextField
              label="Vertex JSON"
              value={providerConfig}
              onChange={(e) => handleVertexConfigChange(e.target.value)}
              onBlur={(e) => validateVertexConfig(e.target.value)}
              placeholder={'{\n  "project_id": "example-project",\n  ...\n}'}
              fullWidth
              multiline
              minRows={8}
              InputProps={{
                sx: { fontFamily: 'monospace' }
              }}
            />
            <Stack direction="row" spacing={1} alignItems="center">
              <input
                ref={fileInputRef}
                type="file"
                hidden
                accept="application/json,.json"
                onChange={handleVertexFileUpload}
              />
              <Button
                variant="outlined"
                startIcon={<UploadFileIcon />}
                onClick={() => fileInputRef.current?.click()}
              >
                JSON 파일 업로드
              </Button>
              <Link
                href="https://cloud.google.com/vertex-ai/docs/generative-ai/start/introduction"
                target="_blank"
                rel="noopener noreferrer"
                variant="body2"
                sx={{ display: 'inline-flex', alignItems: 'center' }}
              >
                Vertex 설정 가이드
                <OpenInNewIcon sx={{ ml: 0.5, fontSize: 'inherit' }} />
              </Link>
            </Stack>
            {vertexError && <FormHelperText error>{vertexError}</FormHelperText>}
          </Stack>
        </Box>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 4 }}>
          <Typography variant="h5" component="h3" gutterBottom>
            3. {apiProvider === 'gemini' ? 'Gemini' : 'OpenRouter'} API 키 입력
          </Typography>
          <TextField
            type="password"
            label={`${apiProvider === 'gemini' ? 'Gemini' : 'OpenRouter'} API Key`}
            value={apiKey}
            onChange={(e) => onApiKeyChange(e.target.value)}
            fullWidth
            placeholder={apiProvider === 'openrouter' ? 'sk-or-... 형식의 키를 입력하세요' : ''}
          />
          <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
            <Link 
              href={apiProvider === 'gemini' 
                ? "https://aistudio.google.com/app/apikey" 
                : "https://openrouter.ai/keys"}
              target="_blank" 
              rel="noopener noreferrer"
              variant="body2"
              sx={{ display: 'inline-flex', alignItems: 'center' }}
            >
              API 키 발급받기
              <OpenInNewIcon sx={{ ml: 0.5, fontSize: 'inherit' }} />
            </Link>
          </Box>
        </Box>
      )}
    </>
  );
}
