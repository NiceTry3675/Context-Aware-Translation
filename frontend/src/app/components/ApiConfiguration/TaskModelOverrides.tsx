import React from 'react';
import { Box, Typography, Divider, FormControlLabel, Switch } from '@mui/material';
import ModelSelector from '../translation/ModelSelector';
import type { ApiProvider } from '../../hooks/useApiKey';

export interface TaskModelOverrides {
  styleModel?: string | null;
  glossaryModel?: string | null;
}

interface TaskModelOverridesProps {
  apiProvider: ApiProvider;
  values: TaskModelOverrides;
  onChange: (values: TaskModelOverrides) => void;
  enabled: boolean;
  onEnabledChange: (enabled: boolean) => void;
}

export default function TaskModelOverrides({ apiProvider, values, onChange, enabled, onEnabledChange }: TaskModelOverridesProps) {
  const handleChange = (key: keyof TaskModelOverrides) => (model: string) => {
    onChange({ ...values, [key]: model });
  };

  return (
    <Box sx={{ mt: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
        <Typography variant="h6" component="h4">
          작업별 모델 선택 (선택)
        </Typography>
        <FormControlLabel
          control={<Switch checked={enabled} onChange={(e) => onEnabledChange(e.target.checked)} />}
          label={enabled ? '켜짐' : '꺼짐'}
        />
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        비활성화 상태에서는 번역 모델 선택에서 선택한 모델을 모든 작업에 사용합니다. (메인 번역은 항상 번역 모델을 사용)
      </Typography>

      <Divider sx={{ mb: 2 }} />

      {enabled && (
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr', gap: 2 }}>
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>스타일 분석 모델</Typography>
            <ModelSelector
              apiProvider={apiProvider}
              selectedModel={values.styleModel || ''}
              onModelChange={handleChange('styleModel')}
              hideTitle
            />
          </Box>
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>용어집 모델</Typography>
            <ModelSelector
              apiProvider={apiProvider}
              selectedModel={values.glossaryModel || ''}
              onModelChange={handleChange('glossaryModel')}
              hideTitle
            />
          </Box>
        </Box>
      )}
    </Box>
  );
}
