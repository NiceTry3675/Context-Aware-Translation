"use client";

import { useState, useEffect, FormEvent, useCallback } from 'react';

// 작업(Job) 데이터의 타입을 정의합니다.
interface Job {
  id: number;
  filename: string;
  status: string;
  progress: number;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
}

// 스타일 데이터 타입을 정의합니다.
interface StyleData {
  narrative_perspective: string;
  primary_speech_level: string;
  tone: string;
}

export default function Home() {
  // 상태 관리
  const [apiKey, setApiKey] = useState<string>('');
  const [file, setFile] = useState<File | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string>("gemini-2.5-flash-lite-preview-06-17");

  // 새로운 상태 추가
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [analysisError, setAnalysisError] = useState<string>('');
  const [styleData, setStyleData] = useState<StyleData | null>(null);
  const [showStyleForm, setShowStyleForm] = useState<boolean>(false); // 팝업 대신 인라인 폼 표시 여부
  const [devMode, setDevMode] = useState<boolean>(false); // 개발자 모드 상태

  const modelOptions = [
    {
      value: "gemini-2.5-flash-lite-preview-06-17",
      label: "Flash Lite (추천)",
      description: "가장 빠르고 경제적입니다. 전체적인 흐름을 빠르게 훑어보거나 초벌 번역에 적합합니다."
    },
    {
      value: "gemini-2.5-flash",
      label: "Flash",
      description: "속도와 품질의 균형을 맞춘 모델입니다. 대부분의 소설 번역에서 안정적인 결과물을 제공합니다."
    },
    {
      value: "gemini-2.5-pro",
      label: "Pro",
      description: "가장 강력한 성능을 지녔지만, 비용과 속도 부담이 있습니다. 문학 작품의 섬세한 뉘앙스까지 살리는 최고 품질을 원할 때 사용하세요."
    },
  ];

  // 백엔드 API의 기본 URL
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // 컴포넌트가 처음 마운트될 때 localStorage에서 API 키와 개발자 모드를 불러옵니다.
  useEffect(() => {
    const storedApiKey = localStorage.getItem('geminiApiKey');
    if (storedApiKey) {
      setApiKey(storedApiKey);
    }
    const isDevMode = localStorage.getItem('devMode') === 'true';
    setDevMode(isDevMode);
  }, []);

  // apiKey 상태가 변경될 때마다 localStorage에 저장합니다.
  useEffect(() => {
    if (apiKey) {
      localStorage.setItem('geminiApiKey', apiKey);
    }
  }, [apiKey]);

  // 페이지 로드 시 localStorage에서 작업 목록을 불러옵니다.
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
            if (response.ok) {
              return response.json();
            }
            // 서버에서 찾을 수 없는 작업은 목록에서 제거합니다.
            return null;
          })
        );

        const validJobs = fetchedJobs
          .filter((job): job is Job => job !== null)
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

        setJobs(validJobs);
      } catch (error) {
        console.error("Failed to load jobs from storage:", error);
        // 문제가 발생하면 저장된 ID를 지워 문제를 방지합니다.
        localStorage.removeItem('jobIds');
      }
    };
    loadJobs();
  }, []); // 빈 배열 의존성으로 마운트 시 한 번만 실행합니다.

  // 진행 중인 작업의 상태를 주기적으로 가져오는 함수
  const pollJobStatus = useCallback(async () => {
    if (!Array.isArray(jobs) || jobs.length === 0) return;
  
    const processingJobs = jobs.filter(job => job.status === 'PROCESSING' || job.status === 'PENDING');
    if (processingJobs.length === 0) return;

    const updatedJobs = await Promise.all(
      processingJobs.map(async (job) => {
        try {
          const response = await fetch(`${API_URL}/status/${job.id}`);
          if (!response.ok) return job;
          return response.json();
        } catch { // 변수 선언 자체를 생략
          return job;
        }
      })
    );

    setJobs(currentJobs =>
      currentJobs.map(job => updatedJobs.find(updated => updated.id === job.id) || job)
    );
  }, [jobs, API_URL]); // API_URL도 의존성에 추가

  useEffect(() => {
    const interval = setInterval(pollJobStatus, 3000);
    return () => clearInterval(interval);
  }, [pollJobStatus]); // 의존성 배열에 pollJobStatus 추가

  // 파일 선택 시 스타일 분석을 시작하는 함수
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
      const response = await fetch(`${API_URL}/api/v1/analyze-style`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '스타일 분석에 실패했습니다.');
      }

      const analyzedStyle = await response.json();
      setStyleData(analyzedStyle);
      setShowStyleForm(true); // 분석 성공 시 인라인 폼 표시

    } catch (err) {
      if (err instanceof Error) {
        setAnalysisError(err.message);
      } else {
        setAnalysisError("알 수 없는 오류가 발생했습니다.");
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  // 최종 번역을 시작하는 함수 (기존 handleUpload 로직 재활용)
  const handleStartTranslation = async () => {
    if (!file || !styleData) {
      setError("번역을 시작할 파일과 스타일 정보가 필요합니다.");
      return;
    }

    setUploading(true);
    setError(null);
    setShowStyleForm(false); // 번역 시작 시 폼 닫기

    const formData = new FormData();
    formData.append("file", file);
    formData.append("api_key", apiKey);
    formData.append("model_name", selectedModel);
    formData.append("style_data", JSON.stringify(styleData));

    try {
      const response = await fetch(`${API_URL}/uploadfile/`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "File upload failed");
      }

      const newJob: Job = await response.json();
      setJobs(prevJobs => [newJob, ...prevJobs]);
      
      const storedJobIds = JSON.parse(localStorage.getItem('jobIds') || '[]');
      const newJobIds = [newJob.id, ...storedJobIds];
      localStorage.setItem('jobIds', JSON.stringify(newJobIds));

      setFile(null); // 작업 제출 후 파일 선택 초기화

    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unknown error occurred.");
      }
    } finally {
      setUploading(false);
    }
  };

  // 스타일 수정을 취소하는 함수
  const handleCancelStyleEdit = () => {
    setShowStyleForm(false);
    setFile(null);
    setStyleData(null);
    // 파일 입력 필드도 초기화
    const fileInput = document.getElementById('file') as HTMLInputElement;
    if (fileInput) {
      fileInput.value = '';
    }
  };

  // 작업 목록에서 특정 작업을 제거하는 함수
  const handleDelete = (jobId: number) => {
    // UI에서 즉시 제거
    setJobs(prevJobs => prevJobs.filter(job => job.id !== jobId));

    // localStorage에서 ID 제거
    const storedJobIds = JSON.parse(localStorage.getItem('jobIds') || '[]');
    const newJobIds = storedJobIds.filter((id: number) => id !== jobId);
    localStorage.setItem('jobIds', JSON.stringify(newJobIds));
  };

  return (
    <main className="flex min-h-screen flex-col items-center p-12 bg-gray-50">
      
      {/* Header Section */}
      <div className="text-center w-full max-w-4xl mb-16">
        <div className="flex justify-center items-center mb-2">
          <h1 className="text-5xl sm:text-6xl font-extrabold text-gray-800">
            냥번역
          </h1>
          <span className="ml-3 px-2 py-1 text-xs font-semibold text-white bg-gray-700 rounded-full">
            beta
          </span>
        </div>
        <p className="mt-2 text-base sm:text-lg text-gray-500 tracking-wider">
          <span className="font-bold text-blue-500">C</span>ontext-
          <span className="font-bold text-green-500">A</span>ware 
          <span className="font-bold text-red-500"> T</span>ranslator
        </p>
      </div>

      {/* Features Section */}
      <div className="w-full max-w-4xl text-center mb-16">
        <h2 className="text-3xl font-bold text-gray-800 mb-4">냥번역은 무엇이 다른가요?</h2>
        <p className="text-lg text-gray-600 max-w-3xl mx-auto">
          단순한 번역기를 넘어, 소설의 맛을 살리는 데 집중했습니다. 일반 생성형 AI 번역에서 발생하는 고질적인 문제들을 해결하여, 처음부터 끝까지 일관성 있는 고품질 번역을 경험할 수 있습니다.
        </p>
        <div className="mt-10 grid md:grid-cols-3 gap-8">
          <div className="p-6 bg-white rounded-lg shadow-lg">
            <div className="flex justify-center items-center mb-4 w-12 h-12 rounded-full bg-blue-100 mx-auto">
              <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 12h6m-6-4h6"></path></svg>
            </div>
            <h3 className="text-xl font-semibold text-gray-800 mb-2">문맥 유지</h3>
            <p className="text-gray-600">소설 전체의 분위기와 등장인물의 말투를 학습하여, 챕터가 넘어가도 번역 품질이 흔들리지 않습니다.</p>
          </div>
          <div className="p-6 bg-white rounded-lg shadow-lg">
            <div className="flex justify-center items-center mb-4 w-12 h-12 rounded-full bg-green-100 mx-auto">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2h1a2 2 0 002-2v-1a2 2 0 012-2h1.945M7.955 16.588l1.414-1.414M16.045 16.588l-1.414-1.414M12 21a9 9 0 110-18 9 9 0 010 18z"></path></svg>
            </div>
            <h3 className="text-xl font-semibold text-gray-800 mb-2">용어 일관성</h3>
            <p className="text-gray-600">고유명사나 특정 용어가 번역될 때마다 달라지는 문제를 해결했습니다. 중요한 단어는 항상 동일하게 번역됩니다.</p>
          </div>
          <div className="p-6 bg-white rounded-lg shadow-lg">
            <div className="flex justify-center items-center mb-4 w-12 h-12 rounded-full bg-red-100 mx-auto">
               <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>
            </div>
            <h3 className="text-xl font-semibold text-gray-800 mb-2">스타일 유지</h3>
            <p className="text-gray-600">작가 특유의 문체나 작품의 스타일을 학습하여, 원작의 느낌을 최대한 살린 번역을 제공합니다.</p>
          </div>
        </div>
      </div>

      {/* Input Section */}
      <div className="w-full max-w-2xl p-8 bg-white rounded-lg shadow-md mb-8">
        
        {/* Model Selection Section */}
        <div className="mb-8">
          <label className="block mb-3 text-lg font-bold text-gray-800">
            1. 번역 모델 선택
          </label>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {modelOptions.map(option => (
              <div
                key={option.value}
                onClick={() => setSelectedModel(option.value)}
                className={`p-4 border rounded-lg cursor-pointer transition-all duration-200 ${
                  selectedModel === option.value
                    ? 'border-blue-500 bg-blue-50 shadow-md'
                    : 'border-gray-300 bg-white hover:border-gray-400 hover:bg-gray-50'
                }`}
              >
                <h4 className="font-semibold text-gray-800">{option.label}</h4>
                <p className="text-xs text-gray-500 mt-1">{option.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* API Key & Upload Section */}
        <div className="mb-6">
            <label htmlFor="api-key" className="block mb-2 text-lg font-bold text-gray-800">
              2. Gemini API 키 입력
            </label>
            <input
              type="password"
              id="api-key"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="API 키를 여기에 입력하세요"
              className="block w-full p-3 text-gray-900 border border-gray-300 rounded-lg bg-gray-50 text-sm focus:ring-blue-500 focus:border-blue-500"
            />
        </div>
        
        <div className="mb-6">
            <label htmlFor="file" className="block mb-2 text-lg font-bold text-gray-800">
              3. 소설 파일 업로드
            </label>
            <input
              type="file"
              id="file"
              onChange={(e) => handleFileChange(e.target.files ? e.target.files[0] : null)}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-3 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              disabled={isAnalyzing || uploading}
            />
        </div>
        {isAnalyzing && (
          <div className="text-center text-blue-600">
            <p>파일을 분석하여 핵심 서사 스타일을 추출하고 있습니다...</p>
          </div>
        )}
        {analysisError && <p className="mt-4 text-sm text-red-600">{analysisError}</p>}
        {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      {analysisError && <p className="mt-4 text-sm text-red-600">{analysisError}</p>}
        {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

        {/* --- 인라인 스타일 수정 폼 --- */}
        <div className={`transition-all duration-500 ease-in-out overflow-hidden ${showStyleForm ? 'max-h-screen mt-8' : 'max-h-0'}`}>
          {styleData && (
            <div className="p-6 border-t-2 border-dashed border-gray-200">
              <h3 className="text-lg font-bold text-gray-900 mb-4">
                4. 핵심 서사 스타일 확인 및 수정
              </h3>
              <p className="text-sm text-gray-700 mb-6">AI가 분석한 소설의 핵심 스타일입니다. 번역의 일관성을 위해 이 스타일을 기준으로 사용합니다. 필요하다면 직접 수정할 수 있습니다.</p>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-800">서사 관점 (Narrative Perspective)</label>
                  <input 
                    type="text"
                    value={styleData.narrative_perspective}
                    onChange={(e) => setStyleData({...styleData, narrative_perspective: e.target.value})}
                    className="mt-1 block w-full p-3 border border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500 bg-white text-gray-900"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-800">주요 말투 (Primary Speech Level)</label>
                  <input 
                    type="text"
                    value={styleData.primary_speech_level}
                    onChange={(e) => setStyleData({...styleData, primary_speech_level: e.target.value})}
                    className="mt-1 block w-full p-3 border border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500 bg-white text-gray-900"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-800">글의 톤 (Tone)</label>
                  <input 
                    type="text"
                    value={styleData.tone}
                    onChange={(e) => setStyleData({...styleData, tone: e.target.value})}
                    className="mt-1 block w-full p-3 border border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500 bg-white text-gray-900"
                  />
                </div>
              </div>

              <div className="mt-8 flex justify-end space-x-4">
                <button 
                  onClick={handleCancelStyleEdit}
                  className="px-6 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors font-semibold"
                >
                  취소
                </button>
                <button 
                  onClick={handleStartTranslation}
                  disabled={uploading}
                  className="px-6 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 font-bold"
                >
                  {uploading ? '번역 요청 중...' : '이 스타일로 번역 시작'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Jobs Table Section */}
      <div className="mt-12 w-full max-w-4xl">
        <h2 className="text-2xl font-semibold text-gray-700 mb-4 text-center">Translation Jobs</h2>
        <div className="overflow-x-auto bg-white shadow-md rounded-lg">
          <table className="min-w-full leading-normal">
            <thead>
              <tr>
                <th className="px-5 py-3 border-b-2 border-gray-200 bg-gray-100 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Filename
                </th>
                <th className="px-5 py-3 border-b-2 border-gray-200 bg-gray-100 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-5 py-3 border-b-2 border-gray-200 bg-gray-100 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Submitted
                </th>
                <th className="px-5 py-3 border-b-2 border-gray-200 bg-gray-100 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id}>
                  <td className="px-5 py-4 border-b border-gray-200 bg-white text-sm">
                    <p className="text-gray-900 whitespace-no-wrap">{job.filename}</p>
                  </td>
                  <td className="px-5 py-4 border-b border-gray-200 bg-white text-sm">
                    {job.status === 'PROCESSING' && job.progress > 0 ? (
                      <div className="w-full bg-gray-200 rounded-full h-4">
                        <div
                          className="bg-blue-500 h-4 rounded-full text-xs font-medium text-blue-100 text-center p-0.5 leading-none"
                          style={{ width: `${job.progress}%` }}
                        >
                          {job.progress}%
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center">
                        <span
                          className={`relative inline-block px-3 py-1 font-semibold leading-tight ${
                            job.status === 'COMPLETED' ? 'text-green-900' :
                            job.status === 'FAILED' ? 'text-red-900' :
                            'text-yellow-900'
                          }`}
                        >
                          <span
                            aria-hidden
                            className={`absolute inset-0 ${
                              job.status === 'COMPLETED' ? 'bg-green-200' :
                              job.status === 'FAILED' ? 'bg-red-200' :
                              'bg-yellow-200'
                            } opacity-50 rounded-full`}
                          ></span>
                          <span className="relative">{job.status}</span>
                        </span>
                        {job.status === 'FAILED' && job.error_message && (
                          <div className="relative ml-2 group">
                            <svg className="w-5 h-5 text-gray-500 cursor-pointer" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                            </svg>
                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 p-3 text-sm text-white bg-gray-800 rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-normal">
                              {job.error_message}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </td>
                  <td className="px-5 py-4 border-b border-gray-200 bg-white text-sm">
                    <p className="text-gray-900 whitespace-no-wrap">
                      {new Date(job.created_at).toLocaleString()}
                    </p>
                  </td>
                  <td className="px-5 py-4 border-b border-gray-200 bg-white text-sm">
                    <div className="flex items-center space-x-4">
                      {job.status === 'COMPLETED' && (
                        <a
                          href={`${API_URL}/download/${job.id}`}
                          download
                          className="text-indigo-600 hover:text-indigo-900 font-semibold"
                        >
                          Download
                        </a>
                      )}
                      {devMode && (job.status === 'COMPLETED' || job.status === 'FAILED') && (
                        <>
                          <a href={`${API_URL}/download/logs/${job.id}/prompts`} download className="text-xs text-gray-500 hover:text-gray-700">Prompts</a>
                          <a href={`${API_URL}/download/logs/${job.id}/context`} download className="text-xs text-gray-500 hover:text-gray-700">Context</a>
                        </>
                      )}
                      <div className="relative group">
                        <button
                          onClick={() => handleDelete(job.id)}
                          className="text-gray-400 hover:text-red-600 transition-colors"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                        </button>
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 text-xs text-white bg-gray-800 rounded-md shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap">
                          Remove from list
                        </div>
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Footer/Sponsorship Section */}
      <footer className="w-full max-w-4xl mt-16 pt-8 border-t border-gray-200 text-center">
        <h3 className="text-xl font-semibold text-gray-700 mb-4">이 서비스가 마음에 드셨나요?</h3>
        <p className="text-gray-600 mb-6">
          여러분의 소중한 후원은 서비스 유지 및 기능 개선에 큰 힘이 됩니다.
        </p>
        <div className="flex justify-center items-center gap-4">
          <a 
            href="https://coff.ee/nicetry3675" 
            target="_blank" 
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center px-6 py-3 text-base font-medium text-gray-900 bg-white border border-gray-300 rounded-lg hover:bg-gray-100 focus:ring-4 focus:ring-gray-100"
          >
            {/* Placeholder for BMC Icon */}
            <span className="text-lg">☕</span>
            <span className="ml-2">Buy Me a Coffee</span>
          </a>
        </div>
      </footer>

    </main>
  );
}