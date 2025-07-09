# Web Service Architecture Plan

This document outlines the technical architecture for the AI Novel Translator web service.

## 1. Guiding Principles

- **Speed of Development:** Prioritize tools and services that allow for rapid prototyping and iteration.
- **Focus on Core Logic:** Offload common web development complexities (like user authentication) to specialized services to focus on the core translation engine.
- **Scalability:** Choose a stack that can start small but scale as the user base grows.

## 2. Technology Stack

| Component | Technology/Service | Rationale |
| :--- | :--- | :--- |
| **Frontend** | **HTML, CSS, JavaScript + Bootstrap** | Fast to develop, beginner-friendly, and easy to create a professional-looking UI without the complexity of a full-blown JS framework. |
| **Backend** | **FastAPI (Python)** | High performance, easy to learn, and allows for the reuse of the existing Python-based translation logic. |
| **Authentication**| **Clerk.com** | Drastically speeds up development by providing a secure, feature-rich, and easy-to-integrate user management solution out of the box. |
| **Database** | **SQLite (Initial) -> PostgreSQL (Production)** | Start with SQLite for simplicity and zero configuration during development. Migrate to the more powerful and robust PostgreSQL for the production environment. |

## 3. System Architecture Flow

1.  **User Interaction (Frontend):**
    - A user visits the web application (built with Bootstrap).
    - The user signs up or logs in using the embedded **Clerk.com** UI components.
    - Once authenticated, the user uploads a novel file and initiates the translation process through the UI.

2.  **Authentication & API Request:**
    - Clerk provides the frontend with a secure JSON Web Token (JWT).
    - The frontend makes a request to the backend API (e.g., `/translate`), including the JWT in the authorization header.

3.  **Backend Processing:**
    - The **FastAPI** backend receives the request.
    - It uses Clerk's library to verify the JWT, ensuring the request is from an authenticated user.
    *   If valid, it proceeds with the core logic:
        *   Saves the uploaded file.
        *   Initiates the translation job (using our existing translation engine).
        *   Stores project details and status in the database.
    - It immediately returns a job ID to the frontend so the UI doesn't have to wait.

4.  **Database Management:**
    - The backend uses **SQLite** (during development) or **PostgreSQL** (in production) to manage all persistent data, such as user information (linked via Clerk user ID), translation projects, glossaries, and job statuses.

5.  **Status Updates & Results:**
    - The frontend can periodically poll a status endpoint on the backend (e.g., `/status/{job_id}`) to check the translation progress.
    - Once the job is complete, the frontend can retrieve the translated file from a download endpoint.

This architecture provides a solid foundation for building a secure, scalable, and feature-rich web service while maintaining a high development velocity.
