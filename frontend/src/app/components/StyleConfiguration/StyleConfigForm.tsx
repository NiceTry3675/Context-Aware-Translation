import { useState, useEffect } from 'react';
import {
  Box, Typography, TextField, Button, Alert, CircularProgress,
  InputAdornment, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, IconButton, CardActions
} from '@mui/material';
import {
  Person as PersonIcon,
  TextFields as TextFieldsIcon,
  Palette as PaletteIcon,
  Gavel as GavelIcon,
  Add as AddIcon,
  Delete as DeleteIcon
} from '@mui/icons-material';
import { StyleData, GlossaryTerm } from '../../types/translation';
import theme from '../../../theme';

interface StyleConfigFormProps {
  styleData: StyleData;
  glossaryData: GlossaryTerm[];
  isAnalyzingGlossary: boolean;
  glossaryAnalysisError?: string;
  uploading: boolean;
  onStyleChange: (styleData: StyleData) => void;
  onGlossaryChange: (glossaryData: GlossaryTerm[]) => void;
  onSubmit: () => void;
  onCancel: () => void;
}

export default function StyleConfigForm({
  styleData,
  glossaryData,
  isAnalyzingGlossary,
  glossaryAnalysisError,
  uploading,
  onStyleChange,
  onGlossaryChange,
  onSubmit,
  onCancel
}: StyleConfigFormProps) {
  const [localStyleData, setLocalStyleData] = useState(styleData);
  const [localGlossaryData, setLocalGlossaryData] = useState(glossaryData);

  useEffect(() => {
    setLocalStyleData(styleData);
  }, [styleData]);

  useEffect(() => {
    setLocalGlossaryData(glossaryData);
  }, [glossaryData]);

  const handleStyleFieldChange = (field: keyof StyleData, value: string) => {
    const updated = { ...localStyleData, [field]: value };
    setLocalStyleData(updated);
    onStyleChange(updated);
  };

  const handleGlossaryChange = (index: number, field: keyof GlossaryTerm, value: string) => {
    const updated = [...localGlossaryData];
    updated[index] = { ...updated[index], [field]: value };
    setLocalGlossaryData(updated);
    onGlossaryChange(updated);
  };

  const handleAddGlossaryTerm = () => {
    const updated = [...localGlossaryData, { term: '', translation: '' }];
    setLocalGlossaryData(updated);
    onGlossaryChange(updated);
  };

  const handleRemoveGlossaryTerm = (index: number) => {
    const updated = localGlossaryData.filter((_, i) => i !== index);
    setLocalGlossaryData(updated);
    onGlossaryChange(updated);
  };

  return (
    <>
      <Typography variant="h5" component="h3" gutterBottom>
        5. 핵심 서사 스타일 확인 및 수정
      </Typography>
      <Typography color="text.secondary" mb={3}>
        AI가 분석한 소설의 핵심 스타일입니다. 필요하다면 직접 수정할 수 있습니다.
      </Typography>
      
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mb: 4 }}>
        <TextField 
          label="1. 주인공 이름" 
          value={localStyleData.protagonist_name} 
          onChange={(e) => handleStyleFieldChange('protagonist_name', e.target.value)} 
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
          value={localStyleData.narration_style_endings} 
          onChange={(e) => handleStyleFieldChange('narration_style_endings', e.target.value)} 
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
          value={localStyleData.tone_keywords} 
          onChange={(e) => handleStyleFieldChange('tone_keywords', e.target.value)} 
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
          value={localStyleData.stylistic_rule} 
          onChange={(e) => handleStyleFieldChange('stylistic_rule', e.target.value)} 
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

      {/* Glossary Editor */}
      <Typography variant="h5" component="h3" gutterBottom>
        6. 고유명사 번역 노트
      </Typography>
      <Typography color="text.secondary" mb={2}>
        AI가 추천한 용어집입니다. 번역을 수정하거나, 새로운 용어를 추가/삭제할 수 있습니다.
      </Typography>

      {glossaryAnalysisError && (
        <Alert severity="warning" sx={{ mb: 2 }}>{glossaryAnalysisError}</Alert>
      )}
      
      {isAnalyzingGlossary ? (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2}}>
          <CircularProgress size={24} />
          <Typography>용어집 분석 중...</Typography>
        </Box>
      ) : localGlossaryData.length > 0 ? (
        <TableContainer component={Paper} sx={{ mb: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>원문 (Term)</TableCell>
                <TableCell>번역 (Translation)</TableCell>
                <TableCell align="right">삭제</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {localGlossaryData.map((term, index) => (
                <TableRow key={index}>
                  <TableCell>
                    <TextField
                      value={term.term}
                      onChange={(e) => handleGlossaryChange(index, 'term', e.target.value)}
                      variant="standard"
                      fullWidth
                    />
                  </TableCell>
                  <TableCell>
                    <TextField
                      value={term.translation}
                      onChange={(e) => handleGlossaryChange(index, 'translation', e.target.value)}
                      variant="standard"
                      fullWidth
                    />
                  </TableCell>
                  <TableCell align="right">
                    <IconButton onClick={() => handleRemoveGlossaryTerm(index)} size="small">
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : null}

      <Button onClick={handleAddGlossaryTerm} startIcon={<AddIcon />} sx={{ mb: 3 }}>
        용어 추가
      </Button>

      <CardActions sx={{ justifyContent: 'flex-end', mt: 3, p: 0 }}>
        <Button onClick={onCancel} color="secondary">
          취소
        </Button>
        <Button 
          onClick={onSubmit} 
          variant="contained" 
          disabled={uploading}
          size="large"
          sx={{
            background: `linear-gradient(45deg, ${theme.palette.primary.main} 30%, ${theme.palette.secondary.main} 90%)`,
            color: 'white',
            '&:hover': {
              opacity: 0.9,
              boxShadow: `0 0 15px ${theme.palette.primary.main}`,
            }
          }}
        >
          {uploading ? <CircularProgress size={24} color="inherit" /> : '이 설정으로 번역 시작'}
        </Button>
      </CardActions>
    </>
  );
}