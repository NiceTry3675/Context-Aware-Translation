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

Railway 배포 후 PostgreSQL 콘솔에서 실행:

```sql
-- 기존 posts 테이블에 images 컬럼 추가 (없는 경우만)
ALTER TABLE posts ADD COLUMN IF NOT EXISTS images JSON DEFAULT '[]';

-- 기존 posts와 comments 테이블에 is_private 컬럼 추가 (없는 경우만)
ALTER TABLE posts ADD COLUMN IF NOT EXISTS is_private BOOLEAN DEFAULT FALSE;
ALTER TABLE comments ADD COLUMN IF NOT EXISTS is_private BOOLEAN DEFAULT FALSE;
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

- [ ] Railway 백엔드 배포 완료
- [ ] 환경 변수 모두 설정
- [ ] 데이터베이스 마이그레이션 완료
- [ ] Vercel 프론트엔드 배포 완료
- [ ] Clerk Webhook 설정 완료
- [ ] 카테고리 초기화 완료
- [ ] 관리자 권한 설정 완료
- [ ] 이미지 업로드 테스트 완료
- [ ] 커뮤니티 기능 테스트 완료

## 🔍 트러블슈팅

### CORS 에러
프론트엔드 URL을 `backend/main.py`의 `allow_origins`에 추가

### 이미지 업로드 에러  
Railway에서 `uploads/images` 디렉토리 생성 확인

### Clerk 인증 에러
환경 변수와 Webhook URL 확인

### 데이터베이스 에러
마이그레이션 SQL 실행 여부 확인 