import {
  Box, Typography, Chip, Slider, FormControlLabel, Switch, Select, MenuItem, FormControl, InputLabel
} from '@mui/material';
import { TranslationSettings as Settings } from '../../types/ui';

interface TranslationSettingsProps {
  settings: Settings;
  onChange: (settings: Settings) => void;
  isTurboLocked?: boolean;
}

export default function TranslationSettings({ settings, onChange, isTurboLocked = false }: TranslationSettingsProps) {
  const updateSetting = <K extends keyof Settings>(key: K, value: Settings[K]) => {
    onChange({ ...settings, [key]: value });
  };

  const turboModeLabel = isTurboLocked ? '터보 모드 활성화 (필수)' : '터보 모드 활성화';

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

      <Box sx={{ mt: 3 }}>
        <Typography variant="h6" gutterBottom>터보 번역 모드</Typography>
        <Typography variant="body2" color="text.secondary" mb={1}>
          동적 스타일 편차, 캐릭터 말투, 용어집 자동 추출을 건너뛰고 빠르게 번역합니다.
        </Typography>
        {isTurboLocked && (
          <Typography variant="caption" color="warning.main" display="block" mb={1}>
            OpenRouter에서 Gemini가 아닌 모델을 사용할 때는 터보 모드가 필수입니다.
          </Typography>
        )}
        <FormControlLabel
          control={
            <Switch
              checked={isTurboLocked ? true : (settings.turboMode ?? false)}
              onChange={(e) => updateSetting('turboMode', e.target.checked)}
              color="warning"
              disabled={isTurboLocked}
            />
          }
          label={turboModeLabel}
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
      
      {/* Illustration Settings - Hidden */}
      {/* <Box sx={{ mt: 3 }}>
        <Typography variant="h6" gutterBottom>삽화 생성 설정</Typography>
        <FormControlLabel
          control={
            <Switch
              checked={settings.enableIllustrations || false}
              onChange={(e) => updateSetting('enableIllustrations', e.target.checked)}
              color="primary"
            />
          }
          label="세그먼트별 삽화 자동 생성"
        />
        
        {settings.enableIllustrations && (
          <Box sx={{ ml: 3, mt: 2 }}>
            <FormControl variant="outlined" size="small" sx={{ mb: 2, minWidth: 200 }}>
              <InputLabel>삽화 스타일</InputLabel>
              <Select
                value={settings.illustrationStyle || 'digital_art'}
                onChange={(e) => updateSetting('illustrationStyle', e.target.value as any)}
                label="삽화 스타일"
              >
                <MenuItem value="realistic">사실적</MenuItem>
                <MenuItem value="artistic">예술적</MenuItem>
                <MenuItem value="watercolor">수채화</MenuItem>
                <MenuItem value="digital_art">디지털 아트</MenuItem>
                <MenuItem value="sketch">스케치</MenuItem>
                <MenuItem value="anime">애니메이션</MenuItem>
                <MenuItem value="vintage">빈티지</MenuItem>
                <MenuItem value="minimalist">미니멀리스트</MenuItem>
              </Select>
            </FormControl>
            
            <Box sx={{ mt: 2 }}>
              <Typography gutterBottom>
                최대 삽화 개수: <strong>{settings.maxIllustrations || '제한 없음'}</strong>
              </Typography>
              <Slider
                value={settings.maxIllustrations || 0}
                onChange={(_, newValue) => updateSetting('maxIllustrations', newValue === 0 ? undefined : newValue as number)}
                valueLabelDisplay="auto"
                step={5}
                marks={[
                  { value: 0, label: '제한 없음' },
                  { value: 10, label: '10개' },
                  { value: 25, label: '25개' },
                  { value: 50, label: '50개' },
                ]}
                min={0}
                max={50}
                color="secondary"
              />
            </Box>
            
            <Box sx={{ mt: 2 }}>
              <Typography gutterBottom>
                삽화 생성 빈도: <strong>{settings.illustrationsPerSegment || 1}개 세그먼트마다</strong>
              </Typography>
              <Slider
                value={settings.illustrationsPerSegment || 1}
                onChange={(_, newValue) => updateSetting('illustrationsPerSegment', newValue as number)}
                valueLabelDisplay="auto"
                step={1}
                marks={[
                  { value: 1, label: '모든 세그먼트' },
                  { value: 3, label: '3개마다' },
                  { value: 5, label: '5개마다' },
                  { value: 10, label: '10개마다' },
                ]}
                min={1}
                max={10}
                color="secondary"
              />
            </Box>
          </Box>
        )}
      </Box> */}
    </>
  );
}
