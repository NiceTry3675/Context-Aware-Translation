# Vertex Provider Integration Design

## Overview

We want to expose Google Vertex AI as a peer provider to the existing Gemini (direct) and OpenRouter options without increasing setup friction for users. Only the Vertex-supported Gemini 2.5 variants (`gemini-2.5-flash-lite`, `gemini-2.5-flash`, `gemini-2.5-pro`) need to be selectable when Vertex is chosen. The cornerstone of the design is a single JSON file that a user can paste or upload, removing the need for environment-variable gymnastics while keeping the security posture identical to the current API-key flow.

## Requirements

### Functional
- Allow every flow that currently supports Gemini (analysis, translation, validation, post-edit, illustration) to opt into Vertex-backed Gemini models.
- Introduce a provider toggle (`gemini`, `vertex`, `openrouter`) that behaves consistently across frontend and backend entry points.
- Accept a single JSON document that contains Vertex project metadata and a Google service-account key. This document must be usable both in the browser (for user onboarding) and on the backend (for Celery tasks).
- Ship with a pre-defined Vertex model list that maps to the Gemini 2.5 variants exposed through Vertex AI (Flash Lite, Flash, Pro).

### Non-functional
- Preserve the zero-persistence policy for user-provided credentials: the JSON is supplied on every request, redacted in logs, and never written to disk or the database.
- Deliver low-effort onboarding: a new user should be able to switch to Vertex by copying JSON from Google Cloud console and pasting it into the UI.
- Provide clear validation errors when JSON is malformed, required fields are missing, or the Vertex project/model is misconfigured.

## User Onboarding Flow

1. In Google Cloud console, the user creates (or locates) a service account that has the `Vertex AI User` role.
2. The user downloads the service-account JSON key.
3. Optionally, the user wraps the downloaded JSON in a lightweight configuration file that also stores the target region and default model (see the schema below). Both wrapped and raw keys are accepted.
4. In the application UI, the user switches the provider toggle to **Vertex AI**. A multiline text field and upload helper appear.
5. The user either uploads the JSON file or pastes its contents. The UI validates the JSON immediately, highlighting missing fields.
6. After picking one of the three supported models, every subsequent request in the session (analysis, translation, etc.) includes the provider metadata and JSON payload.

## Single-File Configuration Specification

Two JSON shapes are supported to minimize friction:

1. **Wrapped configuration** (preferred because it encodes defaults explicitly)
   ```json
   {
     "project_id": "firm-mariner-470708-n9",
     "location": "us-central1",
     "default_model": "gemini-2.5-flash",
     "service_account": {
       "type": "service_account",
       "project_id": "firm-mariner-470708-n9",
       "private_key_id": "...",
       "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
       "client_email": "vertex-translator@firm-mariner-470708-n9.iam.gserviceaccount.com",
       "client_id": "...",
       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
       "token_uri": "https://oauth2.googleapis.com/token",
       "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
       "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/vertex-translator%40firm-mariner-470708-n9.iam.gserviceaccount.com"
     }
   }
   ```

2. **Raw Google key** – the unmodified service-account JSON exported from Google Cloud.

### Parsing rules
- When the payload contains a `service_account` object, treat that as the wrapped configuration and pull `project_id`, `location`, and (optionally) `default_model` from the wrapper.
- When the payload matches the raw Google key shape, derive the `project_id` from `project_id` in the key and default the location to `us-central1` unless the payload also includes a sibling `location` field.
- Reject JSON that cannot be parsed, or that is missing `project_id`, `location`, or the minimum service-account credential set (`client_email`, `private_key`, `token_uri`). Error responses explain which field is absent or invalid.
- When the wrapped configuration provides `default_model`, auto-select that model the first time the provider toggle is switched to Vertex.

### Internal representation
On the frontend we store the validated payload in `localStorage` exactly as provided. On the backend the parsed payload is normalized to:
```json
{
  "project_id": "firm-mariner-470708-n9",
  "location": "us-central1",
  "credentials": { "...": "..." }
}
```
This structure is cached per request and serialized into Celery tasks using standard JSON encoding.

## Frontend Design

### State management
- Expand the existing `useApiKey` (or equivalent) hook so it maintains a record like:
  ```ts
  type ProviderState = {
    provider: 'gemini' | 'vertex' | 'openrouter';
    credentials: {
      gemini?: { apiKey: string; model: string };
      vertex?: { configJson: string; model: string };
      openrouter?: { apiKey: string; model: string };
    };
  };
  ```
- Provider switching logic loads stored credentials/models when toggled and resets state when the JSON becomes invalid.
- Vertex model options are sourced from the same `geminiModelOptions` constant as direct Gemini, ensuring UI parity.

### UI adjustments
- Provider toggle gains a third entry labelled **Vertex AI** with a tooltip explaining the single-file JSON requirement.
- Credential input swaps to a multiline `TextField` + "Upload JSON" button when Vertex is active. The upload handler reads the file, updates the text field, and triggers validation.
- Validation feedback is surfaced inline with actionable copy (e.g., “`project_id` is required. Check that you copied the correct JSON.`”).
- Model selector remains unchanged, but when Vertex is active it displays the Vertex-specific resource names in tooltips for transparency.

### Network layer
- Every API helper (analysis, translation, validation, post-edit, illustration) appends two fields:
  - `api_provider`: one of `"gemini"`, `"vertex"`, or `"openrouter"`.
  - `provider_config`: the exact JSON string when the provider is Vertex; omitted for other providers.
- Multipart requests (file uploads) include `provider_config` as a standard text part and send an empty `api_key` to keep payload structure stable for the backend parser.

## Backend Design

### Provider normalization
- Extend the shared service base (e.g., `ServiceBase`) to accept `api_provider` and `provider_config` in helper methods responsible for creating model clients, validating keys, and orchestrating requests.
- Introduce a `ProviderContext` dataclass that stores the normalized payload:
  ```python
  @dataclass
  class ProviderContext:
      name: Literal['gemini', 'vertex', 'openrouter']
      project_id: str | None = None
      location: str | None = None
      credentials: dict[str, Any] | None = None
  ```
- Parsing logic accepts dicts or JSON strings, raising `HTTPException(status_code=422, detail=...)` with precise messages when validation fails.

### Model factory updates
- Update `ModelAPIFactory` so `create` and `validate_api_key` take a `ProviderContext` argument.
- For Vertex contexts, instantiate a `google.genai.Client` by calling `Credentials.from_service_account_info` on the normalized credentials and setting `vertex_ai=True`, `project`, and `location`.
- Reuse the existing `GeminiModel` abstraction by injecting the client instance instead of an API key. Add a lightweight `validate_with_client` method to confirm that the supplied credentials can fetch model metadata without generating content.
- Vertex model resource names are generated from the short model ID selected in the UI using the template `projects/{project}/locations/{location}/publishers/google/models/{modelId}`.

### API schema changes
- Update request models for analysis, translation job creation, validation triggers, post-edit, and illustration endpoints so they accept the optional fields `api_provider` and `provider_config`.
- Ensure Celery task payloads include the serialized `ProviderContext`. Worker-side bootstrap code reconstructs the context and rebuilds the appropriate client before executing business logic.

### Error handling & logging
- Wrap all Vertex client initialization failures and return descriptive `422` errors (e.g., permission errors, invalid private key format).
- When logging exceptions, redact private key contents by hashing or truncating after the first and last characters.
- Emit structured logs containing the provider name and selected model to simplify monitoring.

## Background Tasks
- Update Celery task signatures (`process_translation_task`, `process_validation_task`, `process_post_edit_task`, illustration tasks) so they accept `provider_context: dict[str, Any]`.
- Serialize the provider context using `json.dumps` before enqueueing tasks and parse it immediately upon task start to rebuild the context object.
- Ensure retries re-use the parsed context instead of reparsing strings repeatedly.

## Model Catalogue (Fixed Set)

| Provider    | UI Label           | Backend Model Identifier                                                     |
|-------------|--------------------|------------------------------------------------------------------------------|
| Gemini API  | Flash Lite (추천)  | `gemini-2.5-flash-lite`                                                     |
| Gemini API  | Flash              | `gemini-2.5-flash`                                                           |
| Gemini API  | Pro                | `gemini-2.5-pro`                                                             |
| Vertex AI   | Flash Lite (추천)  | `projects/{project}/locations/{location}/publishers/google/models/gemini-2.5-flash-lite` |
| Vertex AI   | Flash              | `projects/{project}/locations/{location}/publishers/google/models/gemini-2.5-flash`     |
| Vertex AI   | Pro                | `projects/{project}/locations/{location}/publishers/google/models/gemini-2.5-pro`       |
| OpenRouter  | (existing options) | (unchanged)                                                                |

Helper utilities generate Vertex resource names automatically, ensuring the UI only deals with short model IDs.

## Security Considerations
- Treat the JSON payload like an API key: never store it server-side and clear it from memory after request handling completes.
- Use per-request caching inside backend services to avoid repeated JSON parsing while keeping the payload ephemeral.
- Document least-privilege recommendations (service account with `Vertex AI User`) and note that rotating the key simply requires pasting a new JSON file.

## Testing Strategy
- **Unit tests**: cover provider parsing, normalization, and model factory logic (Vertex success and failure modes).
- **Integration tests**: simulate API requests with multipart payloads to verify `provider_config` parsing, and ensure Celery tasks rebuild the context correctly.
- **Manual smoke tests**: walkthrough of the full UI flow using a staging Vertex project, verifying translation + validation + illustration flows operate with Vertex credentials.
- **Security checks**: confirm logs contain no private key material and that invalid JSON returns informative `422` errors.

## Implementation Roadmap

1. **Configuration parsing foundation**
   - Implement `ProviderContext` and shared parsing helpers.
   - Add unit tests covering wrapped and raw JSON inputs, plus error cases.
2. **Backend plumbing**
   - Update request schemas, service base, and model factory.
   - Introduce Vertex-aware Celery task serialization.
3. **Frontend UX**
   - Extend provider toggle, credential form, and local storage handling.
   - Implement JSON upload + validation UI with copy that links to GCP docs.
4. **End-to-end validation**
   - Execute integration tests, run manual smoke tests, and document the onboarding steps in the README.
5. **Launch**
   - Roll out behind a feature flag for QA, gather feedback, then enable by default once stability is confirmed.

## Open Questions
- Should the backend permit storing the Vertex JSON in the user profile for convenience (disabled by default to maintain zero-persistence)?
- Do we need to surface quota/region mismatch warnings proactively by calling Vertex model listing APIs (could be added later if needed)?
- How do we want to expose model-version updates (e.g., `gemini-2.6` in the future) without releasing new frontend builds every time?
