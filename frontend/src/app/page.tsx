"use client";

import { useState, useEffect, FormEvent } from 'react';

// 작업(Job) 데이터의 타입을 정의합니다.
interface Job {
  id: number;
  filename: string;
  status: string;
  created_at: string;
  completed_at: string | null;
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
      <div className="z-10 w-full max-w-5xl items-center justify-between font-mono text-sm lg:flex">
        <h1 className="text-4xl font-bold text-gray-800 mb-8 text-center w-full">
          Context-Aware Novel Translator
        </h1>
      </div>

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
      </div>

      <div className="w-full max-w-2xl p-8 bg-white rounded-lg shadow-md">
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

      <div className="mt-12 w-full max-w-4xl">
        <h2 className="text-2xl font-semibold text-gray-700 mb-4">Translation Jobs</h2>
        <div className="bg-white shadow-md rounded-lg overflow-hidden">
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
    </main>
  );
}