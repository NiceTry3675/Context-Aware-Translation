# 1. 베이스 이미지 설정
FROM python:3.11-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 4. 의존성 설치
# 먼저 의존성 정의 파일만 복사하여 Docker의 레이어 캐싱을 활용합니다.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# 5. Create necessary directories
# Create directories for file uploads and translated outputs.
RUN mkdir -p uploads translated_novel

# 6. 애플리케이션 코드 복사
COPY . .

# 7. 포트 노출
EXPOSE 8000

# 8. 애플리케이션 실행
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]