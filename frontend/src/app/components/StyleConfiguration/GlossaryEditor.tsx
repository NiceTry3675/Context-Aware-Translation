'use client';

import React, { useRef, useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  TextField,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  UploadFile as UploadFileIcon,
} from '@mui/icons-material';
import { GlossaryTerm } from '../../types/ui';
import { mergeGlossaryTerms, normalizeGlossaryData } from '../../utils/glossary';

interface GlossaryEditorProps {
  glossaryData: GlossaryTerm[];
  isAnalyzingGlossary: boolean;
  glossaryAnalysisError?: string;
  onGlossaryChange: (glossaryData: GlossaryTerm[]) => void;
}

export default function GlossaryEditor({
  glossaryData,
  isAnalyzingGlossary,
  glossaryAnalysisError,
  onGlossaryChange,
}: GlossaryEditorProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [importError, setImportError] = useState('');

  const handleGlossaryChange = (index: number, field: keyof GlossaryTerm, value: string) => {
    const updated = [...glossaryData];
    updated[index] = { ...updated[index], [field]: value };
    onGlossaryChange(updated);
  };

  const handleAddGlossaryTerm = () => {
    const updated = [...glossaryData, { source: '', korean: '' }];
    onGlossaryChange(updated);
  };

  const handleRemoveGlossaryTerm = (index: number) => {
    const updated = glossaryData.filter((_, i) => i !== index);
    onGlossaryChange(updated);
  };

  const handleGlossaryFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(reader.result as string);
        const importedTerms = normalizeGlossaryData(parsed);

        if (!importedTerms.length) {
          setImportError('용어집 파일에서 가져올 항목을 찾지 못했습니다. JSON 구조를 확인해주세요.');
          return;
        }

        const merged = mergeGlossaryTerms(glossaryData, importedTerms);
        onGlossaryChange(merged);
        setImportError('');
      } catch (error) {
        console.error('Failed to parse glossary file:', error);
        setImportError('용어집 파일을 읽는 데 실패했습니다. 유효한 JSON 파일인지 확인해주세요.');
      } finally {
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      }
    };

    reader.onerror = () => {
      setImportError('용어집 파일을 읽는 동안 오류가 발생했습니다. 다시 시도해주세요.');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    };

    reader.readAsText(file);
  };

  return (
    <Box>
      <Typography variant="h5" component="h3" gutterBottom>
        6. 고유명사 번역 노트
      </Typography>
      <Typography color="text.secondary" mb={2}>
        AI가 추천한 용어집입니다. 번역을 수정하거나, 새로운 용어를 추가/삭제할 수 있습니다.
      </Typography>

      {glossaryAnalysisError && (
        <Alert severity="warning" sx={{ mb: 2 }}>{glossaryAnalysisError}</Alert>
      )}

      {importError && (
        <Alert severity="error" sx={{ mb: 2 }}>{importError}</Alert>
      )}
      
      {isAnalyzingGlossary ? (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          <CircularProgress size={24} />
          <Typography>용어집 분석 중...</Typography>
        </Box>
      ) : glossaryData.length > 0 ? (
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
              {glossaryData.map((term, index) => (
                <TableRow key={index}>
                  <TableCell>
                    <TextField
                      value={term.source}
                      onChange={(e) => handleGlossaryChange(index, 'source', e.target.value)}
                      variant="standard"
                      fullWidth
                    />
                  </TableCell>
                  <TableCell>
                    <TextField
                      value={term.korean}
                      onChange={(e) => handleGlossaryChange(index, 'korean', e.target.value)}
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

      <Button
        component="label"
        variant="outlined"
        startIcon={<UploadFileIcon />}
      >
        용어집 불러오기 (.json)
        <input
          ref={fileInputRef}
          type="file"
          hidden
          accept="application/json,.json"
          onChange={handleGlossaryFileChange}
        />
      </Button>
    </Box>
  );
}
