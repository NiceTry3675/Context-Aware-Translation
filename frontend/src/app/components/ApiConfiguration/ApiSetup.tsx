import { Typography, ToggleButtonGroup, ToggleButton, TextField, Box, Link } from '@mui/material';
import { OpenInNew as OpenInNewIcon } from '@mui/icons-material';
import ModelSelector from '../translation/ModelSelector';

interface ApiSetupProps {
  apiProvider: 'gemini' | 'openrouter';
  apiKey: string;
  selectedModel: string;
  onProviderChange: (provider: 'gemini' | 'openrouter') => void;
  onApiKeyChange: (key: string) => void;
  onModelChange: (model: string) => void;
}

export default function ApiSetup({
  apiProvider,
  apiKey,
  selectedModel,
  onProviderChange,
  onApiKeyChange,
  onModelChange
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
        3. {apiProvider === 'gemini' ? 'Gemini' : 'OpenRouter'} API 키 입력
      </Typography>
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
    </>
  );
}