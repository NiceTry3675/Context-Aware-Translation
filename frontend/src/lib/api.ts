/**
 * Type-safe API client using openapi-fetch.
 * 
 * This client is generated from the backend's OpenAPI schema,
 * ensuring all API calls are properly typed.
 */

import createClient from 'openapi-fetch';
import type { paths } from '@/types/api';

// Create the API client with proper base URL
export const api = createClient<paths>({
  baseUrl: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Helper function to add auth headers
export function setAuthToken(token: string) {
  api.use({
    onRequest({ request }) {
      request.headers.set('Authorization', `Bearer ${token}`);
      return request;
    },
  });
}

// Export types from the generated API for convenience
export type Job = paths['/api/v1/jobs']['get']['responses']['200']['content']['application/json'][0];
export type JobCreate = paths['/api/v1/jobs']['post']['requestBody']['content']['multipart/form-data'];
export type Post = paths['/api/v1/community/posts']['get']['responses']['200']['content']['application/json'][0];
export type Comment = paths['/api/v1/community/posts/{post_id}/comments']['get']['responses']['200']['content']['application/json'][0];
export type ValidationResponse = paths['/api/v1/jobs/{job_id}/validation']['put']['responses']['200']['content']['application/json'];
export type PostEditResponse = paths['/api/v1/jobs/{job_id}/post-edit']['put']['responses']['200']['content']['application/json'];

// Type-safe API endpoints
export const endpoints = {
  // Jobs
  async getJobs() {
    return api.GET('/api/v1/jobs');
  },
  
  async getJob(id: number) {
    return api.GET('/api/v1/jobs/{job_id}', { 
      params: { path: { job_id: id } } 
    });
  },
  
  async createJob(data: JobCreate) {
    return api.POST('/api/v1/jobs', { 
      body: data 
    });
  },
  
  async deleteJob(id: number) {
    return api.DELETE('/api/v1/jobs/{job_id}', { 
      params: { path: { job_id: id } } 
    });
  },
  
  // Analysis
  async getAnalysis(jobId: number) {
    return api.GET('/api/v1/jobs/{job_id}/glossary', { 
      params: { path: { job_id: jobId } } 
    });
  },
  
  // Validation
  async validateTranslation(jobId: number, options?: { 
    quick?: boolean; 
    sample_rate?: number 
  }) {
    return api.PUT('/api/v1/jobs/{job_id}/validation', {
      params: { path: { job_id: jobId } },
      body: {
        quick_validation: options?.quick ?? false,
        validation_sample_rate: options?.sample_rate ?? 1.0
      }
    });
  },
  
  // Post-editing
  async postEditTranslation(jobId: number) {
    return api.PUT('/api/v1/jobs/{job_id}/post-edit', {
      params: { path: { job_id: jobId } },
      body: {}
    });
  },
  
  // Community
  async getPosts(params?: { 
    category?: string; 
    search?: string; 
    page?: number; 
    page_size?: number 
  }) {
    return api.GET('/api/v1/community/posts', { 
      params: { query: params } 
    });
  },
  
  async createPost(data: any) {
    return api.POST('/api/v1/community/posts', { 
      body: data 
    });
  },
  
  async getComments(postId: number) {
    return api.GET('/api/v1/community/posts/{post_id}/comments', { 
      params: { path: { post_id: postId } } 
    });
  },
  
  async createComment(postId: number, data: any) {
    return api.POST('/api/v1/community/posts/{post_id}/comments', {
      params: { path: { post_id: postId } },
      body: data
    });
  },
  
  // Schemas
  async getCoreSchemas() {
    return api.GET('/api/v1/schemas/core');
  },
  
  async getBackendSchemas() {
    return api.GET('/api/v1/schemas/backend');
  },
};