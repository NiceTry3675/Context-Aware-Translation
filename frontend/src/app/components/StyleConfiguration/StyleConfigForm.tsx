import { useState, useEffect } from 'react';
import { Button, CircularProgress, CardActions } from '@mui/material';
import { StyleData, GlossaryTerm } from '../../types/translation';
import theme from '../../../theme';
import StyleFieldEditor from './StyleFieldEditor';
import GlossaryEditor from './GlossaryEditor';

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

  return (
    <>
      <StyleFieldEditor 
        styleData={localStyleData}
        onStyleChange={handleStyleFieldChange}
      />

      <GlossaryEditor
        glossaryData={localGlossaryData}
        isAnalyzingGlossary={isAnalyzingGlossary}
        glossaryAnalysisError={glossaryAnalysisError}
        onGlossaryChange={(updated) => {
          setLocalGlossaryData(updated);
          onGlossaryChange(updated);
        }}
      />

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