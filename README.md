<div align="center">

# 📖 Context-Aware AI Novel Translator (냥번역)

**Google Gemini API를 활용한 문맥 인식 AI 소설 번역기**

</div>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white" alt="Python Version">
  <img src="https://img.shields.io/badge/Next.js-15-black?logo=nextdotjs&logoColor=white" alt="Next.js Version">
  <a href="https://github.com/NiceTry3675/Context-Aware-Translation">
    <img src="https://img.shields.io/badge/GitHub-Repository-black?logo=github" alt="GitHub Repository">
  </a>
</p>

---

## 🚀 프로젝트 개요

이 프로젝트는 단순한 텍스트 번역을 넘어, 소설의 **문체, 등장인물, 특정 용어** 등을 깊이 분석하고 일관성을 유지하며 다양한 소스 언어의 소설을 한국어로 번역하는 시스템입니다. Google의 강력한 Gemini API와 세련된 웹 인터페이스를 통해 높은 품질의 번역 경험을 제공하하는 것을 목표로 합니다.

## ✨ 주요 기능

- **🌐 세련된 웹 UI**: **Next.js 15**와 **Material-UI(MUI)**를 사용한 컴포넌트 기반 아키텍처로 직관적이고 아름다운 다크 모드 인터페이스를 제공합니다.
- **✍️ AI 기반 스타일 분석**: 단순 번역을 넘어, 소설의 첫 부분을 AI가 분석하여 **주인공의 이름**과 **핵심 서사 스타일**을 자동으로 정의합니다.
- **🎨 사용자 제어 및 수정**: AI가 분석한 주인공 이름과 서사 스타일(서술 문체, 톤, 핵심 규칙 등)을 번역 시작 전에 사용자가 직접 확인하고 자유롭게 수정할 수 있습니다.
- **📚 동적 문맥 관리**: 번역 과정에서 중요한 **용어(Glossary)**와 등장인물의 **말투(Character Style)**를 동적으로 구축하고 업데이트하여 일관성을 유지합니다.
- **🤖 번역 모델 선택**: **Flash, Pro** 등 번역에 사용할 Gemini 모델을 UI에서 직접 선택할 수 있습니다.
- **🤖 작업별 모델 선택 (신규)**: 용어집 추출, 스타일 분석, 메인 번역을 서로 다른 모델로 지정할 수 있습니다. 백엔드는 `translation_model_name`, `style_model_name`, `glossary_model_name` 폼 필드를 받아 각 단계에 다른 모델을 사용합니다. 미지정 시 `model_name`을 기본값으로 사용합니다.
- **📊 사용량 통계 수집**: 서비스 개선을 위해 번역 소요 시간, 텍스트 길이, 사용 모델 등 익명의 사용 통계를 수집합니다.
- **📢 실시간 공지 기능**: 서버에서 모든 클라이언트에게 실시간으로 중요 공지를 전송할 수 있습니다. (SSE 사용)
- **🔍 실시간 진행률 확인**: 번역 작업의 진행 상황을 실시간으로 웹 화면에서 확인할 수 있습니다.
- **🖼️ 전용 캔버스 페이지**: 번역 결과, 검증 보고서, 포스트 에디팅 로그를 넓은 화면에서 편리하게 확인할 수 있는 전용 작업 공간을 제공합니다.
- **✅ 번역 품질 검증**: AI 기반 자동 검증 시스템으로 번역 정확도, 누락 내용, 이름 일관성 등을 체크합니다. 이제 Gemini Structured Output을 사용해 JSON 스키마로 결과를 수집하고, 프론트엔드가 사용하는 기존 리포트 형태로 안정적으로 매핑합니다.
- **🔧 자동 오류 수정 (Post-Edit)**: 검증에서 발견된 문제를 AI가 자동으로 수정하고 포괄적인 로그를 생성합니다.
- **📄 다양한 파일 형식 지원**: TXT, DOCX, EPUB, PDF 등 주요 문서 파일 형식을 지원합니다.
- **📑 PDF 다운로드 기능**: 번역 결과를 전문적인 PDF 문서로 다운로드할 수 있습니다. 원문 포함 옵션과 생성된 삽화를 PDF에 직접 삽입하는 기능을 제공합니다.
- **🎨 삽화 생성 (실험적)**: AI를 통해 각 번역 세그먼트에 대한 삽화 프롬프트를 생성하고, 외부 이미지 생성 서비스와 연동 가능한 인터페이스를 제공합니다.
- **💬 커뮤니티 게시판**: 사용자들이 공지사항, 건의사항, Q&A, 자유게시판을 통해 소통할 수 있는 커뮤니티 기능을 제공합니다.

### 작업별 모델 오버라이드 사용법

백엔드 `/api/v1/jobs` 업로드 시 다음 폼 필드를 통해 단계별 모델을 지정할 수 있습니다.

- `translation_model_name`: 메인 번역에 사용할 모델
- `style_model_name`: 서사 스타일 분석(주인공/문체) 단계에 사용할 모델
- `glossary_model_name`: 용어집 추출 및 동적 가이드(구조화 출력) 단계에 사용할 모델

지정하지 않으면 모든 단계에서 `model_name` 값을 사용합니다.

예시 (cURL):

```
curl -X POST "$API_URL/api/v1/jobs" \
  -H "Authorization: Bearer <TOKEN>" \
  -F file=@novel.txt \
  -F api_key="$GEMINI_API_KEY" \
  -F model_name="gemini-2.5-flash-lite" \
  -F translation_model_name="gemini-2.5-pro" \
  -F style_model_name="gemini-2.5-flash-lite" \
  -F glossary_model_name="gemini-2.5-flash-lite"
```

참고: 용어집/스타일 편차 등 구조화 출력이 필요한 단계는 Gemini 계열 모델을 권장합니다.

### 📑 PDF 다운로드 기능

번역이 완료된 작업을 전문적인 PDF 문서로 다운로드할 수 있습니다.

**주요 기능:**
- **원문 포함 옵션**: 각 세그먼트의 원문을 번역문과 함께 표시
- **삽화 삽입**: AI로 생성된 삽화를 PDF에 직접 포함
- **전문적인 레이아웃**: 
  - 제목 페이지 및 메타데이터
  - 세그먼트별 구분 및 번호 표시
  - 페이지 번호 및 여백 설정
  - A4/Letter 용지 크기 선택
- **API 엔드포인트**: `GET /api/v1/jobs/{job_id}/pdf`
  - Query 파라미터:
    - `include_source`: 원문 포함 여부 (기본값: true)
    - `include_illustrations`: 삽화 포함 여부 (기본값: true) 
    - `page_size`: 용지 크기 선택 (A4 또는 Letter)

**사용 방법:**
1. 번역 완료된 작업 목록에서 PDF 아이콘 클릭
2. 또는 캔버스 페이지의 작업 사이드바에서 PDF 다운로드 버튼 클릭
3. PDF가 자동으로 생성되어 다운로드됨

## 📂 프로젝트 구조

```
Context-Aware-Translation/
├── backend/                     # 🌐 FastAPI 백엔드 서버
│   ├── domains/                 # 도메인 주도 설계 (DDD)
│   ├── celery_tasks/            # 비동기 작업 처리
│   ├── config/                  # 설정 및 의존성 관리
│   └── migrations/              # Alembic 마이그레이션
├── frontend/                    # 💻 Next.js 프론트엔드
│   └── src/app/
│       ├── components/          # React 컴포넌트
│       ├── hooks/               # 커스텀 React 훅
│       └── canvas/              # 캔버스 페이지
├── core/                        # 🧠 핵심 번역 엔진
│   ├── config/                  # 설정 및 상태 관리
│   ├── prompts/                 # AI 프롬프트 관리
│   └── translation/             # 번역 로직 및 모델
├── tests/                       # 🧪 테스트 코드
├── uploads/                     # 📤 업로드된 파일
├── translated_novel/            # 📚 번역 결과물
├── illustrations/               # 🎨 생성된 삽화
└── logs/                        # 📁 로그 파일
```

## 🏗️ 프론트엔드 아키텍처

- **Next.js 15 App Router**: 최신 React 서버 컴포넌트 활용
- **TypeScript**: 타입 안정성과 개발 생산성 향상
- **Material-UI**: 일관된 디자인 시스템
- **캔버스 페이지**: 번역 작업 전용 워크스페이스 (전체화면 지원)
- **커스텀 훅**: 비즈니스 로직 분리 및 재사용

## 💬 커뮤니티 기능

### 게시판 카테고리
- **공지사항**: 관리자만 작성 가능한 중요 공지사항
- **건의사항**: 서비스 개선을 위한 사용자 제안
- **Q&A**: 질문과 답변을 통한 정보 공유
- **자유게시판**: 자유로운 소통 공간

### 주요 기능
- 로그인한 사용자만 접근 가능 (Clerk 인증)
- 게시글 및 댓글 CRUD
- **📸 이미지 업로드**: 게시글에 여러 이미지 첨부 가능 (최대 10MB, JPG/PNG/GIF/WebP)
- 검색 및 필터링
- **🔒 비밀글**: 작성자와 관리자만 볼 수 있는 비밀글/댓글 작성
- 관리자 권한 시스템
- 조회수 및 댓글 수 표시

### 카테고리 초기화
```bash
python init_categories.py
```

## 🛠️ 설치 및 설정

1.  **사전 준비**:
    -   Python 3.9+
    -   Node.js 및 npm
    -   Git
    -   Redis (백그라운드 작업 처리를 위해 필요)

2.  **프로젝트 클론 및 의존성 설치**:
    ```bash
    # 저장소 복제
    git clone https://github.com/NiceTry3675/Context-Aware-Translation.git
    cd Context-Aware-Translation

    # Python 가상 환경 생성 및 활성화
    python -m venv venv
    # Windows: venv\\Scripts\\activate | macOS/Linux: source venv/bin/activate

    # Python 의존성 설치
    pip install -r requirements.txt

    # Node.js 의존성 설치
    npm install
    ```

3.  **데이터베이스 마이그레이션**:
    
    이 프로젝트는 Alembic을 사용하여 데이터베이스 스키마를 관리합니다.
    
    ```bash
    # 백엔드 디렉토리로 이동
    cd backend
    
    # 데이터베이스 마이그레이션 적용 (테이블 생성)
    alembic upgrade head
    
    # 새 마이그레이션 생성 (스키마 변경 시)
    alembic revision --autogenerate -m "마이그레이션 설명"
    
    # 마이그레이션 히스토리 확인
    alembic history
    
    # 이전 버전으로 롤백
    alembic downgrade -1
    
    # 프로젝트 루트로 돌아가기
    cd ..
    ```

4.  **데이터베이스 백업 시스템 (S3)**:

    이 프로젝트는 AWS S3를 사용한 자동 데이터베이스 백업 시스템을 제공합니다.

    ```bash
    # 수동 백업 실행
    python scripts/backup_database.py

    # 백업 목록 확인
    python scripts/backup_database.py --list

    # 최신 백업에서 복구
    python scripts/backup_database.py --restore

    # 특정 백업에서 복구
    python scripts/backup_database.py --restore backups/full/20250913_141313/database.db.gz

    # 백업 상태 확인
    python scripts/check_backup_status.py
    ```

    **자동 백업 설정**:
    - Celery Beat를 통해 매일 자동 백업이 실행됩니다
    - 백업은 gzip으로 압축되어 S3에 업로드됩니다 (약 81% 압축률)
    - 30일 이상 된 백업은 자동으로 삭제됩니다

    **필요한 환경 변수** (`.env`):
    ```
    AWS_ACCESS_KEY_ID=your-access-key
    AWS_SECRET_ACCESS_KEY=your-secret-key
    AWS_REGION=ap-southeast-2
    S3_BACKUP_BUCKET=your-bucket-name
    BACKUP_RETENTION_DAYS=30
    ```

5.  **코드 생성 (TypeScript 타입 동기화)**:
    
    이 프로젝트는 단일 진실의 원천(Single Source of Truth) 원칙을 따라 Pydantic 모델에서 TypeScript 타입을 자동 생성합니다.
    
    ```bash
    # 전체 코드 생성 파이프라인 실행 (권장)
    make codegen
    
    # 개별 단계 실행
    make openapi       # FastAPI에서 OpenAPI 스키마 추출
    make schemas       # Pydantic 모델에서 JSON 스키마 추출
    make fe-types      # OpenAPI에서 TypeScript API 타입 생성
    make fe-schemas    # JSON 스키마에서 TypeScript 도메인 타입 생성
    
    # 생성된 파일이 최신인지 확인
    make verify
    
    # 생성된 파일 모두 삭제
    make clean
    
    # 도움말 보기
    make help
    ```
    
    **참고**: 백엔드 모델을 수정한 경우 반드시 `make codegen`을 실행하여 프론트엔드 타입을 동기화해야 합니다.

5.  **환경 변수 설정**:
    -   프로젝트 루트 디렉토리에 `.env` 파일을 생성합니다. `start_backend.sh`는 `backend/.env`가 없으면 루트 `.env`를 자동 로드합니다.
    -   필수(백엔드):
        - `GEMINI_API_KEY` — 웹 UI에서 직접 입력하지 않고 서버가 호출할 경우 필요
        - `ADMIN_SECRET_KEY` — 관리자 엔드포인트 보호용
    -   선택(개발 편의):
        - `DATABASE_URL` — 미설정 시 자동으로 로컬 SQLite(`database.db`) 사용
        - `SECRET_KEY` — 미설정 시 개발 기본값(`dev-secret-key`) 사용
        - `OPENROUTER_API_KEY` — OpenRouter 모델을 사용할 때만 필요
        - `CLERK_PUBLISHABLE_KEY` — 프론트엔드용(백엔드 기동에는 불필요)
    -   **웹 UI 사용 시**: Gemini API 키는 웹 화면에서 직접 입력 가능하므로 `.env`에 추가하지 않아도 됩니다.
    -   **CLI 사용 시**: 아래와 같이 Gemini API 키를 추가합니다.
        ```.env
        GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
        USE_STRUCTURED_OUTPUT="true"  # Gemini Structured Output 사용 (기본값: true)
        ```
    -   **데이터베이스 설정**: 로컬 개발에서는 `.env`에 `DATABASE_URL`을 생략하면 자동으로 SQLite(`database.db`)를 사용합니다.

6.  **스크립트 실행 권한 설정** (Linux/Mac):
    ```bash
    chmod +x start_backend.sh
    ```

## ▶️ 실행 방법

### 웹 인터페이스 (권장)

각각 다른 터미널에서 아래 명령어를 실행합니다.

1.  **백엔드 서버 실행** (권장 방법):
    ```bash
    ./start_backend.sh
    ```
    
    이 스크립트는 자동으로:
    - Redis 서버를 시작합니다
    - Celery 워커를 백그라운드에서 실행합니다
    - FastAPI 서버를 시작합니다
    
    수동 실행 (개별 컴포넌트 제어가 필요한 경우):
    ```bash
    # Redis 시작
    redis-server --daemonize yes
    
    # Celery 워커 시작 (별도 터미널)
    celery -A backend.celery_app worker --loglevel=info
    
    # FastAPI 서버 시작
    uvicorn backend.main:app --reload --port 8000
    ```

2.  **프론트엔드 서버 실행**:
    ```bash
    npm run dev
    ```

이제 브라우저에서 `http://localhost:3000`에 접속하여 서비스를 사용할 수 있습니다.

### 번역 워크플로우
1. 메인 페이지에서 파일 업로드 및 번역 설정
2. 번역 시작 시 자동으로 캔버스 페이지(`/canvas`)로 이동
3. 캔버스 페이지에서 번역 진행 상황 실시간 확인
4. 번역 완료 후 검증 및 포스트 에디팅 실행 가능
5. 모든 결과를 넓은 화면에서 편리하게 확인
6. PDF 형식으로 번역 결과 다운로드 (삽화 포함 가능)

### CLI (명령줄)

1.  **원본 소설 준비**:
    -   번역할 소설 파일을 `source_novel` 디렉토리에 추가합니다.

2.  **번역 실행**:
    ```bash
    # 기본 사용법 (API 키는 .env 파일 또는 환경변수로 설정)
    python -m core.main "source_novel/my_novel.txt"
    
    # 출력 파일명 지정
    python -m core.main "source_novel/my_novel.txt" "translated_output.txt"
    
    # API 키 직접 전달
    python -m core.main "source_novel/my_novel.txt" -k "YOUR_API_KEY"
    
    # 번역 품질 검증 활성화
    python -m core.main "source_novel/my_novel.txt" --with-validation
    
    # 빠른 검증 (샘플링)
    python -m core.main "source_novel/my_novel.txt" --with-validation --quick-validation --validation-sample-rate 0.3
    
    # 검증 후 자동 수정 (Post-Edit)
    python -m core.main "source_novel/my_novel.txt" --with-validation --post-edit
    ```
    -   더 많은 옵션은 `python -m core.main --help`로 확인할 수 있습니다.

3.  **결과 확인**:
    -   번역이 완료되면 `translated_novel` 디렉토리에 결과 파일이 생성됩니다.
    -   검증 사용 시 `logs/validation_logs` 디렉토리에 품질 검증 보고서가 생성됩니다.
    -   Post-Edit 사용 시 `logs/postedit_logs` 디렉토리에 전체 수정 내역이 포함된 로그가 생성됩니다.

## 💻 기술 스택

-   **Backend**: `Python`, `FastAPI`, `SQLAlchemy`
-   **Frontend**: `Next.js`, `TypeScript`, `React`, `Material-UI (MUI)`
-   **AI Model**: `Google Gemini (Flash, Pro)`
-   **Database**: `PostgreSQL` (Production), `SQLite` (Local)
-   **Deployment**: `Docker`, `Vercel` (Frontend), `Railway` (Backend)

---

<p align="center">
  Made with ❤️ by NiceTry3675 and sorryhyun
</p>
