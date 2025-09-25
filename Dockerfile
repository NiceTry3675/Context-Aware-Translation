# 1. 베이스 이미지 설정
# Use AWS's public ECR mirror to avoid Docker Hub auth/rate limits during remote builds
FROM public.ecr.aws/docker/library/python:3.11-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 4. 의존성 설치
# 먼저 의존성 정의 파일만 복사하여 Docker의 레이어 캐싱을 활용합니다.
COPY requirements.txt .
# Faster installs using uv (parallel + compiled wheels)
RUN pip install --no-cache-dir --upgrade pip uv \
    && uv pip install --system -r requirements.txt

# 4.1 Runtime packages (redis-server for local dev, curl for health checks)
RUN apt-get update \
    && apt-get install -y --no-install-recommends redis-server redis-tools ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# 5. Create necessary directories
# Create directories for file uploads and translated outputs.
RUN mkdir -p uploads translated_novel

# 6. 애플리케이션 코드 복사
COPY . .

# 7. 포트 노출
EXPOSE 8000

# 8. 엔트리포인트 스크립트 복사 및 실행 권한 부여
COPY docker-entry.sh ./
RUN chmod +x ./docker-entry.sh

# 9. 애플리케이션 실행 (마이그레이션 후 서버 시작)
CMD ["./docker-entry.sh"]
