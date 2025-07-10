"use client";

import { useState, useEffect, FormEvent } from 'react';

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

export default function Home() {
  // 상태 관리
  const [apiKey, setApiKey] = useState<string>('');
  const [file, setFile] = useState<File | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  // 백엔드 API의 기본 URL
  const API_URL = "http://localhost:8000";

  // 컴포넌트가 처음 마운트될 때 localStorage에서 API 키를 불러옵니다.
  useEffect(() => {
    const storedApiKey = localStorage.getItem('geminiApiKey');
    if (storedApiKey) {
      setApiKey(storedApiKey);
    }
  }, []);

  // apiKey 상태가 변경될 때마다 localStorage에 저장합니다.
  useEffect(() => {
    if (apiKey) {
      localStorage.setItem('geminiApiKey', apiKey);
    }
  }, [apiKey]);

  // 진행 중인 작업의 상태를 주기적으로 가져오는 함수
  const pollJobStatus = async () => {
    if (!Array.isArray(jobs) || jobs.length === 0) return;
  
    const processingJobs = jobs.filter(job => job.status === 'PROCESSING' || job.status === 'PENDING');
    if (processingJobs.length === 0) return;

    const updatedJobs = await Promise.all(
      processingJobs.map(async (job) => {
        try {
          const response = await fetch(`${API_URL}/status/${job.id}`);
          if (!response.ok) return job;
          return response.json();
        } catch (e) {
          return job;
        }
      })
    );

    setJobs(currentJobs =>
      currentJobs.map(job => updatedJobs.find(updated => updated.id === job.id) || job)
    );
  };

  useEffect(() => {
    const interval = setInterval(pollJobStatus, 3000);
    return () => clearInterval(interval);
  }, [jobs]);

  // 파일 업로드 처리 함수
  const handleUpload = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a file to upload.");
      return;
    }
    if (!apiKey) {
      setError("Please enter your Gemini API Key.");
      return;
    }

    setUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("api_key", apiKey); // API 키를 함께 전송

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
      setJobs([newJob, ...jobs]);
      setFile(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
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
        <div className="mb-6">
            <label htmlFor="api-key" className="block mb-2 text-sm font-medium text-gray-700">
              Your Gemini API Key
            </label>
            <input
              type="password"
              id="api-key"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Enter your API key here"
              className="block w-full p-2 text-gray-900 border border-gray-300 rounded-lg bg-gray-50 text-sm focus:ring-blue-500 focus:border-blue-500"
            />
        </div>
        <form onSubmit={handleUpload}>
          <div className="mb-6">
            <label htmlFor="file" className="block mb-2 text-sm font-medium text-gray-700">
              Upload your novel (.txt, .epub, .docx)
            </label>
            <input
              type="file"
              id="file"
              onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
          </div>
          <button
            type="submit"
            disabled={!file || uploading || !apiKey}
            className="w-full px-4 py-2 text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {uploading ? 'Uploading...' : 'Translate'}
          </button>
        </form>
        {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      </div>

      {/* Jobs Table Section */}
      <div className="mt-12 w-full max-w-4xl">
        <h2 className="text-2xl font-semibold text-gray-700 mb-4 text-center">Translation Jobs</h2>
        <div className="bg-white shadow-md rounded-lg">
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
                    {job.status === 'COMPLETED' && (
                      <a
                        href={`${API_URL}/download/${job.id}`}
                        download
                        className="text-indigo-600 hover:text-indigo-900"
                      >
                        Download
                      </a>
                    )}
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
