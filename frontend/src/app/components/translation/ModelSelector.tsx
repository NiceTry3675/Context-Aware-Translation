import { Box, Typography, ToggleButtonGroup, ToggleButton, Chip, Alert } from '@mui/material';
import { geminiModelOptions, openRouterModelOptions, vertexModelOptions, type ModelOption } from '../../utils/constants/models';
import type { ApiProvider } from '../../hooks/useApiKey';

interface ModelSelectorProps {
  apiProvider: ApiProvider;
  selectedModel: string;
  onModelChange: (model: string) => void;
  hideTitle?: boolean;
}

export default function ModelSelector({ apiProvider, selectedModel, onModelChange, hideTitle = false }: ModelSelectorProps) {
  const models: ModelOption[] = apiProvider === 'openrouter'
    ? openRouterModelOptions
    : apiProvider === 'vertex'
      ? vertexModelOptions
      : geminiModelOptions;

  const handleModelChange = (_: React.MouseEvent<HTMLElement>, newValue: string) => {
    if (!newValue) return;

    // if (apiProvider === 'gemini' && newValue === 'gemini-2.5-pro') {
    //   const confirmation = window.confirm(
    //     "⚠️ Pro 모델 경고 ⚠️\n\n" +
    //     "Pro 모델은 최고의 번역 품질을 제공하지만, 다음과 같은 단점이 있을 수 있습니다:\n\n" +
    //     "1. 번역 속도가 매우 느립니다.\n" +
    //     "2. API 비용이 다른 모델보다 훨씬 비쌉니다.\n" +
    //     "3. 현재 서비스는 베타 버전으로, 긴 작업 중 서버가 중단될 수 있습니다.\n\n" +
    //     "계속 진행하시겠습니까?"
    //   );
    //
    //   if (!confirmation) {
    //     return;
    //   }
    // }

    onModelChange(newValue);
  };

  return (
    <>
      {!hideTitle && (
        <Typography variant="h5" component="h3" gutterBottom>2. 번역 모델 선택</Typography>
      )}
      <ToggleButtonGroup
        value={selectedModel}
        exclusive
        onChange={handleModelChange}
        aria-label="Translation Model Selection"
        fullWidth
        sx={{ mb: 4, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 1 }}
      >
        {models.map((opt: ModelOption) => (
          <ToggleButton value={opt.value} key={opt.value} sx={{ flexDirection: 'column', flex: 1, p: 2, alignItems: 'center', height: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <Typography variant="button" sx={{ lineHeight: 1.2 }}>{opt.label}</Typography>
              <Chip label={opt.chip} color={opt.chipColor} size="small" />
            </Box>
            <Typography variant="caption" sx={{ textTransform: 'none', mt: 0.5, textAlign: 'center' }}>
              {opt.description}
            </Typography>
          </ToggleButton>
        ))}
      </ToggleButtonGroup>

      {apiProvider === 'openrouter' && (
        <Alert severity="info" sx={{ mb: 4 }}>
          <strong>참고:</strong> 현재 프롬프트는 Gemini 모델에 최적화되어 설계되었습니다. DEEPSEEK 모델은 무료!지만 많이 느립니다.
        </Alert>
      )}
      {apiProvider === 'vertex' && (
        <Alert severity="info" sx={{ mb: 4 }}>
          <strong>Vertex AI:</strong> Vertex 모델은 프로젝트와 지역을 기준으로 호출됩니다. 아래에서 입력한 JSON 구성에 맞춰 {selectedModel} 모델이 자동으로 연결됩니다.
        </Alert>
      )}
    </>
  );
}
