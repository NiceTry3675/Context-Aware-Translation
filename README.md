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

이 프로젝트는 단순한 텍스트 번역을 넘어, 소설의 **문체, 등장인물, 특정 용어** 등을 깊이 분석하고 일관성을 유지하며 영어 소설을 한국어로 번역하는 시스템입니다. Google의 강력한 Gemini API와 세련된 웹 인터페이스를 통해 높은 품질의 번역 경험을 제공하는 것을 목표로 합니다.

## ✨ 주요 기능

- **🌐 세련된 웹 UI**: **Next.js**와 **Material-UI(MUI)**를 사용하여 직관적이고 아름다운 다크 모드 인터페이스를 제공합니다.
- **✍️ 문맥 인식 번역**: 소설 전체의 핵심 서사 스타일과 문맥을 파악하여 번역의 일관성을 유지합니다.
- **🤖 번역 모델 선택**: **Flash, Pro** 등 번역에 사용할 Gemini 모델을 UI에서 직접 선택할 수 있습니다.
- **🎨 핵심 스타일 수정**: AI가 분석한 소설의 **핵심 서사 스타일(서사 관점, 주요 말투, 톤)**을 번역 시작 전에 사용자가 직접 확인하고 수정할 수 있습니다.
- **📚 동적 설정 구축**: 번역 과정에서 중요한 **용어(Glossary)**와 등장인물의 **말투(Character Style)**를 동적으로 구축하고 업데이트합니다.
- **🔍 실시간 진행률 확인**: 번역 작업의 진행 상황을 실시간으로 웹 화면에서 확인할 수 있습니다.
- **📄 다양한 파일 형식 지원**: TXT, DOCX, EPUB, PDF 등 주요 문서 파일 형식을 ��원합니다.

## 📂 프로젝트 구조

```
Context-Aware-Translation/
├── backend/                # 🌐 FastAPI 백엔드 서버
├── frontend/               # 💻 Next.js 프론트엔드
│   ├── src/
│   │   ├── app/            # Next.js 앱 라우터 (페이지, 레이아웃)
│   │   └── theme.ts        # Material-UI 테마 설정
│   └── public/
├── core/                   # 🧠 핵심 번역 엔진
│   ├── translation/        # 번역 로직
│   ├── config/             # 설정 및 상태 관리
│   └── prompts/            # 프롬프트 관리
├── uploads/                # 📤 업로드된 원본 파일
├── translated_novel/       # 📚 번역된 결과물
├── requirements.txt        # 🐍 Python 의존성
├── package.json            # 📦 Node.js 의존성
└── Dockerfile              # 🐳 Docker 설정
```

## 🛠️ 설치 및 실행 방법

### 1. 사전 준비

-   Python 3.9+
-   Node.js 및 npm
-   Git

### 2. 프로젝트 클론 및 설정

```bash
# 저장소 복제
git clone https://github.com/NiceTry3675/Context-Aware-Translation.git
cd Context-Aware-Translation

# Python 가상 환경 생성 및 활성화
python -m venv venv
# Windows: venv\Scripts\activate | macOS/Linux: source venv/bin/activate

# Python 의존성 설치
pip install -r requirements.txt

# Node.js 의존성 설치
npm install
```

### 3. 환경 변수 설정

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고, 로컬 DB를 사용하려면 아래 내용을 비워두거나 주석 처리합니다.

```.env
# .env

# 로컬 개발 시 PostgreSQL 대신 SQLite(database.db)를 사용하려면 아래 줄을 주석 처리하세요.
# DATABASE_URL="postgresql://user:pass@host:port/db"
```

### 4. 실행

각각 다른 터미널에서 아래 명령어를 실행합니다.

1.  **백엔드 서버 실행:**
    ```bash
    uvicorn backend.main:app --reload --port 8000
    ```

2.  **프론트엔드 서버 실행:**
    ```bash
    npm run dev
    ```

이제 브라우저에서 `http://localhost:3000`에 접속하여 서비스를 사용할 수 있습니다.

## 💻 기술 스택

-   **Backend**: `Python`, `FastAPI`, `SQLAlchemy`
-   **Frontend**: `Next.js`, `TypeScript`, `React`, `Material-UI (MUI)`
-   **AI Model**: `Google Gemini (Flash, Pro)`
-   **Database**: `PostgreSQL` (Production), `SQLite` (Local)
-   **Deployment**: `Docker`, `Vercel` (Frontend), `Railway` (Backend)

---

<p align="center">
  Made with ❤️ by NiceTry3675
</p>