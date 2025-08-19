# Makefile 사용 가이드

이 문서는 프로젝트의 `Makefile`에 정의된 자동화 명령어를 설명합니다. `make` 명령어는 반복적인 개발 작업을 단순화하고, 백엔드와 프론트엔드 간의 데이터 타입 일관성을 유지하기 위해 사용됩니다.

## 주요 명령어

터미널에서 `make <명령어>` 형식으로 사용합니다.

### `make help`

사용 가능한 모든 `make` 명령어를 목록과 간단한 설명과 함께 보여줍니다.

---

### `make codegen`

백엔드와 프론트엔드 간의 코드 생성을 위한 전체 파이프라인을 실행합니다. 이 명령어는 아래의 네 가지 명령어를 순서대로 모두 실행하는 것과 같습니다. **백엔드 모델 변경 후 프론트엔드 타입을 업데이트할 때 이 명령어를 사용하세요.**

- **실행 순서:** `openapi` → `schemas` → `fe-types` → `fe-schemas`

---

### `make openapi`

FastAPI 백엔드 애플리케이션에서 `openapi.json` API 명세서를 생성(또는 업데이트)합니다.

- **실행 스크립트:** `backend/scripts/export_openapi.py`

---

### `make schemas`

백엔드의 Pydantic 모델에서 `JSON Schema` 파일들을 `core/schemas/jsonschema/` 디렉토리에 생성합니다. 이 스키마들은 프론트엔드 타입 생성의 기반이 됩니다.

- **실행 스크립트:** `core/schemas/export_jsonschema.py`

---

### `make fe-types`

`openapi.json` 파일을 기반으로 프론트엔드에서 사용할 API 관련 TypeScript 타입을 생성합니다.

- **실행 스크립트:** `frontend` 디렉토리에서 `npm run codegen:api` 실행

---

### `make fe-schemas`

`core/schemas/jsonschema/` 에 있는 JSON 스키마들을 기반으로 프론트엔드에서 사용할 데이터 모델 TypeScript 타입을 생성합니다.

- **실행 스크립트:** `frontend` 디렉토리에서 `npm run codegen:schemas` 실행

---

### `make verify`

생성된 파일들(`openapi.json`, 타입 정의 등)이 최신 상태인지 확인합니다. `git diff`를 사용하여 변경 사항이 있는지 검사하며, 만약 변경된 내용이 커밋되지 않았다면 오류를 발생시킵니다. CI/CD 파이프라인에서 코드 일관성을 검증하는 데 유용합니다.

---

### `make clean`

`codegen` 파이프라인을 통해 생성되었던 모든 파일 및 디렉토리를 삭제합니다. 깨끗한 상태에서 다시 코드를 생성하고 싶을 때 사용합니다.

- **삭제 대상:**
  - `openapi.json`
  - `core/schemas/jsonschema/`
  - `frontend/src/types/schemas/`
  - `frontend/src/types/api.d.ts`
