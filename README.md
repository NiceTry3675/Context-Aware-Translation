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

이 프로젝트는 단순한 텍스트 번역을 넘어, 소설의 **문체, 등장인물, 특정 용어** 등을 깊이 분석하고 일관성을 유지하며 영어 소설을 한국어로 번역하는 시스템입니다. Google의 강력한 Gemini API와 세련된 웹 인터페이스를 통해 높은 품질의 번역 경험을 제공하하는 것을 목표로 합니다.

## ✨ 주요 기능

- **🌐 세련된 웹 UI**: **Next.js 15**와 **Material-UI(MUI)**를 사용한 컴포넌트 기반 아키텍처로 직관적이고 아름다운 다크 모드 인터페이스를 제공합니다.
- **✍️ AI 기반 스타일 분석**: 단순 번역을 넘어, 소설의 첫 부분을 AI가 분석하여 **주인공의 이름**과 **핵심 서사 스타일**을 자동으로 정의합니다.
- **🎨 사용자 제어 및 수정**: AI가 분석한 주인공 이름과 서사 스타일(서술 문체, 톤, 핵심 규칙 등)을 번역 시작 전에 사용자가 직접 확인하고 자유롭게 수정할 수 있습니다.
- **📚 동적 문맥 관리**: 번역 과정에서 중요한 **용어(Glossary)**와 등장인물의 **말투(Character Style)**를 동적으로 구축하고 업데이트하여 일관성을 유지합니다.
- **🤖 번역 모델 선택**: **Flash, Pro** 등 번역에 사용할 Gemini 모델을 UI에서 직접 선택할 수 있습니다.
- **📊 사용량 통계 수집**: 서비스 개선을 위해 번역 소요 시간, 텍스트 길이, 사용 모델 등 익명의 사용 통계를 수집합니다.
- **📢 실시간 공지 기능**: 서버에서 모든 클라이언트에게 실시간으로 중요 공지를 전송할 수 있습니다. (SSE 사용)
- **🔍 실시간 진행률 확인**: 번역 작업의 진행 상황을 실시간으로 웹 화면에서 확인할 수 있습니다.
- **🖼️ 전용 캔버스 페이지**: 번역 결과, 검증 보고서, 포스트 에디팅 로그를 넓은 화면에서 편리하게 확인할 수 있는 전용 작업 공간을 제공합니다.
- **✅ 번역 품질 검증**: AI 기반 자동 검증 시스템으로 번역 정확도, 누락 내용, 이름 일관성 등을 체크합니다.
- **🔧 자동 오류 수정 (Post-Edit)**: 검증에서 발견된 문제를 AI가 자동으로 수정하고 포괄적인 로그를 생성합니다.
- **📄 다양한 파일 형식 지원**: TXT, DOCX, EPUB, PDF 등 주요 문서 파일 형식을 지원합니다.
- **💬 커뮤니티 게시판**: 사용자들이 공지사항, 건의사항, Q&A, 자유게시판을 통해 소통할 수 있는 커뮤니티 기능을 제공합니다.

## 📂 프로젝트 구조

```
Context-Aware-Translation/
├── backend/                     # 🌐 FastAPI 백엔드 서버
│   ├── auth.py                  # 인증 관련 로직
│   ├── auto_init.py             # 자동 초기화 스크립트
│   ├── crud.py                  # 데이터베이스 CRUD 연산
│   ├── database.py              # 데이터베이스 연결 설정
│   ├── main.py                  # FastAPI 앱 진입점
│   ├── migrations.py            # 데이터베이스 마이그레이션
│   ├── models.py                # 데이터베이스 모델 정의
│   └── schemas.py               # Pydantic 스키마 정의
├── frontend/                    # 💻 Next.js 프론트엔드
│   ├── src/
│   │   ├── app/                 # Next.js 앱 라우터 (페이지, 레이아웃)
│   │   │   ├── (auth)/          # 인증 관련 페이지
│   │   │   ├── canvas/          # 번역 작업 전용 캔버스 페이지
│   │   │   ├── community/       # 커뮤니티 관련 페이지
│   │   │   ├── components/      # 재사용 가능한 컴포넌트
│   │   │   │   ├── ApiConfiguration/  # API 설정 컴포넌트
│   │   │   │   ├── AdvancedSettings/  # 고급 번역 설정
│   │   │   │   ├── FileUpload/        # 파일 업로드 처리
│   │   │   │   ├── StyleConfiguration/# 스타일 및 용어집 설정
│   │   │   │   ├── TranslationSidebar/# 캔버스 페이지용 컴포넌트 및 훅
│   │   │   │   ├── jobs/              # 번역 작업 관련 컴포넌트
│   │   │   │   ├── sections/          # 페이지 섹션 컴포넌트
│   │   │   │   ├── shared/            # 공유 컴포넌트 (이슈 칩, 통계 등)
│   │   │   │   └── translation/       # 번역 관련 컴포넌트
│   │   │   ├── hooks/           # 커스텀 React 훅
│   │   │   │   ├── useApiKey.ts         # API 키 관리
│   │   │   │   ├── useTranslationJobs.ts# 번역 작업 상태 관리
│   │   │   │   ├── useTranslationService.ts # 번역 서비스 로직
│   │   │   │   └── useJobActions.ts     # 작업 액션 핸들러
│   │   │   ├── types/           # TypeScript 타입 정의
│   │   │   │   ├── job.ts              # 작업 타입
│   │   │   │   └── translation.ts      # 번역 관련 타입
│   │   │   ├── utils/           # 유틸리티 함수
│   │   │   │   ├── api.ts              # API 통신 함수
│   │   │   │   └── constants/          # 상수 정의
│   │   │   ├── privacy/         # 개인정보 처리방침 페이지
│   │   │   ├── favicon.ico      # 파비콘
│   │   │   ├── globals.css      # 전역 CSS 스타일
│   │   │   ├── layout.tsx       # 루트 레이아웃
│   │   │   └── page.tsx         # 메인 페이지 (267 lines)
│   │   └── theme.ts             # Material-UI 테마 설정
│   └── public/                  # 정적 파일 디렉토리
├── core/                        # 🧠 핵심 번역 엔진
│   ├── config/                  # 설정 및 상태 관리
│   │   ├── builder.py           # 설정 빌더
│   │   ├── character_style.py   # 등장인물 말투 관리
│   │   ├── glossary.py          # 용어집 관리
│   │   └── loader.py            # 설정 로더
│   ├── errors/                  # 에러 처리
│   │   ├── api_errors.py        # API 관련 에러
│   │   ├── base.py              # 기본 에러 클래스
│   │   └── error_logger.py      # 에러 로깅
│   ├── prompts/                 # 프롬프트 관리
│   │   ├── builder.py           # 프롬프트 빌더
│   │   ├── manager.py           # 프롬프트 매니저
│   │   ├── prompts.yaml         # 실제 프롬프트 내용
│   │   ├── README.md            # 프롬프트 문서
│   │   └── sanitizer.py         # 프롬프트 정화기
│   ├── translation/             # 번역 로직
│   │   ├── engine.py            # 번역 엔진
│   │   ├── job.py               # 번역 작업 관리
│   │   ├── validator.py         # 번역 품질 검증기
│   │   ├── post_editor.py       # 자동 오류 수정기
│   │   └── models/              # AI 모델 인터페이스
│   │       ├── gemini.py        # Gemini API 인터페이스
│   │       └── openrouter.py    # OpenRouter API 인터페이스
│   ├── utils/                   # 유틸리티 함수
│   │   ├── file_parser.py       # 파일 파서
│   │   └── retry.py             # 재시도 로직
│   ├── main.py                  # 번역 엔진 진입점
│   └── __init__.py              # 패키지 초기화
├── tests/                       # 🧪 테스트 코드
│   ├── run_tests.py             # 테스트 실행 스크립트
│   ├── test_integration.py      # 통합 테스트
│   └── test_translation_overall.py # 전체 번역 테스트
├── uploads/                     # 📤 업로드된 원본 파일
├── translated_novel/            # 📚 번역된 결과물
├── source_novel/                # 📖 원본 소설 파일
├── context_log/                 # 📝 문맥 분석 로그
├── debug_prompts/               # 🔍 디버그 프롬프트
├── prohibited_content_logs/     # ⚠️ 부적절한 콘텐츠 로그
├── validation_logs/             # ✅ 번역 품질 검증 보고서
├── postedit_logs/               # 🔧 자동 수정 내역 로그
├── requirements.txt             # 🐍 Python 의존성
├── package.json                 # 📦 Node.js 의존성
└── Dockerfile                   # 🐳 Docker 설정
```

## 🏗️ 프론트엔드 아키텍처

### 컴포넌트 구조
- **모듈화된 컴포넌트**: 각 기능별로 독립적인 컴포넌트로 분리하여 재사용성과 유지보수성 향상
- **커스텀 훅**: 비즈니스 로직을 `hooks/` 디렉토리의 커스텀 훅으로 분리하여 관심사 분리
- **타입 안정성**: TypeScript를 활용한 강력한 타입 체크와 IntelliSense 지원
- **최적화된 메인 페이지**: 776줄에서 267줄로 감소 (66% 코드 감소)
- **전용 캔버스 페이지**: 번역 결과 확인을 위한 독립적인 작업 공간 (`/canvas`)

### 주요 컴포넌트
- `ApiConfiguration`: API 제공자 선택 및 키 관리
- `FileUploadSection`: 파일 업로드 및 분석 처리
- `TranslationSettings`: 고급 번역 설정 관리
- `StyleConfigForm`: 스타일 및 용어집 구성
- `JobsTable`: 번역 작업 목록 및 상태 관리
- `Canvas Page`: 번역 결과, 검증 보고서, 포스트 에디팅 확인 전용 페이지
  - 사이드 패널로 작업 정보 및 액션 버튼 제공
  - 탭 기반 콘텐츠 전환 (번역 결과/검증/포스트에디팅)
  - 작업 선택 드롭다운으로 빠른 작업 전환
  - 전체화면 모드 지원

### 커스텀 훅
- `useTranslationService`: 번역 서비스 비즈니스 로직
- `useJobActions`: 작업 관련 액션 (다운로드, 검증, 수정)
- `useTranslationJobs`: 번역 작업 상태 관리
- `useApiKey`: API 키 및 제공자 설정 관리

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

3.  **환경 변수 설정**:
    -   프로젝트 루트 디렉토리에 `.env` 파일을 생성합니다.
    -   **웹 UI 사용 시**: Gemini API 키는 웹 화면에서 직접 입력하므로 `.env` 파일에 추가할 필요가 없습니다.
    -   **CLI 사용 시**: 아래와 같이 Gemini API 키를 추가합니다.
        ```.env
        GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
        ```
    -   **데이터베이스 설정**: 로컬 개발 시 PostgreSQL 대신 SQLite(`database.db`)를 사용하려면, `.env` 파일에 `DATABASE_URL`을 추가하지 않거나 주석 처리하세요.

## ▶️ 실행 방법

### 웹 인터페이스 (권장)

각각 다른 터미널에서 아래 명령어를 실행합니다.

1.  **백엔드 서버 실행**:
    ```bash
    uvicorn backend.main:app --reload --port 8000
    .\venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
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
    -   검증 사용 시 `validation_logs` 디렉토리에 품질 검증 보고서가 생성됩니다.
    -   Post-Edit 사용 시 `postedit_logs` 디렉토리에 전체 수정 내역이 포함된 로그가 생성됩니다.

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