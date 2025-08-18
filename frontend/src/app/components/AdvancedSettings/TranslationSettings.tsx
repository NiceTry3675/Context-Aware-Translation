import {
  Box, Typography, Chip, Slider, FormControlLabel, Switch
} from '@mui/material';
import { TranslationSettings as Settings } from '../../types/ui';

interface TranslationSettingsProps {
  settings: Settings;
  onChange: (settings: Settings) => void;
}

export default function TranslationSettings({ settings, onChange }: TranslationSettingsProps) {
  const updateSetting = <K extends keyof Settings>(key: K, value: Settings[K]) => {
    onChange({ ...settings, [key]: value });
  };

  return (
    <>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <Typography variant="h5" component="h3">4.5 고급 설정 (선택)</Typography>
        <Chip label="Beta" color="info" size="small" />
      </Box>
      
      <Typography color="text.secondary" mb={2}>
        한 번에 번역할 최대 글자 수를 조절합니다. 일본어/중국어의 경우 5000자 내외를 권장합니다.
      </Typography>
      
      <Box>
        <Typography gutterBottom>
          세그먼트 크기: <strong>{settings.segmentSize.toLocaleString()}자</strong>
        </Typography>
        <Slider
          value={settings.segmentSize}
          onChange={(_, newValue) => updateSetting('segmentSize', newValue as number)}
          aria-labelledby="segment-size-slider"
          valueLabelDisplay="auto"
          step={1000}
          marks={[
            { value: 2000, label: '최소' },
            { value: 5000, label: '일/중' },
            { value: 15000, label: '기본' },
            { value: 25000, label: '최대' },
          ]}
          min={2000}
          max={25000}
          color="secondary"
        />
      </Box>
      
      {/* Validation Settings */}
      <Box sx={{ mt: 3 }}>
        <Typography variant="h6" gutterBottom>번역 검증 설정</Typography>
        <FormControlLabel
          control={
            <Switch
              checked={settings.enableValidation}
              onChange={(e) => updateSetting('enableValidation', e.target.checked)}
              color="primary"
            />
          }
          label="번역 완료 후 자동 검증"
        />
        
        {settings.enableValidation && (
          <Box sx={{ ml: 3, mt: 2 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={settings.quickValidation}
                  onChange={(e) => updateSetting('quickValidation', e.target.checked)}
                  color="secondary"
                />
              }
              label="빠른 검증 (중요 문제만 확인)"
            />
            
            <Box sx={{ mt: 2 }}>
              <Typography gutterBottom>
                검증 샘플 비율: <strong>{settings.validationSampleRate}%</strong>
              </Typography>
              <Slider
                value={settings.validationSampleRate}
                onChange={(_, newValue) => updateSetting('validationSampleRate', newValue as number)}
                valueLabelDisplay="auto"
                step={10}
                marks={[
                  { value: 10, label: '10%' },
                  { value: 50, label: '50%' },
                  { value: 100, label: '100%' },
                ]}
                min={10}
                max={100}
                color="primary"
              />
            </Box>
            
            <FormControlLabel
              control={
                <Switch
                  checked={settings.enablePostEdit}
                  onChange={(e) => updateSetting('enablePostEdit', e.target.checked)}
                  color="success"
                  disabled={!settings.enableValidation}
                />
              }
              label="검증된 문제 자동 수정 (Post-Edit)"
            />
          </Box>
        )}
      </Box>
    </>
  );
}