# Context-Aware Translation System - Data Flow Analysis

## Overview
This document analyzes what data is written to the database and filesystem during translation operations.

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     User Request                         │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
│  ┌─────────────────────────────────────────────────┐    │
│  │            Translation Job Created               │    │
│  │         (database.db: translation_jobs)         │    │
│  └─────────────────────┬───────────────────────────┘    │
└────────────────────────┼────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   Celery Worker                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │             Task Execution Tracked               │    │
│  │         (database.db: task_executions)          │    │
│  └─────────────────────┬───────────────────────────┘    │
└────────────────────────┼────────────────────────────────┘
                         │
                    ┌────┴────┐
                    ▼         ▼
            ┌──────────┐  ┌──────────┐
            │ Database │  │   Logs   │
            │  SQLite  │  │Filesystem│
            └──────────┘  └──────────┘
```

## Database Schema

### 1. translation_jobs Table

| Column | Type | Description |
|--------|------|-------------|
| **Core Fields** | | |
| id | INTEGER | Primary key |
| filename | VARCHAR | Original filename |
| status | VARCHAR | PENDING, PROCESSING, COMPLETED, FAILED |
| progress | INTEGER | 0-100 percentage |
| created_at | DATETIME | Job creation timestamp |
| completed_at | DATETIME | Job completion timestamp |
| error_message | VARCHAR | Error details if failed |
| filepath | VARCHAR | Path to source file |
| owner_id | INTEGER | User who created job |
| **Translation Data** | | |
| segment_size | INTEGER | Characters per segment (default: 15000) |
| translation_segments | JSON | Source and translated segment pairs |
| final_glossary | JSON | Final glossary terms |
| **Validation Fields** | | |
| validation_enabled | BOOLEAN | Whether validation requested |
| validation_status | VARCHAR | PENDING, IN_PROGRESS, COMPLETED, FAILED |
| validation_progress | INTEGER | 0-100 percentage |
| validation_sample_rate | INTEGER | Percentage of segments to validate |
| quick_validation | BOOLEAN | Quick validation mode |
| validation_report_path | VARCHAR | Path to validation report |
| validation_completed_at | DATETIME | Validation completion time |
| **Post-Edit Fields** | | |
| post_edit_enabled | BOOLEAN | Whether post-edit requested |
| post_edit_status | VARCHAR | PENDING, IN_PROGRESS, COMPLETED, FAILED |
| post_edit_progress | INTEGER | 0-100 percentage |
| post_edit_log_path | VARCHAR | Path to post-edit log |
| post_edit_completed_at | DATETIME | Post-edit completion time |
| **Illustration Fields** | | |
| illustrations_enabled | BOOLEAN | Whether illustrations requested |
| illustrations_config | JSON | Illustration configuration |
| illustrations_data | JSON | Generated illustration metadata |
| illustrations_status | VARCHAR | Status of illustration generation |
| illustrations_count | INTEGER | Number of illustrations |
| illustrations_directory | VARCHAR | Path to illustrations |
| **Character Base Fields** | | |
| character_profile | JSON | Character profile data |
| character_base_images | JSON | Generated base images |
| character_base_selected_index | INTEGER | Selected base image index |
| character_base_directory | VARCHAR | Path to character images |

### 2. task_executions Table

| Column | Type | Description |
|--------|------|-------------|
| **Identity** | | |
| id | VARCHAR | Celery task ID (UUID) |
| kind | VARCHAR | TRANSLATION, VALIDATION, POST_EDIT, etc. |
| name | VARCHAR | Full task name |
| job_id | INTEGER | Related translation job |
| user_id | INTEGER | User who triggered task |
| **Status Tracking** | | |
| status | VARCHAR | PENDING, STARTED, SUCCESS, FAILURE, RETRY |
| attempts | INTEGER | Number of execution attempts |
| max_retries | INTEGER | Maximum retry limit |
| last_error | TEXT | Last error message |
| next_retry_at | DATETIME | Next retry scheduled time |
| **Performance** | | |
| queue_time | DATETIME | When queued |
| start_time | DATETIME | When started |
| end_time | DATETIME | When completed |
| created_at | DATETIME | Record creation |
| updated_at | DATETIME | Last update |
| **Data** | | |
| args | JSON | Task arguments |
| kwargs | JSON | Task keyword arguments |
| result | JSON | Task result data |
| extra_data | JSON | Additional metadata |

### 3. translation_usage_logs Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| job_id | INTEGER | Related job |
| original_length | INTEGER | Source text length |
| translated_length | INTEGER | Output text length |
| translation_duration_seconds | INTEGER | Time taken |
| model_used | VARCHAR | AI model (Gemini, OpenRouter) |
| error_type | VARCHAR | Error category if failed |
| created_at | DATETIME | Log timestamp |

## Log Directory Structure

```
logs/
├── jobs/                           # Job-centric organization
│   └── {job_id}/                   # Each job gets its own directory
│       ├── input/                  # Source files
│       │   └── original_file.txt   # Original uploaded file
│       │
│       ├── output/                 # Generated files
│       │   └── translated.txt      # Final translation
│       │
│       ├── prompts/                # AI prompts (debug)
│       │   ├── translation_prompts.txt
│       │   ├── validation_prompts.txt
│       │   ├── style_analysis_prompts.txt
│       │   └── postedit_prompts.txt
│       │
│       ├── context/                # Translation context
│       │   ├── translation_context.txt
│       │   ├── validation_context.txt
│       │   └── style_analysis_context.txt
│       │
│       ├── progress/               # Progress tracking
│       │   ├── translation_progress.txt
│       │   ├── validation_progress.txt
│       │   └── postedit_progress.txt
│       │
│       ├── validation/             # Validation results
│       │   └── validation_report.json
│       │
│       ├── postedit/              # Post-edit logs
│       │   └── postedit_log.json
│       │
│       ├── tasks/                  # Task execution logs
│       │   └── {task_type}_task_{timestamp}.log
│       │
│       └── prohibited_content/     # Content policy issues
│           └── retry_attempts.log
│
└── errors/                         # Global error logs
    └── error_{timestamp}.txt       # Error details with traceback
```

## Data Flow by Operation

### 1. Translation Operation

```
START
  │
  ├─► Database Write: translation_jobs
  │     • status = "PROCESSING"
  │     • segment_size, owner_id
  │
  ├─► Database Write: task_executions
  │     • kind = "TRANSLATION"
  │     • status = "STARTED"
  │
  ├─► Log Write: input/
  │     • Save original file
  │
  ├─► For Each Segment:
  │     │
  │     ├─► Log Write: prompts/translation_prompts.txt
  │     │     • Full AI prompt with context
  │     │
  │     ├─► Log Write: context/translation_context.txt
  │     │     • Narrative style deviation
  │     │     • Contextual glossary
  │     │     • Character styles
  │     │     • Previous segment context
  │     │
  │     └─► Log Write: progress/translation_progress.txt
  │           • Segment X/Y (Z%)
  │           • Elapsed time
  │
  ├─► Database Update: translation_jobs
  │     • translation_segments = JSON array
  │     • final_glossary = JSON object
  │     • status = "COMPLETED"
  │
  ├─► Database Update: task_executions
  │     • status = "SUCCESS"
  │     • end_time, duration
  │
  ├─► Database Write: translation_usage_logs
  │     • Original/translated lengths
  │     • Duration, model used
  │
  └─► Log Write: output/translated.txt
        • Final translation
```

### 2. Validation Operation

```
START
  │
  ├─► Database Update: translation_jobs
  │     • validation_status = "IN_PROGRESS"
  │
  ├─► Database Write: task_executions
  │     • kind = "VALIDATION"
  │     • status = "STARTED"
  │
  ├─► For Each Sampled Segment:
  │     │
  │     ├─► Log Write: prompts/validation_prompts.txt
  │     │     • Validation prompt with segment pairs
  │     │
  │     └─► Log Write: progress/validation_progress.txt
  │           • Validation progress
  │
  ├─► Log Write: validation/validation_report.json
  │     • Summary statistics
  │     • Issue dimensions (completeness, accuracy, flow)
  │     • Severity levels (1-3)
  │     • Segment-by-segment cases
  │
  ├─► Database Update: translation_jobs
  │     • validation_status = "COMPLETED"
  │     • validation_report_path
  │
  └─► Database Update: task_executions
        • status = "SUCCESS"
        • result = summary stats
```

### 3. Post-Edit Operation

```
START
  │
  ├─► Database Update: translation_jobs
  │     • post_edit_status = "IN_PROGRESS"
  │
  ├─► Database Write: task_executions
  │     • kind = "POST_EDIT"
  │     • status = "STARTED"
  │
  ├─► For Each Segment with Issues:
  │     │
  │     ├─► Log Write: prompts/postedit_prompts.txt
  │     │     • Correction prompt with issues
  │     │
  │     └─► Apply Corrections
  │
  ├─► Log Write: postedit/postedit_log.json
  │     • Summary (segments edited, percentage)
  │     • Before/after comparisons
  │     • Applied corrections
  │     • Validation cases addressed
  │
  ├─► Log Write: output/translated.txt
  │     • Updated translation
  │
  ├─► Database Update: translation_jobs
  │     • post_edit_status = "COMPLETED"
  │     • post_edit_log_path
  │
  └─► Database Update: task_executions
        • status = "SUCCESS"
```

## Log File Contents

### Context Log Sample (`context/translation_context.txt`)
```
--- CONTEXT FOR SEGMENT 0 ---

### Narrative Style Deviation:
No deviation - maintaining core narrative style

### Contextual Glossary (For This Segment):
- Gregor Samsa: 그레고르 잠자
- vermin: 벌레

### Cumulative Glossary (Full):
- Gregor Samsa: 그레고르 잠자
- travelling salesman: 외판원
- guest house: 게스트하우스

### Cumulative Character Styles:
- Gregor: introspective, anxious

### Immediate Language Context:
[Previous segment ending if applicable]
```

### Validation Report Sample (`validation/validation_report.json`)
```json
{
  "summary": {
    "total_segments": 9,
    "validated_segments": 9,
    "passed": 0,
    "failed": 9,
    "pass_rate": 0.0,
    "case_counts_by_severity": {
      "1": 58,  // Minor issues
      "2": 23,  // Major issues
      "3": 0    // Critical issues
    },
    "case_counts_by_dimension": {
      "completeness": 1,
      "accuracy": 63,
      "flow": 17
    }
  },
  "segments": [
    {
      "segment_index": 0,
      "validation_status": "FAIL",
      "structured_cases": [
        {
          "current_korean_sentence": "...",
          "problematic_source_sentence": "...",
          "reason": "Translation issue description",
          "dimension": "accuracy",
          "severity": "2",
          "recommend_korean_sentence": "...",
          "tags": ["terminology"]
        }
      ]
    }
  ]
}
```

### Post-Edit Log Sample (`postedit/postedit_log.json`)
```json
{
  "summary": {
    "segments_edited": 9,
    "total_segments": 9,
    "edit_percentage": 100.0
  },
  "segments": [
    {
      "segment_index": 0,
      "was_edited": true,
      "source_text": "Original English text...",
      "original_translation": "Initial Korean translation...",
      "edited_translation": "Corrected Korean translation...",
      "validation_status": "FAIL",
      "structured_cases": [
        // Issues that were addressed
      ]
    }
  ]
}
```

## Key Insights

### 1. **Dual Storage Strategy**
- **Database**: Metadata, status, relationships, summaries
- **Filesystem**: Actual content, detailed logs, debug info

### 2. **Job-Centric Architecture**
- All files organized under `/logs/jobs/{job_id}/`
- Easy to track and debug specific jobs
- Clear separation of concerns

### 3. **Comprehensive Tracking**
- Every AI interaction logged (prompts + responses)
- Context preserved for debugging
- Progress tracked in real-time
- Performance metrics captured

### 4. **Audit Trail**
- Complete history in database
- Detailed logs in filesystem
- Before/after comparisons for edits
- Error tracking with full context

### 5. **Structured Output**
- JSON formats enable programmatic analysis
- Consistent schema across operations
- Machine-readable validation and edit reports

## Statistics from Current Database

Based on the current `database.db`:

| Metric | Count |
|--------|-------|
| Total Jobs | 8 |
| Completed Jobs | 1 |
| Failed Jobs | 6 |
| Processing Jobs | 1 |
| Translation Tasks (Success) | 21 |
| Translation Tasks (Failure) | 4 |
| Translation Tasks (Started) | 1 |
| Validation Tasks (Success) | 19 |
| Validation Tasks (Failure) | 8 |
| Post-Edit Tasks (Success) | 3 |

## Recommendations

1. **Log Rotation**: Implement log rotation for old jobs to manage disk space
2. **Metrics Dashboard**: Create visualization for task execution statistics
3. **Error Analysis**: Aggregate error patterns for system improvement
4. **Performance Monitoring**: Track translation speed trends over time
5. **Storage Optimization**: Archive completed job logs after X days