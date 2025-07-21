# 🚀 배포 가이드

## 📋 배포 환경
- **프론트엔드**: Vercel
- **백엔드**: Railway
- **데이터베이스**: Railway PostgreSQL

## 🔧 1단계: 백엔드 배포 (Railway)

### 환경 변수 설정
Railway 대시보드에서 다음 환경 변수들을 설정:

```env
# Clerk 인증
CLERK_SECRET_KEY=sk_live_...  # Clerk Dashboard > API Keys
CLERK_WEBHOOK_SECRET=whsec_...  # Clerk Dashboard > Webhooks

# 관리자 비밀키 (새로 생성)
ADMIN_SECRET_KEY=your-secure-admin-secret-key

# 데이터베이스 (Railway에서 자동 설정)
DATABASE_URL=postgresql://...

# Python 런타임
PYTHON_VERSION=3.9
```

### Railway 배포 설정
1. **GitHub 연결**: Railway에서 repository 연결
2. **브랜치 설정**: `dev` 브랜치로 설정
3. **빌드 명령어**: 자동 감지 (requirements.txt 기반)
4. **시작 명령어**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

## 🔧 2단계: 데이터베이스 마이그레이션

### 방법 1: 자동 마이그레이션 (권장) ⭐
백엔드가 시작될 때 자동으로 실행됩니다. 별도 작업 불필요!

### 방법 2: Railway 대시보드에서 수동 실행
1. **Railway Dashboard** → **프로젝트** → **PostgreSQL**
2. **Data** 탭 → **Query** 섹션에서 실행:

```sql
-- 이미지 업로드를 위한 images 컬럼 추가
ALTER TABLE posts ADD COLUMN IF NOT EXISTS images JSON DEFAULT '[]';

-- 비밀글/댓글을 위한 is_private 컬럼 추가
ALTER TABLE posts ADD COLUMN IF NOT EXISTS is_private BOOLEAN DEFAULT FALSE;
ALTER TABLE comments ADD COLUMN IF NOT EXISTS is_private BOOLEAN DEFAULT FALSE;

-- 성능 최적화 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_posts_is_private ON posts(is_private);
CREATE INDEX IF NOT EXISTS idx_posts_category_created ON posts(category_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id);

-- 마이그레이션 확인 쿼리
SELECT table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_name IN ('posts', 'comments') 
AND column_name IN ('images', 'is_private')
ORDER BY table_name, column_name;
```

### 방법 3: Railway CLI 사용
```bash
# CLI 설치 및 연결
railway login
railway link
railway connect postgresql

# PostgreSQL 프롬프트에서 위 SQL 실행 후
\q
```

### 방법 4: Railway Console에서 스크립트 실행
1. **Railway Dashboard** → **Backend 서비스** → **Deploy** 탭
2. **Console** 버튼 클릭
3. 다음 명령어 실행:
```bash
python migrate_production.py
```

### 마이그레이션 확인
어떤 방법을 사용하든 다음 쿼리로 확인:
```sql
SELECT COUNT(*) FROM posts WHERE images IS NOT NULL;
SELECT COUNT(*) FROM posts WHERE is_private IS NOT NULL;
SELECT COUNT(*) FROM comments WHERE is_private IS NOT NULL;
```

## 🔧 3단계: 프론트엔드 배포 (Vercel)

### 환경 변수 설정
Vercel 대시보드에서 다음 환경 변수 설정:

```env
# API URL (Railway 백엔드 URL)
NEXT_PUBLIC_API_URL=https://your-railway-backend-url

# Clerk 인증
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...  # Clerk Dashboard > API Keys
CLERK_SECRET_KEY=sk_live_...  # 백엔드와 동일

# Clerk Domain (필요시)
NEXT_PUBLIC_CLERK_DOMAIN=your-domain.clerk.accounts.dev
```

### Vercel 배포 설정
1. **GitHub 연결**: Vercel에서 repository 연결
2. **브랜치 설정**: `dev` 브랜치로 설정  
3. **빌드 설정**:
   - Framework Preset: `Next.js`
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `.next`

## 🔧 4단계: Clerk 설정

### Webhook 설정
Clerk Dashboard > Webhooks에서:
1. **Endpoint URL**: `https://your-railway-backend-url/api/v1/webhooks/clerk`
2. **Events**: `user.created`, `user.updated`, `user.deleted`

### 도메인 설정
Clerk Dashboard > Domains에서 프로덕션 도메인 추가

## 🔧 5단계: 카테고리 초기화

백엔드 배포 완료 후, Railway 콘솔에서 실행:

```bash
python init_categories.py
```

## 🔧 6단계: 관리자 권한 설정

첫 관리자 계정 설정:
1. 애플리케이션에 가입/로그인
2. Clerk Dashboard > Users에서 해당 사용자 클릭
3. Metadata > Public metadata에 추가:
```json
{
  "role": "admin"
}
```

## ✅ 배포 완료 체크리스트

### 백엔드 (Railway)
- [ ] Railway 백엔드 배포 완료
- [ ] 환경 변수 모두 설정 (`CLERK_SECRET_KEY`, `CLERK_WEBHOOK_SECRET`, `ADMIN_SECRET_KEY`)
- [ ] 데이터베이스 마이그레이션 완료 (자동 또는 수동)
- [ ] 백엔드 로그에 "🎉 All migrations completed successfully!" 확인
- [ ] API 엔드포인트 응답 테스트 (`/api/v1/community/categories`)

### 프론트엔드 (Vercel)  
- [ ] Vercel 프론트엔드 배포 완료
- [ ] 환경 변수 설정 (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`)
- [ ] 프론트엔드-백엔드 연결 테스트 (CORS 에러 없음)

### 인증 및 권한 (Clerk)
- [ ] Clerk Webhook 설정 완료 (`user.created`, `user.updated`, `user.deleted`)
- [ ] 첫 관리자 권한 설정 완료 (publicMetadata)
- [ ] 사용자 가입/로그인 테스트 완료

### 커뮤니티 기능
- [ ] 카테고리 초기화 완료 (`python init_categories.py`)
- [ ] 공지사항 관리자 전용 글쓰기 테스트
- [ ] 이미지 업로드 테스트 완료 (10MB 제한, 다중 파일)
- [ ] 비밀글/댓글 기능 테스트 완료
- [ ] 게시글 CRUD 모든 기능 테스트

## 🔍 트러블슈팅

### 🚨 데이터베이스 마이그레이션 관련

**문제**: `relation "posts" does not exist` 
**해결**: 첫 배포 시 자동으로 테이블이 생성됩니다. 잠시 기다리세요.

**문제**: 마이그레이션이 실행되지 않음
**해결**: Railway 로그에서 "🎉 All migrations completed successfully!" 확인
```bash
# Railway Console에서 수동 실행
python migrate_production.py
```

**문제**: `column "images" already exists`
**해결**: 정상적인 메시지입니다. `IF NOT EXISTS`로 중복 방지됩니다.

### 🌐 CORS 에러

**증상**: `Access to fetch blocked by CORS policy`
**해결**: 
1. Vercel 배포 URL을 확인
2. `backend/main.py`의 `allow_origins`에 해당 URL 추가:
```python
allow_origins=[
    "http://localhost:3000",
    "https://your-vercel-app.vercel.app",  # 실제 URL로 변경
    # ...
]
```

### 📸 이미지 업로드 에러

**문제**: `File size must be less than 10MB`
**해결**: Railway에는 임시 파일 저장소 제한이 있습니다. AWS S3나 Cloudinary 연동 고려

**문제**: 이미지가 로드되지 않음
**해결**: Railway에서 정적 파일 서빙 확인
```bash
# Railway Console에서 확인
ls -la uploads/images/
```

### 🔐 Clerk 인증 에러

**문제**: `Invalid authentication credentials`  
**해결**:
1. `CLERK_SECRET_KEY` 환경 변수 확인
2. Clerk Dashboard > API Keys에서 올바른 키 복사
3. Live/Test 환경 일치 여부 확인

**문제**: Webhook 404 에러
**해결**: 
- Webhook URL: `https://your-railway-app.railway.app/api/v1/webhooks/clerk`
- `CLERK_WEBHOOK_SECRET` 환경 변수 설정

### 👑 관리자 권한 에러

**문제**: `Only admins can post in this category`
**해결**:
1. Clerk Dashboard > Users > 해당 사용자 > Metadata
2. Public metadata에 추가:
```json
{"role": "admin"}
```

### 🗄️ 데이터베이스 연결 에러

**문제**: `could not connect to server`
**해결**: Railway PostgreSQL 서비스가 시작되었는지 확인

**문제**: 환경 변수 오류
**확인 명령어**:
```bash
# Railway Console에서
echo $DATABASE_URL
echo $CLERK_SECRET_KEY
```

### 📱 프론트엔드 빌드 에러

**문제**: `NEXT_PUBLIC_API_URL is not defined`
**해결**: Vercel 환경 변수에서 `NEXT_PUBLIC_API_URL` 설정 확인

**문제**: Clerk 컴포넌트 에러  
**해결**: `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` 환경 변수 확인

### 🔧 일반적인 배포 문제

**문제**: 500 Internal Server Error
**해결**: Railway 배포 로그 확인
1. Railway Dashboard > Backend Service > Deploy > View Logs
2. 에러 메시지를 바탕으로 문제 해결

**문제**: 빈 페이지 또는 로딩 무한루프
**해결**: 브라우저 개발자 도구 > Network/Console 탭에서 API 요청 에러 확인 