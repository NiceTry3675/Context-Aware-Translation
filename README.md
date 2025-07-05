<div align="center">

# 📖 Context-Aware AI Novel Translator

**Google Gemini API를 활용한 문맥 인식 AI 소설 번역기**

</div>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white" alt="Python Version">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <a href="https://github.com/NiceTry3675/Context-Aware-Translation">
    <img src="https://img.shields.io/badge/GitHub-Repository-black?logo=github" alt="GitHub Repository">
  </a>
</p>

---

## 🚀 프로젝트 개요

이 프로젝트는 단순한 텍스트 번역을 넘어, 소설의 **문체, 등장인물, 특정 용어** 등을 깊이 분석하고 일관성을 유지하며 영어 소설을 한국어로 번역하는 파이썬 기반의 자동 번역 시스템입니다. Google의 강력한 Gemini API를 활용하여 높은 품질의 번역 결과물을 생성하는 것을 목표로 합니다.

## ✨ 주요 기능

- **✍️ 문맥 인식 번역**: 단순한 문장 단위 번역이 아닌, 소설 전체의 핵심 서사 스타일과 문맥을 파악하여 번역합니다.
- **📚 동적 설정 구축**: 번역 과정에서 중요한 **용어(Glossary)**와 등장인물의 **말투(Character Style)**를 동적으로 구축하고 업데이트하여 번역의 일관성을 유지합니다.
- **🎨 스타일 편차 감지**: 각 세그먼트의 문체가 소설의 핵심 서사 스타일에서 벗어나는 경우(예: 편지, 시 등) 이를 감지하고 번역에 반영합니다.
- **⚙️ 유연한 프롬프트 시스템**: 중앙화된 프롬프트 템플릿을 사용하여 번역 요청 프롬프트를 동적으로 생성합니다.
- **🔍 로그 및 디버깅**: 번역 과정에서 생성된 프롬프트와 문맥 정보를 로그 파일로 저장하여 디버깅 및 분석을 용이하게 합니다.

## 📂 프로젝트 구조

```
trans/
├───.gitignore
├───main.py                 # 🚀 프로그램의 메인 실행 파일
├───translation_engine.py   # 🧠 번역 프로세스를 총괄하는 엔진
├───translation_job.py      # 📦 번역할 소설 파일과 세그먼트, 결과물을 관리
├───gemini_model.py         # 🤖 Google Gemini API와의 통신을 담당
├───prompt_builder.py       # 📝 번역 프롬프트를 동적으로 생성
├───prompt_manager.py       # 📜 프롬프트 템플릿을 관리
├───prompt_template.md      # 📄 번역 요청에 사용될 프롬프트 템플릿
├───dynamic_config_builder.py # 🛠️ 동적 가이드(용어, 문체)를 구축
├───config_loader.py        # 🔑 API 키 등 환경 설정을 로드
├───requirements.txt        # libs
├───source_novel/           # 📖 번역할 원본 소설 파일
└───translated_novel/       # 📚 번역된 결과물이 저장되는 폴더
```

## 🛠️ 설치 방법

1.  **저장소 복제**:
    ```bash
    git clone https://github.com/NiceTry3675/Context-Aware-Translation.git
    cd Context-Aware-Translation
    ```

2.  **가상 환경 생성 및 활성화**:
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **필요한 패키지 설치**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **API 키 설정**:
    -   프로젝트 루트 디렉토리에 `.env` 파일을 생성합니다.
    -   파일에 다음과 같이 Google Gemini API 키를 추가합니다:
        ```
        GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
        ```

## ▶️ 사용 방법

1.  **원본 소설 준비**:
    -   번역할 소설 텍스트 파일(`*.txt`)을 `source_novel` 디렉토리에 추가합니다.

2.  **번역 실행**:
    -   `main.py`를 실행하며 번역할 파일의 경로를 인자로 전달합니다.
    ```bash
    # 예시: source_novel 폴더에 있는 my_novel.txt 파일을 번역
    python main.py "source_novel/my_novel.txt"
    ```

3.  **결과 확인**:
    -   번역이 완료되면 `translated_novel` 디렉토리에 `[원본 파일명]_translated.txt` 형식으로 결과 파일이 생성됩니다.
    -   `debug_prompts`와 `context_log` 디렉토리에서 번역 과정의 상세 로그를 확인할 수 있습니다.

## 💻 기술 스택

-   **Language**: `Python 3.9+`
-   **Core Libraries**:
    -   `google-generativeai`: Google Gemini API
    -   `python-dotenv`: 환경 변수 관리
    -   `tqdm`: 진행 상태 표시 바
-   **AI Model**: `Gemini 2.5 Flash Lite` (또는 `config_loader.py`에서 설정된 다른 모델)

---

<p align="center">
  Made with ❤️ by NiceTry3675
</p>
