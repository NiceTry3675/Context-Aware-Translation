'use client';

import React from 'react';
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
} from '@mui/icons-material';
import { GlossaryTerm } from '../../types/ui';

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
    </Box>
  );
}