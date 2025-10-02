import { useState } from 'react';
import {
  Typography, Button, Alert, LinearProgress,
  FormControlLabel, Switch
} from '@mui/material';
import { UploadFile as UploadFileIcon } from '@mui/icons-material';
import { StyleData, GlossaryTerm } from '../../types/ui';

interface FileUploadSectionProps {
  isAnalyzing: boolean;
  isAnalyzingGlossary: boolean;
  uploading: boolean;
  error: string | null;
  onFileSelect: (file: File, analyzeGlossary: boolean) => Promise<{
    styleData: StyleData | null;
    glossaryData: GlossaryTerm[];
    error: string | null;
  }>;
}

export default function FileUploadSection({
  isAnalyzing,
  isAnalyzingGlossary,
  uploading,
  error,
  onFileSelect
}: FileUploadSectionProps) {
  const [file, setFile] = useState<File | null>(null);
  const [analyzeGlossary, setAnalyzeGlossary] = useState(true);
  const [analysisError, setAnalysisError] = useState<string>('');

  const handleFileChange = async (selectedFile: File | null) => {
    if (!selectedFile) {
      setFile(null);
      return;
    }
    
    setFile(selectedFile);
    setAnalysisError('');
    
    try {
      await onFileSelect(selectedFile, analyzeGlossary);
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : "파일 분석 중 오류가 발생했습니다.");
    }
  };

  return (
    <>
      <Typography variant="h5" component="h3" gutterBottom>
        4. 소설 파일 업로드
      </Typography>
      
      <FormControlLabel
        control={
          <Switch 
            checked={analyzeGlossary} 
            onChange={(e) => setAnalyzeGlossary(e.target.checked)} 
          />
        }
        label="AI 용어집 사전분석 및 수정 활성화"
        sx={{ mb: 1 }}
      />
      
      <Button
        variant="contained"
        component="label"
        startIcon={<UploadFileIcon />}
        disabled={isAnalyzing || uploading}
        fullWidth
        size="large"
      >
        {file ? file.name : '파일 선택'}
        <input
          id="file-upload-input"
          type="file"
          hidden
          onChange={(e) => handleFileChange(e.target.files ? e.target.files[0] : null)}
        />
      </Button>

      {(isAnalyzing || isAnalyzingGlossary) && (
        <LinearProgress color="secondary" sx={{ mt: 2 }} />
      )}
      
      {analysisError && (
        <Alert severity="error" sx={{ mt: 2 }}>{analysisError}</Alert>
      )}
      
      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>
      )}
    </>
  );
}