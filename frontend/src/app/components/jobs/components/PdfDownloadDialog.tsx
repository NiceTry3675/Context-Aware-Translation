'use client';

import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControl,
  FormLabel,
  RadioGroup,
  Radio,
  FormControlLabel,
  Box,
  Typography,
} from '@mui/material';

interface PdfDownloadDialogProps {
  open: boolean;
  onClose: () => void;
  onDownload: (illustrationPosition: string) => void;
  jobId: number;
}

export default function PdfDownloadDialog({
  open,
  onClose,
  onDownload,
  jobId,
}: PdfDownloadDialogProps) {
  const [illustrationPosition, setIllustrationPosition] = useState<string>('middle');

  const handleDownload = () => {
    onDownload(illustrationPosition);
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>PDF 다운로드 옵션</DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 2 }}>
          <FormControl component="fieldset">
            <FormLabel component="legend">삽화 위치</FormLabel>
            <RadioGroup
              value={illustrationPosition}
              onChange={(e) => setIllustrationPosition(e.target.value)}
            >
              <FormControlLabel
                value="start"
                control={<Radio />}
                label={
                  <Box>
                    <Typography variant="body1">세그먼트 시작</Typography>
                    <Typography variant="caption" color="text.secondary">
                      번역문 앞에 삽화 표시
                    </Typography>
                  </Box>
                }
              />
              <FormControlLabel
                value="middle"
                control={<Radio />}
                label={
                  <Box>
                    <Typography variant="body1">세그먼트 중간</Typography>
                    <Typography variant="caption" color="text.secondary">
                      중간 문단 뒤에 삽화 표시
                    </Typography>
                  </Box>
                }
              />
              <FormControlLabel
                value="end"
                control={<Radio />}
                label={
                  <Box>
                    <Typography variant="body1">세그먼트 끝</Typography>
                    <Typography variant="caption" color="text.secondary">
                      번역문 뒤에 삽화 표시
                    </Typography>
                  </Box>
                }
              />
            </RadioGroup>
          </FormControl>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>취소</Button>
        <Button onClick={handleDownload} variant="contained" color="primary">
          다운로드
        </Button>
      </DialogActions>
    </Dialog>
  );
}
