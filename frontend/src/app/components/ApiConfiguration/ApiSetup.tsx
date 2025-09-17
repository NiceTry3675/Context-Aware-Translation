import { Typography, ToggleButtonGroup, ToggleButton, TextField, Box, Link } from '@mui/material';
import { OpenInNew as OpenInNewIcon } from '@mui/icons-material';
import ModelSelector from '../translation/ModelSelector';
import type { ApiProvider } from '../../hooks/useApiKey';

interface ApiSetupProps {
  apiProvider: ApiProvider;
  apiKey: string;
  selectedModel: string;
  vertexProjectId: string;
  vertexLocation: string;
  onProviderChange: (provider: ApiProvider) => void;
  onApiKeyChange: (key: string) => void;
  onModelChange: (model: string) => void;
  onVertexProjectIdChange: (projectId: string) => void;
  onVertexLocationChange: (location: string) => void;
}

export default function ApiSetup({
  apiProvider,
  apiKey,
  selectedModel,
  vertexProjectId,
  vertexLocation,
  onProviderChange,
  onApiKeyChange,
  onModelChange,
  onVertexProjectIdChange,
  onVertexLocationChange
}: ApiSetupProps) {
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
        <ToggleButton value="vertex" aria-label="Vertex Gemini">
          Vertex Gemini
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

      {/* Step 3: API Key */}
      <Typography variant="h5" component="h3" gutterBottom>
        {apiProvider === 'vertex'
          ? '3. Vertex Gemini 설정'
          : `3. ${apiProvider === 'gemini' ? 'Gemini' : 'OpenRouter'} API 키 입력`}
      </Typography>

      {apiProvider === 'vertex' ? (
        <Box sx={{ display: 'grid', gap: 2, mb: 4 }}>
          <TextField
            label="Vertex 프로젝트 ID"
            value={vertexProjectId}
            onChange={(e) => onVertexProjectIdChange(e.target.value)}
            fullWidth
            placeholder="예: my-gcp-project"
          />
          <TextField
            label="Vertex 위치"
            value={vertexLocation}
            onChange={(e) => onVertexLocationChange(e.target.value)}
            fullWidth
            placeholder="예: us-central1"
          />
          <TextField
            label="서비스 계정 JSON (키 파일 내용 전체)"
            value={apiKey}
            onChange={(e) => onApiKeyChange(e.target.value)}
            fullWidth
            multiline
            minRows={4}
            placeholder={'{ "type": "service_account", ... }'}
            helperText="Vertex Gemini를 사용하려면 서비스 계정 키 JSON 전체를 붙여넣어 주세요."
          />
          <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
            <Link
              href="https://cloud.google.com/vertex-ai/docs/start/service-account?hl=ko"
              target="_blank"
              rel="noopener noreferrer"
              variant="body2"
              sx={{ display: 'inline-flex', alignItems: 'center' }}
            >
              서비스 계정 키 발급 방법 안내
              <OpenInNewIcon sx={{ ml: 0.5, fontSize: 'inherit' }} />
            </Link>
          </Box>
        </Box>
      ) : (
        <>
          <TextField
            type="password"
            label={`${apiProvider === 'gemini' ? 'Gemini' : 'OpenRouter'} API Key`}
            value={apiKey}
            onChange={(e) => onApiKeyChange(e.target.value)}
            fullWidth
            sx={{ mb: 1 }}
            placeholder={apiProvider === 'openrouter' ? 'sk-or-... 형식의 키를 입력하세요' : ''}
          />
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 4 }}>
            <Link 
              href={apiProvider === 'gemini' 
                ? 'https://aistudio.google.com/app/apikey'
                : 'https://openrouter.ai/keys'}
              target="_blank" 
              rel="noopener noreferrer"
              variant="body2"
              sx={{ display: 'inline-flex', alignItems: 'center' }}
            >
              API 키 발급받기
              <OpenInNewIcon sx={{ ml: 0.5, fontSize: 'inherit' }} />
            </Link>
          </Box>
        </>
      )}
    </>
  );
}
