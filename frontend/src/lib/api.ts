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

// Helper function to create auth headers
export function createAuthHeaders(token?: string) {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

// Export types from the generated API for convenience
export type Job = paths['/api/v1/jobs']['get']['responses']['200']['content']['application/json'][0];
export type JobCreate = paths['/api/v1/jobs']['post']['requestBody']['content']['multipart/form-data'];
export type Post = paths['/api/v1/community/posts/{post_id}']['get']['responses']['200']['content']['application/json'];
export type PostList = paths['/api/v1/community/posts']['get']['responses']['200']['content']['application/json'][0];
export type Comment = paths['/api/v1/community/posts/{post_id}/comments']['post']['responses']['201']['content']['application/json'];
export type PostCategory = paths['/api/v1/community/categories']['get']['responses']['200']['content']['application/json'][0];
export type CategoryOverview = paths['/api/v1/community/categories/overview']['get']['responses']['200']['content']['application/json'][0];
export type Announcement = paths['/api/v1/community/announcements']['get']['responses']['200']['content']['application/json'][0];
export type AnnouncementCreate = paths['/api/v1/community/announcements']['post']['requestBody']['content']['application/json'];
export type CurrentUser = paths['/api/v1/users/me']['get']['responses']['200']['content']['application/json'];
export type ValidationResponse = paths['/api/v1/validate/{job_id}']['post']['responses']['200']['content']['application/json'];
export type PostEditResponse = paths['/api/v1/post-edit/{job_id}']['post']['responses']['200']['content']['application/json'];

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
  
  // Analysis (placeholder; see backend /api/v1/analysis/* endpoints)
  // async getAnalysis(jobId: number) {
  //   return api.POST('/api/v1/analysis/glossary', { body: { job_id: jobId } });
  // },
  
  // Validation
  async validateTranslation(jobId: number, options?: { 
    quick?: boolean; 
    sample_rate?: number 
  }) {
    return api.POST('/api/v1/validate/{job_id}', {
      params: { path: { job_id: jobId } },
      body: {
        quick_validation: options?.quick ?? false,
        validation_sample_rate: options?.sample_rate ?? 1.0
      }
    });
  },
  
  // Post-editing
  async postEditTranslation(
    jobId: number,
    body?: Partial<paths['/api/v1/post-edit/{job_id}']['post']['requestBody']['content']['application/json']>
  ) {
    return api.POST('/api/v1/post-edit/{job_id}', {
      params: { path: { job_id: jobId } },
      body: {
        default_select_all: true,
        ...(body as any),
      },
    });
  },
  
  // Community
  async getPosts(params: {
    category: string;
    search?: string;
    skip?: number;
    limit?: number;
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

  async getPost(postId: number, token?: string) {
    return api.GET('/api/v1/community/posts/{post_id}', {
      params: { path: { post_id: postId } },
      headers: createAuthHeaders(token)
    });
  },

  async getCategories() {
    return api.GET('/api/v1/community/categories');
  },

  async getCategoriesOverview(token?: string) {
    return api.GET('/api/v1/community/categories/overview', {
      headers: createAuthHeaders(token)
    });
  },

  async getComments(postId: number, token?: string) {
    return api.GET('/api/v1/community/posts/{post_id}/comments', {
      params: { path: { post_id: postId } },
      headers: createAuthHeaders(token)
    });
  },

  async createComment(postId: number, data: any, token?: string) {
    return api.POST('/api/v1/community/posts/{post_id}/comments', {
      params: { path: { post_id: postId } },
      body: data,
      headers: createAuthHeaders(token)
    });
  },

  async incrementPostView(postId: number, token?: string) {
    return api.POST('/api/v1/community/posts/{post_id}/view', {
      params: { path: { post_id: postId } },
      headers: createAuthHeaders(token)
    });
  },

  // Announcement endpoints
  async getAnnouncements(params?: { active_only?: boolean; limit?: number }) {
    return api.GET('/api/v1/community/announcements', {
      params: { query: params || {} }
    });
  },

  // User
  async getCurrentUser(token?: string) {
    return api.GET('/api/v1/users/me', {
      headers: createAuthHeaders(token)
    });
  },

  async createAnnouncement(data: any) {
    return api.POST('/api/v1/community/announcements', {
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
