import { useState, useEffect, useCallback } from 'react';
import { Job } from '../types/job';

interface UseTranslationJobsOptions {
  apiUrl: string;
  pollInterval?: number;
}

export function useTranslationJobs({ apiUrl, pollInterval = 3000 }: UseTranslationJobsOptions) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load jobs from localStorage on mount
  useEffect(() => {
    const loadJobs = async () => {
      setLoading(true);
      setError(null);
      
      const storedJobIdsString = localStorage.getItem('jobIds');
      if (!storedJobIdsString) {
        setLoading(false);
        return;
      }
      
      const storedJobIds = JSON.parse(storedJobIdsString);
      if (!Array.isArray(storedJobIds) || storedJobIds.length === 0) {
        setLoading(false);
        return;
      }

      const uniqueJobIds = [...new Set(storedJobIds)];

      try {
        const fetchedJobs: Job[] = await Promise.all(
          uniqueJobIds.map(async (id: number) => {
            const response = await fetch(`${apiUrl}/api/v1/jobs/${id}`);
            return response.ok ? response.json() : null;
          })
        );
        
        const validJobs = fetchedJobs
          .filter((job): job is Job => job !== null)
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        
        setJobs(validJobs);
      } catch (err) {
        console.error("Failed to load jobs from storage:", err);
        setError("Failed to load saved jobs");
        localStorage.removeItem('jobIds');
      } finally {
        setLoading(false);
      }
    };
    
    loadJobs();
  }, [apiUrl]);

  // Poll for job status updates
  const pollJobStatus = useCallback(async () => {
    const processingJobs = jobs.filter(job => ['PROCESSING', 'PENDING'].includes(job.status));
    if (processingJobs.length === 0) return;

    const updatedJobs = await Promise.all(
      processingJobs.map(async (job) => {
        try {
          const response = await fetch(`${apiUrl}/api/v1/jobs/${job.id}`);
          return response.ok ? response.json() : job;
        } catch {
          return job;
        }
      })
    );
    
    setJobs(currentJobs =>
      currentJobs.map(job => updatedJobs.find(updated => updated.id === job.id) || job)
    );
  }, [jobs, apiUrl]);

  // Set up polling interval
  useEffect(() => {
    const interval = setInterval(pollJobStatus, pollInterval);
    return () => clearInterval(interval);
  }, [pollJobStatus, pollInterval]);

  // Add a new job
  const addJob = useCallback((newJob: Job) => {
    setJobs(prevJobs => [newJob, ...prevJobs]);
    const storedJobIds = JSON.parse(localStorage.getItem('jobIds') || '[]');
    localStorage.setItem('jobIds', JSON.stringify([newJob.id, ...storedJobIds]));
  }, []);

  // Delete a job
  const deleteJob = useCallback((jobId: number) => {
    setJobs(prevJobs => prevJobs.filter(job => job.id !== jobId));
    const storedJobIds = JSON.parse(localStorage.getItem('jobIds') || '[]');
    localStorage.setItem('jobIds', JSON.stringify(storedJobIds.filter((id: number) => id !== jobId)));
  }, []);

  // Refresh all jobs
  const refreshJobs = useCallback(async () => {
    await pollJobStatus();
  }, [pollJobStatus]);

  return {
    jobs,
    loading,
    error,
    addJob,
    deleteJob,
    refreshJobs,
    setError
  };
}