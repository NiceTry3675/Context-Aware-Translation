# 🚀 Development Plan: AI Novel Translator Web Service

This document outlines the development roadmap for transforming the current script into a commercial-grade, web-based literary translation service.

---

## 🎯 1. Core Mission

To develop and launch a commercial web service that provides professional-grade, context-aware literary translation, making it the go-to platform for authors, publishers, and translation agencies who require high-fidelity, nuanced localization of creative works.

---

## 🌟 2. Short-Term Goals

*These are immediate priorities focused on optimizing the core logic and preparing for web deployment.*

| Priority | Feature/Task | Description | Status |
| :---: | :--- | :--- | :---: |
| **High** | **Contextual Glossary Injection** | Modify the prompt building process to only include glossary terms relevant to the current source segment. This will optimize prompt size, reduce token consumption, and potentially improve contextual focus. | solve! |
| **High** | **Web Service Architecture Plan** | Design the full-stack architecture for the web service. This includes selecting the tech stack (e.g., FastAPI/Django for backend, React/Vue for frontend), database schema for users and projects, and planning for user authentication and file management. | solve! |
| Medium | **Expanded File Format Support** | Implement parsers for various document types beyond `.txt`. Prioritize common formats like `.docx`, `.epub`, and `.md`. The system should be able to extract clean text from these files for translation. | solve! |
| Medium | **Initial Backend Scaffolding** | Develop the basic backend API endpoints required for the service (e.g., user registration/login, file upload, start translation job, check job status). | 로그인 제외 구현완료 |

---

## 🗺️ 3. Mid-Term Goals

*These goals focus on building the user-facing application and adding deep customization features.*

| Priority | Feature/Task | Description | Status |
| :---: | :--- | :--- | :---: |
| **High** | **Full Customization UI** | Develop a web interface where users can manage all aspects of their translation projects. This includes: <br>- Uploading and managing source files. <br>- Editing the auto-generated glossary and character styles. <br>- Defining the core narrative style manually. <br>- Adjusting model parameters (e.g., temperature). | 📝 To Do |
| **High** | **Frontend Development** | Build the complete frontend application based on the architecture plan. This includes the dashboard, project management views, and the translation editor interface. | 📝 To Do |
| Medium | **Interactive Translation Editor** | Create a side-by-side view where users can review the translated segments, make corrections, and save them. The corrections should update the context for future segments. | 📝 To Do |
| Medium | **User & Subscription Management** | Implement a robust user management system, including different subscription tiers (e.g., free trial, pro, enterprise) with varying feature access and usage quotas. | 📝 To Do |

---

## 🔭 4. Long-Term & Visionary Goals

*Ambitious ideas to establish the service as a market leader.*

- **Collaborative Translation Platform:** Allow multiple users to collaborate on a single translation project, with roles like translator, editor, and proofreader.
- **Automated Quality Scoring:** Develop a system that automatically scores the quality and consistency of a translation, flagging potential issues for human review.
- **Integration with Publishing Platforms:** Create APIs and plugins that allow seamless integration with platforms like Amazon KDP, allowing authors to translate and publish their work directly from the service.
- **Fine-tuning Custom Models:** For enterprise clients, offer the ability to fine-tune a dedicated model on their existing translated works to create a unique "author" or "brand" voice.

---