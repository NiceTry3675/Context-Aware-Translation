'use client';

import React from 'react';
import {
  Box,
  Typography,
  TextField,
  InputAdornment,
} from '@mui/material';
import {
  Person as PersonIcon,
  TextFields as TextFieldsIcon,
  Palette as PaletteIcon,
  Gavel as GavelIcon,
} from '@mui/icons-material';
import { StyleData } from '../../types/ui';

interface StyleFieldEditorProps {
  styleData: StyleData;
  onStyleChange: (field: keyof StyleData, value: string) => void;
}

export default function StyleFieldEditor({ styleData, onStyleChange }: StyleFieldEditorProps) {
  return (
    <Box>
      <Typography variant="h5" component="h3" gutterBottom>
        5. 핵심 서사 스타일 확인 및 수정
      </Typography>
      <Typography color="text.secondary" mb={3}>
        AI가 분석한 소설의 핵심 스타일입니다. 필요하다면 직접 수정할 수 있습니다.
      </Typography>
      
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mb: 4 }}>
        <TextField 
          label="1. 주인공 이름" 
          value={styleData.protagonist_name} 
          onChange={(e) => onStyleChange('protagonist_name', e.target.value)} 
          fullWidth
          variant="outlined"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <PersonIcon />
              </InputAdornment>
            ),
          }}
        />
        
        <TextField 
          label="2. 서술 문체 및 어미" 
          value={styleData.narration_style_endings} 
          onChange={(e) => onStyleChange('narration_style_endings', e.target.value)} 
          fullWidth
          multiline
          rows={4}
          variant="outlined"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <TextFieldsIcon />
              </InputAdornment>
            ),
          }}
        />
        
        <TextField 
          label="3. 핵심 톤과 키워드 (전체 분위기)" 
          value={styleData.tone_keywords} 
          onChange={(e) => onStyleChange('tone_keywords', e.target.value)} 
          fullWidth
          multiline
          rows={3}
          variant="outlined"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <PaletteIcon />
              </InputAdornment>
            ),
          }}
        />
        
        <TextField 
          label="4. 가장 중요한 스타일 규칙 (Golden Rule)" 
          value={styleData.stylistic_rule} 
          onChange={(e) => onStyleChange('stylistic_rule', e.target.value)} 
          fullWidth
          multiline
          rows={3}
          variant="outlined"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <GavelIcon />
              </InputAdornment>
            ),
          }}
        />
      </Box>
    </Box>
  );
}