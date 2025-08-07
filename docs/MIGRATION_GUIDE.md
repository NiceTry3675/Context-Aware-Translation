# 커뮤니티 게시판 데이터베이스 마이그레이션 가이드

## 🚨 중요 안내

커뮤니티 게시판 기능을 사용하기 위해서는 데이터베이스 스키마를 업데이트해야 합니다.

## 📋 새로 추가된 테이블

1. **post_categories** - 게시판 카테고리
2. **posts** - 게시글
3. **comments** - 댓글

## 🔧 마이그레이션 방법

### 방법 1: 자동 마이그레이션 (개발 환경)

FastAPI가 시작될 때 자동으로 새 테이블이 생성됩니다.

```bash
# 백엔드 서버 실행
uvicorn backend.main:app --reload --port 8000
```

### 방법 2: 수동 SQL 실행 (프로덕션 환경)

```sql
-- User 테이블에 role 컬럼 추가
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR DEFAULT 'user';

-- PostCategory 테이블 생성
CREATE TABLE IF NOT EXISTS post_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    display_name VARCHAR NOT NULL,
    description VARCHAR,
    is_admin_only BOOLEAN DEFAULT FALSE,
    "order" INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Post 테이블 생성
CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR NOT NULL,
    content TEXT NOT NULL,
    author_id INTEGER NOT NULL REFERENCES users(id),
    category_id INTEGER NOT NULL REFERENCES post_categories(id),
    is_pinned BOOLEAN DEFAULT FALSE,
    is_private BOOLEAN DEFAULT FALSE,
    view_count INTEGER DEFAULT 0,
    images JSON DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Comment 테이블 생성
CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    author_id INTEGER NOT NULL REFERENCES users(id),
    post_id INTEGER NOT NULL REFERENCES posts(id),
    parent_id INTEGER REFERENCES comments(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_posts_category_id ON posts(category_id);
CREATE INDEX IF NOT EXISTS idx_posts_author_id ON posts(author_id);
CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id);
CREATE INDEX IF NOT EXISTS idx_comments_author_id ON comments(author_id);
```

## 📂 카테고리 초기화

데이터베이스 마이그레이션 후 기본 카테고리를 생성해야 합니다.

```bash
# .env 파일에 ADMIN_SECRET_KEY가 설정되어 있는지 확인
python init_categories.py
```

## ✅ 확인 사항

1. **User 테이블**: `role` 컬럼이 추가되었는지 확인
2. **새 테이블**: `post_categories`, `posts`, `comments` 테이블이 생성되었는지 확인
3. **카테고리**: 기본 카테고리 4개가 생성되었는지 확인

## 🔐 관리자 설정

특정 사용자를 관리자로 설정하려면:

```sql
UPDATE users SET role = 'admin' WHERE email = 'admin@example.com';
```

관리자는 다음 권한을 가집니다:
- 공지사항 작성
- 비밀글/댓글 조회

## 📸 이미지 업로드 기능 (v1.2.0)

기존 posts 테이블에 images 필드를 추가해야 합니다:

```sql
-- 기존 posts 테이블에 images 컬럼 추가
ALTER TABLE posts ADD COLUMN IF NOT EXISTS images JSON DEFAULT '[]';
```

### 업로드 디렉토리 생성

```bash
mkdir -p uploads/images
```

이미지 파일들은 `uploads/images/` 디렉토리에 저장되며, `/static/images/` URL로 접근할 수 있습니다.
- 모든 게시글/댓글 수정 및 삭제
- 게시글 상단 고정 