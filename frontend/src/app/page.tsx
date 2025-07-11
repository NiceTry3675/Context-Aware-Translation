"use client";

import { useState, useEffect, useCallback } from 'react';
import {
  Container, Box, Typography, TextField, Button, CircularProgress, Alert,
  Card, CardContent, CardActions, IconButton, Tooltip, Chip,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
  LinearProgress, ToggleButtonGroup, ToggleButton
} from '@mui/material';
import {
  UploadFile as UploadFileIcon,
  Delete as DeleteIcon,
  Download as DownloadIcon,
  Info as InfoIcon,
  Coffee as CoffeeIcon,
  Email as EmailIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Pending as PendingIcon,
  AccountTree as AccountTreeIcon,
  Spellcheck as SpellcheckIcon,
  Style as StyleIcon,
  Description as DescriptionIcon, // 로그 아이콘
  Chat as ChatIcon // 프롬프트 아이콘
} from '@mui/icons-material';
import theme from '../theme'; // Import the custom theme

// --- Type Definitions ---
interface Job {
  id: number;
  filename: string;
  status: string;
  progress: number;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
}

interface StyleData {
  narrative_perspective: string;
  primary_speech_level: string;
  tone: string;
}

const modelOptions = [
    {
      value: "gemini-2.5-flash-lite-preview-06-17",
      label: "Flash Lite",
      description: "가장 빠르고 경제적입니다. 초벌 번역에 적합합니다."
    },
    {
      value: "gemini-2.5-flash",
      label: "Flash",
      description: "속도와 품질의 균형을 맞춘 모델입니다."
    },
    {
      value: "gemini-2.5-pro",
      label: "Pro",
      description: "최고 품질을 원할 때 사용하세요."
    },
];

const featureItems = [
  {
    icon: <AccountTreeIcon sx={{ fontSize: 40 }} />,
    title: "문맥 유지",
    text: "소설 전체의 분위기와 등장인물의 말투를 학습하여, 챕터가 넘어가도 번역 품질이 흔들리지 않습니다.",
    color: theme.palette.primary.main,
  },
  {
    icon: <SpellcheckIcon sx={{ fontSize: 40 }} />,
    title: "용어 일관성",
    text: "고유명사나 특정 용어가 번역될 때마다 달라지는 문제를 해결했습니니다. 중요한 단어는 항상 동일하게 번역됩니다.",
    color: theme.palette.success.main,
  },
  {
    icon: <StyleIcon sx={{ fontSize: 40 }} />,
    title: "스타일 유지",
    text: "작가 특유의 문체나 작품의 스타일을 학습하여, 원작의 느낌을 최대한 살린 번역을 제공합니다.",
    color: theme.palette.info.main,
  },
];


// --- Main Component ---
export default function Home() {
  // --- State Management ---
  const [apiKey, setApiKey] = useState<string>('');
  const [file, setFile] = useState<File | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string>(modelOptions[0].value);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [analysisError, setAnalysisError] = useState<string>('');
  const [styleData, setStyleData] = useState<StyleData | null>(null);
  const [showStyleForm, setShowStyleForm] = useState<boolean>(false);
  const [devMode, setDevMode] = useState<boolean>(false);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // --- Effects ---
  useEffect(() => {
    const storedApiKey = localStorage.getItem('geminiApiKey');
    if (storedApiKey) setApiKey(storedApiKey);
    setDevMode(localStorage.getItem('devMode') === 'true');
  }, []);

  useEffect(() => {
    if (apiKey) localStorage.setItem('geminiApiKey', apiKey);
  }, [apiKey]);

  useEffect(() => {
    const loadJobs = async () => {
      const storedJobIdsString = localStorage.getItem('jobIds');
      if (!storedJobIdsString) return;
      const storedJobIds = JSON.parse(storedJobIdsString);
      if (!Array.isArray(storedJobIds) || storedJobIds.length === 0) return;

      try {
        const fetchedJobs: Job[] = await Promise.all(
          storedJobIds.map(async (id: number) => {
            const response = await fetch(`${API_URL}/status/${id}`);
            return response.ok ? response.json() : null;
          })
        );
        const validJobs = fetchedJobs
          .filter((job): job is Job => job !== null)
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        setJobs(validJobs);
      } catch (error) {
        console.error("Failed to load jobs from storage:", error);
        localStorage.removeItem('jobIds');
      }
    };
    loadJobs();
  }, [API_URL]);

  const pollJobStatus = useCallback(async () => {
    const processingJobs = jobs.filter(job => ['PROCESSING', 'PENDING'].includes(job.status));
    if (processingJobs.length === 0) return;

    const updatedJobs = await Promise.all(
      processingJobs.map(async (job) => {
        try {
          const response = await fetch(`${API_URL}/status/${job.id}`);
          return response.ok ? response.json() : job;
        } catch {
          return job;
        }
      })
    );
    setJobs(currentJobs =>
      currentJobs.map(job => updatedJobs.find(updated => updated.id === job.id) || job)
    );
  }, [jobs, API_URL]);

  useEffect(() => {
    const interval = setInterval(pollJobStatus, 3000);
    return () => clearInterval(interval);
  }, [pollJobStatus]);

  // --- Handlers ---
  const handleFileChange = async (selectedFile: File | null) => {
    if (!selectedFile) {
      setFile(null);
      return;
    }
    setFile(selectedFile);
    if (!apiKey) {
      setError("API 키를 먼저 입력해주세요.");
      return;
    }
    setIsAnalyzing(true);
    setAnalysisError('');
    setError(null);
    setStyleData(null);

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('api_key', apiKey);
    formData.append('model_name', selectedModel);

    try {
      const response = await fetch(`${API_URL}/api/v1/analyze-style`, { method: 'POST', body: formData });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '스타일 분석에 실패했습니다.');
      }
      const analyzedStyle = await response.json();
      setStyleData(analyzedStyle);
      setShowStyleForm(true);
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleStartTranslation = async () => {
    if (!file || !styleData) {
      setError("번역을 시작할 파일과 스타일 정보가 필요합니다.");
      return;
    }
    setUploading(true);
    setError(null);
    setShowStyleForm(false);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("api_key", apiKey);
    formData.append("model_name", selectedModel);
    formData.append("style_data", JSON.stringify(styleData));

    try {
      const response = await fetch(`${API_URL}/uploadfile/`, { method: 'POST', body: formData });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "File upload failed");
      }
      const newJob: Job = await response.json();
      setJobs(prevJobs => [newJob, ...prevJobs]);
      const storedJobIds = JSON.parse(localStorage.getItem('jobIds') || '[]');
      localStorage.setItem('jobIds', JSON.stringify([newJob.id, ...storedJobIds]));
      setFile(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unknown error occurred.");
    } finally {
      setUploading(false);
    }
  };

  const handleCancelStyleEdit = () => {
    setShowStyleForm(false);
    setFile(null);
    setStyleData(null);
    const fileInput = document.getElementById('file-upload-input') as HTMLInputElement;
    if (fileInput) fileInput.value = '';
  };

  const handleDelete = (jobId: number) => {
    setJobs(prevJobs => prevJobs.filter(job => job.id !== jobId));
    const storedJobIds = JSON.parse(localStorage.getItem('jobIds') || '[]');
    localStorage.setItem('jobIds', JSON.stringify(storedJobIds.filter((id: number) => id !== jobId)));
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'COMPLETED': return <CheckCircleIcon color="success" />;
      case 'FAILED': return <ErrorIcon color="error" />;
      case 'PENDING': return <PendingIcon color="warning" />;
      default: return <CircularProgress size={20} />;
    }
  };

  // --- Render ---
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box textAlign="center" mb={10}>
        <Box display="flex" justifyContent="center" alignItems="center" gap={2}>
          <Typography variant="h1" component="h1" sx={{
            background: `linear-gradient(45deg, #00BFFF 30%, #FF69B4 90%)`,
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            냥번역
          </Typography>
          <Chip label="beta" color="secondary" size="small" />
        </Box>
        <Typography variant="h5" color="text.secondary" component="p" mt={1}>
          <Box component="span" sx={{ color: 'primary.main', fontWeight: 'bold' }}>C</Box>ontext-
          <Box component="span" sx={{ color: 'primary.main', fontWeight: 'bold' }}>A</Box>ware{' '}
          <Box component="span" sx={{ color: 'primary.main', fontWeight: 'bold' }}>T</Box>ranslator
        </Typography>
      </Box>

      {/* Features Section */}
      <Box mb={10}>
        <Typography variant="h2" component="h2" textAlign="center" gutterBottom>
          냥번역은 무엇이 다른가요?
        </Typography>
        <Typography textAlign="center" color="text.secondary" maxWidth="md" mx="auto" mb={5}>
          단순한 번역기를 넘어, 소설의 맛을 살리는 데 집중했습니다. 일반 생성형 AI 번역에서 발생하는 고질적인 문제들을 해결하여, 처음부터 끝까지 일관성 있는 고품질 번역을 경험할 수 있습니다.
        </Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 4 }}>
          {featureItems.map(item => (
            <Card key={item.title} sx={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', p: 3, textAlign: 'center' }}>
              <Box mb={2} sx={{
                width: 80,
                height: 80,
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: `${item.color}20`,
                color: item.color,
                boxShadow: `0 0 20px ${item.color}40`,
              }}>
                {item.icon}
              </Box>
              <Typography variant="h5" component="h3" gutterBottom>{item.title}</Typography>
              <Typography color="text.secondary">{item.text}</Typography>
            </Card>
          ))}
        </Box>
      </Box>

      {/* Main Action Card */}
      <Card sx={{ p: { xs: 2, md: 4 }, mb: 8 }}>
        <CardContent>
          {/* Step 1: Model Selection */}
          <Typography variant="h5" component="h3" gutterBottom>1. 번역 모델 선택</Typography>
          <ToggleButtonGroup
            value={selectedModel}
            exclusive
            onChange={(_, newValue) => { if (newValue) setSelectedModel(newValue); }}
            aria-label="Translation Model Selection"
            fullWidth
            sx={{ mb: 4 }}
          >
            {modelOptions.map(opt => (
              <ToggleButton value={opt.value} key={opt.value} sx={{ flexDirection: 'column', flex: 1, p: 2 }}>
                <Typography variant="button">{opt.label}</Typography>
                <Typography variant="caption" sx={{ textTransform: 'none', mt: 0.5 }}>{opt.description}</Typography>
              </ToggleButton>
            ))}
          </ToggleButtonGroup>

          {/* Step 2: API Key */}
          <Typography variant="h5" component="h3" gutterBottom>2. Gemini API 키 입력</Typography>
          <TextField
            type="password"
            label="Gemini API Key"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            fullWidth
            sx={{ mb: 4 }}
          />

          {/* Step 3: File Upload */}
          <Typography variant="h5" component="h3" gutterBottom>3. 소설 파일 업로드</Typography>
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

          {isAnalyzing && <LinearProgress color="secondary" sx={{ mt: 2 }} />}
          {analysisError && <Alert severity="error" sx={{ mt: 2 }}>{analysisError}</Alert>}
          {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
        </CardContent>

        {/* Step 4: Style Form */}
        {showStyleForm && styleData && (
          <CardContent sx={{ borderTop: 1, borderColor: 'divider', mt: 2 }}>
            <Typography variant="h5" component="h3" gutterBottom>4. 핵심 서사 스타일 확인 및 수정</Typography>
            <Typography color="text.secondary" mb={3}>AI가 분석한 소설의 핵심 스타일입니다. 필요하다면 직접 수정할 수 있습니다.</Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 2 }}>
                <TextField 
                  label="서사 관점" 
                  value={styleData.narrative_perspective} 
                  onChange={(e) => setStyleData(prev => prev ? { ...prev, narrative_perspective: e.target.value } : null)} 
                  fullWidth 
                />
                <TextField 
                  label="주요 말투" 
                  value={styleData.primary_speech_level} 
                  onChange={(e) => setStyleData(prev => prev ? { ...prev, primary_speech_level: e.target.value } : null)} 
                  fullWidth 
                />
                <TextField 
                  label="글의 톤" 
                  value={styleData.tone} 
                  onChange={(e) => setStyleData(prev => prev ? { ...prev, tone: e.target.value } : null)} 
                  fullWidth 
                />
            </Box>
            <CardActions sx={{ justifyContent: 'flex-end', mt: 3, p: 0 }}>
              <Button onClick={handleCancelStyleEdit} color="secondary">취소</Button>
              <Button 
                onClick={handleStartTranslation} 
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
                {uploading ? <CircularProgress size={24} color="inherit" /> : '이 스타일로 번역 시작'}
              </Button>
            </CardActions>
          </CardContent>
        )}
      </Card>

      {/* Jobs Table */}
      <Typography variant="h2" component="h2" textAlign="center" gutterBottom>Translation Jobs</Typography>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Filename</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Submitted</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {jobs.map((job) => (
              <TableRow key={job.id} hover sx={{ '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.04)' }}}>
                <TableCell>{job.filename}</TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {getStatusIcon(job.status)}
                    <Typography variant="body2">
                      {job.status} {job.status === 'PROCESSING' && `(${job.progress}%)`}
                    </Typography>
                    {job.status === 'FAILED' && job.error_message && (
                      <Tooltip title={job.error_message}><InfoIcon fontSize="small" sx={{ cursor: 'pointer' }} /></Tooltip>
                    )}
                  </Box>
                  {job.status === 'PROCESSING' && <LinearProgress variant="determinate" value={job.progress} />}
                </TableCell>
                <TableCell>{new Date(job.created_at).toLocaleString()}</TableCell>
                <TableCell align="right">
                  <Box sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
                    {job.status === 'COMPLETED' && (
                      <Tooltip title="Download Translated File">
                        <IconButton color="primary" href={`${API_URL}/download/${job.id}`} download>
                          <DownloadIcon />
                        </IconButton>
                      </Tooltip>
                    )}
                    {devMode && (job.status === 'COMPLETED' || job.status === 'FAILED') && (
                      <>
                        <Tooltip title="Download Prompts Log">
                          <IconButton size="small" href={`${API_URL}/download/logs/${job.id}/prompts`} download>
                            <ChatIcon />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Download Context Log">
                          <IconButton size="small" href={`${API_URL}/download/logs/${job.id}/context`} download>
                            <DescriptionIcon />
                          </IconButton>
                        </Tooltip>
                      </>
                    )}
                    <Tooltip title="Delete Job">
                      <IconButton onClick={() => handleDelete(job.id)}>
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Footer */}
      <Box textAlign="center" mt={10} pt={4} borderTop={1} borderColor="divider">
        <Typography variant="h6" gutterBottom>이 서비스가 마음에 드셨나요?</Typography>
        <Typography color="text.secondary" mb={2}>여러분의 소중한 후원은 서비스 유지 및 기능 개선에 큰 힘이 됩니다.</Typography>
        <Box>
          <Button
            variant="contained"
            startIcon={<CoffeeIcon />}
            href="https://coff.ee/nicetry3675"
            target="_blank"
            rel="noopener noreferrer"
            sx={{ 
              mr: 1,
              backgroundColor: theme.palette.warning.main,
              color: theme.palette.getContrastText(theme.palette.warning.main),
              '&:hover': {
                backgroundColor: '#ffca28'
              }
            }}
          >
            Buy Me a Coffee
          </Button>
          <Button
            variant="outlined"
            startIcon={<EmailIcon />}
            href="mailto:tomtom5330@gmail.com"
          >
            Contact Us
          </Button>
        </Box>
      </Box>
    </Container>
  );
}