"use client";

import { useState, useEffect, useCallback } from 'react';
import { useAuth, useClerk } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';

import {
  Container, Box, Typography, TextField, Button, CircularProgress, Alert,
  Card, CardContent, CardActions, IconButton, Tooltip, Chip,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
  LinearProgress, ToggleButtonGroup, ToggleButton, InputAdornment, Link, Slider,
  Switch, FormControlLabel
} from '@mui/material';
import {
  UploadFile as UploadFileIcon,
  Delete as DeleteIcon,
  Download as DownloadIcon,
  Coffee as CoffeeIcon,
  Email as EmailIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Pending as PendingIcon,
  AccountTree as AccountTreeIcon,
  Spellcheck as SpellcheckIcon,
  Style as StyleIcon,
  Description as DescriptionIcon,
  Chat as ChatIcon,
  Add as AddIcon,

  Person as PersonIcon,
  TextFields as TextFieldsIcon,
  Palette as PaletteIcon,
  Gavel as GavelIcon,
  OpenInNew as OpenInNewIcon,
  AutoStories as AutoStoriesIcon,
  MenuBook as MenuBookIcon,
  Forum as ForumIcon,
  FactCheck as FactCheckIcon,
  Edit as EditIcon,
  Assessment as AssessmentIcon,
} from '@mui/icons-material';
import theme from '../theme';

import AuthButtons from './components/AuthButtons';
import TranslationSidebar from './components/TranslationSidebar';
import VisibilityIcon from '@mui/icons-material/Visibility';

// --- Type Definitions ---
interface Job {
  id: number;
  filename: string;
  status: string;
  progress: number;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
  validation_enabled: boolean;
  validation_status: string | null;
  validation_progress: number;
  validation_sample_rate: number;
  quick_validation: boolean;
  validation_completed_at: string | null;
  post_edit_enabled: boolean;
  post_edit_status: string | null;
  post_edit_completed_at: string | null;
}

interface StyleData {
  protagonist_name: string;
  narration_style_endings: string;
  tone_keywords: string;
  stylistic_rule: string;
}

interface GlossaryTerm {
  term: string;
  translation: string;
}

const geminiModelOptions = [
    {
      value: "gemini-2.5-flash-lite",
      label: "Flash Lite (추천)",
      description: "가장 빠른 속도와 저렴한 비용으로 빠르게 결과물을 확인하고 싶을 때 적합합니다.",
      chip: "속도",
      chipColor: "primary" as "primary" | "success" | "info" | "error",
    },
    {
      value: "gemini-2.5-flash",
      label: "Flash",
      description: "준수한 품질과 합리적인 속도의 균형을 원할 때 가장 이상적인 선택입니다.",
      chip: "균형",
      chipColor: "info" as "primary" | "success" | "info" | "error",
    },
    {
      value: "gemini-2.5-pro",
      label: "Pro",
      description: "최고 수준의 문학적 번역 품질을 원하신다면 선택하세요. (느리고 비쌀 수 있음)",
      chip: "품질",
      chipColor: "error" as "primary" | "success" | "info" | "error",
    },
];

const openRouterModelOptions = [
    {
      value: "google/gemini-2.5-flash-lite",
      label: "Gemini 2.5 Flash Lite",
      description: " ",
      chip: "속도",
      chipColor: "primary" as "primary" | "success" | "info" | "error",
    },
    {
        value: "google/gemini-2.5-flash",
        label: "Gemini 2.5 Flash",
        description: " ",
        chip: "균형",
        chipColor: "success" as "primary" | "success" | "info" | "error",
    },
    {
        value: "google/gemini-2.5-pro",
        label: "Gemini 2.5 Pro",
        description: " ",
        chip: "품질",
        chipColor: "info" as "primary" | "success" | "info" | "error",
    },
    {
        value: "openai/gpt-4o",
        label: "GPT-4o",
        description: " ",
        chip: "품질",
        chipColor: "warning" as "primary" | "success" | "info" | "error",
    },
    {
        value: "anthropic/claude-sonnet-4",
        label: "Claude Sonnet 4",
        description: " ",
        chip: "품질",
        chipColor: "info" as "primary" | "success" | "info" | "error",
    },
    {
        value: "openai/gpt-4.1",
        label: "GPT-4.1",
        description: " ",
        chip: "속도",
        chipColor: "success" as "primary" | "success" | "info" | "error",
    },
    {
        value: "x-ai/grok-4",
        label: "Grok-4",
        description: " ",
        chip: "품질",
        chipColor: "success" as "primary" | "success" | "info" | "error",
    },
    {
        value: "tngtech/deepseek-r1t2-chimera:free",
        label: "DeepSeek R1 T2 Chimera (무료)",
        description: " ",
        chip: "속도",
        chipColor: "success" as "primary" | "success" | "info" | "error",
    },
    {
        value: "deepseek/deepseek-r1-0528:free",
        label: "DeepSeek R1 (무료)",
        description: " ",
        chip: "품질",
        chipColor: "success" as "primary" | "success" | "info" | "error",
    },
];

const featureItems = [
  {
    icon: <AccountTreeIcon sx={{ fontSize: 40 }} />,
    title: "문맥 유지",
    text: "소설 전체의 분위기와 등장인물의 말투를 분석하여, 챕터가 넘어가도 번역 품질이 흔들리지 않습니다.",
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

const formatDuration = (start: string, end: string | null): string => {
  if (!end) return '';
  const startDate = new Date(start);
  const endDate = new Date(end);
  const seconds = Math.floor((endDate.getTime() - startDate.getTime()) / 1000);
  if (seconds < 60) return `${seconds}초`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}분 ${remainingSeconds}초`;
};


// --- Main Component ---
export default function Home() {
  const { getToken, isSignedIn, isLoaded } = useAuth();
  const { openSignIn } = useClerk();
  const router = useRouter();
  // --- State Management ---
  const [apiKey, setApiKey] = useState<string>('');
  const [file, setFile] = useState<File | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [apiProvider, setApiProvider] = useState<'gemini' | 'openrouter'>('gemini');
  const [selectedModel, setSelectedModel] = useState<string>(geminiModelOptions[0].value);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [isAnalyzingGlossary, setIsAnalyzingGlossary] = useState<boolean>(false);
  const [analysisError, setAnalysisError] = useState<string>('');
  const [glossaryAnalysisError, setGlossaryAnalysisError] = useState<string>('');
  const [styleData, setStyleData] = useState<StyleData | null>(null);
  const [showStyleForm, setShowStyleForm] = useState<boolean>(false);
  const [glossaryData, setGlossaryData] = useState<GlossaryTerm[]>([]);
  const [analyzeGlossary, setAnalyzeGlossary] = useState<boolean>(true);
  const [devMode, setDevMode] = useState<boolean>(false);
  const [segmentSize, setSegmentSize] = useState<number>(15000);
  const [enableValidation, setEnableValidation] = useState<boolean>(false);
  const [quickValidation, setQuickValidation] = useState<boolean>(false);
  const [validationSampleRate, setValidationSampleRate] = useState<number>(100);
  const [enablePostEdit, setEnablePostEdit] = useState<boolean>(false);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(false);
  const [selectedJobForSidebar, setSelectedJobForSidebar] = useState<Job | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // --- Effects ---
  useEffect(() => {
    const storedApiKey = localStorage.getItem('geminiApiKey');
    const storedProvider = localStorage.getItem('apiProvider') as 'gemini' | 'openrouter' | null;
    
    if (storedApiKey) {
        const provider = storedProvider || (storedApiKey.startsWith('sk-or-') ? 'openrouter' : 'gemini');
        setApiProvider(provider);
        setApiKey(storedApiKey);

        if (provider === 'openrouter') {
            setSelectedModel(localStorage.getItem('openRouterModel') || openRouterModelOptions[0].value);
        } else {
            setSelectedModel(localStorage.getItem('geminiModel') || geminiModelOptions[0].value);
        }
    }
    setDevMode(localStorage.getItem('devMode') === 'true');
  }, []);

  useEffect(() => {
    if (!apiKey) return;
    localStorage.setItem('geminiApiKey', apiKey);
    localStorage.setItem('apiProvider', apiProvider);
  }, [apiKey, apiProvider]);

  useEffect(() => {
    if (apiProvider === 'gemini') {
        const newModel = geminiModelOptions[0].value;
        setSelectedModel(newModel);
        localStorage.setItem('geminiModel', newModel);
    } else {
        const newModel = openRouterModelOptions[0].value;
        setSelectedModel(newModel);
        localStorage.setItem('openRouterModel', newModel);
    }
  }, [apiProvider]);


  const handleModelChange = (newValue: string) => {
    if (!newValue) return;

    const previousModel = selectedModel;
    setSelectedModel(newValue);

    if (apiProvider === 'gemini' && newValue === 'gemini-2.5-pro') {
      const confirmation = window.confirm(
        "⚠️ Pro 모델 경고 ⚠️\n\n" +
        "Pro 모델은 최고의 번역 품질을 제공하지만, 다음과 같은 단점이 있을 수 있습니다:\n\n" +
        "1. 번역 속도가 매우 느립니다.\n" +
        "2. API 비용이 다른 모델보다 훨씬 비쌉니다.\n" +
        "3. 현재 서비스는 베타 버전으로, 긴 작업 중 서버가 중단될 수 있습니다.\n\n" +
        "계속 진행하시겠습니까?"
      );

      if (!confirmation) {
        setSelectedModel(previousModel);
      }
    }
    
    if (apiProvider === 'gemini') {
        localStorage.setItem('geminiModel', newValue);
    } else {
        localStorage.setItem('openRouterModel', newValue);
    }
  };

  
  useEffect(() => {
    const loadJobs = async () => {
      const storedJobIdsString = localStorage.getItem('jobIds');
      if (!storedJobIdsString) return;
      const storedJobIds = JSON.parse(storedJobIdsString);
      if (!Array.isArray(storedJobIds) || storedJobIds.length === 0) return;

      const uniqueJobIds = [...new Set(storedJobIds)];

      try {
        const fetchedJobs: Job[] = await Promise.all(
          uniqueJobIds.map(async (id: number) => {
            const response = await fetch(`${API_URL}/api/v1/jobs/${id}`);
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
          const response = await fetch(`${API_URL}/api/v1/jobs/${job.id}`);
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
    
    // Check authentication first
    if (!isLoaded) {
      setError("인증 정보를 불러오는 중입니다. 잠시 후 다시 시도해주세요.");
      return;
    }
    
    if (!isSignedIn) {
      setError("번역을 시작하려면 먼저 로그인해주세요.");
      openSignIn({ redirectUrl: '/' });
      return;
    }
    
    setFile(selectedFile);
    if (!apiKey) {
        setError("API 키를 먼저 입력해주세요.");
        return;
    }

    setIsAnalyzing(true);
    setAnalysisError('');
    setGlossaryAnalysisError('');
    setError(null);
    setStyleData(null);
    setGlossaryData([]);
    setShowStyleForm(false);

    const styleFormData = new FormData();
    styleFormData.append('file', selectedFile);
    styleFormData.append('api_key', apiKey);
    styleFormData.append('model_name', selectedModel);

    try {
        // --- 1. Analyze Style ---
        const styleResponse = await fetch(`${API_URL}/api/v1/analyze-style`, {
            method: 'POST',
            body: styleFormData,
        });

        if (!styleResponse.ok) {
            const errorData = await styleResponse.json();
            throw new Error(errorData.detail || '스타일 분석에 실패했습니다.');
        }

        const analyzedStyle = await styleResponse.json();
        setStyleData(analyzedStyle);
        setShowStyleForm(true);

        // --- 2. Analyze Glossary (if toggled) ---
        if (analyzeGlossary) {
            setIsAnalyzingGlossary(true);
            const glossaryFormData = new FormData();
            glossaryFormData.append('file', selectedFile);
            glossaryFormData.append('api_key', apiKey);
            glossaryFormData.append('model_name', selectedModel);

            try {
                const glossaryResponse = await fetch(`${API_URL}/api/v1/analyze-glossary`, {
                    method: 'POST',
                    body: glossaryFormData,
                });

                if (glossaryResponse.ok) {
                    const result = await glossaryResponse.json();
                    setGlossaryData(result.glossary || []);
                } else {
                    const errorData = await glossaryResponse.json();
                    const errorMessage = errorData.detail || 'AI 용어집 분석에 실패했습니다. 수동으로 추가하거나, 기본 설정으로 번역을 시작할 수 있습니다.';
                    setGlossaryAnalysisError(errorMessage);
                    setGlossaryData([]); // Clear any previous data
                }
            } catch (err) {
                const errorMessage = err instanceof Error ? err.message : '용어집 분석 중 예기치 않은 오류가 발생했습니다. 네트워크 연결을 확인해주세요.';
                setGlossaryAnalysisError(errorMessage);
                setGlossaryData([]);
            } finally {
                setIsAnalyzingGlossary(false);
            }
        }

    } catch (err) {
        setAnalysisError(err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다.");
        setShowStyleForm(false); // Hide form on critical error
    } finally {
        setIsAnalyzing(false);
    }
};


  const handleGlossaryChange = (index: number, field: keyof GlossaryTerm, value: string) => {
    const updatedGlossary = [...glossaryData];
    updatedGlossary[index] = { ...updatedGlossary[index], [field]: value };
    setGlossaryData(updatedGlossary);
  };

  const handleAddGlossaryTerm = () => {
    setGlossaryData([...glossaryData, { term: '', translation: '' }]);
  };

  const handleRemoveGlossaryTerm = (index: number) => {
    const updatedGlossary = glossaryData.filter((_, i) => i !== index);
    setGlossaryData(updatedGlossary);
  };

  const handleStartTranslation = async () => {
    if (!file || !styleData) {
      setError("번역을 시작할 파일과 스타일 정보가 필요합니다.");
      return;
    }

    if (!isLoaded) {
      setError("인증 정보를 불러오는 중입니다. 잠시 후 다시 시도해주세요.");
      return;
    }

    if (!isSignedIn) {
      openSignIn({ redirectUrl: '/' });
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
    if (glossaryData.length > 0) {
      formData.append("glossary_data", JSON.stringify(glossaryData));
    }
    formData.append("segment_size", segmentSize.toString());

    try {
      const token = await getToken();
      if (!token) {
        console.error("Failed to get authentication token");
        setError("로그인은 되었으나, 인증 토큰을 가져오지 못했습니다. 잠시 후 다시 시도하거나, 페이지를 새로고침해주세요.");
        setUploading(false);
        return;
      }
      
      console.log("Got token, uploading file with authentication...");
      const response = await fetch(`${API_URL}/api/v1/jobs`, { 
        method: 'POST', 
        headers: { 
          'Authorization': `Bearer ${token}`
        },
        body: formData 
      });
      
      if (!response.ok) {
        console.error(`Upload failed with status ${response.status}: ${response.statusText}`);
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        if (response.status === 401) {
          throw new Error("인증에 실패했습니다. 다시 로그인해주세요.");
        }
        throw new Error(errorData.detail || `File upload failed: ${response.statusText}`);
      }
      const newJob: Job = await response.json();
      setJobs(prevJobs => [newJob, ...prevJobs]);
      const storedJobIds = JSON.parse(localStorage.getItem('jobIds') || '[]');
      localStorage.setItem('jobIds', JSON.stringify([newJob.id, ...storedJobIds]));
      setFile(null);
      setStyleData(null);
      setGlossaryData([]);
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
    setGlossaryData([]);
    const fileInput = document.getElementById('file-upload-input') as HTMLInputElement;
    if (fileInput) fileInput.value = '';
  };

  const handleDelete = (jobId: number) => {
    setJobs(prevJobs => prevJobs.filter(job => job.id !== jobId));
    const storedJobIds = JSON.parse(localStorage.getItem('jobIds') || '[]');
    localStorage.setItem('jobIds', JSON.stringify(storedJobIds.filter((id: number) => id !== jobId)));
  };

  const handleTriggerValidation = async (jobId: number) => {
    try {
      const token = await getToken();
      const formData = new FormData();
      formData.append('quick_validation', quickValidation.toString());
      formData.append('validation_sample_rate', validationSampleRate.toString());
      
      const response = await fetch(`${API_URL}/api/v1/jobs/${jobId}/validation`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });
      
      if (response.ok) {
        setError(null);
        // Job list will be refreshed by the automatic polling
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to start validation');
      }
    } catch (error) {
      console.error('Error triggering validation:', error);
      setError('Failed to start validation');
    }
  };

  const handleTriggerPostEdit = async (jobId: number) => {
    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/v1/jobs/${jobId}/post-edit`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        setError(null);
        // Job list will be refreshed by the automatic polling
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to start post-editing');
      }
    } catch (error) {
      console.error('Error triggering post-edit:', error);
      setError('Failed to start post-editing');
    }
  };

  const handleDownloadValidationReport = async (jobId: number) => {
    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/v1/jobs/${jobId}/validation-report`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const report = await response.json();
        const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `validation_report_job_${jobId}.json`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to download validation report');
      }
    } catch (error) {
      console.error('Error downloading validation report:', error);
      setError('Failed to download validation report');
    }
  };

  const handleDownloadPostEditLog = async (jobId: number) => {
    try {
      const token = await getToken();
      const response = await fetch(`${API_URL}/api/v1/jobs/${jobId}/post-edit-log`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const log = await response.json();
        const blob = new Blob([JSON.stringify(log, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `post_edit_log_job_${jobId}.json`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Failed to download post-edit log');
      }
    } catch (error) {
      console.error('Error downloading post-edit log:', error);
      setError('Failed to download post-edit log');
    }
  };

  const handleDownload = async (url: string, filename: string) => {
    if (!isSignedIn) {
      openSignIn({ redirectUrl: '/' });
      return;
    }
    try {
      const token = await getToken();
      if (!token) {
        setError("다운로드에 필요한 인증 토큰을 가져올 수 없습니다.");
        return;
      }
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to download file from ${url}`);
      }

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);

    } catch (err) {
      setError(err instanceof Error ? err.message : "An unknown error occurred during download.");
    }
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
      <Box sx={{ position: 'fixed', top: 32, right: 32, zIndex: 1000, display: 'flex', gap: 2 }}>
        {isSignedIn && (
          <Button
            variant="outlined"
            startIcon={<ForumIcon />}
            onClick={() => router.push('/community')}
            sx={{
              borderColor: theme.palette.primary.main,
              color: theme.palette.primary.main,
              '&:hover': {
                borderColor: theme.palette.primary.dark,
                backgroundColor: `${theme.palette.primary.main}10`,
              }
            }}
          >
            커뮤니티
          </Button>
        )}
        <AuthButtons />
      </Box>
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
          {/* Step 1: API Provider Selection */}
          <Typography variant="h5" component="h3" gutterBottom>1. API 제공자 선택</Typography>
          <ToggleButtonGroup
            value={apiProvider}
            exclusive
            onChange={(_, newProvider) => { if (newProvider) setApiProvider(newProvider); }}
            aria-label="API Provider"
            fullWidth
            sx={{ mb: 4 }}
          >
            <ToggleButton value="gemini" aria-label="Gemini">
              Google Gemini
            </ToggleButton>
            <ToggleButton value="openrouter" aria-label="OpenRouter">
              OpenRouter
            </ToggleButton>
          </ToggleButtonGroup>

          {/* Step 2: Model Selection */}
          <Typography variant="h5" component="h3" gutterBottom>2. 번역 모델 선택</Typography>
          <ToggleButtonGroup
            value={selectedModel}
            exclusive
            onChange={(_, newValue) => handleModelChange(newValue)}
            aria-label="Translation Model Selection"
            fullWidth
            sx={{ mb: 4, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 1 }}
          >
            {(apiProvider === 'gemini' ? geminiModelOptions : openRouterModelOptions).map(opt => (
              <ToggleButton value={opt.value} key={opt.value} sx={{ flexDirection: 'column', flex: 1, p: 2, alignItems: 'center', height: '100%' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Typography variant="button" sx={{ lineHeight: 1.2 }}>{opt.label}</Typography>
                  <Chip label={opt.chip} color={opt.chipColor} size="small" />
                </Box>
                <Typography variant="caption" sx={{ textTransform: 'none', mt: 0.5, textAlign: 'center' }}>
                  {opt.description}
                </Typography>
              </ToggleButton>
            ))}
          </ToggleButtonGroup>

          {apiProvider === 'openrouter' && (
            <Alert severity="info" sx={{ mb: 4 }}>
              <strong>참고:</strong> 현재 프롬프트는 Gemini 모델에 최적화되어 설계되었습니다. DEEPSEEK 모델은 무료!지만 많이 느립니다.
            </Alert>
          )}

          {/* Step 3: API Key */}
          <Typography variant="h5" component="h3" gutterBottom>3. {apiProvider === 'gemini' ? 'Gemini' : 'OpenRouter'} API 키 입력</Typography>
          <TextField
            type="password"
            label={`${apiProvider === 'gemini' ? 'Gemini' : 'OpenRouter'} API Key`}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            fullWidth
            sx={{ mb: 1 }}
            placeholder={apiProvider === 'openrouter' ? 'sk-or-... 형식의 키를 입력하세요' : ''}
          />
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 4 }}>
            <Link 
              href={apiProvider === 'gemini' ? "https://aistudio.google.com/app/apikey" : "https://openrouter.ai/keys"}
              target="_blank" 
              rel="noopener noreferrer"
              variant="body2"
              sx={{ display: 'inline-flex', alignItems: 'center' }}
            >
              API 키 발급받기
              <OpenInNewIcon sx={{ ml: 0.5, fontSize: 'inherit' }} />
            </Link>
          </Box>

          {/* Step 4: File Upload */}
          <Typography variant="h5" component="h3" gutterBottom>4. 소설 파일 업로드</Typography>
          <FormControlLabel
            control={<Switch checked={analyzeGlossary} onChange={(e) => setAnalyzeGlossary(e.target.checked)} />}
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

          {(isAnalyzing || isAnalyzingGlossary) && <LinearProgress color="secondary" sx={{ mt: 2 }} />}
          {analysisError && <Alert severity="error" sx={{ mt: 2 }}>{analysisError}</Alert>}
          {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
        </CardContent>

        {/* Step 4.5: Advanced Settings */}
        <CardContent sx={{ borderTop: 1, borderColor: 'divider', mt: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Typography variant="h5" component="h3">4.5 고급 설정 (선택)</Typography>
                <Chip label="Beta" color="info" size="small" />
            </Box>
            <Typography color="text.secondary" mb={2}>
              한 번에 번역할 최대 글자 수를 조절합니다. 일본어/중국어의 경우 5000자 내외를 권장합니다.
            </Typography>
            <Box>
                <Typography gutterBottom>
                    세그먼트 크기: <strong>{segmentSize.toLocaleString()}자</strong>
                </Typography>
                <Slider
                    value={segmentSize}
                    onChange={(_, newValue) => setSegmentSize(newValue as number)}
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
            
            {/* Validation Settings */}
            <Box sx={{ mt: 3 }}>
                <Typography variant="h6" gutterBottom>번역 검증 설정</Typography>
                <FormControlLabel
                    control={
                        <Switch
                            checked={enableValidation}
                            onChange={(e) => setEnableValidation(e.target.checked)}
                            color="primary"
                        />
                    }
                    label="번역 완료 후 자동 검증"
                />
                {enableValidation && (
                    <Box sx={{ ml: 3, mt: 2 }}>
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={quickValidation}
                                    onChange={(e) => setQuickValidation(e.target.checked)}
                                    color="secondary"
                                />
                            }
                            label="빠른 검증 (중요 문제만 확인)"
                        />
                        <Box sx={{ mt: 2 }}>
                            <Typography gutterBottom>
                                검증 샘플 비율: <strong>{validationSampleRate}%</strong>
                            </Typography>
                            <Slider
                                value={validationSampleRate}
                                onChange={(_, newValue) => setValidationSampleRate(newValue as number)}
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
                                    checked={enablePostEdit}
                                    onChange={(e) => setEnablePostEdit(e.target.checked)}
                                    color="success"
                                    disabled={!enableValidation}
                                />
                            }
                            label="검증된 문제 자동 수정 (Post-Edit)"
                        />
                    </Box>
                )}
            </Box>
        </CardContent>

        {/* Step 5: Style and Glossary Form */}
        {showStyleForm && styleData && (
          <CardContent sx={{ borderTop: 1, borderColor: 'divider', mt: 2 }}>
            <Typography variant="h5" component="h3" gutterBottom>5. 핵심 서사 스타일 확인 및 수정</Typography>
            <Typography color="text.secondary" mb={3}>AI가 분석한 소설의 핵심 스타일입니다. 필요하다면 직접 수정할 수 있습니다.</Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mb: 4 }}>
                <TextField 
                  label="1. 주인공 이름" 
                  value={styleData.protagonist_name} 
                  onChange={(e) => setStyleData(prev => prev ? { ...prev, protagonist_name: e.target.value } : null)} 
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
                  onChange={(e) => setStyleData(prev => prev ? { ...prev, narration_style_endings: e.target.value } : null)} 
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
                  onChange={(e) => setStyleData(prev => prev ? { ...prev, tone_keywords: e.target.value } : null)} 
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
                  onChange={(e) => setStyleData(prev => prev ? { ...prev, stylistic_rule: e.target.value } : null)} 
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

            <>
              <Typography variant="h5" component="h3" gutterBottom>6. 고유명사 번역 노트</Typography>
              <Typography color="text.secondary" mb={2}>
                {analyzeGlossary
                  ? "AI가 추천한 용어집입니다. 번역을 수정하거나, 새로운 용어를 추가/삭제할 수 있습니다."
                  : "번역에 사용할 고유명사(인물, 지명 등)를 직접 추가할 수 있습니다. AI 분석은 비활성화됩니다."
                }
              </Typography>

              {glossaryAnalysisError && <Alert severity="warning" sx={{ mb: 2 }}>{glossaryAnalysisError}</Alert>}
              
              {isAnalyzingGlossary ? (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2}}>
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
              ) : (
                null
              )}

              <Button onClick={handleAddGlossaryTerm} startIcon={<AddIcon />} sx={{ mb: 3 }}>
                용어 추가
              </Button>

              <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
                <Button
                  component="label"
                  variant="outlined"
                  startIcon={<UploadFileIcon />}
                >
                  용어집 불러오기 (.json)
                  <input
                    type="file"
                    hidden
                    accept=".json"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) {
                        const reader = new FileReader();
                        reader.onload = (event) => {
                          try {
                            const newGlossaryJson = JSON.parse(event.target?.result as string);
                            
                            // Create a Map to merge glossaries, ensuring new terms overwrite old ones
                            const mergedGlossaryMap = new Map<string, string>();

                            // Add existing terms to the map
                            glossaryData.forEach(term => mergedGlossaryMap.set(term.term, term.translation));

                            // Add new/updated terms from the file to the map
                            Object.entries(newGlossaryJson).forEach(([term, translation]) => {
                              if (typeof term === 'string' && typeof translation === 'string') {
                                mergedGlossaryMap.set(term, translation);
                              }
                            });

                            // Convert the map back to an array of objects
                            const mergedGlossary = Array.from(mergedGlossaryMap, ([term, translation]) => ({ term, translation }));

                            setGlossaryData(mergedGlossary);
                          } catch (error) {
                            console.error("Error parsing glossary file:", error);
                            setError("용어집 파일을 읽는 데 실패했습니다. 유효한 JSON 파일인지 확인해주세요.");
                          }
                        };
                        reader.readAsText(file);
                      }
                    }}
                  />
                </Button>
              </Box>
            </>

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
                {uploading ? <CircularProgress size={24} color="inherit" /> : '이 설정으로 번역 시작'}
              </Button>
            </CardActions>
          </CardContent>
        ) }
      </Card>

      {/* Jobs Section */}
      <Typography variant="h2" component="h2" textAlign="center" gutterBottom>Translation Jobs</Typography>
      
      {jobs.some(job => job.status === 'PROCESSING') && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <strong>안내:</strong> 번역 작업은 내부적으로 여러 단계를 거칩니다. 첫 챕터(약 5~10분)의 분석 및 번역이 완료될 때까지 진행률이 0%로 표시될 수 있으니 잠시만 기다려주세요.
        </Alert>
      )}

      {jobs.some(job => job.status === 'COMPLETED' && !job.filename.toLowerCase().endsWith('.epub')) && (
        <Alert severity="success" icon={<MenuBookIcon fontSize="inherit" />} sx={{ mb: 2 }}>
          <strong>팁:</strong> 완료된 TXT 파일은{' '}
          <Link href="https://calibre-ebook.com/download" target="_blank" rel="noopener noreferrer" sx={{ fontWeight: 'bold' }}>
            Calibre
          </Link>
          {' '}
          를 사용하여 EPUB 등 원하는 전자책 형식으로 쉽게 변환할 수 있습니다.
        </Alert>
      )}

      {jobs.length > 0 ? (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>파일명</TableCell>
                <TableCell>상태</TableCell>
                <TableCell>소요 시간</TableCell>
                <TableCell align="right">작업</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {jobs.map((job) => (
                <TableRow key={`job-row-${job.id}`} hover>
                  <TableCell component="th" scope="row">
                    <Typography variant="body2" noWrap title={job.filename} sx={{ maxWidth: '300px' }}>
                      {job.filename}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(job.created_at).toLocaleString()}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {job.status === 'FAILED' && job.error_message ? (
                      <Tooltip title={job.error_message} arrow>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, cursor: 'help' }}>
                          {getStatusIcon(job.status)}
                          <Typography variant="body2">
                            {job.status}
                          </Typography>
                        </Box>
                      </Tooltip>
                    ) : (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {getStatusIcon(job.status)}
                        <Typography variant="body2">
                          {job.status} {job.status === 'PROCESSING' && `(${job.progress}%)`}
                        </Typography>
                      </Box>
                    )}
                    {job.status === 'PROCESSING' && <LinearProgress variant="determinate" value={job.progress} sx={{ mt: 0.5 }} />}
                    
                    {/* Validation Status */}
                    {job.validation_enabled && (
                      <Box sx={{ mt: 1 }}>
                        <Chip 
                          label={`검증: ${job.validation_status || 'PENDING'}`}
                          size="small"
                          color={
                            job.validation_status === 'COMPLETED' ? 'success' :
                            job.validation_status === 'IN_PROGRESS' ? 'warning' :
                            job.validation_status === 'FAILED' ? 'error' : 'default'
                          }
                        />
                      </Box>
                    )}
                    
                    {/* Post-Edit Status */}
                    {job.post_edit_enabled && (
                      <Box sx={{ mt: 0.5 }}>
                        <Chip 
                          label={`수정: ${job.post_edit_status || 'PENDING'}`}
                          size="small"
                          color={
                            job.post_edit_status === 'COMPLETED' ? 'success' :
                            job.post_edit_status === 'IN_PROGRESS' ? 'warning' :
                            job.post_edit_status === 'FAILED' ? 'error' : 'default'
                          }
                        />
                      </Box>
                    )}
                  </TableCell>
                  <TableCell>
                    {job.status === 'COMPLETED' ? formatDuration(job.created_at, job.completed_at) : '-'}
                  </TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
                      {(job.status === 'COMPLETED' || job.status === 'FAILED') && (
                        <Tooltip title="번역 파일 다운로드">
                          <IconButton 
                            color="primary" 
                            onClick={() => handleDownload(`${API_URL}/api/v1/jobs/${job.id}/output`, `${job.filename.split('.')[0]}_translated.${job.filename.toLowerCase().endsWith('.epub') ? 'epub' : 'txt'}`)}
                          >
                            <DownloadIcon />
                          </IconButton>
                        </Tooltip>
                      )}
                      {job.status === 'COMPLETED' && (
                        <>
                          <Tooltip title="용어집 다운로드">
                            <IconButton 
                              color="secondary"
                              onClick={() => handleDownload(`${API_URL}/api/v1/jobs/${job.id}/glossary`, `${job.filename.split('.')[0]}_glossary.json`)}
                            >
                              <MenuBookIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="상세 보기">
                            <IconButton 
                              color="primary"
                              onClick={() => {
                                setSelectedJobForSidebar(job);
                                setSidebarOpen(true);
                              }}
                            >
                              <VisibilityIcon />
                            </IconButton>
                          </Tooltip>
                        </>
                      )}
                      
                      {/* Validation Actions */}
                      {job.status === 'COMPLETED' && !job.validation_enabled && (
                        <Tooltip title="번역 검증 시작">
                          <IconButton 
                            color="info"
                            onClick={() => handleTriggerValidation(job.id)}
                          >
                            <FactCheckIcon />
                          </IconButton>
                        </Tooltip>
                      )}
                      {job.validation_status === 'COMPLETED' && (
                        <Tooltip title="검증 보고서 다운로드">
                          <IconButton 
                            color="info"
                            onClick={() => handleDownloadValidationReport(job.id)}
                          >
                            <AssessmentIcon />
                          </IconButton>
                        </Tooltip>
                      )}
                      
                      {/* Post-Edit Actions */}
                      {job.validation_status === 'COMPLETED' && !job.post_edit_enabled && (
                        <Tooltip title="자동 수정 시작">
                          <IconButton 
                            color="success"
                            onClick={() => handleTriggerPostEdit(job.id)}
                          >
                            <EditIcon />
                          </IconButton>
                        </Tooltip>
                      )}
                      {job.post_edit_status === 'COMPLETED' && (
                        <Tooltip title="수정 로그 다운로드">
                          <IconButton 
                            color="success"
                            onClick={() => handleDownloadPostEditLog(job.id)}
                          >
                            <DescriptionIcon />
                          </IconButton>
                        </Tooltip>
                      )}
                      {devMode && (job.status === 'COMPLETED' || job.status === 'FAILED') && (
                        <>
                          <Tooltip title="프롬프트 로그 다운로드">
                            <IconButton 
                              size="small" 
                              onClick={() => handleDownload(`${API_URL}/api/v1/jobs/${job.id}/logs/prompts`, `prompts_job_${job.id}_${job.filename.split('.')[0]}.txt`)}
                            >
                              <ChatIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="컨텍스트 로그 다운로드">
                            <IconButton 
                              size="small" 
                              onClick={() => handleDownload(`${API_URL}/api/v1/jobs/${job.id}/logs/context`, `context_job_${job.id}_${job.filename.split('.')[0]}.txt`)}
                            >
                              <DescriptionIcon />
                            </IconButton>
                          </Tooltip>
                        </>
                      )}
                      <Tooltip title="작업 삭제">
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
      ) : (
        <Paper sx={{ p: 4, textAlign: 'center', backgroundColor: 'rgba(255, 255, 255, 0.05)' }}>
          <AutoStoriesIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" component="p">
            아직 번역한 작업이 없네요.
          </Typography>
          <Typography color="text.secondary">
            첫 번째 소설을 번역해보세요!
          </Typography>
        </Paper>
      )}

      {/* Translation Sidebar */}
      {selectedJobForSidebar && (
        <TranslationSidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          jobId={selectedJobForSidebar.id.toString()}
          jobStatus={selectedJobForSidebar.status}
          validationStatus={selectedJobForSidebar.validation_status || undefined}
          postEditStatus={selectedJobForSidebar.post_edit_status || undefined}
          validationProgress={selectedJobForSidebar.validation_progress}
          onRefresh={pollJobStatus}
        />
      )}

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
            href="https://forms.gle/st93J7NT2PLcxgaj9"
            target="_blank"
            rel="noopener noreferrer"
          >
            Contact Us
          </Button>
        </Box>
        <Box mt={2}>
          <Link href="/privacy" color="text.secondary" variant="body2">
            개인정보처리방침
          </Link>
        </Box>
      </Box>
    </Container>
  );
}