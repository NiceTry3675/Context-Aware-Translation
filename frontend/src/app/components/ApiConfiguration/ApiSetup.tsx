import React from 'react';
import { Typography, ToggleButtonGroup, ToggleButton, TextField, Box, Link, Collapse, IconButton, Divider, FormControlLabel, Switch, FormControl, InputLabel, Select, MenuItem, SelectChangeEvent, Grid } from '@mui/material';
import { OpenInNew as OpenInNewIcon } from '@mui/icons-material';
import ModelSelector from '../translation/ModelSelector';
import { geminiModelOptions, openRouterModelOptions } from '../../utils/constants/models';

interface ApiSetupProps {
  apiProvider: 'gemini' | 'openrouter';
  apiKey: string;
  selectedModel: string;
  taskModels: { translate: string; style: string; glossary: string; validation?: string; postedit?: string };
  useAdvancedTaskModels: boolean;
  onProviderChange: (provider: 'gemini' | 'openrouter') => void;
  onApiKeyChange: (key: string) => void;
  onModelChange: (model: string) => void;
  onTaskModelChange: (task: 'translate' | 'style' | 'glossary' | 'validation' | 'postedit', model: string) => void;
  onAdvancedToggle: (enabled: boolean) => void;
}

export default function ApiSetup({
  apiProvider,
  apiKey,
  selectedModel,
  taskModels,
  useAdvancedTaskModels,
  onProviderChange,
  onApiKeyChange,
  onModelChange,
  onTaskModelChange,
  onAdvancedToggle
}: ApiSetupProps) {
  const options = apiProvider === 'gemini' ? geminiModelOptions : openRouterModelOptions;
  const handleCompactChange = (task: 'style' | 'glossary' | 'validation' | 'postedit') => (e: SelectChangeEvent<string>) => {
    const value = e.target.value as string;
    onTaskModelChange(task, value);
  };
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

      {/* Advanced: per-task model selection */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 1, mb: 1 }}>
        <Typography variant="subtitle1">고급 설정: 작업별 모델</Typography>
        <FormControlLabel 
          control={<Switch checked={useAdvancedTaskModels} onChange={(e) => onAdvancedToggle(e.target.checked)} />} 
          label={useAdvancedTaskModels ? '활성화' : '비활성화'} 
        />
      </Box>
      <Collapse in={useAdvancedTaskModels} timeout="auto" unmountOnExit>
        <Box sx={{ p: 2, borderRadius: 1, border: '1px dashed', borderColor: 'divider', mb: 2 }}>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel id="style-model-label">스타일 분석</InputLabel>
                <Select
                  labelId="style-model-label"
                  value={taskModels.style}
                  label="스타일 분석"
                  onChange={handleCompactChange('style')}
                >
                  {options.map((opt) => (
                    <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel id="glossary-model-label">용어집 추출</InputLabel>
                <Select
                  labelId="glossary-model-label"
                  value={taskModels.glossary}
                  label="용어집 추출"
                  onChange={handleCompactChange('glossary')}
                >
                  {options.map((opt) => (
                    <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel id="validation-model-label">검증</InputLabel>
                <Select
                  labelId="validation-model-label"
                  value={taskModels.validation || selectedModel}
                  label="검증"
                  onChange={handleCompactChange('validation')}
                >
                  {options.map((opt) => (
                    <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel id="postedit-model-label">후편집</InputLabel>
                <Select
                  labelId="postedit-model-label"
                  value={taskModels.postedit || selectedModel}
                  label="후편집"
                  onChange={handleCompactChange('postedit')}
                >
                  {options.map((opt) => (
                    <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </Box>
      </Collapse>

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
