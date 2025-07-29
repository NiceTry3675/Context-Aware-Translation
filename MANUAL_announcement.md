# 실시간 공지 전송 매뉴얼

이 문서는 관리자가 모든 사용자에게 실시간으로 공지를 보내는 방법을 설명합니다.

**요구사항:**
- PowerShell 터미널 사용 (Windows) 또는 curl 명령어 (Linux/Mac)
- 올바른 백엔드 URL과 관리자 시크릿 키
- UTF-8 인코딩 지원으로 한글, 이모지 사용 가능

---

## 🌐 환경별 설정

### 로컬 개발 환경
- **URL**: `http://localhost:8000`
- **시크릿 키**: `.env` 파일의 `DEV_SECRET_KEY` 값 사용

### 프로덕션 환경 (Railway)
- **URL**: `https://catrans.up.railway.app`
- **시크릿 키**: `.env` 파일의 `PROD_SECRET_KEY` 값 사용

---

## 📤 1. 새로운 공지 생성 및 전송

아래 명령어를 사용하여 새로운 공지를 생성하고 모든 클라이언트에 즉시 전송합니다. 
이전 공지는 자동으로 비활성화되고 새로운 공지가 활성화됩니다.

### 🏆 권장 방법 (Python 스크립트)

**한글 공지를 완벽하게 보내는 가장 좋은 방법:**

**1. 빠른 전송 (사전 정의된 메시지):**
```bash
python send_announcement.py quick
```

**2. 커스텀 메시지 전송:**
```bash
python send_announcement.py
```

**3. 사전 정의된 메시지들:**
- `1.` 📢 시스템 점검 안내: 오늘 밤 12시부터 서비스가 일시 중단됩니다.
- `2.` 🎉 새로운 번역 모델이 추가되었습니다! Gemini 2.5 Flash를 체험해보세요.
- `3.` ⚠️ 긴급: 서버 부하로 인해 일시적으로 번역 속도가 느려질 수 있습니다.
- `4.` ✅ 시스템 점검 완료: 모든 서비스가 정상적으로 복구되었습니다.
- `5.` 🚀 서비스 업데이트: 번역 품질이 대폭 개선되었습니다!

### 💡 대안 방법 (PowerShell + JSON 파일)

PowerShell을 사용해야 하는 경우:

1. **announcement.json 파일 생성:**
```json
{
    "message": "📢 한글 공지: 원하는 메시지를 여기에 입력하세요! 🚀✅",
    "is_active": true
}
```

2. **PowerShell 명령어 실행:**
```powershell
# 로컬 개발환경
$headers = @{'Content-Type'='application/json; charset=utf-8'; 'x-admin-secret'=$env:DEV_SECRET_KEY}
$jsonContent = Get-Content -Path "announcement.json" -Encoding UTF8 -Raw
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/announcements" -Method POST -Headers $headers -Body $jsonContent

# 프로덕션 환경
$headers = @{'Content-Type'='application/json; charset=utf-8'; 'x-admin-secret'=$env:PROD_SECRET_KEY}
$jsonContent = Get-Content -Path "announcement.json" -Encoding UTF8 -Raw
Invoke-RestMethod -Uri "https://catrans.up.railway.app/api/v1/admin/announcements" -Method POST -Headers $headers -Body $jsonContent
```

### PowerShell (한 줄 명령어 - 영어만)

**로컬 개발환경:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/announcements" -Method POST -Headers @{'Content-Type'='application/json; charset=utf-8'; 'x-admin-secret'=$env:DEV_SECRET_KEY} -Body '{"message": "🚀 System Update: Translation service has been improved! ✅", "is_active": true}'
```

**프로덕션 환경:**
```powershell
Invoke-RestMethod -Uri "https://catrans.up.railway.app/api/v1/admin/announcements" -Method POST -Headers @{'Content-Type'='application/json; charset=utf-8'; 'x-admin-secret'=$env:PROD_SECRET_KEY} -Body '{"message": "🚀 시스템 업데이트: 번역 서비스가 개선되었습니다! ✅", "is_active": true}'
```

### cURL (Linux/Mac)

**로컬 개발환경:**
```bash
curl -X POST "http://localhost:8000/api/v1/admin/announcements" \
  -H "Content-Type: application/json; charset=utf-8" \
  -H "x-admin-secret: $DEV_SECRET_KEY" \
  -d '{"message": "🚀 시스템 업데이트: 번역 서비스가 개선되었습니다! ✅", "is_active": true}'
```

**프로덕션 환경:**
```bash
curl -X POST "https://catrans.up.railway.app/api/v1/admin/announcements" \
  -H "Content-Type: application/json; charset=utf-8" \
  -H "x-admin-secret: $PROD_SECRET_KEY" \
  -d '{"message": "🚀 시스템 업데이트: 번역 서비스가 개선되었습니다! ✅", "is_active": true}'
```

### 📝 메시지 예시

```json
{"message": "📢 공지: 오늘 밤 12시부터 2시간 동안 시스템 점검이 있습니다.", "is_active": true}
{"message": "🎉 새로운 번역 모델이 추가되었습니다! Gemini 2.5 Flash를 체험해보세요.", "is_active": true}
{"message": "⚠️ 긴급: 서버 부하로 인해 일시적으로 번역 속도가 느려질 수 있습니다.", "is_active": true}
{"message": "✅ 시스템 점검 완료: 모든 서비스가 정상적으로 복구되었습니다.", "is_active": true}
```

---

## 🔇 2. 공지 비활성화

### 🏆 권장 방법 (Python 스크립트)

**Python 스크립트 사용:**
```bash
python send_announcement.py
# 메뉴에서 선택:
# 2. 특정 공지 비활성화 (ID 필요)
# 3. 모든 공지 비활성화 (권장)
```

### 💡 대안 방법 (직접 API 호출)

#### A. 모든 공지 비활성화 (권장)

**PowerShell:**
```powershell
# 로컬 개발환경
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/announcements/deactivate-all" -Method PUT -Headers @{'x-admin-secret'=$env:DEV_SECRET_KEY}

# 프로덕션 환경
Invoke-RestMethod -Uri "https://catrans.up.railway.app/api/v1/admin/announcements/deactivate-all" -Method PUT -Headers @{'x-admin-secret'=$env:PROD_SECRET_KEY}
```

**cURL:**
```bash
# 로컬 개발환경
curl -X PUT "http://localhost:8000/api/v1/admin/announcements/deactivate-all" \
  -H "x-admin-secret: $DEV_SECRET_KEY"

# 프로덕션 환경
curl -X PUT "https://catrans.up.railway.app/api/v1/admin/announcements/deactivate-all" \
  -H "x-admin-secret: $PROD_SECRET_KEY"
```

#### B. 특정 공지 비활성화

특정 공지의 `id`가 필요합니다. (id는 생성 명령어 실행 시 반환 값에서 확인할 수 있습니다.)

**PowerShell:**
```powershell
# 로컬 개발환경
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/announcements/{ID}/deactivate" -Method PUT -Headers @{'x-admin-secret'=$env:DEV_SECRET_KEY}

# 프로덕션 환경
Invoke-RestMethod -Uri "https://catrans.up.railway.app/api/v1/admin/announcements/{ID}/deactivate" -Method PUT -Headers @{'x-admin-secret'=$env:PROD_SECRET_KEY}
```

**cURL:**
```bash
# 로컬 개발환경
curl -X PUT "http://localhost:8000/api/v1/admin/announcements/{ID}/deactivate" \
  -H "x-admin-secret: $DEV_SECRET_KEY"

# 프로덕션 환경
curl -X PUT "https://catrans.up.railway.app/api/v1/admin/announcements/{ID}/deactivate" \
  -H "x-admin-secret: $PROD_SECRET_KEY"
```

**예시 (ID가 25인 공지 비활성화):**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/announcements/25/deactivate" -Method PUT -Headers @{'x-admin-secret'=$env:DEV_SECRET_KEY}
```

---

## 📡 3. 실시간 공지 스트림 확인

사용자들이 받는 실시간 공지 스트림을 확인할 수 있습니다.

### cURL로 SSE 스트림 확인

**로컬 개발환경:**
```bash
curl -N "http://localhost:8000/api/v1/announcements/stream"
```

**프로덕션 환경:**
```bash
curl -N "https://catrans.up.railway.app/api/v1/announcements/stream"
```

---

## 🔧 4. 문제 해결 가이드

### 한글 깨짐 문제
✅ **해결됨**: UTF-8 인코딩이 적용되어 한글과 이모지가 정상적으로 표시됩니다.

### 일반적인 오류 해결

**1. 403 Forbidden - Invalid admin secret key**
```
해결: x-admin-secret 헤더의 값이 올바른지 확인하세요.
- .env 파일의 DEV_SECRET_KEY 또는 PROD_SECRET_KEY 값을 확인하세요.
```

**2. 404 Not Found**
```
해결: URL이 올바른지 확인하세요.
- 로컬: http://localhost:8000
- 프로덕션: https://catrans.up.railway.app
```

**3. Connection Refused**
```
해결: 서버가 실행 중인지 확인하세요.
- 로컬: netstat -an | findstr :8000
```

**4. PowerShell 긴 명령어 문제**
```
해결: 변수를 사용하여 명령어를 분할하세요.
$headers = @{'Content-Type'='application/json; charset=utf-8'; 'x-admin-secret'=$env:DEV_SECRET_KEY}
$body = '{"message": "공지 내용", "is_active": true}'
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/announcements" -Method POST -Headers $headers -Body $body
```

**5. PowerShell 한글 입력 문제**
```
❌ 문제: PowerShell에서 한글 입력 시 데이터베이스에 ???로 저장됨
✅ 해결: Python 스크립트 사용 권장

Python 스크립트 사용법:
python send_announcement.py quick     # 빠른 전송
python send_announcement.py          # 커스텀 메시지

대안 - JSON 파일 사용:
1. announcement.json 파일 생성 (UTF-8 인코딩)
2. PowerShell로 파일 읽기 (여전히 불완전할 수 있음)
```

**6. PowerShell 한글 표시 문제**
```
❌ 문제: PowerShell 응답에서 한글이 ???로 표시됨
⚠️ 주의: 이는 PowerShell 표시 문제이며, 실제 서버 저장에도 영향을 줄 수 있음

✅ 완전한 해결책: Python 스크립트 사용
- 한글 입력/출력 모두 완벽 지원
- UTF-8 인코딩 보장
- 실시간 검증 기능 내장
```

---

## 🎯 5. 성공적인 응답 예시

**공지 생성 성공:**
```json
{
  "id": 25,
  "message": "🚀 시스템 업데이트: 번역 서비스가 개선되었습니다! ✅",
  "is_active": true,
  "created_at": "2025-07-13T10:36:13"
}
```

**공지 비활성화 성공:**
```json
{
  "id": 25,
  "message": "🚀 시스템 업데이트: 번역 서비스가 개선되었습니다! ✅",
  "is_active": false,
  "created_at": "2025-07-13T10:36:13"
}
```

---

## 📋 6. 주요 참고사항

- **UTF-8 인코딩**: 한글, 중국어, 일본어, 이모지 모두 지원
- **실시간 전송**: SSE(Server-Sent Events)를 통해 즉시 모든 클라이언트에 전달
- **자동 비활성화**: 새 공지 생성 시 이전 공지는 자동으로 비활성화
- **실시간 업데이트**: 새로고침 없이 공지가 나타나고 사라짐
- **자동 재연결**: 연결이 끊어져도 자동으로 재연결 시도
- **보안**: 관리자 시크릿 키를 통한 인증 필요
- **브라우저 호환성**: 모든 모던 브라우저에서 SSE 지원

## 🚀 7. 새로운 실시간 기능

### ✨ **즉시 반영되는 기능들**
- **공지 생성**: 새 공지가 생성되면 모든 사용자에게 즉시 표시
- **공지 비활성화**: 공지를 비활성화하면 모든 사용자 화면에서 즉시 사라짐
- **모든 공지 비활성화**: 한 번에 모든 활성 공지를 비활성화 가능
- **연결 상태 표시**: 개발 모드에서 실시간 연결 상태 확인 가능
- **자동 재연결**: 네트워크 문제 시 자동으로 재연결 시도

### 🔧 **개발자 모드 기능**
개발 환경에서는 화면 우상단에 연결 상태가 표시됩니다:
- 🟢 **공지 연결됨**: 정상 연결 상태
- 🟡 **연결 중...**: 연결 시도 중
- 🔴 **연결 끊김**: 연결 실패 (클릭하여 수동 재연결)

---

**마지막 업데이트**: 2025-07-13 (UTF-8 인코딩 지원 및 dumps_kwargs 오류 해결)
