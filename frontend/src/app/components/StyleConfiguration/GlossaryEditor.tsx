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
  Upload as UploadIcon,
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
  const parseImportedGlossary = (json: any): GlossaryTerm[] => {
    try {
      if (!json) return [];
      // Structured response shape
      if (Array.isArray((json as any).glossary)) {
        return (json as any).glossary
          .map((it: any) => ({ source: String(it.term || ''), korean: String(it.translation || '') }))
          .filter((t: GlossaryTerm) => t.source && t.korean);
      }
      if ((json as any).translated_terms && Array.isArray((json as any).translated_terms.translations)) {
        return (json as any).translated_terms.translations
          .map((it: any) => ({ source: String(it.source || ''), korean: String(it.korean || '') }))
          .filter((t: GlossaryTerm) => t.source && t.korean);
      }
      // Plain dict
      if (typeof json === 'object' && !Array.isArray(json)) {
        return Object.entries(json as Record<string, unknown>)
          .map(([k, v]) => ({ source: String(k), korean: String(v as any) }))
          .filter((t: GlossaryTerm) => t.source && t.korean);
      }
      // Array forms
      if (Array.isArray(json)) {
        const out: GlossaryTerm[] = [];
        for (const item of json) {
          if (typeof item !== 'object' || item == null) continue;
          if ('source' in item && 'korean' in item) {
            const source = String((item as any).source || '');
            const korean = String((item as any).korean || '');
            if (source && korean) out.push({ source, korean });
            continue;
          }
          if ('term' in item && 'translation' in item) {
            const source = String((item as any).term || '');
            const korean = String((item as any).translation || '');
            if (source && korean) out.push({ source, korean });
            continue;
          }
          // Single-key object { "Term": "번역" }
          const entries = Object.entries(item);
          if (entries.length === 1) {
            const [k, v] = entries[0];
            const source = String(k || '');
            const korean = String((v as any) || '');
            if (source && korean) out.push({ source, korean });
          }
        }
        return out;
      }
    } catch (e) {
      // fallthrough
    }
    return [];
  };

  const handleImportGlossaryJson = async () => {
    try {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.json,application/json';
      input.onchange = async () => {
        if (!input.files || input.files.length === 0) return;
        const file = input.files[0];
        const text = await file.text();
        let json: any;
        try {
          json = JSON.parse(text);
        } catch (e) {
          alert('유효한 JSON 파일이 아닙니다.');
          return;
        }
        const imported = parseImportedGlossary(json);
        if (!imported.length) {
          alert('인식 가능한 용어집 형식이 아닙니다.');
          return;
        }
        // Merge by source, prefer imported values
        const mergedMap = new Map<string, string>();
        for (const term of glossaryData) {
          if (term.source && term.korean) mergedMap.set(term.source, term.korean);
        }
        for (const term of imported) {
          mergedMap.set(term.source, term.korean);
        }
        const merged: GlossaryTerm[] = Array.from(mergedMap.entries()).map(([source, korean]) => ({ source, korean }));
        onGlossaryChange(merged);
      };
      input.click();
    } catch (error) {
      console.error('Glossary JSON import error:', error);
    }
  };

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

      <Box sx={{ display: 'flex', gap: 1, mb: 3 }}>
        <Button onClick={handleAddGlossaryTerm} startIcon={<AddIcon />}>
          용어 추가
        </Button>
        <Button variant="outlined" onClick={handleImportGlossaryJson} startIcon={<UploadIcon />}>
          JSON 용어집 주입
        </Button>
      </Box>
    </Box>
  );
}