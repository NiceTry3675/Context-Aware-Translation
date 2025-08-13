import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';
import { getCachedClerkToken } from '../utils/authToken';
import { Job } from '../types/job';

interface UseTranslationJobsOptions {
  apiUrl: string;
}

export function useTranslationJobs({ apiUrl }: UseTranslationJobsOptions) {
  const { getToken, isSignedIn, isLoaded } = useAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load jobs from server on mount
  useEffect(() => {
    const loadJobs = async () => {
      if (!isLoaded) return;
      if (!isSignedIn) {
        setJobs([]);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);
      
      try {
        const token = await getCachedClerkToken(getToken);
        if (!token) {
          throw new Error("Failed to get authentication token");
        }

        const response = await fetch(`${apiUrl}/api/v1/jobs`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!response.ok) {
          throw new Error(`Failed to fetch jobs: ${response.status}`);
        }
        
        const fetchedJobs: Job[] = await response.json();
        setJobs(fetchedJobs);
        
        // Migrate from localStorage if needed
        const storedJobIdsString = localStorage.getItem('jobIds');
        if (storedJobIdsString) {
          console.log('Migrating from localStorage to server-based storage');
          localStorage.removeItem('jobIds');
        }
      } catch (err) {
        console.error("Failed to load jobs from server:", err);
        setError("Failed to load jobs");
      } finally {
        setLoading(false);
      }
    };
    
    loadJobs();
  }, [apiUrl, getToken, isSignedIn, isLoaded]);

  // Poll for job status updates without Clerk token (public endpoint per job)
  const pollJobStatus = useCallback(async () => {
    if (!isSignedIn) return;
    const processingJobs = jobs.filter(job =>
      ['PROCESSING', 'PENDING'].includes(job.status) ||
      job.validation_status === 'IN_PROGRESS' ||
      job.post_edit_status === 'IN_PROGRESS'
    );
    if (processingJobs.length === 0) return;

    try {
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
    } catch (err) {
      console.error('Failed to poll job status:', err);
    }
  }, [jobs, apiUrl, isSignedIn]);

  // Set up polling interval (lightweight, no token)
  useEffect(() => {
    const interval = setInterval(pollJobStatus, 3000);
    return () => clearInterval(interval);
  }, [pollJobStatus]);

  // Add a new job
  const addJob = useCallback((newJob: Job) => {
    setJobs(prevJobs => [newJob, ...prevJobs]);
  }, []);

  // Delete a job
  const deleteJob = useCallback((jobId: number) => {
    setJobs(prevJobs => prevJobs.filter(job => job.id !== jobId));
  }, []);

  // Refresh all jobs
  const refreshJobs = useCallback(async () => {
    if (!isSignedIn) return;
    
    try {
      const token = await getCachedClerkToken(getToken);
      if (!token) {
        throw new Error("Failed to get authentication token");
      }

      const response = await fetch(`${apiUrl}/api/v1/jobs`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch jobs: ${response.status}`);
      }
      
      const fetchedJobs: Job[] = await response.json();
      setJobs(fetchedJobs);
    } catch (err) {
      console.error("Failed to refresh jobs:", err);
      setError("Failed to refresh jobs");
    }
  }, [apiUrl, getToken, isSignedIn]);

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